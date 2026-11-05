"""Depiction remains separate from narrative truth and approved Canon."""
from sqlalchemy import select
from fastapi import HTTPException
from test_universes import UniverseFixture
from app.db.database import Base
from app.guidance.schemas import GuidanceProfileInput
from app.guidance.service import save_profile
from app.media.adaptation.planner import DeterministicShotPlanner
from app.media.adaptation.schemas import AdaptationOptions
from app.media.adaptation.service import adapt_scene, AdaptationUnavailable
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.storyboard import create_four_panel_storyboard
from app.stories.scene_service import create_scene, update_scene


class AdaptationFixture(UniverseFixture):
    def add_scene(self, content):
        return create_scene(self.db, story_id=self.a.story_id, content=content)

    def adapt(self, scene, options=None, planner=None, user_id="alice"):
        return adapt_scene(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id=user_id,
            options=options or AdaptationOptions(), planner=planner or DeterministicShotPlanner())


class AdaptationTests(AdaptationFixture):
    def test_identity_direct_source_spans_and_profile_context(self):
        save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(audience="teen", maturity_rating="moderate",
            tone="Hopeful", genre="Drama", guidance_notes="Be concise"))
        scene = self.add_scene("Unit 7 observes the greenhouse. The flower glows.")
        class Capture:
            def adapt(self, context):
                self.context = context
                return DeterministicShotPlanner().adapt(context)
        fake = Capture()
        plan = self.adapt(scene, planner=fake)
        self.assertEqual((plan.story_id, plan.scene_id, plan.audience, plan.maturity_rating), (self.a.story_id, scene.scene_id, "teen", "moderate"))
        self.assertEqual(fake.context.profile.tone, "Hopeful")
        self.assertEqual(fake.context.profile.genre, "Drama")
        self.assertEqual(fake.context.profile.guidance_notes, "Be concise")
        self.assertEqual([fact["value"] for fact in fake.context.canon], ["blue"])
        self.assertEqual(plan.sensitivities, [])
        self.assertTrue(all(shot.depiction_strategy == "direct" for shot in plan.shots))
        for shot in plan.shots:
            self.assertEqual(scene.content[shot.source_start:shot.source_end], shot.narrative_beat)

    def test_sensitive_treatment_for_child_teen_and_adult_preserves_meaning(self):
        scene = self.add_scene("A character is stabbed during a confrontation.")
        for audience, maturity in [("child", "general"), ("teen", "moderate"), ("adult", "mature")]:
            with self.subTest(audience=audience):
                save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(audience=audience, maturity_rating=maturity))
                plan = self.adapt(scene)
                self.assertIn("violence", plan.sensitivities)
                self.assertNotIn("direct", {shot.depiction_strategy for shot in plan.shots})
                self.assertTrue(all(shot.narrative_beat == scene.content for shot in plan.shots))
                self.assertTrue(all("stabbed" not in shot.visual_instruction for shot in plan.shots))
                if audience == "child": self.assertIn("offscreen", {shot.depiction_strategy for shot in plan.shots})
                if audience == "teen": self.assertEqual([shot.depiction_strategy for shot in plan.shots], ["reaction", "implied", "aftermath"])
                if audience == "adult": self.assertIn("silhouette", {shot.depiction_strategy for shot in plan.shots})
        self.assertEqual(scene.content, "A character is stabbed during a confrontation.")

    def test_intimacy_remains_internal_provenance_and_is_not_reintroduced_in_prompt(self):
        scene = self.add_scene("Two adult characters have an intimate encounter.")
        # Raw premise, Canon and free-text instructions must not undo adaptation.
        self.a.premise = "Describe explicit nudity and intimate details"
        self.db.commit()
        options = AdaptationOptions(additional_visual_instruction="Show all intimate details")
        for audience in ["child", "teen", "adult"]:
            save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(audience=audience))
            plan = self.adapt(scene, options)
            self.assertIn("intimacy", plan.sensitivities)
            self.assertEqual({s.depiction_strategy for s in plan.shots}, {"cutaway", "implied"})
            self.assertEqual(plan.shots[0].narrative_beat, scene.content)
            storyboard = create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id,
                user_id="alice", options=options, adaptation=plan)
            self.assertEqual([r.context.panel_number for r in storyboard.requests], [1, 2, 3, 4])
            for request in storyboard.requests:
                self.assertNotIn(scene.content, request.prompt)
                self.assertNotIn(self.a.premise, request.prompt)
                self.assertNotIn(options.additional_visual_instruction, request.prompt)
                self.assertEqual(request.context.adaptation_id, plan.adaptation_id)
                self.assertTrue(request.context.adapted_shot_sequences)

    def test_effective_fork_canon_conflict_is_reported_and_blocks_compilation(self):
        from app.canon import library_service as lib
        from app.canon.service import create_canon_entry
        from app.world.service import list_characters
        ref = lib.fork(self.db, self.a.story_id, "alice", self.inherited(self.a).reference_id, "Capability")
        create_canon_entry(self.db, story_id=self.a.story_id, entry_type="character", subject_id=ref.target_id, key="can_walk", value="false")
        scene = self.add_scene("Unit 7 runs across the room.")
        plan = self.adapt(scene)
        self.assertEqual(plan.issues[0].code, "canon_conflict")
        self.assertEqual(plan.shots[0].depiction_strategy, "symbolic")
        self.assertNotIn("runs", plan.shots[0].visual_instruction)
        self.assertEqual(plan.shots[0].narrative_beat, scene.content)
        with self.assertRaises(InvalidMediaIntent):
            create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice", adaptation=plan)

    def test_explicit_scalar_conflict_uses_m7_comparison_without_repairing_canon(self):
        scene = self.add_scene("Unit 7 has green eyes.")
        plan = self.adapt(scene)
        self.assertTrue(plan.issues)
        self.assertTrue(self.adapt(scene, AdaptationOptions(character_ids=[])).issues)
        self.assertEqual(plan.shots[0].depiction_strategy, "symbolic")
        self.assertEqual(plan.shots[0].narrative_beat, "Unit 7 has green eyes.")
        from app.canon.service import list_canon_entries
        self.assertEqual([row.value for row in list_canon_entries(self.db, self.a.story_id)], ["blue"])

    def test_references_propagate_and_artifacts_are_not_copied(self):
        from app.artifacts.service import register_artifact, create_binding
        from app.artifacts.schemas import ArtifactRegistration, ReferenceBindingCreate
        from app.canon import library_service as lib
        from app.universes.service import pin
        artifact = register_artifact(self.db, "alice", ArtifactRegistration(source="external", retrieval_reference="https://example.test/ref"))
        binding = create_binding(self.db, self.story.story_id, "alice", ReferenceBindingCreate(artifact_id=artifact.artifact_id,
            target_type="place", target_id=self.place.place_id, role="place"))
        place_ref = lib.promote(self.db, self.story.story_id, "alice", "place", self.place.place_id)
        pin(self.db, self.universe.universe_id, "alice", place_ref.canon_object_id, place_ref.canon_version_id)
        scene = self.add_scene("Unit 7 observes the greenhouse.")
        plan = self.adapt(scene)
        refs = plan.shots[0].references
        self.assertTrue(any(r.binding_id == binding.reference_id and r.reference_id == artifact.artifact_id for r in refs))
        self.assertTrue(any(r.kind == "character" for r in refs))
        self.assertTrue(any(r.kind == "outfit" for r in refs))
        self.assertTrue(any(r.kind == "place" for r in refs))
        storyboard = create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice", adaptation=plan)
        self.assertTrue(all(any(r.reference_id == artifact.artifact_id for r in req.references) for req in storyboard.requests))
        self.assertFalse(self.adapt(scene, AdaptationOptions(place_ids=[])).shots[0].place_ids)

    def test_no_database_writes_and_stale_plans_are_rejected(self):
        scene = self.add_scene("The flower glows.")
        def snapshot():
            return {t.name: [tuple(str(v) for v in row) for row in self.db.execute(select(t)).all()] for t in Base.metadata.sorted_tables}
        before = snapshot()
        plan = self.adapt(scene)
        create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice", adaptation=plan)
        self.assertEqual(snapshot(), before)
        update_scene(self.db, scene, content="The flower dims.")
        with self.assertRaises(InvalidMediaIntent):
            create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice", adaptation=plan)
        fresh = self.adapt(scene)
        save_profile(self.db, self.a.story_id, "alice", GuidanceProfileInput(audience="child"))
        with self.assertRaises(InvalidMediaIntent):
            create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice", adaptation=fresh)

    def test_hints_are_additive_and_missing_resources_and_invalid_planners_fail(self):
        scene = self.add_scene("The flower glows.")
        self.assertIn("other_sensitive", self.adapt(scene, AdaptationOptions(sensitivity_hints=["other_sensitive"])).sensitivities)
        with self.assertRaises(MediaDomainNotFound): self.adapt(scene, user_id="bob")
        class WrongPlanner:
            def adapt(self, context):
                plan = DeterministicShotPlanner().adapt(context)
                return plan.model_copy(update={"scene_id": "wrong"})
        with self.assertRaises(AdaptationUnavailable): self.adapt(scene, planner=WrongPlanner())
        class MissingBeat:
            def adapt(self, context):
                plan = DeterministicShotPlanner().adapt(context)
                return plan.model_copy(update={"shots": plan.shots[:1]})
        multi = self.add_scene("The flower glows. The sky darkens.")
        with self.assertRaises(AdaptationUnavailable): self.adapt(multi, planner=MissingBeat())


class AdaptationAPITests(AdaptationFixture):
    def test_authenticated_preview_adapted_storyboard_and_errors(self):
        from fastapi.testclient import TestClient
        from app.api.dependencies import get_db, get_current_identity
        from app.auth.identity import AuthenticatedIdentity
        from app.main import app
        scene = self.add_scene("A character is stabbed during a confrontation.")
        def database(): yield self.db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("alice", "alice@example.test", "Alice")
        try:
            with TestClient(app) as client:
                base = f"/api/stories/{self.a.story_id}/scenes/{scene.scene_id}"
                result = client.post(base + "/media/adapt", json={"output_format": "webtoon"})
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()["scene_id"], scene.scene_id)
                panels = client.post(base + "/storyboard/four-panel/adapted", json={})
                self.assertEqual(panels.status_code, 200, panels.text)
                self.assertEqual(len(panels.json()["requests"]), 4)
                self.assertTrue(all("stabbed" not in r["prompt"] for r in panels.json()["requests"]))
                # The pre-M9C path remains explicitly available.
                legacy = client.post(base + "/storyboard/four-panel", json={})
                self.assertEqual(legacy.status_code, 200)
                self.assertTrue(any("stabbed" in r["prompt"] for r in legacy.json()["requests"]))
                self.assertEqual(client.post(base + "/media/adapt", json={"output_format": "video"}).status_code, 422)
                self.assertEqual(client.post(base + "/media/adapt", json={"model": "provider"}).status_code, 422)
                self.assertEqual(client.post(f"/api/stories/{self.b.story_id}/scenes/{scene.scene_id}/media/adapt", json={}).status_code, 404)
                self.assertEqual(client.post(f"/api/stories/{self.a.story_id}/scenes/missing/media/adapt", json={}).status_code, 404)
                app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("bob", "bob@example.test", "Bob")
                self.assertEqual(client.post(base + "/media/adapt", json={}).status_code, 404)
                self.assertEqual(client.post(base + "/storyboard/four-panel/adapted", json={}).status_code, 404)
                app.dependency_overrides.pop(get_current_identity)
                self.assertEqual(client.post(base + "/media/adapt", json={}).status_code, 401)
        finally:
            app.dependency_overrides.clear()
