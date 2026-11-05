from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.media.adaptation.planner import ShotPlanner, get_shot_planner
from app.media.adaptation.schemas import AdaptationOptions, MediaAdaptationPlan
from app.media.adaptation.service import adapt_scene, AdaptationUnavailable
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.schemas import StoryboardPlan
from app.media.storyboard import create_four_panel_storyboard

router = APIRouter(prefix="/stories/{story_id}/scenes/{scene_id}", tags=["media-adaptation"])


def translate(error):
    code = 404 if isinstance(error, MediaDomainNotFound) else 502 if isinstance(error, AdaptationUnavailable) else 422
    return HTTPException(code, str(error))


@router.post("/media/adapt", response_model=MediaAdaptationPlan)
def adaptation_endpoint(story_id: str, scene_id: str, options: AdaptationOptions = AdaptationOptions(),
                        db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
                        planner: ShotPlanner = Depends(get_shot_planner)):
    try:
        return adapt_scene(db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id, options=options, planner=planner)
    except (InvalidMediaIntent, MediaDomainNotFound, AdaptationUnavailable) as error:
        raise translate(error) from error


@router.post("/storyboard/four-panel/adapted", response_model=StoryboardPlan)
def adapted_storyboard_endpoint(story_id: str, scene_id: str, options: AdaptationOptions = AdaptationOptions(),
                                db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
                                planner: ShotPlanner = Depends(get_shot_planner)):
    try:
        adaptation = adapt_scene(db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id, options=options, planner=planner)
        return create_four_panel_storyboard(db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id,
                                            options=options, adaptation=adaptation)
    except (InvalidMediaIntent, MediaDomainNotFound, AdaptationUnavailable) as error:
        raise translate(error) from error
