"""M3 compiles domain intent locally; no provider or infrastructure is required."""
import json
import os
import unittest
from unittest.mock import patch

os.environ.update({
    "DATABASE_URL": "sqlite:///:memory:",
    "IS_ISSUER": "https://identity.example.test",
    "IS_CLIENT_ID": "test-client",
    "IS_CLIENT_SECRET": "test-client-secret",
    "SANDCASTLE_AUTH_SECRET": "test-session-secret",
    "SANDCASTLE_AUTH_CALLBACK_URL": "http://testserver/api/auth/callback",
    "SANDCASTLE_WEB_URL": "http://testserver",
})

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.canon.service import create_canon_entry
from app.db.database import Base
from app.db.models import CanonEntry, Scene, Story
from app.main import app
from app.media.schemas import (
    ArtifactReference, MediaContext, MediaPurpose, MediaRequest, MediaType,
    SceneImageOptions, SceneImagePlanInput,
)
from app.media.service import (
    InvalidMediaIntent, MediaDomainNotFound, create_media_plan, create_scene_image_request,
)
from app.stories.scene_service import create_scene, update_scene
from app.stories.service import create_story
from app.world.service import create_character, create_place


class MediaFixture(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine)
        self.db = self.sessions()
        self.story = create_story(
            self.db, "alice", title="The Last Flower",
            premise="A robot finds a flower", objective="Protect the flower",
        )
        self.character = create_character(
            self.db, self.story.story_id, name="Unit 7", appearance="Blue eyes",
            outfit="Yellow utility sash", personality="Gentle",
        )
        self.place = create_place(
            self.db, self.story.story_id, name="Greenhouse", description="Abandoned",
            appearance="Cracked glass", atmosphere="Quiet",
        )
        self.scene = create_scene(
            self.db, story_id=self.story.story_id, title="Discovery",
            content="Unit 7 kneels beside the last flower in the greenhouse.",
        )
        self.canon = create_canon_entry(
            self.db, story_id=self.story.story_id, entry_type="rule", key="flower",
            value="Only one living flower remains.",
        )
        old = create_canon_entry(
            self.db, story_id=self.story.story_id, entry_type="rule", key="old",
            value="There are many flowers.",
        )
        old.status = "superseded"
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def request(self, **overrides):
        args = {"story_id": self.story.story_id, "scene_id": self.scene.scene_id, "user_id": "alice"}
        return create_scene_image_request(self.db, **(args | overrides))


class MediaServiceTests(MediaFixture):
    def test_scene_image_request_semantics_and_references_without_provider_calls(self):
        options = SceneImageOptions(
            aspect_ratio="4:5",
            artifact_references=[
                ArtifactReference(kind="uploaded_artifact", reference_id="upload-123"),
                ArtifactReference(kind="generated_artifact", reference_id="prior-456"),
            ],
        )
        with patch("socket.create_connection", side_effect=AssertionError("No networking allowed")):
            result = self.request(options=options)
        self.assertEqual(result.media_type, MediaType.IMAGE)
        self.assertEqual(result.purpose, MediaPurpose.SCENE)
        self.assertEqual(result.story_id, self.story.story_id)
        self.assertEqual(result.scene_id, self.scene.scene_id)
        self.assertEqual(result.aspect_ratio, "4:5")
        self.assertTrue(result.media_request_id)
        self.assertIsNotNone(result.created_at.tzinfo)
        refs = {(ref.kind, ref.reference_id) for ref in result.references}
        self.assertEqual(refs, {
            ("character", self.character.character_id), ("outfit", self.character.character_id),
            ("place", self.place.place_id), ("uploaded_artifact", "upload-123"),
            ("generated_artifact", "prior-456"),
        })
        for text in ["single image", "The Last Flower", "Protect the flower", "Discovery", "Blue eyes",
                     "Yellow utility sash", "Greenhouse", "Cracked glass", "Quiet", self.scene.content,
                     "Only one living flower remains."]:
            self.assertIn(text, result.prompt)
        self.assertNotIn("There are many flowers", result.prompt)
        self.assertEqual(result.context.canon_entry_ids, [self.canon.canon_entry_id])
        self.assertEqual(result.context.scene_sequence_number, 1)
        serialized = result.model_dump_json().lower()
        for forbidden in ["openai", "vercel", "redis", "api_key", "model_id", "blob", "rq", "database_url"]:
            self.assertNotIn(forbidden, serialized)
        self.assertNotIn("user_id", json.loads(serialized))

    def test_selection_determinism_and_edited_scene_content(self):
        other = create_character(self.db, self.story.story_id, name="Mara")
        update_scene(self.db, self.scene, content="Edited prose: Unit 7 returns at dawn.")
        options = SceneImageOptions(
            character_ids=[self.character.character_id], place_ids=[],
            artifact_references=[
                ArtifactReference(kind="uploaded_artifact", reference_id="b"),
                ArtifactReference(kind="uploaded_artifact", reference_id="a"),
                ArtifactReference(kind="uploaded_artifact", reference_id="b"),
            ],
        )
        first = self.request(options=options)
        second = self.request(options=options)
        self.assertEqual(first.prompt, second.prompt)
        self.assertEqual(first.references, second.references)
        self.assertEqual(first.context, second.context)
        self.assertNotEqual(first.media_request_id, second.media_request_id)
        self.assertIn("Edited prose", first.prompt)
        self.assertNotIn("Mara", first.prompt)
        self.assertNotIn("Environment:", first.prompt)
        self.assertNotIn(other.character_id, [ref.reference_id for ref in first.references])
        self.assertEqual([ref.reference_id for ref in first.references if ref.kind == "uploaded_artifact"], ["a", "b"])

    def test_plan_produces_ordered_requests_and_writes_nothing(self):
        next_scene = create_scene(self.db, story_id=self.story.story_id, content="The robot returns home.")
        before = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        plan = create_media_plan(
            self.db, story_id=self.story.story_id, user_id="alice",
            intent=SceneImagePlanInput(scene_ids=[next_scene.scene_id, self.scene.scene_id], aspect_ratio="9:16"),
        )
        self.assertEqual(plan.story_id, self.story.story_id)
        self.assertEqual([item.scene_id for item in plan.requests], [next_scene.scene_id, self.scene.scene_id])
        self.assertEqual(len({item.media_request_id for item in plan.requests}), 2)
        self.assertTrue(all(item.aspect_ratio == "9:16" for item in plan.requests))
        self.assertTrue(all(item.media_type == MediaType.IMAGE for item in plan.requests))
        self.db.expire_all()
        after = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        self.assertEqual(before, after)
        self.assertEqual(self.db.get(CanonEntry, self.canon.canon_entry_id).status, "approved")

    def test_missing_cross_story_and_invalid_domain_objects(self):
        other_story = create_story(self.db, "alice", title="Other story")
        foreign_character = create_character(self.db, other_story.story_id, name="Foreign")
        foreign_place = create_place(self.db, other_story.story_id, name="Foreign")
        foreign_scene = create_scene(self.db, story_id=other_story.story_id, content="Other scene")
        for args, message in [
            ({"story_id": "missing"}, "Story not found"),
            ({"user_id": "bob"}, "Story not found"),
            ({"scene_id": "missing"}, "Scene not found"),
            ({"scene_id": foreign_scene.scene_id}, "Scene not found"),
            ({"options": SceneImageOptions(character_ids=[foreign_character.character_id])}, "Character not found"),
            ({"options": SceneImageOptions(place_ids=[foreign_place.place_id])}, "Place not found"),
        ]:
            with self.subTest(args=args), self.assertRaisesRegex(MediaDomainNotFound, message):
                self.request(**args)
        self.scene.content = " "
        self.db.commit()
        with self.assertRaisesRegex(InvalidMediaIntent, "Scene content"):
            self.request()
        self.scene.content = "Valid prose"
        self.story.title = " "
        self.db.commit()
        with self.assertRaisesRegex(InvalidMediaIntent, "Story title"):
            self.request()

    def test_empty_world_and_dto_validation(self):
        empty = create_story(self.db, "alice", title="Empty world")
        scene = create_scene(self.db, story_id=empty.story_id, content="A sunrise.")
        result = self.request(story_id=empty.story_id, scene_id=scene.scene_id)
        self.assertEqual(result.references, [])
        self.assertEqual(result.context.canon_entry_ids, [])
        self.assertIn("A sunrise", result.prompt)
        for args in [
            {"aspect_ratio": "0:5"}, {"aspect_ratio": "wide"}, {"provider": "specific"},
            {"character_ids": ["id", "id"]}, {"artifact_references": [{"kind": "uploaded_artifact", "reference_id": " "}]},
        ]:
            with self.subTest(args=args), self.assertRaises(ValidationError):
                SceneImageOptions(**args)
        for scene_ids in [[], ["id", "id"]]:
            with self.assertRaises(ValidationError):
                SceneImagePlanInput(scene_ids=scene_ids)
        # Additional media purposes/types do not require scene-specific context.
        video = MediaRequest(
            media_type=MediaType.VIDEO, purpose=MediaPurpose.VIDEO_SCENE,
            prompt="Depict a sunrise", story_id=empty.story_id, context=MediaContext(),
        )
        self.assertEqual(video.media_type, "video")


class MediaAPITests(MediaFixture):
    def setUp(self):
        super().setUp()

        def override_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sign_in("alice")
        self.url = f"/api/stories/{self.story.story_id}/scenes/{self.scene.scene_id}/media/image-request"
        self.plan_url = f"/api/stories/{self.story.story_id}/media-plans"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        super().tearDown()

    def sign_in(self, user_id):
        token = AuthSessionManager(os.environ["SANDCASTLE_AUTH_SECRET"]).create_session_token(
            AuthenticatedIdentity(user_id, f"{user_id}@example.test", user_id),
        )
        self.client.cookies.set(SESSION_COOKIE, token)

    def test_image_and_plan_endpoints(self):
        response = self.client.post(self.url, json={"aspect_ratio": "4:5"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["purpose"], "scene")
        self.assertEqual(response.json()["scene_id"], self.scene.scene_id)
        plan = self.client.post(self.plan_url, json={"scene_ids": [self.scene.scene_id]})
        self.assertEqual(plan.status_code, 200, plan.text)
        self.assertEqual(len(plan.json()["requests"]), 1)
        self.assertEqual(self.client.post(self.url, json={"model_id": "provider-model"}).status_code, 422)
        self.assertEqual(self.client.post(self.plan_url, json={"scene_ids": []}).status_code, 422)
        self.assertEqual(self.client.post(self.url, json={"character_ids": ["missing"]}).status_code, 404)

    def test_ownership_missing_scene_and_authentication(self):
        self.sign_in("bob")
        self.assertEqual(self.client.post(self.url, json={}).status_code, 404)
        self.assertEqual(self.client.post(self.plan_url, json={"scene_ids": [self.scene.scene_id]}).status_code, 404)
        self.sign_in("alice")
        other = create_story(self.db, "alice", title="Other story")
        other_url = f"/api/stories/{other.story_id}/scenes/{self.scene.scene_id}/media/image-request"
        self.assertEqual(self.client.post(other_url, json={}).status_code, 404)
        bad_plan = self.client.post(self.plan_url, json={"scene_ids": [self.scene.scene_id, "missing"]})
        self.assertEqual(bad_plan.status_code, 404)
        self.scene.content = " "
        self.db.commit()
        invalid = self.client.post(self.url, json={})
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("Scene content", invalid.json()["detail"])
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url, json={}).status_code, 401)
        self.assertEqual(self.client.post(self.plan_url, json={"scene_ids": [self.scene.scene_id]}).status_code, 401)
