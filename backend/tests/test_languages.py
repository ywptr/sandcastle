"""C2 real detector/service contracts; no live model calls or external database."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.languages.service import detect, production_language, conversation_language, validate_output
import test_world_api as world
from app.main import app
from app.api.creative_direction import get_recommender
from app.creative_direction.schemas import Recommendation
from app.db.models import StoryAction
from sqlalchemy import select

EN = "A young girl discovers a secret map in the library and tries to save her family before sunrise."
ID = "Seorang gadis menemukan peta rahasia di perpustakaan dan berusaha menyelamatkan keluarganya sebelum matahari terbit."
TEXTS = {
 "en": EN, "id": ID,
 "ja":"少女は図書館で秘密の地図を見つけて、夜明け前に家族を救うために未知の街へ旅立ちます。",
 "ko":"어린 소녀는 도서관에서 비밀 지도를 발견하고 해가 뜨기 전에 가족을 구하기 위해 낯선 도시로 떠납니다.",
 "zh-CN":"一个年轻的女孩在图书馆发现了一张秘密地图，为了在日出之前拯救自己的家人，她决定前往陌生的城市。",
 "fr":"Une jeune fille découvre une carte secrète dans la bibliothèque et tente de sauver sa famille avant le lever du soleil.",
 "de":"Ein junges Mädchen entdeckt eine geheime Karte in der Bibliothek und versucht ihre Familie vor Sonnenaufgang zu retten.",
 "es":"Una joven descubre un mapa secreto en la biblioteca e intenta salvar a su familia antes del amanecer.",
}


class DetectionTests(unittest.TestCase):
 def test_eight_language_profiles_and_seeded_repeatability(self):
  for code,text in TEXTS.items():
   with self.subTest(code=code):
    self.assertEqual(detect(text)["language"],code)
    self.assertEqual(detect(text),detect(text))
 def test_uncertainty_mixing_quotes_and_empty(self):
  for text in ["", "Hello", "Mara Daniel", "12345", "```import some_module with a very_long_name```", EN+" "+ID, "هذه قصة طويلة عن فتاة تبحث عن عائلتها في مدينة بعيدة قبل شروق الشمس."]:
   with self.subTest(text=text):self.assertTrue(detect(text)["review_required"])
  self.assertEqual(detect(ID+' She calls him "Alexander the Great".')['language'],'id')
  self.assertEqual(detect(EN+' Her friend is named Sakura.')['language'],'en')
 def test_precedence_and_output_checks(self):
  self.assertEqual(production_language('id','fr')['language'],'fr')
  self.assertEqual(production_language('id')['language'],'id')
  self.assertTrue(production_language(None)['fallback'])
  self.assertEqual(conversation_language(EN,saved='id')['language'],'en')
  self.assertEqual(conversation_language(ID,'fr','de','en')['language'],'fr')
  self.assertEqual(conversation_language('Hi',preference='de')['language'],'de')
  self.assertEqual(validate_output(ID,'id'),'verified')
  with self.assertRaises(HTTPException):validate_output(EN,'id')
  self.assertEqual(validate_output('Mara?','id'),'unverified_short_or_ambiguous')


class LanguageAPITests(unittest.TestCase):
 setUp=world.WorldAPITests.setUp
 tearDown=world.WorldAPITests.tearDown
 sign_in=world.WorldAPITests.sign_in
 post=world.WorldAPITests.post
 patch=world.WorldAPITests.patch
 def test_creation_auto_confirmation_provenance_and_backward_compatibility(self):
  response=self.client.post('/api/languages/detect',json={'text':ID});self.assertEqual(response.status_code,200);self.assertEqual(response.json()['language'],'id')
  self.assertEqual(response.headers['cache-control'],'no-store')
  data=dict(title='Peta',premise=ID,language='id',language_mode='automatic')
  story=self.post('/api/stories',data);self.assertEqual(story['language'],'id');self.assertEqual(story['language_provenance']['source'],'automatic_creation');self.assertNotIn(ID,str(story['language_provenance']))
  self.post('/api/stories',{**data,'language':'en'},expected=422)
  self.post('/api/stories',{**data,'premise':'Mara'},expected=422)
  self.post('/api/stories',{**data,'premise':'Mara','language':'fr','language_mode':'explicit'})
  self.assertIsNone(self.post('/api/stories',{'title':'Legacy'})['language'])
 def test_operation_overrides_conversation_and_wrong_output_fail_closed(self):
  self.patch(self.root,{'language':'id'});before=self.client.get(self.root).json()
  fake=world.RecordingGenerator(ID)
  with patch('app.api.stories.get_story_generator',return_value=fake):
   result=self.post(self.root+'/scenes/generate',{'request':EN},expected=200)
  self.assertEqual(fake.context.language,'id');self.assertEqual(result['language_context']['conversation']['language'],'en');self.assertEqual(result['language_context']['production']['language'],'id');self.assertIn('saved for review',result['assistant_message'])
  fake=world.RecordingGenerator(TEXTS['fr'])
  with patch('app.api.stories.get_story_generator',return_value=fake):
   result=self.post(self.root+'/scenes/generate',{'request':ID,'output_language':'fr','response_language':'de'},expected=200)
  self.assertEqual(fake.context.language,'fr');self.assertEqual(result['language_context']['conversation']['language'],'de');self.assertIn('gespeichert',result['assistant_message'])
  self.assertEqual(self.client.get(self.root).json(),before)
  count=len(self.client.get(self.root+'/scenes').json())
  with patch('app.api.stories.get_story_generator',return_value=world.RecordingGenerator(EN)):
   self.post(self.root+'/scenes/generate',{'request':ID},expected=502)
  self.assertEqual(len(self.client.get(self.root+'/scenes').json()),count)
  with self.sessions() as db:
   rows=list(db.scalars(select(StoryAction).where(StoryAction.story_id==self.story['story_id'])))
   self.assertTrue(any(row.language_context and row.language_context['production']['source']=='operation_override' for row in rows))
  self.post(self.root+'/scenes/generate',{'request':EN,'output_language':'xx'},expected=422)
 def test_story_edit_conflict_and_historical_direction_language(self):
  from test_creative_direction import direction
  self.patch(self.root,{'language':'id'});approved=self.client.put(self.root+'/creative-direction',json=direction()).json()
  old=self.client.get(self.root).json()
  changed=self.patch(self.root,{'language':'fr','expected_updated_at':old['updated_at']})
  self.assertEqual(changed['language_provenance']['source'],'explicit_edit')
  self.patch(self.root,{'language':'en','expected_updated_at':old['updated_at']},expected=409)
  snapshot=self.client.get(self.root+'/creative-direction').json();self.assertEqual(snapshot,approved);self.assertEqual(snapshot['direction']['language_at_approval'],'id')
  self.assertEqual(self.client.put(self.root+'/creative-direction',json=direction()).status_code,409)
 def test_recommendation_response_language_is_independent(self):
  fake=AsyncMock();fake.recommend.return_value=Recommendation(target_format='webtoon',storytelling_style_id='korean_romance_drama',audience_rating='teen_13',visual_style='match_style',language='id',rationale=EN)
  app.dependency_overrides[get_recommender]=lambda:fake
  result=self.post('/api/styles/recommend',{'idea':ID,'target_format':'webtoon','language':'id','response_language':'en'},expected=200)
  self.assertEqual(result['language'],'id');self.assertEqual(result['language_context']['conversation']['language'],'en')
  self.assertEqual(fake.recommend.call_args.args[0]['narrative_data']['response_language'],'en')
  self.post('/api/styles/recommend',{'idea':ID,'target_format':'webtoon','language':'id','response_language':'id'},expected=502)
 def test_guidance_different_from_story_and_authorization(self):
  self.patch(self.root,{'language':'id'})
  result=self.post(self.root+'/workflow/steps/narrative_guidance',{'user_message':EN},expected=200)
  self.assertEqual(result['language_context']['language'],'en');self.assertIn('objective',result['suggestions'][0]['text'])
  self.assertEqual(self.client.get(self.root).json()['language'],'id')
  self.sign_in('bob');self.post(self.root+'/scenes/generate',{'request':EN,'output_language':'fr'},expected=404)
  self.client.cookies.clear();self.post('/api/languages/detect',{'text':ID},expected=401)


class ControlledAdapterLanguageTests(unittest.IsolatedAsyncioTestCase):
 async def test_all_providers_receive_each_explicit_language_instruction(self):
  import json
  import httpx
  from types import SimpleNamespace
  from unittest.mock import MagicMock
  from app.stories.generator import SceneGenerationContext
  from app.llm.providers.anthropic import AnthropicStoryGenerator
  from app.llm.providers.google import GoogleStoryGenerator
  from app.stories.adapters.openai_generator import OpenAIStoryGenerator
  from app.stories.metadata import LANGUAGE_NAMES
  for language,text in TEXTS.items():
   context=SceneGenerationContext(title='Mara',premise=ID,objective=None,canon=[],previous_scenes=[],request=EN,language=language)
   for Adapter,provider in [(AnthropicStoryGenerator,'anthropic'),(GoogleStoryGenerator,'google')]:
    async def handle(request):
     body=json.loads(request.content);prompt=body['messages'][0]['content'] if provider=='anthropic' else body['contents'][0]['parts'][0]['text']
     self.assertIn(f'{LANGUAGE_NAMES[language]} ({language})',prompt)
     return httpx.Response(200,json={'stop_reason':'end_turn','content':[{'type':'text','text':text}]} if provider=='anthropic' else {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]}}]})
    self.assertEqual(await Adapter(api_key='controlled-test-key',model='fixture',transport=httpx.MockTransport(handle)).generate_scene(context),text)
   client=MagicMock();client.responses.create=AsyncMock(return_value=SimpleNamespace(status='completed',output_text=text))
   manager=MagicMock(__aenter__=AsyncMock(return_value=client),__aexit__=AsyncMock(return_value=False))
   with patch('app.stories.adapters.openai_generator.AsyncOpenAI',return_value=manager):
    self.assertEqual(await OpenAIStoryGenerator(api_key='controlled-test-key',model='fixture').generate_scene(context),text)
   self.assertIn(f'{LANGUAGE_NAMES[language]} ({language})',client.responses.create.call_args.kwargs['input'])


class ProductionLanguageTests(unittest.TestCase):
 def test_spoken_fields_checked_separately_and_source_evidence_not_translated(self):
  from test_production import proposal
  from app.media.production.schemas import ProductionProposal
  from app.media.production.service import validate_narrative_language
  value=proposal();value['summary']=ID;value['production']['panels'][0]['dialogue']=EN
  with self.assertRaises(HTTPException):validate_narrative_language(ProductionProposal.model_validate(value),'id')
  value['production']['panels'][0]['dialogue']=ID
  self.assertEqual(validate_narrative_language(ProductionProposal.model_validate(value),'id'),'unverified_short_or_ambiguous')
