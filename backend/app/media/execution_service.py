"""Durable approval, per-panel submission, and request-driven synchronization."""
import hashlib
import json

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.artifact import Artifact
from app.db.models.media_execution import MediaExecution
from app.db.models.story import Story
from app.db.types import utc_now
from app.media.execution_client import ExecutionClientError, MediaExecutionClient
from app.media.schemas import MediaRequest, StoryboardPlan
from app.media.service import InvalidMediaIntent, MediaDomainNotFound, _require_story
from app.stories.scene_service import get_scene
from app.world.service import get_character, get_place


class ExecutionConflict(ValueError):
    pass


def _error_message(error: Exception) -> str:
    return str(error) if isinstance(error, ExecutionClientError) else "Execution client failed; no automatic resubmission was attempted."


def _plan_executions(db: Session, plan_id: str, user_id: str) -> list[MediaExecution]:
    return list(db.scalars(select(MediaExecution).where(
        MediaExecution.storyboard_plan_id == plan_id, MediaExecution.user_id == user_id,
    ).order_by(MediaExecution.panel_number)))


def execute_storyboard(
    db: Session,
    *,
    story_id: str,
    scene_id: str,
    user_id: str,
    plan: StoryboardPlan,
    client: MediaExecutionClient,
) -> list[MediaExecution]:
    _require_story(db, story_id, user_id)
    if get_scene(db, story_id, scene_id) is None:
        raise MediaDomainNotFound("Scene not found in story")
    # Revalidate even for direct service callers holding a mutated DTO.
    try:
        plan = StoryboardPlan.model_validate(plan.model_dump(mode="json"))
    except ValidationError as error:
        raise InvalidMediaIntent("Invalid four-panel storyboard") from error
    if plan.story_id != story_id or plan.scene_id != scene_id:
        raise InvalidMediaIntent("Approved plan must match the requested Story and Scene")
    request_ids = [request.media_request_id for request in plan.requests]
    if len(set(request_ids)) != 4 or any(not item.strip() or len(item) > 255 for item in request_ids):
        raise InvalidMediaIntent("Panel request IDs must be distinct nonblank identifiers of at most 255 characters")
    if not plan.media_plan_id.strip() or len(plan.media_plan_id) > 255:
        raise InvalidMediaIntent("Invalid storyboard plan ID")

    digest = hashlib.sha256(json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # Serialize duplicate approval requests in PostgreSQL. No remote work occurs under this lock.
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    existing = _plan_executions(db, plan.media_plan_id, user_id)
    if existing:
        if len(existing) != 4 or any(row.plan_digest != digest for row in existing):
            raise ExecutionConflict("This plan ID already has a different approved snapshot")
        # Replays never submit again, including after a timeout or process interruption.
        return existing

    for request in plan.requests:
        for reference in request.references:
            if reference.kind in {"character", "outfit"}:
                if get_character(db, story_id, reference.reference_id) is None:
                    raise MediaDomainNotFound("Character reference not found in story")
            elif reference.kind == "place" and get_place(db, story_id, reference.reference_id) is None:
                raise MediaDomainNotFound("Place reference not found in story")

    approved_at = utc_now()
    rows = [MediaExecution(
        user_id=user_id, story_id=story_id, scene_id=scene_id,
        storyboard_plan_id=plan.media_plan_id, media_request_id=request.media_request_id,
        panel_number=request.context.panel_number, backend_name=client.backend_name,
        status="pending", request_snapshot=request.model_dump(mode="json"),
        plan_digest=digest, approved_at=approved_at,
    ) for request in plan.requests]
    db.add_all(rows)
    db.commit()  # All four immutable approval snapshots precede any external side effect.

    for row in rows:
        row.started_at = utc_now()
        db.commit()  # Durable attempt marker; a crash must not cause a blind resubmission.
        try:
            submitted = client.submit(
                MediaRequest.model_validate(row.request_snapshot),
                actor_id=user_id, correlation_id=row.execution_id,
            )
        except Exception as error:
            row.status = "failed"
            row.error_message = _error_message(error)
            row.completed_at = utc_now()
        else:
            row.external_execution_id = submitted.external_execution_id
            row.status = "submitted"
        db.commit()
    return rows


def get_execution(db: Session, execution_id: str, user_id: str, *, lock: bool = False) -> MediaExecution:
    statement = select(MediaExecution).join(Story, Story.story_id == MediaExecution.story_id).where(
        MediaExecution.execution_id == execution_id,
        MediaExecution.user_id == user_id, Story.user_id == user_id,
    )
    if lock:
        statement = statement.with_for_update(of=MediaExecution)
    execution = db.scalar(statement)
    if execution is None:
        raise MediaDomainNotFound("Execution not found")
    return execution


def list_executions(db: Session, story_id: str, user_id: str) -> list[MediaExecution]:
    _require_story(db, story_id, user_id)
    return list(db.scalars(select(MediaExecution).where(
        MediaExecution.story_id == story_id, MediaExecution.user_id == user_id,
    ).order_by(MediaExecution.created_at, MediaExecution.storyboard_plan_id, MediaExecution.panel_number)))


def list_artifacts(db: Session, story_id: str, user_id: str) -> list[Artifact]:
    _require_story(db, story_id, user_id)
    return list(db.scalars(select(Artifact).where(
        Artifact.story_id == story_id, Artifact.user_id == user_id,
    ).order_by(Artifact.created_at, Artifact.artifact_id)))


def sync_execution(
    db: Session, *, execution_id: str, user_id: str, client: MediaExecutionClient,
) -> MediaExecution:
    row = get_execution(db, execution_id, user_id, lock=True)
    if row.status in {"completed", "failed"}:
        return row
    if client.backend_name != row.backend_name:
        raise ExecutionConflict("Execution client does not match the original execution backend")
    if not row.external_execution_id:
        # Pending records may remain after an interrupted process. Never resubmit blindly.
        row.error_message = "No external execution ID was recorded. Manual reconciliation is required before any new submission."
        db.commit()
        return row
    try:
        status = client.get_status(row.external_execution_id, actor_id=user_id)
        if status.status == "failed":
            row.status = "failed"
            row.error_message = status.error_message or "External execution failed"
            row.completed_at = utc_now()
        elif status.status == "completed":
            result = client.get_result(row.external_execution_id, actor_id=user_id)
            seen = set()
            for image in result.images:
                if image.mime_type and not image.mime_type.startswith("image/"):
                    raise ExecutionClientError("Execution returned a non-image result")
                if image.external_reference in seen:
                    raise ExecutionClientError("Execution returned duplicate image references")
                seen.add(image.external_reference)
            artifacts = [Artifact(
                user_id=row.user_id, story_id=row.story_id, scene_id=row.scene_id,
                execution_id=row.execution_id, media_type="image", source="generated",
                external_reference=image.external_reference,
                external_artifact_id=image.external_artifact_id,
                retrieval_reference=image.retrieval_reference,
                mime_type=image.mime_type, metadata_json=image.metadata,
            ) for image in result.images]
            db.add_all(artifacts)
            row.status = "completed"
            row.completed_at = utc_now()
            row.error_message = None
        else:
            # Do not regress a running execution when a stale status read says submitted.
            if row.status != "running":
                row.status = "submitted" if status.status == "pending" else status.status
            if status.status == "running":
                row.status = "running"
            row.error_message = None
    except Exception as error:
        # Poll/result transport failures are retryable; retain the external ID and prior status.
        row.error_message = _error_message(error)
    db.commit()  # Artifact insertion and completed status are one transaction.
    return row
