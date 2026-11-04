"""Library pinning, stable local subjects, and independent M7/M6 resolution."""
from fastapi import HTTPException
from sqlalchemy import select
from test_media import MediaFixture
from app.canon import library_service as lib
from app.canon.service import create_canon_entry, list_canon_entries
from app.canon.candidate_service import propose_candidate, approve_candidate
from app.canon.candidate_schemas import ManualCandidate, CandidateApproval
from app.db.models import CanonObjectVersion, CanonObject, StoryCanonReference
from app.stories.service import create_story
from app.world.service import get_character, update_character

class CanonLibraryTests(MediaFixture):
    def promote(self, kind="character"):
        target = self.character.character_id if kind == "character" else self.place.place_id
        return lib.promote(self.db, self.story.story_id, "alice", kind, target)

    def second(self, ref):
        other = create_story(self.db, "alice", title="Second", premise="Another", objective="Continue")
        linked = lib.attach(self.db, other.story_id, "alice", ref.canon_object_id, ref.canon_version_id)
        return other, linked

    def test_character_place_promotion_preserves_ids_and_no_name_dedup(self):
        ref = self.promote()
        self.assertEqual(ref.target_id, self.character.character_id)
        self.assertEqual(self.promote().reference_id, ref.reference_id)
        place = self.promote("place")
        self.assertEqual(place.target_id, self.place.place_id)
        lib.create_object(self.db, "alice", "character", {"name": self.character.name})
        self.assertEqual(len(list(self.db.scalars(select(CanonObject)))), 3)

    def test_shared_version_pin_fork_and_typed_story_edit(self):
        ref = self.promote()
        original = ref.canon_version_id
        other, linked = self.second(ref)
        self.assertEqual(linked.canon_version_id, original)
        target = get_character(self.db, other.story_id, linked.target_id)
        with self.assertRaises(HTTPException) as error:
            update_character(self.db, target, appearance="Green eyes")
        self.assertEqual(error.exception.status_code, 409)
        self.db.rollback()
        lib.fork(self.db, other.story_id, "alice", linked.reference_id, "Different appearance")
        fork_id = linked.canon_version_id
        self.assertEqual(self.db.get(CanonObjectVersion, fork_id).parent_version_id, original)
        update_character(self.db, target, appearance="Green eyes")
        self.assertNotEqual(linked.canon_version_id, fork_id)
        self.assertEqual(ref.canon_version_id, original)
        self.assertEqual(self.db.get(CanonObjectVersion, original).data["structure"]["appearance"], "Blue eyes")
        newer = lib.shared_version(self.db, ref.canon_object_id, "alice", original, {"name": "New shared name"})
        self.assertEqual(ref.canon_version_id, original)
        lib.move(self.db, self.story.story_id, "alice", ref.reference_id, newer.canon_version_id)
        self.assertEqual(self.character.name, "New shared name")
        self.assertEqual(target.appearance, "Green eyes")

    def test_m7_fork_approval_and_effective_canon_are_independent(self):
        create_canon_entry(self.db, story_id=self.story.story_id, entry_type="character",
            subject_id=self.character.character_id, key="eye_color", value="blue")
        ref = self.promote()
        other, linked = self.second(ref)
        proposal = propose_candidate(self.db, story_id=other.story_id, user_id="alice", proposal=ManualCandidate(
            type="character", subject_id=linked.target_id, key="eye_color", value="green", evidence="Author choice"))
        self.assertEqual(proposal.classification, "conflict")
        with self.assertRaises(HTTPException):
            approve_candidate(self.db, story_id=other.story_id, candidate_id=proposal.canon_candidate_id,
                user_id="alice", approval=CandidateApproval(replace_conflicts=True))
        lib.fork(self.db, other.story_id, "alice", linked.reference_id, "New continuity")
        approve_candidate(self.db, story_id=other.story_id, candidate_id=proposal.canon_candidate_id,
            user_id="alice", approval=CandidateApproval(replace_conflicts=True))
        def eyes(story_id):
            return [r.value for r in list_canon_entries(self.db, story_id) if r.key == "eye_color" and r.status == "approved"]
        self.assertEqual(eyes(self.story.story_id), ["blue"])
        self.assertEqual(eyes(other.story_id), ["green"])
        self.assertEqual(proposal.subject_id, linked.target_id)
        follow = propose_candidate(self.db, story_id=other.story_id, user_id="alice", proposal=ManualCandidate(
            type="character", subject_id=linked.target_id, key="eye_color", value="green", evidence="Still green"))
        self.assertEqual(follow.classification, "consistent")
        self.assertEqual(follow.comparison_snapshot[0]["canon_version_id"], linked.canon_version_id)

    def test_private_library_story_and_history_ownership(self):
        ref = self.promote()
        for operation in [lambda: lib.get_object(self.db, ref.canon_object_id, "bob"),
                          lambda: lib.attach(self.db, self.story.story_id, "bob", ref.canon_object_id, ref.canon_version_id),
                          lambda: lib.fork(self.db, self.story.story_id, "bob", ref.reference_id, "No")]:
            with self.assertRaises(HTTPException) as error:
                operation()
            self.assertEqual(error.exception.status_code, 404)
        bob = create_story(self.db, "bob", title="Private", premise="", objective="")
        with self.assertRaises(HTTPException):
            lib.attach(self.db, bob.story_id, "bob", ref.canon_object_id, ref.canon_version_id)

    def test_visuals_inherited_by_reference_and_filtered(self):
        from app.artifacts.service import register_artifact, create_binding
        from app.artifacts.schemas import ArtifactRegistration, ReferenceBindingCreate
        from app.artifacts.resolver import resolve_applicable_references
        artifact = register_artifact(self.db, "alice", ArtifactRegistration(source="external", retrieval_reference="https://example.test/ref"))
        binding = create_binding(self.db, self.story.story_id, "alice", ReferenceBindingCreate(
            artifact_id=artifact.artifact_id, target_type="character", target_id=self.character.character_id, role="character_identity"))
        ref = self.promote()
        other, linked = self.second(ref)
        lib.fork(self.db, other.story_id, "alice", linked.reference_id, "Inherited visuals")
        result = resolve_applicable_references(self.db, story_id=other.story_id, user_id="alice", character_ids=[linked.target_id], place_ids=[])
        self.assertEqual([(r.reference_id, r.binding_id) for r in result], [(artifact.artifact_id, binding.reference_id)])
        self.assertEqual(resolve_applicable_references(self.db, story_id=other.story_id, user_id="alice", character_ids=[], place_ids=[]), [])
        from app.stories.scene_service import create_scene
        from app.media.storyboard import create_four_panel_storyboard
        from app.media.execution_service import execute_storyboard
        from test_media_execution import FakeExecutionClient
        scene = create_scene(self.db, story_id=other.story_id, content="Unit 7 walks along the harbor.")
        plan = create_four_panel_storyboard(self.db, story_id=other.story_id, scene_id=scene.scene_id, user_id="alice")
        self.assertTrue(all(any(r.binding_id == binding.reference_id for r in request.references) for request in plan.requests))
        rows = execute_storyboard(self.db, story_id=other.story_id, scene_id=scene.scene_id, user_id="alice", plan=plan, client=FakeExecutionClient())
        self.assertTrue(all(row.status == "submitted" for row in rows))

class CanonLibraryAPITests(MediaFixture):
    def test_authenticated_library_lifecycle_and_ownership(self):
        from fastapi.testclient import TestClient
        from app.api.dependencies import get_db, get_current_identity
        from app.auth.identity import AuthenticatedIdentity
        from app.main import app
        def database():
            yield self.db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity(user_id="alice", email="alice@example.test", name="Alice")
        try:
            with TestClient(app) as client:
                prefix = f"/api/stories/{self.story.story_id}/canon"
                result = client.post(prefix + "/library/promote", json={"target_type": "character", "target_id": self.character.character_id})
                self.assertEqual(result.status_code, 200, result.text)
                ref = result.json()
                obj = ref["canon_object_id"]
                self.assertEqual(client.get("/api/canon/library").status_code, 200)
                history = client.get(f"/api/canon/library/{obj}/versions").json()
                self.assertEqual(len(history), 1)
                self.assertEqual(client.patch(f"/api/stories/{self.story.story_id}/characters/{self.character.character_id}", json={"outfit": "Blue coat"}).status_code, 409)
                forked = client.post(prefix + f"/references/{ref['reference_id']}/fork", json={"reason": "Divergence"})
                self.assertEqual(forked.status_code, 200, forked.text)
                self.assertEqual(client.patch(f"/api/stories/{self.story.story_id}/characters/{self.character.character_id}", json={"outfit": "Blue coat"}).status_code, 200)
                self.assertEqual(client.post("/api/canon/library", json={"object_type": "place", "data": {}}).status_code, 422)
                app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity(user_id="bob", email="bob@example.test", name="Bob")
                for path in [f"/api/canon/library/{obj}", f"/api/canon/library/{obj}/versions", prefix + "/references"]:
                    self.assertEqual(client.get(path).status_code, 404)
                self.assertEqual(client.post(prefix + f"/references/{ref['reference_id']}/fork", json={"reason": "No"}).status_code, 404)
        finally:
            app.dependency_overrides.clear()

    def test_library_attach_and_version_api_validation(self):
        # Service layer must reject cross-object pins and private branch reuse too.
        from app.canon.library_service import get_version
        obj = lib.create_object(self.db, "alice", "place", {"name": "Same name"})
        first = self.db.scalar(select(CanonObjectVersion).where(CanonObjectVersion.canon_object_id == obj.canon_object_id))
        other_obj = lib.create_object(self.db, "alice", "place", {"name": "Same name"})
        with self.assertRaises(HTTPException):
            get_version(self.db, other_obj, first.canon_version_id)
        attached = lib.attach(self.db, self.story.story_id, "alice", obj.canon_object_id, first.canon_version_id)
        lib.fork(self.db, self.story.story_id, "alice", attached.reference_id, "Local harbor")
        second = create_story(self.db, "alice", title="Other")
        with self.assertRaises(HTTPException) as error:
            lib.attach(self.db, second.story_id, "alice", obj.canon_object_id, attached.canon_version_id)
        self.assertEqual(error.exception.status_code, 409)
