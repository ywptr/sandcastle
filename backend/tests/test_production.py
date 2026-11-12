"""Text-only production translation/review/approval; no live IS, provider, or media calls."""
import copy
import os
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import func, select
import test_world_api
from app.main import app
from app.api.production import get_translator_resolver
from app.db.database import Base
from app.db.models import ApprovedMediaAdaptation, Artifact, MediaExecution
from app.llm.resolver import resolve_adapter
from app.llm.service import set_provider_config
from app.llm.schemas import ProviderUpdate
from app.media.production.compiler import compile_instructions, compile_manifest
from app.media.production.schemas import MediaProductionPlan, ProductionProposal
from app.media.production import service

SOURCE = "Mara enters the abandoned station. An old radio lights up. Elias's voice comes through. Mara answers, but the transmission cuts out."


def proposal(target="webtoon", character_ids=None, place_ids=None, artifact_ids=None):
    base = dict(narrative_purpose="Reveal the unexpected signal", source_excerpt="An old radio lights up.",
        visual_description="Mara looks toward a newly lit radio.", character_ids=character_ids or [], place_ids=place_ids or [],
        artifact_ids=artifact_ids or [], continuity_notes=["Keep the identity of the speaker uncertain."])
    if target == "webtoon":
        production = dict(target_format=target, reading_order="top_to_bottom", layout_hint="A vertical reveal.", panels=[
            dict(**base, panel_number=1, framing="wide", dialogue="", caption=""),
            dict(**base, panel_number=2, framing="close_up", dialogue="Elias?", caption="")])
    elif target == "short_drama":
        production = dict(target_format=target, target_duration_seconds=8, audio_direction="A short radio crackle.", shots=[
            dict(**base, shot_number=1, estimated_duration=3, shot_scale="wide", camera_direction="Hold.", performance_direction="Notice the light.", dialogue="", voiceover="", audio_or_ambience="Silence."),
            dict(**base, shot_number=2, estimated_duration=5, shot_scale="close_up", camera_direction="Slow push.", performance_direction="Restrained surprise.", dialogue="Elias?", voiceover="", audio_or_ambience="Radio crackle.")])
    else:
        production = dict(target_format=target, target_duration_seconds=6, narration_text_strategy="Read the reveal before the reaction.", visual_strategy="Alternate place and reaction.", beats=[
            dict(**base, beat_number=1, duration=3, on_screen_text="A signal.", voiceover="", transition_hint="Cut."),
            dict(**base, beat_number=2, duration=3, on_screen_text="Then silence.", voiceover="Elias…", transition_hint="Hold.")])
    return dict(summary="Suara radio memecah keheningan stasiun dan membuat Mara menoleh dengan penuh rasa ingin tahu.", production=production, continuity_notes=["Preserve the unresolved transmission."],
        warnings=[dict(code="continuity_uncertainty", message="Confirm whether Elias is a recorded or live voice.")])


class FakeTranslator:
    def __init__(self):
        self.contexts = []
        self.output = None
        self.failure = False

    async def translate(self, context):
        self.contexts.append(context)
        if self.failure:
            raise RuntimeError("secret-provider-error-do-not-expose")
        return copy.deepcopy(self.output) if self.output is not None else proposal(context.target_format,
            [c.character_id for c in context.continuity.characters], [p.place_id for p in context.continuity.places],
            [r.reference_id for r in context.continuity.references if r.kind == "artifact"])


class ProductionTests(unittest.TestCase):
    def setUp(self):
        # Earlier Alembic tests configure logging with disable_existing_loggers=True.
        logging_patch = patch.object(service.logger, "disabled", False)
        logging_patch.start()
        self.addCleanup(logging_patch.stop)
        self.world = test_world_api.WorldAPITests(); self.world.setUp()
        self.client, self.sessions = self.world.client, self.world.sessions
        self.scene = self.world.post(self.world.root+"/scenes", {"title":"The signal", "content":SOURCE})
        self.character = self.world.post(self.world.root+"/characters", {"name":"Mara", "appearance":"Dark curls", "outfit":"Blue coat"})
        self.place = self.world.post(self.world.root+"/places", {"name":"Abandoned station", "appearance":"Dusty radio room"})
        self.world.post(self.world.root+"/canon", {"type":"world", "key":"radio.state", "value":"The station is abandoned."})
        self.world.patch(self.world.root, {"language":"id", "primary_genre":"mystery", "secondary_genres":["drama"]})
        self.base = self.world.root+"/scenes/"+self.scene["scene_id"]+"/adaptations"
        self.fake = FakeTranslator(); self.resolutions = []
        def resolver(db, user_id, role):
            self.resolutions.append((user_id,role)); return self.fake
        app.dependency_overrides[get_translator_resolver] = lambda: resolver

    def tearDown(self):
        self.world.tearDown()

    def translated(self, target="webtoon"):
        r = self.client.post(self.base, json={"target_format":target})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def approve(self, plan):
        r = self.client.post(self.base+"/approve", json={"approved":True,"plan":plan})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def counts(self):
        with self.sessions() as db:
            return {table.name:db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}

    def test_authentication_ownership_checked_before_provider_resolution(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.base,json={"target_format":"webtoon"}).status_code,401)
        self.world.sign_in("bob")
        self.assertEqual(self.client.post(self.base,json={"target_format":"webtoon"}).status_code,404)
        self.assertEqual(self.client.get(self.base).status_code,404)
        self.assertEqual(self.resolutions,[])

    def test_all_formats_typed_ephemeral_context_and_no_media_execution(self):
        before = self.counts()
        with patch("httpx.AsyncClient.send",side_effect=AssertionError("No media or content HTTP in domain planning")):
            for target in ["webtoon","short_drama","story_reel"]:
                plan = self.translated(target)
                self.assertEqual(MediaProductionPlan.model_validate(plan).target_format,target)
                self.assertEqual(len(plan["compiled_instructions"]),2)
                self.assertTrue(plan["source_digest"])
        context = self.fake.contexts[-1]
        self.assertEqual(context.scene.content,SOURCE)
        self.assertEqual(context.continuity.story.language,"id")
        self.assertEqual(context.continuity.story.primary_genre,"mystery")
        self.assertEqual(context.continuity.characters[0].character_id,self.character["character_id"])
        self.assertEqual(context.continuity.places[0].place_id,self.place["place_id"])
        self.assertEqual(context.continuity.canon[0].value,"The station is abandoned.")
        self.assertEqual(context.workflow["difficulty"],"easy")
        self.assertEqual(self.resolutions,[('alice','narrative_media_translator')]*3)
        self.assertEqual(self.counts(),before)

    def test_no_configured_provider_safe_503(self):
        app.dependency_overrides.pop(get_translator_resolver)
        before = self.counts()
        r = self.client.post(self.base,json={"target_format":"webtoon"})
        self.assertEqual(r.status_code,503)
        self.assertEqual(self.counts(),before)

    def test_role_routes_all_three_adapters_with_existing_credentials(self):
        with patch.dict(os.environ,SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            for provider,prefix in [('openai','OpenAI'),('anthropic','Anthropic'),('google','Google')]:
                with self.sessions() as db:
                    for row in db.scalars(select(__import__('app.db.models',fromlist=['LLMProviderConfig']).LLMProviderConfig)):
                        row.enabled=False
                    db.commit()
                    set_provider_config(db,'alice',provider,ProviderUpdate(enabled=True,credentials={'api_key':'fake-provider-test'},config={'default_model':'test-model'}))
                    adapter=resolve_adapter(db,'alice','narrative_media_translator')
                    self.assertEqual(type(adapter).__name__,prefix+'NarrativeMediaTranslator')

    def test_provider_failures_and_invalid_results_never_persist(self):
        before=self.counts();self.fake.failure=True
        r=self.client.post(self.base,json={"target_format":"webtoon"})
        self.assertEqual(r.status_code,502);self.assertNotIn('secret-provider-error',r.text)
        self.fake.failure=False
        for output in [{},proposal('short_drama'),{**proposal(), 'unexpected':'value'}]:
            self.fake.output=output
            self.assertEqual(self.client.post(self.base,json={"target_format":"webtoon"}).status_code,502)
        self.assertEqual(self.counts(),before)

    def test_character_place_artifact_and_evidence_validation(self):
        for field,value in [('character_ids',['invented']),('place_ids',['invented']),('artifact_ids',['foreign-artifact']),('source_excerpt','Invented narrative')]:
            plan=self.translated();plan['production']['panels'][0][field]=value
            self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':plan}).status_code,422)
        output=proposal(character_ids=['invented']);self.fake.output=output
        self.assertEqual(self.client.post(self.base,json={'target_format':'webtoon'}).status_code,502)
        self.assertEqual(self.counts()['approved_media_adaptations'],0)

    def test_classified_failures_log_safely_and_leave_every_table_unchanged(self):
        from unittest.mock import AsyncMock
        from app.llm.errors import ProviderFailed, ProviderIncomplete, ProviderOutputInvalid
        from app.media.production.diagnostics import TranslationFailed
        secret = "private-provider-payload-never-log"
        cases = [
            (ProviderFailed(secret), None, "provider_request_failed", "request_failed"),
            (ProviderIncomplete(secret), None, "provider_incomplete", "response_not_completed"),
            (ProviderOutputInvalid(secret), None, "provider_structured_output_invalid", "credential_output_rejected"),
            (TranslationFailed("provider_structured_output_invalid", "parsed_output_missing"), None,
                "provider_structured_output_invalid", "parsed_output_missing"),
            (None, {"summary": secret}, "schema_validation_failed", "invalid_proposal_schema"),
            (RuntimeError(secret), None, "unexpected_translation_failure", "internal_error"),
            (None, proposal("short_drama"), "domain_validation_failed", "wrong_target_format"),
        ]
        for field, value, reason in [
            ("source_excerpt", "Paraphrased source", "source_excerpt_not_exact"),
            ("character_ids", ["invented"], "unavailable_character_id"),
            ("place_ids", ["invented"], "unavailable_place_id"),
            ("artifact_ids", ["invented"], "unavailable_artifact_id"),
        ]:
            output = proposal(); output["production"]["panels"][0][field] = value
            cases.append((None, output, "domain_validation_failed", reason))
        output = proposal("short_drama"); output["production"]["target_duration_seconds"] = 99
        cases.append((None, output, "schema_validation_failed", "duration_mismatch"))
        artifact = self.world.post("/api/artifacts", {"source": "external", "story_id": self.world.story["story_id"],
            "retrieval_reference": "https://media.example.test/diagnostic"})
        self.world.post(self.world.root + "/references", {"artifact_id": artifact["artifact_id"], "target_type": "character",
            "target_id": self.character["character_id"], "role": "character_identity"})
        cases.append((None, proposal(artifact_ids=[artifact["artifact_id"]]), "domain_validation_failed", "artifact_binding_mismatch"))
        def snapshot():
            with self.sessions() as db:
                return {table.name: [dict(row) for row in db.execute(select(table)).mappings()]
                    for table in Base.metadata.sorted_tables}
        before = snapshot()
        for error, output, category, reason in cases:
            with self.subTest(category=category, reason=reason):
                with patch.object(self.fake, "translate", AsyncMock(side_effect=error, return_value=output)), \
                     self.assertLogs("app.media.production.service", level="WARNING") as captured:
                    response = self.client.post(self.base, json={"target_format": "webtoon"})
                self.assertEqual(response.status_code, 502)
                logs = "\n".join(captured.output)
                self.assertIn("category=" + category, logs)
                self.assertIn("reason=" + reason, logs)
                self.assertNotIn(secret, logs + response.text)
                self.assertNotIn(SOURCE, logs + response.text)
                self.assertEqual(snapshot(), before)
        with patch("app.media.production.service.compile_instructions", side_effect=RuntimeError(secret)), \
             self.assertLogs("app.media.production.service", level="WARNING") as captured:
            # Select a valid unbound proposal so the compiler is reached.
            self.fake.output = proposal()
            response = self.client.post(self.base, json={"target_format": "webtoon"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("unexpected_translation_failure", str(captured.output))
        self.assertNotIn(secret, str(captured.output) + response.text)
        self.assertEqual(snapshot(), before)

    def test_source_evidence_requires_verbatim_contiguous_original_text(self):
        for excerpt in ["An old radio lights up!", "Radio menyala.",
                        "Mara enters … the transmission cuts out.", "Elias’s voice comes through.",
                        "An old radio lights up. Mara answers"]:
            output = proposal(); output["production"]["panels"][0]["source_excerpt"] = excerpt
            self.fake.output = output
            with self.assertLogs("app.media.production.service", level="WARNING") as captured:
                response = self.client.post(self.base, json={"target_format": "webtoon"})
            self.assertEqual(response.status_code, 502)
            self.assertIn("source_excerpt_not_exact", str(captured.output))
        self.fake.output = proposal()
        self.fake.output["production"]["panels"][0]["source_excerpt"] = "Elias's voice comes through."
        self.translated()

    def test_prompt_allowlists_are_exact_and_empty_when_no_records_selected(self):
        self.translated()
        context = self.fake.contexts[-1]
        data = context.narrative_data()
        self.assertEqual(data["allowed_ids"]["character_ids"], [self.character["character_id"]])
        self.assertEqual(data["allowed_ids"]["place_ids"], [self.place["place_id"]])
        self.assertEqual(data["allowed_ids"]["artifact_ids"], [])
        from dataclasses import replace
        continuity = context.continuity.model_copy(update={"characters": [], "places": []})
        self.assertEqual(replace(context, continuity=continuity).narrative_data()["allowed_ids"],
            {"character_ids": [], "place_ids": [], "artifact_ids": []})

    def test_metadata_only_artifact_reference_and_no_duplicate_storage(self):
        artifact=self.world.post('/api/artifacts',{'source':'external','story_id':self.world.story['story_id'],'display_name':'Station reference','retrieval_reference':'https://media.example.test/reference'})
        self.world.post(self.world.root+'/references',{'artifact_id':artifact['artifact_id'],'target_type':'story','role':'visual_style'})
        before=self.counts()
        with patch('httpx.AsyncClient.send',side_effect=AssertionError('No content reads')):
            plan=self.translated();saved=self.approve(plan)
        self.assertIn(artifact['artifact_id'],plan['production']['panels'][0]['artifact_ids'])
        self.assertNotIn('https://media.example.test',str(plan))
        self.assertNotIn('retrieval_reference',str(plan))
        self.assertTrue(any(r['reference_id']==artifact['artifact_id'] for r in saved['manifest']['requests'][0]['references']))
        after=self.counts();self.assertEqual(after['artifacts'],before['artifacts']);self.assertEqual(after['media_executions'],before['media_executions'])

    def test_compiler_determinism_and_client_output_is_not_trusted(self):
        plan=self.translated();typed=MediaProductionPlan.model_validate(plan)
        self.assertEqual(compile_instructions(typed),compile_instructions(typed))
        self.assertEqual(compile_manifest(typed),compile_manifest(typed))
        plan['compiled_instructions'][0]['compiled']='FAKE COMPILER OUTPUT'
        plan['compiled_instructions'][0]['effective']='FAKE COMPILER OUTPUT'
        r=self.client.post(self.base+'/compile',json={'plan':plan})
        self.assertEqual(r.status_code,200)
        self.assertNotIn('FAKE COMPILER OUTPUT',str(r.json()))
        self.assertIn('The station is abandoned.',r.json()['plan']['compiled_instructions'][0]['compiled'])

    def test_explicit_override_distinct_and_difficulty_enforced(self):
        plan=self.translated();plan['overrides']=[{'beat_number':1,'instruction':'Use a low viewpoint.'}]
        self.assertEqual(self.client.post(self.base+'/compile',json={'plan':plan}).status_code,422)
        r=self.client.put(self.world.root+'/workflow',json={'difficulty':'difficult','workflow_template_id':'standard-story','template_version':1})
        self.assertEqual(r.status_code,200,r.text)
        r=self.client.post(self.base+'/compile',json={'plan':plan})
        self.assertEqual(r.status_code,200,r.text)
        instruction=r.json()['plan']['compiled_instructions'][0]
        self.assertEqual(instruction['override'],'Use a low viewpoint.')
        self.assertNotIn('Use a low viewpoint.',instruction['compiled'])
        self.assertIn('The station is abandoned.',instruction['effective'])
        saved=self.approve(r.json()['plan'])
        self.assertEqual(saved['plan']['overrides'],plan['overrides'])

    def test_approval_atomic_idempotent_and_immutable_revisions(self):
        plan=self.translated();before=self.counts()
        first=self.approve(plan);again=self.approve(plan)
        self.assertEqual(first['adaptation_id'],again['adaptation_id'])
        self.assertEqual(first['revision'],1)
        edited=copy.deepcopy(first['plan']);edited['production']['panels'][0]['visual_description']='A wider view of the same radio.'
        second=self.approve(edited);self.assertEqual(second['revision'],2)
        self.assertNotEqual(first['adaptation_id'],second['adaptation_id'])
        original=self.client.get('/api/media/adaptations/'+first['adaptation_id']).json()
        self.assertEqual(original['plan'],first['plan'])
        self.assertEqual(original['manifest'],first['manifest'])
        self.assertEqual(original['plan']['warnings'],plan['warnings'])
        after=self.counts()
        for key in before:
            self.assertEqual(after[key],before[key]+(2 if key=='approved_media_adaptations' else 0),key)

    def test_stale_source_and_context_are_detected_without_mutating_approval(self):
        plan=self.translated();first=self.approve(plan)
        self.world.patch(self.world.root+'/scenes/'+self.scene['scene_id'],{'content':SOURCE+' Then the room darkens.'})
        r=self.client.get(self.base);self.assertEqual(r.status_code,200)
        self.assertTrue(r.json()[0]['source_changed'])
        self.assertEqual(r.json()[0]['plan'],first['plan'])
        edited=copy.deepcopy(plan);edited['summary']='A revised interpretation.'
        self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':edited}).status_code,409)
        self.world.patch(self.world.root+'/scenes/'+self.scene['scene_id'],{'content':SOURCE})
        self.world.patch(self.world.root,{'objective':'Follow the signal'})
        self.assertTrue(self.client.get(self.base).json()[0]['context_changed'])
        self.assertEqual(self.client.post(self.base+'/compile',json={'plan':plan}).status_code,409)

    def test_tampered_authoritative_context_and_cross_user_history_denied(self):
        plan=self.translated();saved=self.approve(plan)
        plan['continuity_context']['canon']=[]
        self.assertEqual(self.client.post(self.base+'/compile',json={'plan':plan}).status_code,409)
        self.world.sign_in('bob')
        self.assertEqual(self.client.get('/api/media/adaptations/'+saved['adaptation_id']).status_code,404)
        self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':saved['plan']}).status_code,404)

    def test_schema_bounds_and_approval_required(self):
        for target in ['episode','image','video','custom']:
            self.assertEqual(self.client.post(self.base,json={'target_format':target}).status_code,422)
        plan=self.translated()
        self.assertEqual(self.client.post(self.base+'/approve',json={'plan':plan}).status_code,422)
        self.assertEqual(self.client.post(self.base+'/approve',json={'approved':False,'plan':plan}).status_code,422)
        for panels in [[],[plan['production']['panels'][0]]*13]:
            value=copy.deepcopy(plan);value['production']['panels']=panels
            self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':value}).status_code,422)
        drama=self.translated('short_drama')
        for duration in [-1,0,31,True,1.5]:
            value=copy.deepcopy(drama);value['production']['shots'][0]['estimated_duration']=duration
            self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':value}).status_code,422)
        drama['production']['target_duration_seconds']=99
        self.assertEqual(self.client.post(self.base+'/approve',json={'approved':True,'plan':drama}).status_code,422)

    def test_failed_approval_rolls_back(self):
        plan=MediaProductionPlan.model_validate(self.translated())
        with self.sessions() as db,patch.object(db,'commit',side_effect=RuntimeError('storage-error')):
            with self.assertRaises(HTTPException) as caught:
                service.approve_plan(db,self.world.story['story_id'],self.scene['scene_id'],'alice',plan)
            self.assertEqual(caught.exception.status_code,503)
        self.assertEqual(self.counts()['approved_media_adaptations'],0)

    def test_subject_reference_binding_is_available_to_translator_and_validated_per_beat(self):
        artifact=self.world.post('/api/artifacts',{'source':'external','story_id':self.world.story['story_id'],'retrieval_reference':'https://media.example.test/mara'})
        self.world.post(self.world.root+'/references',{'artifact_id':artifact['artifact_id'],'target_type':'character','target_id':self.character['character_id'],'role':'character_identity'})
        plan=self.translated()
        binding=plan['continuity_context']['reference_bindings'][0]
        self.assertEqual((binding['target_type'],binding['target_id']),('character',self.character['character_id']))
        self.assertNotIn('retrieval_reference',binding)
        self.assertNotIn('metadata',binding)
        plan['production']['panels'][0]['character_ids']=[]
        self.assertEqual(self.client.post(self.base+'/compile',json={'plan':plan}).status_code,422)
