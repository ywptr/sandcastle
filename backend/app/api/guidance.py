from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.guidance.generator import NarrativeSuggestionGenerator, get_suggestion_generator
from app.guidance.schemas import GuidanceProfileInput, GuidanceProfileResponse, SuggestionOptions, SuggestionResponse
from app.guidance import service

router = APIRouter(prefix="/stories/{story_id}/guidance", tags=["narrative-guidance"])


@router.get("/profile", response_model=GuidanceProfileResponse)
def read_profile(story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.get_profile(db, story_id, identity.user_id)


@router.put("/profile", response_model=GuidanceProfileResponse)
def save_profile(story_id: str, profile: GuidanceProfileInput, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.save_profile(db, story_id, identity.user_id, profile)


@router.post("/next-scene", response_model=SuggestionResponse)
async def next_scene(story_id: str, options: SuggestionOptions = SuggestionOptions(), db: Session = Depends(get_db),
                     identity: AuthenticatedIdentity = Depends(get_current_identity),
                     generator: NarrativeSuggestionGenerator = Depends(get_suggestion_generator)):
    return await service.suggest_next_scene(db, story_id, identity.user_id, options, generator)
