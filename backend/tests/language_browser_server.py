"""Local C2 acceptance server: real services/SQLite/detector, fixed identity/providers."""
import os
os.environ.update(DATABASE_URL="sqlite:///:memory:", IS_ISSUER="https://identity.example.test", IS_CLIENT_ID="test-client", IS_CLIENT_SECRET="test-secret", SANDCASTLE_AUTH_SECRET="test-session-secret", SANDCASTLE_AUTH_CALLBACK_URL="http://testserver/api/auth/callback", SANDCASTLE_WEB_URL="http://testserver")
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.database import Base
from app.api.dependencies import get_db,get_current_identity
from app.auth.identity import AuthenticatedIdentity
from app.creative_direction.schemas import Recommendation
from app.api.creative_direction import get_recommender
from app.api.production import get_translator_resolver
from app.story_import.analyzer import get_import_analyzer
from app.story_import.schemas import ImportAnalysis, ProposedStory
from app.languages.service import production_language, detect
from test_languages import TEXTS
from test_production import proposal
from app.media.production.schemas import ProductionProposal,units
from app.db.models import Story,Scene,StoryAction,ApprovedMediaAdaptation
import app.api.stories as stories_api
import uvicorn
engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
Base.metadata.create_all(engine);sessions=sessionmaker(engine)
def db():
 with sessions() as session:yield session
app.dependency_overrides[get_db]=db
from fastapi import Response, HTTPException
from app.auth.session import AuthSessionManager, SESSION_COOKIE
@app.post('/api/__fixture__/session')
def fixture_session(response:Response,user_id:str='alice'):
 if user_id not in {'alice','bob'}:raise HTTPException(422,'Fixture identity unavailable')
 token=AuthSessionManager(os.environ['SANDCASTLE_AUTH_SECRET']).create_session_token(AuthenticatedIdentity(user_id,'writer@example.test','Studio language review'))
 response.set_cookie(SESSION_COOKIE,token,httponly=True,secure=True,samesite='lax',path='/')
 return {'fixture_only':True}

operations=[]
class Writer:
 async def generate_scene(self,context):
  operations.append({'kind':'scene','language':context.language})
  if '[provider-failure]' in context.request:raise RuntimeError('Controlled provider failure')
  return TEXTS['en' if '[wrong]' in context.request else context.language]
stories_api.get_story_generator=lambda db,user_id:Writer()
class Recommender:
 async def recommend(self,envelope):
  data=envelope['narrative_data'];operations.append({'kind':'recommendation','language':data['language'],'response_language':data['response_language']})
  return Recommendation(target_format=data['target_format'],language=data['language'] or 'und',primary_genre='fantasy',secondary_genres=['mystery'],storytelling_style_id='korean_romance_drama',audience_rating='teen_13',visual_style='match_style',tone='Emotional',rationale=TEXTS[data['response_language']],warnings=[])
app.dependency_overrides[get_recommender]=lambda:Recommender()
class Translator:
 async def translate(self,context):
  language=production_language(context.continuity.story.language,context.output_language)['language'];operations.append({'kind':'production','language':language})
  value=proposal(context.target_format);value['summary']=TEXTS[language]
  result=ProductionProposal.model_validate(value)
  for beat in units(result.production):
   beat.source_excerpt=context.scene.content[:180]
   for field in ['dialogue','caption','voiceover','on_screen_text']:
    if hasattr(beat,field):setattr(beat,field,TEXTS[language])
  return result
app.dependency_overrides[get_translator_resolver]=lambda:(lambda db,user,role:Translator())
class Importer:
 async def analyze(self,request):
  return ImportAnalysis(story=ProposedStory(proposed_title='Import preview',premise=request.content[:2000],detected_language=detect(request.content)['language'],primary_genre='unknown',secondary_genres=[],evidence=[request.content[:500]]))
app.dependency_overrides[get_import_analyzer]=lambda:Importer()
@app.post('/api/__fixture__/reset')
def reset():
 Base.metadata.drop_all(engine);Base.metadata.create_all(engine);operations.clear();return {'fixture_only':True}
@app.get('/api/__fixture__/audit')
def audit():
 with sessions() as session:
  return {'fixture_only':True,'operations':operations,'stories':[{'id':row.story_id,'language':row.language,'provenance':row.language_provenance} for row in session.scalars(select(Story))], 'scenes':len(list(session.scalars(select(Scene)))),'plans':len(list(session.scalars(select(ApprovedMediaAdaptation))))}
if __name__ == '__main__':
 uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('LANGUAGE_BROWSER_PORT','8014')),log_level='warning')
