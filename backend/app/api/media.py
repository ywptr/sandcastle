from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.media.schemas import MediaPlan, MediaRequest, SceneImageOptions, SceneImagePlanInput, StoryboardPlan
from app.media.storyboard import create_four_panel_storyboard
from app.media.service import (
    InvalidMediaIntent, MediaDomainNotFound, create_media_plan, create_scene_image_request,
)

router = APIRouter(prefix="/stories/{story_id}", tags=["media"])


@router.post("/scenes/{scene_id}/media/image-request", response_model=MediaRequest)
def scene_image_request_endpoint(
    story_id: str,
    scene_id: str,
    options: SceneImageOptions,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return create_scene_image_request(
            db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id, options=options,
        )
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from error


@router.post("/media-plans", response_model=MediaPlan)
def media_plan_endpoint(
    story_id: str,
    intent: SceneImagePlanInput,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return create_media_plan(db, story_id=story_id, user_id=identity.user_id, intent=intent)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from error


@router.post("/scenes/{scene_id}/storyboard/four-panel", response_model=StoryboardPlan)
def four_panel_storyboard_endpoint(
    story_id: str,
    scene_id: str,
    options: SceneImageOptions,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return create_four_panel_storyboard(
            db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id, options=options,
        )
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from error
