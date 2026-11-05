"""Provider-free advisory planning, bounded context, and explicit user control."""
import asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from test_universes import UniverseFixture
from app.db.database import Base
from app.db.models import NarrativeGuidanceProfile, CanonObjectVersion
from app.guidance.generator import DeterministicSuggestionGenerator
from app.guidance.schemas import GuidanceProfileInput, Suggestion, SuggestionOptions
from app.guidance import service
from app.canon import library_service as library
from app.stories.scene_service import create_scene, update_scene


class CaptureGenerator:
    def __init__(self):
        self.context = None
    async def suggest(self, context, *, count):
        self.context = context
        return await DeterministicSuggestionGenerator().suggest(context, count=count)


class GuidanceTests(UniverseFixture):
    def suggest(self, story=None, options=None, generator=None):
        return asyncio.run(service.suggest_next_scene(self.db, (story or self.a).story_id, "alice",
            options or SuggestionOptions(), generator or DeterministicSuggestionGenerator()))

    def test_profile_defaults_roundtrip_compatibility_and_feedback_validation(self):
        profile = service.get_profile(self.db, self.a.story_id, "alice")
        self.assertEqual((profile.audience, profile.maturity_rating), ("adult", "general"))
        self.assertIsNone(self.db.get(NarrativeGuidanceProfile, self.a.story_id))
        saved = service.save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(
            audience="teen", maturity_rating="moderate", tone="Reflective", genre="Mystery", guidance_notes="Keep questions open",
            average_rating=4.2, rating_count=5, feedback_tags=["suspense"]))
        self.assertEqual(saved.rating_count, 5)
        self.assertEqual(service.get_profile(self.db, self.a.story_id, "alice").audience, "teen")
        for values in [{"audience": "baby"}, {"maturity_rating": "R"}, {"audience": "child", "maturity_rating": "mature"},
                       {"audience": "teen", "maturity_rating": "mature"}, {"rating_count": -1}, {"average_rating": 6, "rating_count": 1},
                       {"average_rating": 4}, {"rating_count": 1}, {"average_rating": float("nan"), "rating_count": 1}]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                GuidanceProfileInput(**values)

    def test_context_uses_effective_universe_canon_and_bounded_edited_recent_scenes(self):
        self.a.premise = "A journey through the garden"
        self.a.objective = "Protect the flower"
        self.db.commit()
        for i in range(7):
            scene = create_scene(self.db, story_id=self.a.story_id, title=str(i), content=f"Scene {i} content")
        update_scene(self.db, scene, content="Edited latest content" + "x" * 5000)
        fake = CaptureGenerator()
        self.suggest(generator=fake)
        ctx = fake.context
        self.assertEqual(ctx.premise, self.a.premise)
        self.assertEqual(ctx.objective, self.a.objective)
        self.assertEqual([s["sequence_number"] for s in ctx.recent_scenes], [4, 5, 6, 7])
        self.assertTrue(ctx.recent_scenes[-1]["content"].startswith("Edited latest"))
        self.assertTrue(ctx.recent_scenes[-1]["truncated"])
        self.assertEqual(len(ctx.recent_scenes[-1]["content"]), 4000)
        self.assertEqual(ctx.universe["universe_id"], self.universe.universe_id)
        self.assertEqual([fact["value"] for fact in ctx.canon], ["blue"])
        self.assertIsNone(ctx.feedback)
        self.assertEqual(ctx.profile.maturity_rating, "general")
        self.assertTrue(any("cannot override" in rule for rule in ctx.constraints))
        self.suggest(options=SuggestionOptions(recent_scene_count=2), generator=fake)
        self.assertEqual(len(fake.context.recent_scenes), 2)

    def test_story_forked_canon_precedes_universe_and_profile_feedback_is_passed(self):
        ref = library.fork(self.db, self.b.story_id, "alice", self.inherited(self.b).reference_id, "New continuity")
        candidate = self.propose(self.b, "green")
        from app.canon.candidate_service import approve_candidate
        from app.canon.candidate_schemas import CandidateApproval
        approve_candidate(self.db, story_id=self.b.story_id, user_id="alice", candidate_id=candidate.canon_candidate_id,
            approval=CandidateApproval(replace_conflicts=True))
        service.save_profile(self.db, self.b.story_id, "alice", GuidanceProfileInput(audience="child", maturity_rating="mild",
            average_rating=4, rating_count=2, feedback_tags=["friendship"]))
        fake = CaptureGenerator()
        result = self.suggest(story=self.b, generator=fake)
        self.assertEqual([fact["value"] for fact in fake.context.canon], ["green"])
        self.assertEqual(fake.context.canon[0]["canon_version_id"], ref.canon_version_id)
        self.assertEqual(fake.context.profile.audience, "child")
        self.assertEqual(fake.context.feedback["tags"], ["friendship"])
        self.assertIn("simple words", result.suggestions[0].text)

    def test_counts_distinctness_length_and_audience_specific_fallback(self):
        for audience in ["child", "teen", "adult"]:
            service.save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(audience=audience))
            for count in range(1, 6):
                response = self.suggest(options=SuggestionOptions(count=count))
                self.assertEqual(len(response.suggestions), count)
                self.assertEqual(len({s.text for s in response.suggestions}), count)
                self.assertLessEqual(sum(len((s.title + " " + s.text).split()) for s in response.suggestions), 200)
        for values in [{"count": 0}, {"count": 6}, {"recent_scene_count": 0}, {"recent_scene_count": 6}, {"model": "provider"}]:
            with self.assertRaises(ValidationError): SuggestionOptions(**values)

    def test_suggestions_and_profile_read_do_not_mutate_any_persisted_domain(self):
        def snapshot():
            return {table.name: [tuple(str(v) for v in row) for row in self.db.execute(select(table)).all()] for table in Base.metadata.sorted_tables}
        before = snapshot()
        self.suggest()
        self.suggest(story=self.story)
        service.get_profile(self.db, self.a.story_id, "alice")
        self.assertEqual(snapshot(), before)

    def test_invalid_generator_outputs_and_failures_are_clear(self):
        class InvalidGenerator:
            async def suggest(self, context, *, count):
                return [Suggestion(id="1", title="Same", text="Same thought")] * count
        with self.assertRaises(HTTPException) as error:
            self.suggest(generator=InvalidGenerator())
        self.assertEqual(error.exception.status_code, 502)
        class ExcessiveGenerator:
            async def suggest(self, context, *, count):
                return [Suggestion(id=str(i), title="Too long", text=("word " * 100) + str(i)) for i in range(count)]
        with self.assertRaises(HTTPException): self.suggest(generator=ExcessiveGenerator())
        class FailingGenerator:
            async def suggest(self, context, *, count): raise RuntimeError("Provider unavailable")
        with self.assertRaises(HTTPException): self.suggest(generator=FailingGenerator())


class GuidanceAPITests(UniverseFixture):
    def test_profile_suggestions_validation_and_ownership(self):
        from fastapi.testclient import TestClient
        from app.api.dependencies import get_db, get_current_identity
        from app.auth.identity import AuthenticatedIdentity
        from app.guidance.generator import get_suggestion_generator
        from app.main import app
        def database(): yield self.db
        fake = CaptureGenerator()
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("alice", "alice@example.test", "Alice")
        app.dependency_overrides[get_suggestion_generator] = lambda: fake
        try:
            with TestClient(app) as client:
                base = f"/api/stories/{self.a.story_id}/guidance"
                self.assertEqual(client.get(base + "/profile").json()["maturity_rating"], "general")
                saved = client.put(base + "/profile", json={"audience": "teen", "maturity_rating": "mild"})
                self.assertEqual(saved.status_code, 200, saved.text)
                response = client.post(base + "/next-scene", json={"count": 2})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()["suggestions"]), 2)
                self.assertEqual(fake.context.profile.audience, "teen")
                self.assertEqual(client.post(base + "/next-scene").status_code, 200)
                self.assertEqual(client.post(base + "/next-scene", json={"count": 6}).status_code, 422)
                self.assertEqual(client.put(base + "/profile", json={"audience": "child", "maturity_rating": "mature"}).status_code, 422)
                app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("bob", "bob@example.test", "Bob")
                self.assertEqual(client.get(base + "/profile").status_code, 404)
                self.assertEqual(client.put(base + "/profile", json={}).status_code, 404)
                self.assertEqual(client.post(base + "/next-scene", json={}).status_code, 404)
                app.dependency_overrides.pop(get_current_identity)
                self.assertEqual(client.post(base + "/next-scene", json={}).status_code, 401)
        finally:
            app.dependency_overrides.clear()
