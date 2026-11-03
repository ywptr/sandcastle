from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.media.execution_client import ExecutionState
from app.media.schemas import StoryboardPlan
from app.validation import InputModel


class ApprovedStoryboard(InputModel):
    approved: Literal[True]
    plan: StoryboardPlan

    @field_validator("approved", mode="before")
    @classmethod
    def explicit_approval(cls, value):
        if value is not True:
            raise ValueError("Explicit approval must be true")
        return value


class MediaExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    execution_id: str
    story_id: str
    scene_id: str
    storyboard_plan_id: str
    media_request_id: str
    panel_number: int
    status: ExecutionState
    backend_name: str
    external_execution_id: str | None
    error_message: str | None
    request_snapshot: dict
    approved_at: datetime
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    artifact_id: str
    story_id: str | None
    scene_id: str | None
    execution_id: str | None
    media_type: str
    source: str
    external_reference: str | None
    display_name: str | None
    external_artifact_id: str | None
    retrieval_reference: str
    mime_type: str | None
    metadata: dict = Field(validation_alias="metadata_json")
    created_at: datetime
