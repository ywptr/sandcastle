"""Durable execution is exercised with a fake client, never a live control plane."""
import copy
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from test_media import MediaFixture
from app.api.dependencies import get_db
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.db.models import Artifact, MediaExecution
from app.integrations.ig.client import get_execution_client
from app.main import app
from app.media.execution_client import (
    ExecutionClientError, ExecutionResult, ExternalStatus, GeneratedImage, Submission,
)
from app.media.execution_service import (
    ExecutionConflict, execute_storyboard, get_execution, list_artifacts, sync_execution,
)
from app.media.service import InvalidMediaIntent, MediaDomainNotFound
from app.media.storyboard import create_four_panel_storyboard
from app.stories.scene_service import create_scene, update_scene
from app.stories.service import create_story
from app.world.service import create_character


class FakeExecutionClient:
    backend_name = "fake"

    def __init__(self):
        self.submissions = []
        self.states = {}
        self.fail_panel = None
        self.poll_error = False
        self.bad_result = False
        self.result_reads = 0

    def submit(self, request, *, actor_id, correlation_id):
        self.submissions.append((request.model_dump(mode="json"), actor_id, correlation_id))
        if request.context.panel_number == self.fail_panel:
            raise ExecutionClientError("Panel submission rejected")
        external_id = f"external-{request.context.panel_number}"
        self.states[external_id] = "submitted"
        return Submission(external_execution_id=external_id)

    def get_status(self, external_execution_id, *, actor_id):
        if self.poll_error:
            raise ExecutionClientError("Status temporarily unavailable")
        return ExternalStatus(status=self.states[external_execution_id])

    def get_result(self, external_execution_id, *, actor_id):
        self.result_reads += 1
        if self.bad_result:
            raise ExecutionClientError("Result temporarily unavailable")
        return ExecutionResult(images=[GeneratedImage(
            external_reference=external_execution_id,
            retrieval_reference=f"https://media.example.test/content/{external_execution_id}",
            mime_type="image/png", metadata={"size_bytes": 321},
        )])


class ExecutionFixture(MediaFixture):
    def setUp(self):
        super().setUp()
        self.plan = create_four_panel_storyboard(
            self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id, user_id="alice",
        )
        self.fake = FakeExecutionClient()

    def execute(self, **changes):
        args = {"story_id": self.story.story_id, "scene_id": self.scene.scene_id,
                "user_id": "alice", "plan": self.plan, "client": self.fake}
        return execute_storyboard(self.db, **(args | changes))

    def sync(self, row):
        return sync_execution(self.db, execution_id=row.execution_id, user_id="alice", client=self.fake)


class ExecutionServiceTests(ExecutionFixture):
    def test_four_durable_ordered_snapshots_precede_submission_and_replay_is_idempotent(self):
        original_submit = self.fake.submit

        def inspect_before_submit(request, **kwargs):
            with self.sessions() as separate:
                self.assertEqual(separate.scalar(select(func.count()).select_from(MediaExecution)), 4)
            return original_submit(request, **kwargs)

        self.fake.submit = inspect_before_submit
        rows = self.execute()
        self.assertEqual([row.panel_number for row in rows], [1, 2, 3, 4])
        self.assertEqual([row.media_request_id for row in rows], [request.media_request_id for request in self.plan.requests])
        self.assertTrue(all(row.status == "submitted" for row in rows))
        self.assertTrue(all(row.user_id == "alice" and row.backend_name == "fake" for row in rows))
        self.assertTrue(all(row.started_at and row.approved_at for row in rows))
        for row, request, submission in zip(rows, self.plan.requests, self.fake.submissions):
            self.assertEqual(row.request_snapshot, request.model_dump(mode="json"))
            self.assertEqual(submission[0], row.request_snapshot)
            self.assertEqual(submission[1:], ("alice", row.execution_id))
        again = self.execute()
        self.assertEqual([row.execution_id for row in again], [row.execution_id for row in rows])
        self.assertEqual(len(self.fake.submissions), 4)
        self.plan.requests[0].prompt = "Changed after approval"
        update_scene(self.db, self.scene, content="Edited after approval")
        with self.assertRaises(ExecutionConflict):
            self.execute()
        self.db.expire_all()
        self.assertNotEqual(get_execution(self.db, rows[0].execution_id, "alice").request_snapshot["prompt"], "Changed after approval")
        self.assertNotIn("Edited after approval", rows[0].request_snapshot["prompt"])

    def test_completed_sync_creates_artifact_once_and_failed_panel_creates_none(self):
        rows = self.execute()
        self.fake.states[rows[0].external_execution_id] = "running"
        self.assertEqual(self.sync(rows[0]).status, "running")
        self.fake.states[rows[0].external_execution_id] = "completed"
        self.assertEqual(self.sync(rows[0]).status, "completed")
        artifacts = list_artifacts(self.db, self.story.story_id, "alice")
        self.assertEqual(len(artifacts), 1)
        artifact = artifacts[0]
        self.assertEqual(artifact.execution_id, rows[0].execution_id)
        self.assertEqual(artifact.story_id, self.story.story_id)
        self.assertEqual(artifact.scene_id, self.scene.scene_id)
        self.assertEqual(artifact.media_type, "image")
        self.assertEqual(artifact.source, "generated")
        self.assertEqual(artifact.metadata_json, {"size_bytes": 321})
        self.assertIsNone(artifact.external_artifact_id)
        self.assertTrue(artifact.retrieval_reference.startswith("https://"))
        self.sync(rows[0])
        self.assertEqual(len(list_artifacts(self.db, self.story.story_id, "alice")), 1)
        self.assertEqual(self.fake.result_reads, 1)
        self.fake.states[rows[1].external_execution_id] = "failed"
        failed = self.sync(rows[1])
        self.assertEqual(failed.status, "failed")
        self.assertTrue(failed.error_message)
        self.assertIsNotNone(failed.completed_at)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Artifact)), 1)

    def test_submit_failures_and_retryable_poll_result_errors(self):
        self.fake.fail_panel = 2
        rows = self.execute()
        self.assertEqual([row.status for row in rows], ["submitted", "failed", "submitted", "submitted"])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Artifact)), 0)
        self.fake.poll_error = True
        self.assertEqual(self.sync(rows[0]).status, "submitted")
        self.assertIn("temporarily unavailable", rows[0].error_message)
        self.fake.poll_error = False
        self.fake.states[rows[0].external_execution_id] = "completed"
        self.fake.bad_result = True
        self.assertEqual(self.sync(rows[0]).status, "submitted")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Artifact)), 0)
        self.fake.bad_result = False
        self.assertEqual(self.sync(rows[0]).status, "completed")
        self.assertIsNone(rows[0].error_message)
        self.execute()
        self.assertEqual(len(self.fake.submissions), 4)

    def test_interrupted_submission_preserves_pending_approvals_without_resubmission(self):
        def interrupted(*args, **kwargs):
            raise KeyboardInterrupt("simulate process interruption")
        self.fake.submit = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.execute()
        rows = list(self.db.scalars(select(MediaExecution).order_by(MediaExecution.panel_number)))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row.status == "pending" for row in rows))
        self.assertTrue(rows[0].started_at)
        self.assertEqual(len(self.execute()), 4)
        pending = self.sync(rows[0])
        self.assertEqual(pending.status, "pending")
        self.assertIn("reconciliation", pending.error_message)

    def test_missing_mismatched_and_foreign_resources_fail_before_submission(self):
        other = create_story(self.db, "alice", title="Other")
        scene = create_scene(self.db, story_id=other.story_id, content="Other scene")
        for args in [{"story_id": "missing"}, {"scene_id": "missing"}, {"user_id": "bob"}, {"scene_id": scene.scene_id}]:
            with self.subTest(args=args), self.assertRaises(MediaDomainNotFound):
                self.execute(**args)
        wrong = self.plan.model_copy(deep=True)
        wrong.story_id = other.story_id
        with self.assertRaises(InvalidMediaIntent):
            self.execute(plan=wrong)
        duplicate = self.plan.model_copy(deep=True)
        duplicate.requests[1].media_request_id = duplicate.requests[0].media_request_id
        with self.assertRaises(InvalidMediaIntent):
            self.execute(plan=duplicate)
        character = create_character(self.db, other.story_id, name="Foreign")
        foreign = self.plan.model_copy(deep=True)
        foreign.requests[0].references[0].reference_id = character.character_id
        with self.assertRaises(MediaDomainNotFound):
            self.execute(plan=foreign)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MediaExecution)), 0)
        self.assertEqual(self.fake.submissions, [])

    def test_service_owner_checks_and_backend_mismatch(self):
        row = self.execute()[0]
        with self.assertRaises(MediaDomainNotFound):
            get_execution(self.db, row.execution_id, "bob")
        with self.assertRaises(MediaDomainNotFound):
            list_artifacts(self.db, self.story.story_id, "bob")
        with self.assertRaises(MediaDomainNotFound):
            sync_execution(self.db, execution_id=row.execution_id, user_id="bob", client=self.fake)
        self.fake.backend_name = "other"
        with self.assertRaises(ExecutionConflict):
            self.sync(row)


class ExecutionAPITests(ExecutionFixture):
    def setUp(self):
        super().setUp()
        def override_db():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_execution_client] = lambda: self.fake
        self.client = TestClient(app)
        self.sign_in("alice")
        self.url = f"/api/stories/{self.story.story_id}/scenes/{self.scene.scene_id}/storyboard/four-panel/execute"
        self.body = {"approved": True, "plan": self.plan.model_dump(mode="json")}

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        super().tearDown()

    def sign_in(self, user_id):
        token = AuthSessionManager(os.environ["SANDCASTLE_AUTH_SECRET"]).create_session_token(
            AuthenticatedIdentity(user_id, f"{user_id}@example.test", user_id),
        )
        self.client.cookies.set(SESSION_COOKIE, token)

    def test_approve_read_sync_artifacts_and_cross_user_isolation(self):
        result = self.client.post(self.url, json=self.body)
        self.assertEqual(result.status_code, 201, result.text)
        rows = result.json()
        self.assertEqual(len(rows), 4)
        execution_id = rows[0]["execution_id"]
        self.assertEqual(self.client.get(f"/api/media/executions/{execution_id}").status_code, 200)
        self.fake.states[rows[0]["external_execution_id"]] = "completed"
        synced = self.client.post(f"/api/media/executions/{execution_id}/sync")
        self.assertEqual(synced.json()["status"], "completed", synced.text)
        artifact_url = f"/api/stories/{self.story.story_id}/artifacts"
        artifacts = self.client.get(artifact_url).json()
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["metadata"], {"size_bytes": 321})
        artifact_id = artifacts[0]["artifact_id"]
        self.sign_in("bob")
        for path in [f"/api/media/executions/{execution_id}", f"/api/media/artifacts/{artifact_id}", artifact_url,
                     f"/api/stories/{self.story.story_id}/media/executions"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(f"/api/media/executions/{execution_id}/sync").status_code, 404)
        self.assertEqual(self.client.post(self.url, json=self.body).status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url, json=self.body).status_code, 401)

    def test_explicit_approval_input_validation_and_snapshot_conflict(self):
        for body in [{}, {"approved": False, "plan": self.body["plan"]},
                     {"approved": 1, "plan": self.body["plan"]}, {"plan": self.body["plan"]}]:
            self.assertEqual(self.client.post(self.url, json=body).status_code, 422)
        self.assertEqual(self.client.post(self.url.replace(self.scene.scene_id, "missing"), json=self.body).status_code, 404)
        self.assertEqual(self.client.post(self.url, json=self.body).status_code, 201)
        changed = copy.deepcopy(self.body)
        changed["plan"]["requests"][0]["prompt"] = "Changed request"
        self.assertEqual(self.client.post(self.url, json=changed).status_code, 409)
        self.assertEqual(len(self.fake.submissions), 4)

    def test_default_adapter_is_fail_closed_but_approval_remains_durable(self):
        app.dependency_overrides.pop(get_execution_client)
        response = self.client.post(self.url, json=self.body)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual([row["status"] for row in response.json()], ["failed"] * 4)
        self.assertTrue(all("service-caller" in row["error_message"] for row in response.json()))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MediaExecution)), 4)
