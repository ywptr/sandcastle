"""Offline tests of inspected HTTP shapes; no IG imports or browser credentials."""
import json
import unittest
from unittest.mock import patch

import httpx

from app.integrations.ig.client import IGMediaExecutionClient, get_execution_client
from app.media.execution_client import ExecutionClientError, ExecutionRejected, ExecutionUnavailable
from app.media.schemas import MediaContext, MediaPurpose, MediaRequest, MediaType, Reference


class IGClientTests(unittest.TestCase):
    def request(self):
        return MediaRequest(
            media_type=MediaType.IMAGE, purpose=MediaPurpose.COMIC_PANEL, prompt="Depict the approved panel",
            story_id="story", scene_id="scene", aspect_ratio="1:1", context=MediaContext(),
            references=[Reference(kind="character", reference_id="character-id")],
        )

    def test_submit_maps_current_contract_without_story_or_credential_fields(self):
        seen = []
        def handler(request):
            seen.append(request)
            return httpx.Response(202, json={"media_type": "image", "request_id": "ig-image-1", "status": "generating"})
        client = IGMediaExecutionClient("https://ig.example.test", transport=httpx.MockTransport(handler))
        submission = client.submit(self.request(), actor_id="alice", correlation_id="exec-1")
        self.assertEqual(submission.external_execution_id, "ig-image-1")
        self.assertEqual(seen[0].url.path, "/v2/media/generations")
        payload = json.loads(seen[0].content)
        self.assertEqual(payload["strategy"], "single")
        self.assertEqual(payload["intent"]["description"], "Depict the approved panel")
        self.assertEqual(payload["output"]["layout"], {"type": "single"})
        self.assertEqual(payload["references"], [])
        for key in ["story_id", "scene_id", "provider", "model", "user_id"]:
            self.assertNotIn(key, payload)
        self.assertNotIn("cookie", seen[0].headers)
        self.assertNotIn("authorization", seen[0].headers)

    def test_status_result_use_image_request_contract_not_fabricated_job_or_artifact_api(self):
        paths = []
        def handler(request):
            paths.append(request.url.path)
            return httpx.Response(200, json={"request_id": "image-1", "status": "completed", "mime_type": "image/png", "size_bytes": 123})
        client = IGMediaExecutionClient("https://ig.example.test", transport=httpx.MockTransport(handler))
        self.assertEqual(client.get_status("image-1", actor_id="alice").status, "completed")
        image = client.get_result("image-1", actor_id="alice").images[0]
        self.assertEqual(paths, ["/v1/images/image-1", "/v1/images/image-1"])
        self.assertIsNone(image.external_artifact_id)
        self.assertEqual(image.retrieval_reference, "https://ig.example.test/v1/images/image-1/content")
        self.assertEqual(image.external_reference, "image-1")

    def test_live_transport_is_blocked_even_with_base_url_and_fake_token(self):
        with patch.dict("os.environ", {"IG_BASE_URL": "https://ig.example.test", "IG_SERVICE_TOKEN": "not-a-real-contract"}):
            client = get_execution_client()
            with patch("httpx.Client", side_effect=AssertionError("Must not open a live client")):
                with self.assertRaisesRegex(ExecutionUnavailable, "service-caller"):
                    client.submit(self.request(), actor_id="alice", correlation_id="exec")
                with self.assertRaises(ExecutionUnavailable):
                    client.get_status("id", actor_id="alice")
                with self.assertRaises(ExecutionUnavailable):
                    client.get_result("id", actor_id="alice")

    def test_rejects_unsupported_media_framing_and_unresolved_artifacts(self):
        client = IGMediaExecutionClient("https://ig.example.test", transport=httpx.MockTransport(lambda request: self.fail("No HTTP expected")))
        for change in [{"media_type": MediaType.VIDEO}, {"aspect_ratio": "9:16"},
                       {"references": [Reference(kind="uploaded_artifact", reference_id="opaque")]}]:
            with self.subTest(change=change), self.assertRaises(ExecutionRejected):
                client.submit(self.request().model_copy(update=change), actor_id="alice", correlation_id="exec")

    def test_transport_errors_and_unknown_or_mismatched_responses_fail_safely(self):
        for status, payload in [(401, {"secret": "never-persist"}), (200, {"request_id": "wrong", "status": "completed"}),
                                (200, {"request_id": "id", "status": "invented"})]:
            client = IGMediaExecutionClient("https://ig.example.test", transport=httpx.MockTransport(
                lambda request: httpx.Response(status, json=payload)))
            with self.assertRaises(ExecutionClientError) as raised:
                client.get_status("id", actor_id="alice")
            self.assertNotIn("never-persist", str(raised.exception))
