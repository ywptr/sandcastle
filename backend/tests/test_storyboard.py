"""Four-panel intent planning uses M3 and never executes media generation."""
import copy
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from test_media import MediaFixture
from app.api.dependencies import get_db
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.db.database import Base
from app.main import app
from app.media.schemas import (
    ArtifactReference, MediaPlan, MediaPurpose, MediaType, SceneImageOptions, StoryboardPlan,
)
from app.media.service import InvalidMediaIntent, MediaDomainNotFound
from app.media.storyboard import create_four_panel_storyboard
from app.stories.scene_service import create_scene, update_scene
from app.stories.service import create_story
from app.world.service import create_character, create_place

BEATS = [
    "Unit 7 enters the abandoned greenhouse.",
    "A faint green glow draws the robot toward a cracked planter.",
    "The robot discovers a living flower beneath the glass.",
    "Unit 7 kneels beside the flower in wonder.",
]


class StoryboardServiceTests(MediaFixture):
    def storyboard(self, **changes):
        args = {"story_id": self.story.story_id, "scene_id": self.scene.scene_id, "user_id": "alice"}
        return create_four_panel_storyboard(self.db, **(args | changes))

    def test_four_ordered_distinct_image_panels_with_shared_references_and_no_writes(self):
        update_scene(self.db, self.scene, content=" ".join(BEATS))
        options = SceneImageOptions(artifact_references=[
            ArtifactReference(kind="uploaded_artifact", reference_id="upload-123"),
            ArtifactReference(kind="generated_artifact", reference_id="prior-456"),
        ])
        before = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        with patch("socket.create_connection", side_effect=AssertionError("No provider calls allowed")):
            plan = self.storyboard(options=options)
        self.assertIsInstance(plan, MediaPlan)
        self.assertEqual(len(plan.requests), 4)
        self.assertEqual([request.context.panel_number for request in plan.requests], [1, 2, 3, 4])
        self.assertEqual(len({request.prompt for request in plan.requests}), 4)
        self.assertEqual(len({request.media_request_id for request in plan.requests}), 4)
        self.assertEqual(plan.story_id, self.story.story_id)
        self.assertEqual(plan.scene_id, self.scene.scene_id)
        expected_references = {
            ("character", self.character.character_id), ("outfit", self.character.character_id),
            ("place", self.place.place_id), ("uploaded_artifact", "upload-123"),
            ("generated_artifact", "prior-456"),
        }
        for number, request in enumerate(plan.requests):
            self.assertEqual(request.story_id, self.story.story_id)
            self.assertEqual(request.scene_id, self.scene.scene_id)
            self.assertEqual(request.media_type, MediaType.IMAGE)
            self.assertEqual(request.purpose, MediaPurpose.COMIC_PANEL)
            self.assertEqual(request.context.panel_count, 4)
            self.assertTrue(request.context.panel_role)
            self.assertEqual(request.context.scene_sequence_number, 1)
            self.assertEqual(request.context.canon_entry_ids, [self.canon.canon_entry_id])
            self.assertEqual(request.aspect_ratio, "1:1")
            self.assertIn(BEATS[number], request.prompt)
            for other in BEATS[:number] + BEATS[number + 1:]:
                self.assertNotIn(other, request.prompt)
            self.assertIn("Blue eyes", request.prompt)
            self.assertIn("Yellow utility sash", request.prompt)
            self.assertIn("Cracked glass", request.prompt)
            self.assertIn("Only one living flower remains", request.prompt)
            self.assertNotIn("There are many flowers", request.prompt)
            self.assertEqual({(ref.kind, ref.reference_id) for ref in request.references}, expected_references)
        after = {table.name: self.db.execute(select(table)).all() for table in Base.metadata.sorted_tables}
        self.assertEqual(before, after)
        # The same M3 envelope round-trips without a separate execution-plan schema.
        self.assertEqual(len(MediaPlan.model_validate(plan.to_media_plan().model_dump()).requests), 4)
        for provider_detail in ["openai", "vercel", "redis", "model_id", "api_key", "database_url"]:
            self.assertNotIn(provider_detail, plan.model_dump_json().lower())

    def test_ordered_source_partition_preserves_long_scene(self):
        sentences = [f"The traveler records observation {index}." for index in range(1, 10)]
        update_scene(self.db, self.scene, content=" ".join(sentences))
        plan = self.storyboard()
        positions = []
        for sentence in sentences:
            matching = [index for index, request in enumerate(plan.requests) if sentence in request.prompt]
            self.assertEqual(len(matching), 1)
            positions.append(matching[0])
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(set(positions), {0, 1, 2, 3})

    def test_short_scenes_use_distinct_framings_without_invented_events(self):
        for prose in ["A traveler waits.", "A traveler arrives. A door opens.",
                      "A traveler enters. Rain begins. The traveler waits.",
                      "One lamp glows; another dims; rain falls; dawn breaks.",
                      "第一幕。\n第二幕。\n第三幕。\n第四幕。"]:
            with self.subTest(prose=prose):
                update_scene(self.db, self.scene, content=prose)
                plan = self.storyboard()
                self.assertEqual(len(plan.requests), 4)
                self.assertEqual(len({request.prompt for request in plan.requests}), 4)
                for request in plan.requests:
                    self.assertIn("Do not invent actions", request.prompt)
                if prose == "A traveler waits.":
                    self.assertTrue(all(prose in request.prompt for request in plan.requests))
                    self.assertIn("wide establishing", plan.requests[0].prompt)
                    self.assertIn("medium view", plan.requests[1].prompt)
                    self.assertIn("close view", plan.requests[2].prompt)
                    self.assertIn("closing view", plan.requests[3].prompt)

    def test_determinism_edited_content_and_explicit_reference_selection(self):
        other_character = create_character(self.db, self.story.story_id, name="Mara")
        create_place(self.db, self.story.story_id, name="Tower")
        update_scene(self.db, self.scene, content=" ".join(BEATS))
        options = SceneImageOptions(character_ids=[other_character.character_id], place_ids=[], aspect_ratio="4:5")
        first = self.storyboard(options=options)
        second = self.storyboard(options=options)
        self.assertNotEqual(first.media_plan_id, second.media_plan_id)
        for a, b in zip(first.requests, second.requests):
            self.assertEqual(a.prompt, b.prompt)
            self.assertEqual(a.context, b.context)
            self.assertEqual(a.references, b.references)
            self.assertEqual(a.aspect_ratio, "4:5")
            self.assertEqual([(ref.kind, ref.reference_id) for ref in a.references], [("character", other_character.character_id)])
        update_scene(self.db, self.scene, content="The robot leaves the greenhouse.")
        changed = self.storyboard(options=options)
        self.assertTrue(all("The robot leaves the greenhouse." in request.prompt for request in changed.requests))
        self.assertTrue(all(BEATS[0] not in request.prompt for request in changed.requests))
        self.assertEqual(options.aspect_ratio, "4:5")

    def test_invalid_missing_and_cross_story_domain_objects(self):
        other = create_story(self.db, "alice", title="Other story")
        foreign_scene = create_scene(self.db, story_id=other.story_id, content="Other scene")
        character = create_character(self.db, other.story_id, name="Foreign")
        place = create_place(self.db, other.story_id, name="Foreign")
        for changes, message in [
            ({"story_id": "missing"}, "Story not found"),
            ({"user_id": "bob"}, "Story not found"),
            ({"scene_id": "missing"}, "Scene not found"),
            ({"scene_id": foreign_scene.scene_id}, "Scene not found"),
            ({"options": SceneImageOptions(character_ids=[character.character_id])}, "Character not found"),
            ({"options": SceneImageOptions(place_ids=[place.place_id])}, "Place not found"),
        ]:
            with self.subTest(changes=changes), self.assertRaisesRegex(MediaDomainNotFound, message):
                self.storyboard(**changes)
        update_scene(self.db, self.scene, content=" \n ")
        with self.assertRaisesRegex(InvalidMediaIntent, "Scene content"):
            self.storyboard()

    def test_storyboard_dto_enforces_count_order_identity_and_media_contract(self):
        original = self.storyboard().model_dump(mode="json")
        for change in ["count", "order", "story", "scene", "type", "purpose", "panel_count"]:
            data = copy.deepcopy(original)
            if change == "count":
                data["requests"].pop()
            elif change == "order":
                data["requests"].reverse()
            elif change == "story":
                data["requests"][0]["story_id"] = "other"
            elif change == "scene":
                data["requests"][0]["scene_id"] = "other"
            elif change == "type":
                data["requests"][0]["media_type"] = "video"
            elif change == "purpose":
                data["requests"][0]["purpose"] = "scene"
            else:
                data["requests"][0]["context"]["panel_count"] = 3
            with self.subTest(change=change), self.assertRaises(ValidationError):
                StoryboardPlan.model_validate(data)


class StoryboardAPITests(MediaFixture):
    def setUp(self):
        super().setUp()

        def override_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sign_in("alice")
        self.url = f"/api/stories/{self.story.story_id}/scenes/{self.scene.scene_id}/storyboard/four-panel"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        super().tearDown()

    def sign_in(self, user_id):
        token = AuthSessionManager("test-session-secret").create_session_token(
            AuthenticatedIdentity(user_id, f"{user_id}@example.test", user_id),
        )
        self.client.cookies.set(SESSION_COOKIE, token)

    def test_authenticated_storyboard_and_invalid_input(self):
        result = self.client.post(self.url, json={"aspect_ratio": "4:5"})
        self.assertEqual(result.status_code, 200, result.text)
        payload = result.json()
        self.assertEqual(len(payload["requests"]), 4)
        self.assertEqual([request["context"]["panel_number"] for request in payload["requests"]], [1, 2, 3, 4])
        self.assertTrue(all(request["purpose"] == "comic_panel" for request in payload["requests"]))
        self.assertEqual(self.client.post(self.url, json={"aspect_ratio": "0:5"}).status_code, 422)
        self.assertEqual(self.client.post(self.url, json={"model_id": "provider"}).status_code, 422)
        self.assertEqual(self.client.post(self.url, json={"character_ids": ["missing"]}).status_code, 404)

    def test_ownership_missing_resources_invalid_content_and_authentication(self):
        self.sign_in("bob")
        self.assertEqual(self.client.post(self.url, json={}).status_code, 404)
        self.sign_in("alice")
        missing_story = "/api/stories/missing/scenes/missing/storyboard/four-panel"
        self.assertEqual(self.client.post(missing_story, json={}).status_code, 404)
        self.assertEqual(self.client.post(self.url.replace(self.scene.scene_id, "missing"), json={}).status_code, 404)
        other = create_story(self.db, "alice", title="Other story")
        wrong_story = self.url.replace(self.story.story_id, other.story_id)
        self.assertEqual(self.client.post(wrong_story, json={}).status_code, 404)
        update_scene(self.db, self.scene, content=" ")
        self.assertEqual(self.client.post(self.url, json={}).status_code, 422)
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url, json={}).status_code, 401)
        self.client.cookies.set(SESSION_COOKIE, "tampered")
        self.assertEqual(self.client.post(self.url, json={}).status_code, 401)
