"""M6 metadata, binding selection, lineage, and refinement; no live media calls."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from test_media import MediaFixture
from test_media_execution import FakeExecutionClient
from app.api.dependencies import get_db
from app.artifacts.schemas import ArtifactRegistration, ArtifactRelationCreate, ReferenceBindingCreate
from app.artifacts.service import (
    ArtifactConflict, create_binding, create_relation, delete_binding, get_artifact,
    list_artifacts, list_bindings, list_relations, register_artifact,
)
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.db.database import Base
from app.db.models import Artifact, ArtifactRelation, MediaExecution, ReferenceBinding
from app.main import app
from app.media.execution_service import execute_storyboard, sync_execution
from app.media.refinement import create_refinement_request
from app.media.schemas import MediaPurpose, MediaType, Reference, RefinementInput, SceneImageOptions
from app.media.service import InvalidMediaIntent, MediaDomainNotFound, create_scene_image_request
from app.media.storyboard import create_four_panel_storyboard
from app.stories.service import create_story
from app.world.service import create_character, create_place


class ReferenceFixture(MediaFixture):
    def artifact(self, source="uploaded", user="alice", **values):
        return register_artifact(self.db, user, ArtifactRegistration(
            source=source, retrieval_reference="https://media.example.test/already-stored.png",
            mime_type="image/png", display_name="Visual reference", **values,
        ))

    def bind(self, artifact, target_type="story", target_id=None, role="visual_style", story_id=None, user="alice"):
        return create_binding(self.db, story_id or self.story.story_id, user, ReferenceBindingCreate(
            artifact_id=artifact.artifact_id, target_type=target_type, target_id=target_id, role=role,
        ))

    def scene_request(self, **options):
        return create_scene_image_request(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                          user_id="alice", options=SceneImageOptions(**options))


class ReferenceServiceTests(ReferenceFixture):
    def test_register_uploaded_external_independent_artifacts_without_storage_calls(self):
        with patch("socket.create_connection", side_effect=AssertionError("No storage/network calls")):
            uploaded = self.artifact(metadata={"credit": "Author", "tags": ["night"]})
            external = self.artifact("external")
        self.assertEqual(uploaded.source, "uploaded")
        self.assertEqual(external.source, "external")
        self.assertIsNone(uploaded.story_id)
        self.assertIsNone(uploaded.execution_id)
        self.assertIsNone(uploaded.scene_id)
        self.assertIsNone(uploaded.external_reference)
        self.assertEqual(uploaded.metadata_json, {"credit": "Author", "tags": ["night"]})
        self.assertEqual(len(list_artifacts(self.db, "alice")), 2)
        self.assertEqual(len(list_artifacts(self.db, "alice", source="external")), 1)
        for values in [
            {"source": "generated", "retrieval_reference": "https://media.example.test/x"},
            {"source": "uploaded", "retrieval_reference": "data:image/png;base64,AAAA"},
            {"source": "uploaded", "retrieval_reference": "file:///tmp/image.png"},
            {"source": "uploaded", "retrieval_reference": "https://user:secret@media.example.test/x"},
            {"source": "uploaded", "retrieval_reference": "https://media.example.test/x", "media_type": "video"},
        ]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ArtifactRegistration(**values)

    def test_one_artifact_can_bind_character_outfit_place_style_and_multiple_stories(self):
        artifact = self.artifact()
        bindings = [self.bind(artifact, "character", self.character.character_id, "character_identity"),
                    self.bind(artifact, "character", self.character.character_id, "outfit"),
                    self.bind(artifact, "place", self.place.place_id, "place"), self.bind(artifact)]
        other_story = create_story(self.db, "alice", title="Another story")
        self.bind(artifact, story_id=other_story.story_id)
        self.assertEqual(len(list_bindings(self.db, self.story.story_id, "alice")), 4)
        self.assertEqual({binding.artifact_id for binding in bindings}, {artifact.artifact_id})
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Artifact)), 1)
        self.assertEqual(list_artifacts(self.db, "alice", story_id=other_story.story_id)[0].artifact_id, artifact.artifact_id)
        with self.assertRaises(ArtifactConflict):
            self.bind(artifact)
        delete_binding(self.db, self.story.story_id, bindings[0].reference_id, "alice")
        self.assertEqual(len(list_bindings(self.db, self.story.story_id, "alice")), 3)
        self.assertEqual(get_artifact(self.db, artifact.artifact_id, "alice").artifact_id, artifact.artifact_id)

    def test_owner_target_and_role_validation(self):
        artifact = self.artifact()
        other_story = create_story(self.db, "alice", title="Other story")
        character = create_character(self.db, other_story.story_id, name="Other")
        place = create_place(self.db, other_story.story_id, name="Other")
        for target_type, target_id, role in [("character", "missing", "character_identity"),
                                            ("character", character.character_id, "outfit"),
                                            ("place", place.place_id, "place"), ("story", other_story.story_id, "general")]:
            with self.subTest(target_type=target_type), self.assertRaises(MediaDomainNotFound):
                self.bind(artifact, target_type, target_id, role)
        with self.assertRaises(InvalidMediaIntent):
            self.bind(artifact, "story", None, "outfit")
        with self.assertRaises(MediaDomainNotFound):
            get_artifact(self.db, artifact.artifact_id, "bob")
        bob_story = create_story(self.db, "bob", title="Bob's story")
        with self.assertRaises(MediaDomainNotFound):
            self.bind(artifact, user="bob", story_id=bob_story.story_id)
        with self.assertRaises(MediaDomainNotFound):
            self.bind(artifact, story_id="missing")
        with self.assertRaises(MediaDomainNotFound):
            register_artifact(self.db, "bob", ArtifactRegistration(source="external", story_id=self.story.story_id,
                                                                  retrieval_reference="https://media.example.test/x"))

    def test_applicable_reference_ids_enter_scene_and_four_panel_requests(self):
        style, character, place, unused = [self.artifact() for _ in range(4)]
        style_binding = self.bind(style)
        character_binding = self.bind(character, "character", self.character.character_id, "character_identity")
        self.bind(place, "place", self.place.place_id, "place")
        other_character = create_character(self.db, self.story.story_id, name="Mara")
        self.bind(unused, "character", other_character.character_id, "outfit")
        options = {"character_ids": [self.character.character_id], "place_ids": []}
        request = self.scene_request(**options)
        refs = [ref for ref in request.references if ref.kind == "artifact"]
        self.assertEqual({ref.reference_id for ref in refs}, {style.artifact_id, character.artifact_id})
        self.assertEqual({ref.binding_id for ref in refs}, {style_binding.reference_id, character_binding.reference_id})
        self.assertEqual({ref.role for ref in refs}, {"visual_style", "character_identity"})
        self.assertNotIn(style.retrieval_reference, request.model_dump_json())
        self.assertEqual(self.scene_request(**options).references, request.references)
        plan = create_four_panel_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                            user_id="alice", options=SceneImageOptions(**options))
        for panel in plan.requests:
            self.assertEqual([ref for ref in panel.references if ref.kind == "artifact"], refs)
        empty = self.scene_request(character_ids=[], place_ids=[])
        self.assertEqual([ref.reference_id for ref in empty.references if ref.kind == "artifact"], [style.artifact_id])
        explicit = self.scene_request(character_ids=[], place_ids=[], artifact_ids=[place.artifact_id])
        self.assertIn(place.artifact_id, [ref.reference_id for ref in explicit.references if ref.kind == "artifact"])
        bob_artifact = self.artifact(user="bob")
        with self.assertRaises(MediaDomainNotFound):
            self.scene_request(artifact_ids=[bob_artifact.artifact_id])

    def test_refinement_source_provenance_context_and_no_writes_or_provider_calls(self):
        source, outfit, extra = [self.artifact() for _ in range(3)]
        binding = self.bind(outfit, "character", self.character.character_id, "outfit")
        before = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        intent = RefinementInput(
            instruction="Keep identity and outfit unchanged; change the background to a rainy night market.",
            story_id=self.story.story_id, scene_id=self.scene.scene_id,
            character_ids=[self.character.character_id], place_ids=[], artifact_ids=[extra.artifact_id],
        )
        with patch("socket.create_connection", side_effect=AssertionError("No media calls")):
            request = create_refinement_request(self.db, artifact_id=source.artifact_id, user_id="alice", intent=intent)
        self.assertEqual(request.media_type, MediaType.IMAGE)
        self.assertEqual(request.purpose, MediaPurpose.IMAGE_REFINEMENT)
        self.assertEqual(request.context.source_artifact_id, source.artifact_id)
        self.assertEqual(request.references[0].role, "source")
        self.assertEqual(request.references[0].reference_id, source.artifact_id)
        self.assertIn(binding.reference_id, [ref.binding_id for ref in request.references])
        self.assertIn(extra.artifact_id, [ref.reference_id for ref in request.references])
        self.assertEqual(request.story_id, self.story.story_id)
        self.assertEqual(request.scene_id, self.scene.scene_id)
        self.assertIn(intent.instruction, request.prompt)
        self.assertIn("Yellow utility sash", request.prompt)
        self.assertEqual(request.context.canon_entry_ids, [self.canon.canon_entry_id])
        after = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        self.assertEqual(before, after)
        self.assertNotIn(source.retrieval_reference, request.model_dump_json())
        for provider_field in ["openai", "vercel", "api_key", "model_id", "ig_session"]:
            self.assertNotIn(provider_field, request.model_dump_json().lower())
        standalone = create_refinement_request(self.db, artifact_id=source.artifact_id, user_id="alice",
                                               intent=RefinementInput(instruction="Change the background to night"))
        self.assertIsNone(standalone.story_id)
        self.assertIsNone(standalone.scene_id)
        self.assertEqual(standalone.context.source_artifact_id, source.artifact_id)
        with self.assertRaises(MediaDomainNotFound):
            create_refinement_request(self.db, artifact_id=source.artifact_id, user_id="bob", intent=intent)
        with self.assertRaises(InvalidMediaIntent):
            create_refinement_request(self.db, artifact_id=source.artifact_id, user_id="alice",
                                       intent=RefinementInput(instruction="Edit", scene_id=self.scene.scene_id))

    def test_multi_parent_lineage_idempotency_self_cycle_and_owner_validation(self):
        a, b, c, d = [self.artifact() for _ in range(4)]
        ab = create_relation(self.db, b.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=a.artifact_id))
        duplicate = create_relation(self.db, b.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=a.artifact_id))
        self.assertEqual(ab.relation_id, duplicate.relation_id)
        create_relation(self.db, c.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=b.artifact_id))
        create_relation(self.db, c.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=d.artifact_id, relation_type="reference_input"))
        self.assertEqual(len(list_relations(self.db, c.artifact_id, "alice")), 2)
        for parent, child in [(a, a), (c, a), (b, a)]:
            with self.subTest(parent=parent.artifact_id), self.assertRaises(InvalidMediaIntent):
                create_relation(self.db, child.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=parent.artifact_id))
        bob = self.artifact(user="bob")
        with self.assertRaises(MediaDomainNotFound):
            create_relation(self.db, b.artifact_id, "alice", ArtifactRelationCreate(parent_artifact_id=bob.artifact_id))
        with self.assertRaises(MediaDomainNotFound):
            list_relations(self.db, a.artifact_id, "bob")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(ArtifactRelation)), 3)
        self.db.add(ArtifactRelation(user_id="alice", parent_artifact_id=a.artifact_id,
                                    child_artifact_id=a.artifact_id, relation_type="derived_from"))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_execution_checks_durable_artifact_and_binding_ownership(self):
        owned = self.artifact()
        foreign = self.artifact(user="bob")
        bob_story = create_story(self.db, "bob", title="Bob's references")
        foreign_binding = self.bind(foreign, story_id=bob_story.story_id, user="bob")
        fake = FakeExecutionClient()
        for reference in [
            Reference(kind="artifact", reference_id=foreign.artifact_id, role="general"),
            Reference(kind="artifact", reference_id=owned.artifact_id, role="visual_style",
                      binding_id=foreign_binding.reference_id),
        ]:
            plan = create_four_panel_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id, user_id="alice")
            plan.requests[0].references.append(reference)
            with self.assertRaises(MediaDomainNotFound):
                execute_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                   user_id="alice", plan=plan, client=fake)
        self.assertEqual(fake.submissions, [])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MediaExecution)), 0)
        binding = self.bind(owned)
        plan = create_four_panel_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id, user_id="alice")
        rows = execute_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                 user_id="alice", plan=plan, client=fake)
        saved = rows[0].request_snapshot
        self.assertIn(binding.reference_id, [ref.get("binding_id") for ref in saved["references"]])
        delete_binding(self.db, self.story.story_id, binding.reference_id, "alice")
        self.db.expire_all()
        self.assertEqual(self.db.get(MediaExecution, rows[0].execution_id).request_snapshot, saved)

    def test_generated_execution_artifacts_remain_usable_without_forging_origin(self):
        fake = FakeExecutionClient()
        plan = create_four_panel_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id, user_id="alice")
        rows = execute_storyboard(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                 user_id="alice", plan=plan, client=fake)
        fake.states[rows[0].external_execution_id] = "completed"
        sync_execution(self.db, execution_id=rows[0].execution_id, user_id="alice", client=fake)
        artifact = list_artifacts(self.db, "alice", source="generated")[0]
        self.assertEqual(artifact.execution_id, rows[0].execution_id)
        self.bind(artifact, "character", self.character.character_id, "character_identity")
        self.assertIn(artifact.artifact_id, [ref.reference_id for ref in self.scene_request().references])


class ReferenceAPITests(ReferenceFixture):
    def setUp(self):
        super().setUp()
        def override_db():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sign_in("alice")
        self.references_url = f"/api/stories/{self.story.story_id}/references"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        super().tearDown()

    def sign_in(self, user_id):
        token = AuthSessionManager(os.environ["SANDCASTLE_AUTH_SECRET"]).create_session_token(
            AuthenticatedIdentity(user_id, f"{user_id}@example.test", user_id),
        )
        self.client.cookies.set(SESSION_COOKIE, token)

    def register(self, source="uploaded"):
        response = self.client.post("/api/artifacts", json={"source": source,
            "retrieval_reference": "https://media.example.test/stored.png", "metadata": {"credit": "Author"}})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_registration_reference_crud_and_refinement_api(self):
        artifact = self.register()
        artifact_id = artifact["artifact_id"]
        self.assertIsNone(artifact["execution_id"])
        self.assertEqual(self.client.get("/api/artifacts?source=uploaded").json()[0]["artifact_id"], artifact_id)
        self.assertEqual(self.client.get(f"/api/media/artifacts/{artifact_id}").status_code, 200)
        binding = self.client.post(self.references_url, json={"artifact_id": artifact_id, "target_type": "character",
            "target_id": self.character.character_id, "role": "character_identity", "label": "Mara appearance"})
        self.assertEqual(binding.status_code, 201, binding.text)
        reference_id = binding.json()["reference_id"]
        self.assertEqual(self.client.get(self.references_url).json()[0]["artifact_id"], artifact_id)
        preview = self.client.post(f"/api/artifacts/{artifact_id}/refinement", json={"instruction": "Keep identity; change background to night"})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()["context"]["source_artifact_id"], artifact_id)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MediaExecution)), 0)
        self.assertEqual(self.client.delete(f"{self.references_url}/{reference_id}").status_code, 204)
        self.assertEqual(self.client.get(self.references_url).json(), [])
        self.assertEqual(self.client.get(f"/api/artifacts/{artifact_id}").status_code, 200)
        other = self.register("external")
        relation = self.client.post(f"/api/artifacts/{other['artifact_id']}/relations", json={"parent_artifact_id": artifact_id})
        self.assertEqual(relation.status_code, 201, relation.text)
        self.assertEqual(len(self.client.get(f"/api/artifacts/{artifact_id}/relations").json()), 1)

    def test_invalid_missing_and_cross_user_resources_fail_without_leaking(self):
        artifact = self.register()
        artifact_id = artifact["artifact_id"]
        binding_body = {"artifact_id": artifact_id, "target_type": "story", "role": "visual_style"}
        binding = self.client.post(self.references_url, json=binding_body).json()
        self.assertEqual(self.client.post(self.references_url, json=binding_body).status_code, 409)
        for body in [{"source": "generated", "retrieval_reference": "https://media.example.test/x"},
                     {"source": "uploaded", "retrieval_reference": "data:image/png;base64,a"},
                     {"source": "external", "retrieval_reference": "https://media.example.test/x", "user_id": "bob"}]:
            self.assertEqual(self.client.post("/api/artifacts", json=body).status_code, 422)
        self.assertEqual(self.client.post(self.references_url, json={**binding_body, "target_type": "character", "target_id": "missing"}).status_code, 404)
        self.assertEqual(self.client.post(f"/api/artifacts/{artifact_id}/refinement", json={"instruction": " "}).status_code, 422)
        self.assertEqual(self.client.post(f"/api/artifacts/{artifact_id}/relations", json={"parent_artifact_id": artifact_id}).status_code, 422)
        self.sign_in("bob")
        self.assertEqual(self.client.get("/api/artifacts").json(), [])
        for path in [f"/api/artifacts/{artifact_id}", f"/api/media/artifacts/{artifact_id}", self.references_url,
                     f"/api/artifacts/{artifact_id}/relations"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(self.references_url, json=binding_body).status_code, 404)
        bob_story = create_story(self.db, "bob", title="Bob")
        self.assertEqual(self.client.post(f"/api/stories/{bob_story.story_id}/references", json=binding_body).status_code, 404)
        self.assertEqual(self.client.delete(f"{self.references_url}/{binding['reference_id']}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/artifacts/{artifact_id}/refinement", json={"instruction": "Edit"}).status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/artifacts").status_code, 401)
        self.assertEqual(self.client.post("/api/artifacts", json={"source": "uploaded", "retrieval_reference": "https://example.test/x"}).status_code, 401)
