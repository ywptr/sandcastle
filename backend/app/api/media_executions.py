from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.db.models.artifact import Artifact
from app.db.models.story import Story
from app.integrations.ig.client import get_execution_client
from app.media.execution_client import MediaExecutionClient
from app.media.execution_schemas import ApprovedStoryboard, ArtifactResponse, MediaExecutionResponse
from app.media.execution_service import (
    ExecutionConflict, execute_storyboard, get_execution, list_artifacts, list_executions, sync_execution,
)
from app.media.service import InvalidMediaIntent, MediaDomainNotFound

router = APIRouter(tags=["media-executions"])


@router.post(
    "/stories/{story_id}/scenes/{scene_id}/storyboard/four-panel/execute",
    response_model=list[MediaExecutionResponse], status_code=201,
)
def execute_storyboard_endpoint(
    story_id: str,
    scene_id: str,
    approval: ApprovedStoryboard,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    client: MediaExecutionClient = Depends(get_execution_client),
):
    try:
        return execute_storyboard(
            db, story_id=story_id, scene_id=scene_id, user_id=identity.user_id,
            plan=approval.plan, client=client,
        )
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except InvalidMediaIntent as error:
        raise HTTPException(422, str(error)) from error
    except ExecutionConflict as error:
        raise HTTPException(409, str(error)) from error


@router.get("/media/executions/{execution_id}", response_model=MediaExecutionResponse)
def read_execution_endpoint(
    execution_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return get_execution(db, execution_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.post("/media/executions/{execution_id}/sync", response_model=MediaExecutionResponse)
def sync_execution_endpoint(
    execution_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    client: MediaExecutionClient = Depends(get_execution_client),
):
    try:
        return sync_execution(db, execution_id=execution_id, user_id=identity.user_id, client=client)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error
    except ExecutionConflict as error:
        raise HTTPException(409, str(error)) from error


@router.get("/stories/{story_id}/media/executions", response_model=list[MediaExecutionResponse])
def list_executions_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return list_executions(db, story_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.get("/stories/{story_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    try:
        return list_artifacts(db, story_id, identity.user_id)
    except MediaDomainNotFound as error:
        raise HTTPException(404, str(error)) from error


@router.get("/media/artifacts/{artifact_id}", response_model=ArtifactResponse)
def read_artifact_endpoint(
    artifact_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    artifact = db.scalar(select(Artifact).join(Story, Story.story_id == Artifact.story_id).where(
        Artifact.artifact_id == artifact_id, Artifact.user_id == identity.user_id,
        Story.user_id == identity.user_id,
    ))
    if artifact is None:
        raise HTTPException(404, "Artifact not found")
    return artifact
