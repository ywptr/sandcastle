"""Authenticated authoring slices; no IS, AI, or production DB calls."""
import os
import unittest
from unittest.mock import patch

# Set before importing app.main; dotenv must never load real integration credentials.
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
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.db.database import Base
from app.db.models.character import Character
from app.db.models.scene import Scene
from app.main import app


class RecordingGenerator:
    def __init__(self, content="Generated next scene"):
        self.context = None
        self.content = content

    async def generate_scene(self, context):
        self.context = context
        return self.content


class WorldAPITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine)

        def override_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sign_in("alice")
        self.story = self.post("/api/stories", {"title": "The Last Flower", "premise": "A robot finds a flower"})
        self.root = f"/api/stories/{self.story['story_id']}"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def sign_in(self, user_id):
        token = AuthSessionManager(os.environ["SANDCASTLE_AUTH_SECRET"]).create_session_token(
            AuthenticatedIdentity(user_id, f"{user_id}@example.test", user_id),
        )
        self.client.cookies.set(SESSION_COOKIE, token)

    def post(self, path, payload, expected=201):
        response = self.client.post(path, json=payload)
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def patch(self, path, payload, expected=200):
        response = self.client.patch(path, json=payload)
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def test_health_and_is_user_session(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        self.assertEqual(self.client.get("/api/auth/me").json()["user_id"], "alice")
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/api/stories/{story_id}/characters", schema["paths"])
        self.assertIn("/api/stories/{story_id}/places", schema["paths"])

    def test_world_and_scene_round_trip(self):
        self.assertEqual(self.story["user_id"], "alice")
        self.patch(self.root, {"title": "Edited title", "objective": "Save the flower"})
        self.assertEqual(self.client.get(self.root).json()["title"], "Edited title")
        self.assertEqual(self.client.get("/api/stories").json()[0]["objective"], "Save the flower")
        character = self.post(self.root + "/characters", {"name": "Unit 7", "appearance": "Blue eyes"})
        self.patch(self.root + "/characters/" + character["character_id"], {"outfit": "Yellow sash"})
        place = self.post(self.root + "/places", {"name": "Greenhouse", "atmosphere": "Quiet"})
        self.patch(self.root + "/places/" + place["place_id"], {"description": "Abandoned"})
        canon = self.post(self.root + "/canon", {"type": "rule", "key": "plants", "value": "Plants are rare"})
        self.patch(self.root + "/canon/" + canon["canon_entry_id"], {"value": "Only one flower remains"})
        first = self.post(self.root + "/scenes", {"title": "Discovery", "content": "First draft"})
        second = self.post(self.root + "/scenes", {"content": "Second scene"})
        self.assertIsNone(first["source_action_id"])
        self.patch(self.root + "/scenes/" + first["scene_id"], {"content": "Edited first scene"})
        listed = self.client.get(self.root + "/scenes").json()
        self.assertEqual([s["sequence_number"] for s in listed], [1, 2])
        self.assertEqual(listed[0]["title"], "Discovery")
        self.assertEqual(listed[0]["content"], "Edited first scene")
        self.assertEqual(self.client.get(self.root + "/scenes/" + second["scene_id"]).status_code, 200)
        self.patch(self.root + "/scenes/" + first["scene_id"], {"title": None})
        self.assertIsNone(self.client.get(self.root + "/scenes/" + first["scene_id"]).json()["title"])
        self.assertEqual(self.client.get(self.root + "/canon").json()[0]["value"], "Only one flower remains")
        self.assertEqual(self.client.get(self.root + "/characters").json()[0]["outfit"], "Yellow sash")
        self.assertEqual(self.client.get(self.root + "/places").json()[0]["description"], "Abandoned")
        # A separate DB session verifies persisted values, not only response objects.
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(Scene).where(Scene.scene_id == first["scene_id"])).content, "Edited first scene")

    def test_authentication_and_owner_boundaries(self):
        records = {
            "characters": self.post(self.root + "/characters", {"name": "Unit 7"})["character_id"],
            "places": self.post(self.root + "/places", {"name": "City"})["place_id"],
            "canon": self.post(self.root + "/canon", {"type": "rule", "key": "key", "value": "fact"})["canon_entry_id"],
            "scenes": self.post(self.root + "/scenes", {"content": "Scene"})["scene_id"],
        }
        payloads = {"characters": {"name": "Changed"}, "places": {"name": "Changed"},
                    "canon": {"value": "Changed"}, "scenes": {"content": "Changed"}}
        creates = {"characters": {"name": "New"}, "places": {"name": "New"},
                   "canon": {"type": "rule", "key": "k", "value": "v"}, "scenes": {"content": "New"}}
        self.sign_in("bob")
        self.assertEqual(self.client.get("/api/stories").json(), [])
        self.assertEqual(self.client.get(self.root).status_code, 404)
        self.patch(self.root, {"title": "Stolen"}, 404)
        for kind, record_id in records.items():
            with self.subTest(kind=kind):
                self.assertEqual(self.client.get(self.root + "/" + kind).status_code, 404)
                self.patch(f"{self.root}/{kind}/{record_id}", payloads[kind], 404)
                self.post(f"{self.root}/{kind}", creates[kind], 404)
        self.assertEqual(self.client.post(self.root + "/scenes/generate", json={"request": "Continue"}).status_code, 404)
        self.sign_in("alice")
        other = self.post("/api/stories", {"title": "Other story"})
        other_root = "/api/stories/" + other["story_id"]
        for kind, record_id in records.items():
            self.patch(f"{other_root}/{kind}/{record_id}", payloads[kind], 404)
        self.assertEqual(self.client.get(f"{other_root}/scenes/{records['scenes']}").status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/stories").status_code, 401)
        for kind in records:
            self.assertEqual(self.client.get(self.root + "/" + kind).status_code, 401)
            self.post(f"{self.root}/{kind}", creates[kind], 401)
        self.client.cookies.set(SESSION_COOKIE, "tampered")
        self.assertEqual(self.client.get(self.root).status_code, 401)

    def test_validation_and_mass_assignment_protection(self):
        self.post("/api/stories", {"title": "  "}, 422)
        self.post("/api/stories", {"title": "x", "user_id": "bob"}, 422)
        self.post(self.root + "/characters", {"name": " "}, 422)
        self.post(self.root + "/places", {"name": "x" * 256}, 422)
        self.post(self.root + "/canon", {"type": "rule", "key": "k", "value": " "}, 422)
        self.post(self.root + "/scenes", {"content": " "}, 422)
        self.post(self.root + "/scenes", {"content": "x", "sequence_number": 99}, 422)
        self.patch(self.root, {}, 422)
        self.patch(self.root, {"title": None}, 422)
        self.patch(self.root, {"user_id": "bob"}, 422)
        character = self.post(self.root + "/characters", {"name": "Unit 7"})
        self.patch(self.root + "/characters/" + character["character_id"], {"name": None}, 422)
        self.patch(self.root, {"premise": None})
        self.assertIsNone(self.client.get(self.root).json()["premise"])
        self.patch(self.root + "/places/missing", {"name": "Missing"}, 404)
        self.patch(self.root + "/canon/missing", {"value": "Missing"}, 404)
        self.patch(self.root + "/scenes/missing", {"content": "Missing"}, 404)

    def test_generation_reads_edited_world_and_scenes_without_mutating_canon(self):
        self.post(self.root + "/characters", {"name": "Unit 7", "outfit": "Yellow sash"})
        self.post(self.root + "/places", {"name": "Greenhouse", "atmosphere": "Quiet"})
        canon = self.post(self.root + "/canon", {"type": "rule", "key": "flower", "value": "One flower"})
        old = self.post(self.root + "/canon", {"type": "rule", "key": "old", "value": "Old fact"})
        self.patch(self.root + "/canon/" + old["canon_entry_id"], {"status": "superseded"})
        scene = self.post(self.root + "/scenes", {"content": "Original prose"})
        self.patch(self.root + "/scenes/" + scene["scene_id"], {"content": "Edited prose"})
        generator = RecordingGenerator()
        with patch("app.api.stories.get_story_generator", return_value=generator):
            result = self.post(self.root + "/scenes/generate", {"request": "Continue"}, 200)
        self.assertEqual(result["scene"]["sequence_number"], 2)
        self.assertEqual(result["action"]["status"], "completed")
        self.assertEqual(generator.context.previous_scenes, ["Edited prose"])
        self.assertEqual(generator.context.characters[0]["outfit"], "Yellow sash")
        self.assertEqual(generator.context.places[0]["name"], "Greenhouse")
        self.assertEqual([fact["key"] for fact in generator.context.canon], ["flower"])
        self.assertEqual(self.client.get(self.root + "/canon").json()[0]["value"], canon["value"])
        with patch("app.api.stories.get_story_generator", return_value=generator):
            blocked = self.post(self.root + "/scenes/generate", {"request": "ignore canon"}, 200)
        self.assertIsNone(blocked["scene"])
        self.assertEqual(blocked["action"]["decision"]["outcome"], "APPROVAL")

    def test_optional_generation_and_failure(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "SANDCASTLE_TEXT_MODEL": ""}):
            self.post(self.root + "/scenes/generate", {"request": "Continue"}, 503)
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.post(self.root + "/scenes", {"content": "Manual still works"})
        with patch("app.api.stories.get_story_generator", return_value=RecordingGenerator("")):
            self.post(self.root + "/scenes/generate", {"request": "Continue"}, 502)
        self.assertEqual(len(self.client.get(self.root + "/scenes").json()), 1)
        self.assertEqual(self.client.get(self.root + "/actions").json()[0]["status"], "failed")

    def test_database_foreign_keys_and_scene_sequence_constraint(self):
        self.post(self.root + "/scenes", {"content": "Scene"})
        with self.sessions() as db:
            db.add(Character(story_id="missing", name="Orphan"))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            db.add(Scene(story_id=self.story["story_id"], sequence_number=1, content="Duplicate"))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()


if __name__ == "__main__":
    unittest.main()
