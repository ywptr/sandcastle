from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.workflows import registry, service
from app.workflows.schemas import StoryWorkflowInput, WorkflowAction, StepId
from app.guidance.generator import get_suggestion_generator, NarrativeSuggestionGenerator
from app.canon.deterministic_extractor import get_canon_extractor
from app.canon.extractor import CanonExtractor
from app.media.adaptation.planner import get_shot_planner, ShotPlanner
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.adaptation.service import AdaptationUnavailable
from app.canon.candidate_service import ExtractionFailed

router = APIRouter(tags=["workflows"])


@router.get("/workflows/difficulties")
def difficulties(identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return registry.difficulties()


@router.get("/workflows/templates")
def templates(identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return registry.list_templates()


@router.get("/workflows/templates/{template_id}")
def template(template_id: str, version: int = 1, identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return registry.get_template(template_id, version)


@router.get("/stories/{story_id}/workflow")
def workflow(story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.read_workflow(db, story_id, identity.user_id)


@router.put("/stories/{story_id}/workflow")
def save_workflow(story_id: str, selection: StoryWorkflowInput, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.save_workflow(db, story_id, identity.user_id, selection)


@router.post("/stories/{story_id}/workflow/steps/{step_id}")
async def workflow_step(story_id: str, step_id: StepId, action: WorkflowAction = WorkflowAction(),
                        db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
                        generator: NarrativeSuggestionGenerator = Depends(get_suggestion_generator),
                        extractor: CanonExtractor = Depends(get_canon_extractor), planner: ShotPlanner = Depends(get_shot_planner)):
    try:
        result = await service.perform_step(db, story_id, identity.user_id, step_id, action,
            generator=generator, extractor=extractor, planner=planner)
        if isinstance(result, list):
            from app.canon.candidate_schemas import CanonCandidateResponse
            return [CanonCandidateResponse.model_validate(row) for row in result]
        return result
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from error
    except (AdaptationUnavailable, ExtractionFailed) as error:
        raise HTTPException(502, str(error)) from error
