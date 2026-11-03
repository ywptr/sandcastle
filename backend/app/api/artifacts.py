from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.artifacts import service
from app.artifacts.schemas import (
    ArtifactRegistration, ArtifactRelationCreate, ArtifactRelationResponse,
    ReferenceBindingCreate, ReferenceBindingResponse,
)
from app.auth.identity import AuthenticatedIdentity
from app.media.execution_schemas import ArtifactResponse
from app.media.refinement import create_refinement_request
from app.media.schemas import MediaRequest, RefinementInput
from app.media.service import InvalidMediaIntent, MediaDomainNotFound

router = APIRouter(tags=["artifacts", "references"])


def _http_error(error: ValueError) -> HTTPException:
    if isinstance(error, MediaDomainNotFound):
        return HTTPException(404, str(error))
    if isinstance(error, service.ArtifactConflict):
        return HTTPException(409, str(error))
    return HTTPException(422, str(error))


@router.post("/artifacts", response_model=ArtifactResponse, status_code=201)
def register_artifact_endpoint(
    registration: ArtifactRegistration,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.register_artifact(db, identity.user_id, registration)
    except (InvalidMediaIntent, MediaDomainNotFound) as error:
        raise _http_error(error) from error


@router.get("/artifacts", response_model=list[ArtifactResponse])
def list_artifacts_endpoint(
    story_id: str | None = None,
    source: Literal["generated", "uploaded", "external"] | None = None,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.list_artifacts(db, identity.user_id, story_id=story_id, source=source)
    except MediaDomainNotFound as error:
        raise _http_error(error) from error


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def read_artifact_endpoint(
    artifact_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.get_artifact(db, artifact_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise _http_error(error) from error


@router.post("/stories/{story_id}/references", response_model=ReferenceBindingResponse, status_code=201)
def create_reference_endpoint(
    story_id: str,
    intent: ReferenceBindingCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.create_binding(db, story_id, identity.user_id, intent)
    except (InvalidMediaIntent, MediaDomainNotFound, service.ArtifactConflict) as error:
        raise _http_error(error) from error


@router.get("/stories/{story_id}/references", response_model=list[ReferenceBindingResponse])
def list_references_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.list_bindings(db, story_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise _http_error(error) from error


@router.delete("/stories/{story_id}/references/{reference_id}", status_code=204)
def delete_reference_endpoint(
    story_id: str,
    reference_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        service.delete_binding(db, story_id, reference_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise _http_error(error) from error
    return Response(status_code=204)


@router.post("/artifacts/{artifact_id}/relations", response_model=ArtifactRelationResponse, status_code=201)
def create_relation_endpoint(
    artifact_id: str,
    intent: ArtifactRelationCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.create_relation(db, artifact_id, identity.user_id, intent)
    except (InvalidMediaIntent, MediaDomainNotFound, service.ArtifactConflict) as error:
        raise _http_error(error) from error


@router.get("/artifacts/{artifact_id}/relations", response_model=list[ArtifactRelationResponse])
def list_relations_endpoint(
    artifact_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return service.list_relations(db, artifact_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise _http_error(error) from error


@router.post("/artifacts/{artifact_id}/refinement", response_model=MediaRequest)
def refinement_endpoint(
    artifact_id: str,
    intent: RefinementInput,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return create_refinement_request(db, artifact_id=artifact_id, user_id=identity.user_id, intent=intent)
    except (InvalidMediaIntent, MediaDomainNotFound) as error:
        raise _http_error(error) from error
