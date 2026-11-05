import asyncio
from copy import deepcopy
from unittest.mock import patch
from fastapi import HTTPException
from pydantic import ValidationError
from test_universes import UniverseFixture
from app.db.models import StoryWorkflow
from app.workflows import registry, service
from app.workflows.schemas import StoryWorkflowInput, WorkflowConfiguration, WorkflowAction
from app.guidance.generator import DeterministicSuggestionGenerator
from app.canon.deterministic_extractor import DeterministicCanonExtractor
from app.media.adaptation.planner import DeterministicShotPlanner
from app.stories.scene_service import create_scene


class WorkflowTests(UniverseFixture):
    def save(self, difficulty="normal", template="standard-story", configuration=None):
        return service.save_workflow(self.db, self.a.story_id, "alice", StoryWorkflowInput(
            difficulty=difficulty, workflow_template_id=template, configuration=configuration))

    def act(self, step, scene_id=None, generator=None):
        return asyncio.run(service.perform_step(self.db, self.a.story_id, "alice", step, WorkflowAction(scene_id=scene_id),
            generator=generator or DeterministicSuggestionGenerator(), extractor=DeterministicCanonExtractor(), planner=DeterministicShotPlanner()))

    def test_capabilities_are_monotonic_and_templates_are_not_billing(self):
        levels = registry.difficulties()
        self.assertEqual([row["id"] for row in levels], ["easy", "normal", "difficult", "impossible"])
        for left, right in zip(levels, levels[1:]):
            self.assertLess(set(left["capabilities"]), set(right["capabilities"]))
        self.assertEqual(len(registry.list_templates()), 4)
        self.assertIn("media_adaptation", registry.get_template("webtoon")["configuration"]["order"])
        self.assertNotIn("billing", str(levels))
        self.assertFalse(any(s["enabled"] for s in registry.get_template("standard-story")["configuration"]["steps"] if s["step_id"] == "media_execution"))

    def test_lazy_defaults_selection_and_version_pinning(self):
        default = service.read_workflow(self.db, self.a.story_id, "alice")
        self.assertEqual((default["difficulty"], default["workflow_template_id"], default["template_version"]), ("easy", "standard-story", 1))
        self.assertIsNone(self.db.get(StoryWorkflow, self.a.story_id))
        saved = self.save(template="guided-story")
        self.assertEqual(saved["configuration"]["guidance"]["recent_scene_count"], 5)
        newer = deepcopy(registry.get_template("guided-story"))
        newer["version"] = 2
        newer["configuration"]["guidance"]["count"] = 1
        with patch.dict(registry.TEMPLATES, {("guided-story", 2): newer}):
            current = service.read_workflow(self.db, self.a.story_id, "alice")
            self.assertEqual(current["template_version"], 1)
            self.assertEqual(current["configuration"]["guidance"]["count"], 3)
            service.save_workflow(self.db, self.a.story_id, "alice", StoryWorkflowInput(difficulty="normal", workflow_template_id="guided-story", template_version=2))
            self.assertEqual(service.read_workflow(self.db, self.a.story_id, "alice")["template_version"], 2)

    def test_easy_cannot_configure_advanced_normal_can_configure_supported_options(self):
        config = WorkflowConfiguration()
        config.guidance.count = 2
        with self.assertRaises(HTTPException): self.save("easy", configuration=config)
        with self.assertRaises(HTTPException): self.save("easy", template="webtoon")
        saved = self.save(configuration=config)
        self.assertEqual(saved["configuration"]["guidance"]["count"], 2)
        config.steps[0].enabled = False
        with self.assertRaises(HTTPException): self.save("normal", configuration=config)
        self.assertFalse(self.save("difficult", configuration=config)["configuration"]["steps"][0]["enabled"])
        config.references.artifact_ids = ["example"]
        with self.assertRaises(HTTPException): self.save("difficult", configuration=config)
        self.assertEqual(self.save("impossible", configuration=config)["configuration"]["references"]["artifact_ids"], ["example"])

    def test_invalid_structure_order_and_unknown_configuration_rejected(self):
        default = WorkflowConfiguration().model_dump()
        bad = deepcopy(default); bad["order"][5], bad["order"][6] = bad["order"][6], bad["order"][5]
        with self.assertRaises(ValidationError): WorkflowConfiguration.model_validate(bad)
        bad = deepcopy(default); bad["steps"][5]["enabled"] = False
        with self.assertRaises(ValidationError): WorkflowConfiguration.model_validate(bad)
        bad = deepcopy(default); bad["steps"][-1]["enabled"] = True
        with self.assertRaises(ValidationError): WorkflowConfiguration.model_validate(bad)
        with self.assertRaises(ValidationError): WorkflowConfiguration.model_validate({**default, "provider": "specific"})
        valid = deepcopy(default); valid["order"][3], valid["order"][4] = valid["order"][4], valid["order"][3]
        saved = self.save("difficult", configuration=WorkflowConfiguration.model_validate(valid))
        self.assertEqual(saved["configuration"]["order"], valid["order"])

    def test_saved_guidance_options_delegate_without_creating_scene_or_canon(self):
        from sqlalchemy import select, func
        from app.db.models import Scene, CanonCandidate
        config = WorkflowConfiguration()
        config.guidance.count = 2
        config.guidance.recent_scene_count = 1
        self.save(configuration=config)
        create_scene(self.db, story_id=self.a.story_id, content="First scene")
        create_scene(self.db, story_id=self.a.story_id, content="Edited latest scene")
        class Capture:
            async def suggest(self, context, *, count):
                self.context = context
                return await DeterministicSuggestionGenerator().suggest(context, count=count)
        fake = Capture()
        before = self.db.scalar(select(func.count()).select_from(Scene))
        result = self.act("narrative_guidance", generator=fake)
        self.assertEqual(len(result.suggestions), 2)
        self.assertEqual(len(fake.context.recent_scenes), 1)
        self.assertEqual([f["value"] for f in fake.context.canon], ["blue"])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Scene)), before)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(CanonCandidate)), 0)

    def test_strict_checkpoint_uses_m7_and_media_remains_m9c_adapted(self):
        from app.canon.candidate_service import propose_candidate, approve_candidate
        from app.canon.candidate_schemas import ManualCandidate, CandidateApproval
        self.save(template="canon-strict")
        scene = create_scene(self.db, story_id=self.a.story_id, content="A character is stabbed during a confrontation.")
        candidate = propose_candidate(self.db, story_id=self.a.story_id, user_id="alice", proposal=ManualCandidate(
            type="world", key="gravity", value="Normal", evidence="Author choice"))
        self.assertEqual(candidate.classification, "new")
        with self.assertRaises(HTTPException) as blocked: self.act("media_adaptation", scene.scene_id)
        self.assertEqual(blocked.exception.status_code, 409)
        self.assertEqual(candidate.status, "pending")
        approve_candidate(self.db, story_id=self.a.story_id, user_id="alice", candidate_id=candidate.canon_candidate_id, approval=CandidateApproval())
        adapted = self.act("media_adaptation", scene.scene_id)
        self.assertIn("violence", adapted.sensitivities)
        storyboard = self.act("storyboard_planning", scene.scene_id)
        self.assertEqual(len(storyboard.requests), 4)
        self.assertTrue(all("stabbed" not in r.prompt for r in storyboard.requests))
        with self.assertRaises(HTTPException): self.act("media_execution", scene.scene_id)


class WorkflowAPITests(UniverseFixture):
    def test_authenticated_contract_selection_actions_and_ownership(self):
        from fastapi.testclient import TestClient
        from app.api.dependencies import get_current_identity, get_db
        from app.auth.identity import AuthenticatedIdentity
        from app.main import app
        def database(): yield self.db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("alice", "alice@example.test", "Alice")
        try:
            with TestClient(app) as client:
                base = f"/api/stories/{self.a.story_id}/workflow"
                self.assertEqual(len(client.get("/api/workflows/difficulties").json()), 4)
                self.assertEqual(client.get("/api/workflows/templates/standard-story").status_code, 200)
                self.assertEqual(client.get("/api/workflows/templates/missing").status_code, 404)
                self.assertEqual(client.get(base).json()["difficulty"], "easy")
                selected = client.put(base, json={"difficulty": "normal", "workflow_template_id": "webtoon"})
                self.assertEqual(selected.status_code, 200, selected.text)
                self.assertEqual(client.post(base + "/steps/narrative_guidance", json={}).status_code, 200)
                self.assertEqual(client.post(base + "/steps/media_execution", json={}).status_code, 409)
                self.assertEqual(client.post(base + "/steps/storyboard_planning", json={}).status_code, 422)
                self.assertEqual(client.post(base + "/steps/custom-code", json={}).status_code, 422)
                app.dependency_overrides[get_current_identity] = lambda: AuthenticatedIdentity("bob", "bob@example.test", "Bob")
                self.assertEqual(client.get(base).status_code, 404)
                self.assertEqual(client.put(base, json={}).status_code, 404)
                self.assertEqual(client.post(base + "/steps/narrative_guidance", json={}).status_code, 404)
                app.dependency_overrides.pop(get_current_identity)
                self.assertEqual(client.get("/api/workflows/templates").status_code, 401)
        finally:
            app.dependency_overrides.clear()
