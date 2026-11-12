from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.llm.resolver import resolve_adapter
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.production import service
from app.media.production.schemas import (TranslationRequest, ReviewRequest, ApprovalRequest, MediaProductionPlan,
    ApprovedProduction, CompiledProduction)

router = APIRouter(tags=["narrative-production"])
BASE = "/stories/{story_id}/scenes/{scene_id}/adaptations"


def get_translator_resolver():
    return resolve_adapter


def _call(function, *args):
    try:
        return function(*args)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from None
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from None


@router.post(BASE, response_model=MediaProductionPlan)
async def translate(story_id: str, scene_id: str, request: TranslationRequest, response: Response,
    db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
    resolver=Depends(get_translator_resolver)):
    # Authenticate and check ownership before selecting any credential or invoking a provider.
    context = _call(service.build_context, db, story_id, scene_id, identity.user_id, request.target_format, request.instruction, request.output_language)
    translator = resolver(db, identity.user_id, "narrative_media_translator")
    result = await service.translate_scene(db, context, translator)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(BASE + "/compile", response_model=CompiledProduction)
def compile_review(story_id: str, scene_id: str, request: ReviewRequest, response: Response,
    db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    response.headers["Cache-Control"] = "no-store"
    return _call(service.review_plan, db, story_id, scene_id, identity.user_id, request.plan)


@router.post(BASE + "/approve", response_model=ApprovedProduction, status_code=201)
def approve(story_id: str, scene_id: str, request: ApprovalRequest,
    db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return _call(service.approve_plan, db, story_id, scene_id, identity.user_id, request.plan)


@router.get(BASE, response_model=list[ApprovedProduction])
def history(story_id: str, scene_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return _call(service.list_approved, db, story_id, scene_id, identity.user_id)


@router.get("/media/adaptations/{adaptation_id}", response_model=ApprovedProduction)
def read(adaptation_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    row = _call(service.owned_row, db, identity.user_id, adaptation_id)
    return _call(service.approval_view, db, row)
