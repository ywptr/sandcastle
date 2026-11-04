from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.canon import candidate_service as service
from app.canon.candidate_schemas import (
    CandidateApproval, CandidateRejection, CandidateStatus, CanonCandidateResponse,
    ContinuityClassification, ContinuityReport, ManualCandidate,
)
from app.canon.deterministic_extractor import get_canon_extractor
from app.canon.extractor import CanonExtractor
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound

router = APIRouter(prefix="/stories/{story_id}", tags=["canon-intelligence"])
_ERRORS = (MediaDomainNotFound, InvalidMediaIntent, service.CandidateConflict, service.ExtractionFailed)


def _http_error(error):
    code = 404 if isinstance(error, MediaDomainNotFound) else 409 if isinstance(error, service.CandidateConflict) else 502 if isinstance(error, service.ExtractionFailed) else 422
    return HTTPException(code, str(error))


@router.post("/scenes/{scene_id}/canon/candidates/extract", response_model=list[CanonCandidateResponse])
@router.post("/scenes/{scene_id}/canon/extract", response_model=list[CanonCandidateResponse], include_in_schema=False)
async def extract_scene_endpoint(
    story_id: str, scene_id: str, db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    extractor: CanonExtractor = Depends(get_canon_extractor),
):
    try:
        return await service.extract_candidates(db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id, extractor=extractor)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.post("/canon/candidates/extract", response_model=list[CanonCandidateResponse])
async def extract_story_endpoint(
    story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
    extractor: CanonExtractor = Depends(get_canon_extractor),
):
    try:
        return await service.extract_candidates(db, story_id=story_id, user_id=identity.user_id, extractor=extractor)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.post("/canon/candidates", response_model=CanonCandidateResponse, status_code=201)
def propose_candidate_endpoint(
    story_id: str, proposal: ManualCandidate, db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.propose_candidate(db, story_id=story_id, user_id=identity.user_id, proposal=proposal)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.get("/canon/candidates", response_model=list[CanonCandidateResponse])
def list_candidates_endpoint(
    story_id: str, status: CandidateStatus | None = None, classification: ContinuityClassification | None = None,
    scene_id: str | None = None, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.list_candidates(db, story_id, identity.user_id, status=status, classification=classification, scene_id=scene_id)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.post("/canon/candidates/reclassify", response_model=list[CanonCandidateResponse])
def reclassify_endpoint(
    story_id: str, scene_id: str | None = None, db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.reclassify_pending(db, story_id=story_id, user_id=identity.user_id, scene_id=scene_id)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.get("/canon/candidates/{candidate_id}", response_model=CanonCandidateResponse)
def read_candidate_endpoint(
    story_id: str, candidate_id: str, db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.get_candidate(db, story_id, candidate_id, identity.user_id)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.post("/canon/candidates/{candidate_id}/approve", response_model=CanonCandidateResponse)
def approve_endpoint(
    story_id: str, candidate_id: str, approval: CandidateApproval | None = None,
    db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.approve_candidate(db, story_id=story_id, candidate_id=candidate_id, user_id=identity.user_id,
                                         approval=approval or CandidateApproval())
    except _ERRORS as error:
        raise _http_error(error) from error


@router.post("/canon/candidates/{candidate_id}/reject", response_model=CanonCandidateResponse)
def reject_endpoint(
    story_id: str, candidate_id: str, rejection: CandidateRejection | None = None,
    db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.reject_candidate(db, story_id=story_id, candidate_id=candidate_id, user_id=identity.user_id,
                                        note=rejection.note if rejection else None)
    except _ERRORS as error:
        raise _http_error(error) from error


@router.get("/canon/continuity", response_model=ContinuityReport)
def continuity_endpoint(
    story_id: str, scene_id: str | None = None, db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.continuity_report(db, story_id=story_id, user_id=identity.user_id, scene_id=scene_id)
    except _ERRORS as error:
        raise _http_error(error) from error
