"""Universe inheritance is read-only; explicit Story forks isolate divergence."""
from fastapi import HTTPException
from sqlalchemy import select, func
from test_media import MediaFixture
from app.db.models import Character, CanonEntry, CanonObjectVersion, StoryCanonReference, UniverseCanonReference, Universe
from app.canon import library_service as library
from app.canon.candidate_service import propose_candidate, approve_candidate, continuity_report
from app.canon.candidate_schemas import ManualCandidate, CandidateApproval
from app.canon.service import create_canon_entry, list_canon_entries
from app.stories.service import create_story
from app.universes import service
from app.world.service import list_characters, list_places, update_character


class UniverseFixture(MediaFixture):
    def setUp(self):
        super().setUp()
        create_canon_entry(self.db, story_id=self.story.story_id, entry_type="character", subject_id=self.character.character_id,
            key="eye_color", value="blue")
        self.source = library.promote(self.db, self.story.story_id, "alice", "character", self.character.character_id)
        self.universe = service.create_universe(self.db, "alice", name="The garden", description="A world beyond one Story")
        self.pin = service.pin(self.db, self.universe.universe_id, "alice", self.source.canon_object_id, self.source.canon_version_id)
        self.a = create_story(self.db, "alice", title="Story A")
        self.b = create_story(self.db, "alice", title="Story B")
        for row in (self.a, self.b):
            service.attach_story(self.db, self.universe.universe_id, row.story_id, "alice")

    def inherited(self, story):
        return next(ref for ref in library.references(self.db, story.story_id) if ref.canon_object_id == self.source.canon_object_id)

    def propose(self, story, value, evidence="Author choice"):
        ref = self.inherited(story)
        return propose_candidate(self.db, story_id=story.story_id, user_id="alice", proposal=ManualCandidate(
            type="character", subject_id=ref.target_id, key="eye_color", value=value, evidence=evidence))


class UniverseTests(UniverseFixture):
    def test_two_stories_inherit_without_copying_and_standalone_is_unchanged(self):
        self.assertEqual(library.references(self.db, self.a.story_id)[0].canon_version_id, self.source.canon_version_id)
        self.assertEqual(self.inherited(self.b).canon_version_id, self.source.canon_version_id)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Character).where(Character.story_id == self.a.story_id)), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StoryCanonReference).where(StoryCanonReference.story_id == self.a.story_id)), 0)
        self.assertEqual(list_characters(self.db, self.a.story_id)[0].name, self.character.name)
        self.assertEqual(list_characters(self.db, self.story.story_id)[0].character_id, self.character.character_id)
        self.assertEqual(len(service.list_members(self.db, self.universe.universe_id, "alice")), 2)
        self.assertEqual([r.value for r in list_canon_entries(self.db, self.a.story_id)], ["blue"])

    def test_m7_classification_requires_fork_and_divergence_is_isolated(self):
        candidate = self.propose(self.b, "green")
        original_ref = self.inherited(self.b)
        stable_id = original_ref.target_id
        self.assertEqual(candidate.classification, "conflict")
        with self.assertRaises(HTTPException) as error:
            approve_candidate(self.db, story_id=self.b.story_id, candidate_id=candidate.canon_candidate_id,
                user_id="alice", approval=CandidateApproval(replace_conflicts=True))
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(HTTPException):
            update_character(self.db, list_characters(self.db, self.b.story_id)[0], outfit="Different")
        self.db.rollback()
        fork = library.fork(self.db, self.b.story_id, "alice", original_ref.reference_id, "Story B diverges")
        self.assertEqual(fork.target_id, stable_id)
        self.assertEqual(self.db.get(CanonObjectVersion, fork.canon_version_id).parent_version_id, self.pin.canon_version_id)
        approve_candidate(self.db, story_id=self.b.story_id, candidate_id=candidate.canon_candidate_id,
            user_id="alice", approval=CandidateApproval(replace_conflicts=True))
        self.assertEqual([r.value for r in list_canon_entries(self.db, self.b.story_id) if r.status == "approved"], ["green"])
        self.assertEqual([r.value for r in list_canon_entries(self.db, self.a.story_id) if r.status == "approved"], ["blue"])
        self.assertEqual(self.pin.canon_version_id, self.source.canon_version_id)
        self.assertEqual(self.propose(self.a, "blue").classification, "consistent")
        self.assertEqual(self.propose(self.b, "green", evidence="Later confirmation").classification, "consistent")
        self.assertEqual(continuity_report(self.db, story_id=self.a.story_id, user_id="alice").counts["consistent"], 1)

    def test_explicit_promotion_and_no_automatic_discovery_publication(self):
        fork = library.fork(self.db, self.b.story_id, "alice", self.inherited(self.b).reference_id, "Story-specific finding")
        # A second Universe can receive an explicitly published branch baseline.
        another = service.create_universe(self.db, "alice", name="Another")
        with self.assertRaises(HTTPException):
            service.pin(self.db, another.universe_id, "alice", fork.canon_object_id, fork.canon_version_id)
        published = service.pin(self.db, another.universe_id, "alice", fork.canon_object_id, fork.canon_version_id, promote=True)
        shared = self.db.get(CanonObjectVersion, published.canon_version_id)
        self.assertIsNone(shared.created_by_story_id)
        self.assertEqual(shared.parent_version_id, fork.canon_version_id)
        self.assertEqual(len(service.list_references(self.db, self.universe.universe_id, "alice")), 1)
        self.assertEqual(self.pin.canon_version_id, self.source.canon_version_id)

    def test_remove_membership_preserves_story_data_and_forks(self):
        original_id = self.inherited(self.b).target_id
        library.fork(self.db, self.b.story_id, "alice", self.inherited(self.b).reference_id, "Keep local")
        service.remove_story(self.db, self.universe.universe_id, self.b.story_id, "alice")
        self.assertEqual(list_characters(self.db, self.b.story_id)[0].character_id, original_id)
        self.assertEqual(len(library.references(self.db, self.b.story_id)), 1)
        service.remove_story(self.db, self.universe.universe_id, self.a.story_id, "alice")
        self.assertEqual(list_characters(self.db, self.a.story_id), [])
        self.assertIsNotNone(self.db.get(Universe, self.universe.universe_id))
        self.assertEqual(self.db.get(UniverseCanonReference, self.pin.reference_id).canon_version_id, self.source.canon_version_id)

    def test_ownership_membership_limits_and_invalid_pins(self):
        other = service.create_universe(self.db, "alice", name="Second")
        with self.assertRaises(HTTPException) as error:
            service.attach_story(self.db, other.universe_id, self.a.story_id, "alice")
        self.assertEqual(error.exception.status_code, 409)
        bob = create_story(self.db, "bob", title="Private")
        for operation in [lambda: service.get_universe(self.db, self.universe.universe_id, "bob"),
                          lambda: service.attach_story(self.db, self.universe.universe_id, bob.story_id, "bob"),
                          lambda: service.attach_story(self.db, self.universe.universe_id, bob.story_id, "alice"),
                          lambda: service.pin(self.db, other.universe_id, "bob", self.source.canon_object_id, self.source.canon_version_id)]:
            with self.assertRaises(HTTPException) as denied:
                operation()
            self.assertEqual(denied.exception.status_code, 404)
        self.assertEqual(service.list_universes(self.db, "bob"), [])
        with self.assertRaises(HTTPException):
            service.pin(self.db, other.universe_id, "alice", self.source.canon_object_id, "missing")

    def test_pin_updates_affect_inheritors_but_not_explicit_story_pins(self):
        fork = library.fork(self.db, self.b.story_id, "alice", self.inherited(self.b).reference_id, "Pinned branch")
        original_branch = fork.canon_version_id
        shared = library.shared_version(self.db, self.source.canon_object_id, "alice", self.source.canon_version_id,
            {"name": "Unit 7", "outfit": "White cloak"})
        self.assertEqual(list_characters(self.db, self.a.story_id)[0].outfit, "Yellow utility sash")
        service.move_pin(self.db, self.universe.universe_id, "alice", self.pin.reference_id, shared.canon_version_id)
        self.assertEqual(list_characters(self.db, self.a.story_id)[0].outfit, "White cloak")
        self.assertEqual(fork.canon_version_id, original_branch)
        self.assertEqual(list_characters(self.db, self.b.story_id)[0].outfit, "Yellow utility sash")
        update_character(self.db, list_characters(self.db, self.b.story_id)[0], outfit="Blue cape")
        # Explicit promotion publishes the full branch snapshot; there is no merge.
        service.pin(self.db, self.universe.universe_id, "alice", fork.canon_object_id, fork.canon_version_id, promote=True)
        self.assertEqual(list_characters(self.db, self.a.story_id)[0].outfit, "Blue cape")
        self.assertNotEqual(self.pin.canon_version_id, fork.canon_version_id)

    def test_places_inherit_and_universe_outlives_an_empty_member_story(self):
        place = library.promote(self.db, self.story.story_id, "alice", "place", self.place.place_id)
        service.pin(self.db, self.universe.universe_id, "alice", place.canon_object_id, place.canon_version_id)
        self.assertEqual(list_places(self.db, self.a.story_id)[0].name, self.place.name)
        version_id = self.pin.canon_version_id
        self.db.delete(self.a)
        self.db.commit()
        self.assertIsNotNone(self.db.get(Universe, self.universe.universe_id))
        self.assertIsNotNone(self.db.get(CanonObjectVersion, version_id))
        self.assertEqual(len(service.list_members(self.db, self.universe.universe_id, "alice")), 1)
        self.assertEqual(list_characters(self.db, self.b.story_id)[0].name, self.character.name)

    def test_inherited_visuals_and_media_planning_preserve_reference_identity(self):
        from app.artifacts.schemas import ArtifactRegistration, ReferenceBindingCreate
        from app.artifacts.service import register_artifact, create_binding
        from app.stories.scene_service import create_scene
        from app.media.storyboard import create_four_panel_storyboard
        artifact = register_artifact(self.db, "alice", ArtifactRegistration(source="external", retrieval_reference="https://example.test/harbor"))
        binding = create_binding(self.db, self.story.story_id, "alice", ReferenceBindingCreate(
            artifact_id=artifact.artifact_id, target_type="place", target_id=self.place.place_id, role="place"))
        place_ref = library.promote(self.db, self.story.story_id, "alice", "place", self.place.place_id)
        service.pin(self.db, self.universe.universe_id, "alice", place_ref.canon_object_id, place_ref.canon_version_id)
        scene = create_scene(self.db, story_id=self.a.story_id, content="Unit 7 rests in the greenhouse.")
        plan = create_four_panel_storyboard(self.db, story_id=self.a.story_id, scene_id=scene.scene_id, user_id="alice")
        self.assertTrue(all(any(ref.binding_id == binding.reference_id and ref.reference_id == artifact.artifact_id
            for ref in request.references) for request in plan.requests))
        self.assertTrue(all("blue" in request.prompt for request in plan.requests))
        discovery = propose_candidate(self.db, story_id=self.a.story_id, user_id="alice", proposal=ManualCandidate(
            type="world", key="weather", value="Rainy", evidence="Author discovery"))
        approve_candidate(self.db, story_id=self.a.story_id, user_id="alice", candidate_id=discovery.canon_candidate_id, approval=CandidateApproval())
        self.assertEqual(len(service.list_references(self.db, self.universe.universe_id, "alice")), 2)
        self.assertNotIn("weather", [row.key for row in list_canon_entries(self.db, self.b.story_id)])

    def test_failed_fork_rolls_back_materialized_handle_and_story_pin(self):
        from unittest.mock import patch
        ref = self.inherited(self.a)
        with patch("app.canon.library_service.append_version", side_effect=RuntimeError("Cannot append")):
            with self.assertRaisesRegex(RuntimeError, "Cannot append"):
                library.fork(self.db, self.a.story_id, "alice", ref.reference_id, "Attempt")
        self.assertIsNone(self.db.get(Character, ref.target_id))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StoryCanonReference).where(StoryCanonReference.story_id == self.a.story_id)), 0)
        self.assertEqual(self.inherited(self.a).canon_version_id, self.pin.canon_version_id)


class UniverseAPITests(MediaFixture):
    def test_authenticated_universe_crud_membership_promotion_and_errors(self):
        from fastapi.testclient import TestClient
        from app.api.dependencies import get_db, get_current_identity
        from app.auth.identity import AuthenticatedIdentity
        from app.main import app
        def database():
            yield self.db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("alice", "alice@example.test", "Alice")
        try:
            with TestClient(app) as client:
                created = client.post("/api/universes", json={"name": "Garden", "description": "Beyond Stories"})
                self.assertEqual(created.status_code, 201, created.text)
                universe_id = created.json()["universe_id"]
                base = f"/api/universes/{universe_id}"
                self.assertEqual(len(client.get("/api/universes").json()), 1)
                self.assertEqual(client.get(base).json()["name"], "Garden")
                self.assertEqual(client.patch(base, json={"name": "The garden"}).json()["name"], "The garden")
                self.assertEqual(client.patch(base, json={"name": " "}).status_code, 422)
                membership = client.post(base + f"/stories/{self.story.story_id}")
                self.assertEqual(membership.status_code, 200, membership.text)
                promoted = library.promote(self.db, self.story.story_id, "alice", "character", self.character.character_id)
                payload = {"canon_object_id": promoted.canon_object_id, "canon_version_id": promoted.canon_version_id}
                self.assertEqual(client.post(base + "/canon/references/promote", json=payload).status_code, 201)
                other = create_story(self.db, "alice", title="New member")
                self.assertEqual(client.post(base + f"/stories/{other.story_id}").status_code, 200)
                refs = client.get(f"/api/stories/{other.story_id}/canon/references").json()
                self.assertEqual(refs[0]["universe_id"], universe_id)
                self.assertTrue(refs[0]["inherited"])
                forked = client.post(f"/api/stories/{other.story_id}/canon/references/{refs[0]['reference_id']}/fork", json={"reason": "Local change"})
                self.assertEqual(forked.status_code, 200, forked.text)
                self.assertFalse(forked.json()["inherited"])
                self.assertEqual(forked.json()["target_id"], refs[0]["target_id"])
                self.assertEqual(client.delete(base + f"/stories/{other.story_id}").status_code, 204)
                self.assertEqual(client.get(base + "/canon/references").status_code, 200)
                app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("bob", "bob@example.test", "Bob")
                self.assertEqual(client.get(base).status_code, 404)
                self.assertEqual(client.patch(base, json={"name": "No"}).status_code, 404)
                self.assertEqual(client.get(base + "/canon/references").status_code, 404)
                self.assertEqual(client.post(base + "/canon/references", json=payload).status_code, 404)
                self.assertEqual(client.post(base + f"/stories/{self.story.story_id}").status_code, 404)
                app.dependency_overrides.pop(get_current_identity)
                self.assertEqual(client.get("/api/universes").status_code, 401)
        finally:
            app.dependency_overrides.clear()
