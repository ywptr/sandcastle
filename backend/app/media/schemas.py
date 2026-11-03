from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.db.types import utc_now
from app.validation import InputModel, Name, NonBlank

AspectRatio = Annotated[
    str, StringConstraints(pattern=r"^[1-9][0-9]{0,2}:[1-9][0-9]{0,2}$"),
]


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class MediaPurpose(StrEnum):
    CHARACTER_REFERENCE = "character_reference"
    OUTFIT_REFERENCE = "outfit_reference"
    PLACE_REFERENCE = "place_reference"
    SCENE = "scene"
    COMIC_PANEL = "comic_panel"
    COVER = "cover"
    VIDEO_SCENE = "video_scene"


class ArtifactReference(InputModel):
    """An opaque artifact identifier, not a storage location or access credential."""

    kind: Literal["generated_artifact", "uploaded_artifact"]
    reference_id: Name


class Reference(InputModel):
    """A future resolver can map (kind, reference_id) to visual input."""

    kind: Literal["character", "outfit", "place", "generated_artifact", "uploaded_artifact"]
    reference_id: Name


class SceneImageOptions(InputModel):
    # None selects the Story's world; [] explicitly selects no entities of that kind.
    character_ids: list[Name] | None = None
    place_ids: list[Name] | None = None
    artifact_references: list[ArtifactReference] = Field(default_factory=list)
    aspect_ratio: AspectRatio | None = None

    @field_validator("character_ids", "place_ids")
    @classmethod
    def unique_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Reference IDs must be unique")
        return value


class SceneImagePlanInput(SceneImageOptions):
    scene_ids: list[Name] = Field(min_length=1, max_length=20)

    @field_validator("scene_ids")
    @classmethod
    def unique_scene_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Scene IDs must be unique")
        return value


class MediaContext(InputModel):
    """Provenance for Sandcastle; an execution client need not interpret it."""

    scene_sequence_number: int | None = None
    canon_entry_ids: list[str] = Field(default_factory=list)
    panel_number: int | None = Field(default=None, ge=1)
    panel_count: int | None = Field(default=None, ge=1)
    panel_role: NonBlank | None = None


class MediaRequest(InputModel):
    media_request_id: str = Field(default_factory=lambda: str(uuid4()))
    media_type: MediaType
    purpose: MediaPurpose
    prompt: NonBlank
    story_id: Name
    scene_id: Name | None = None
    references: list[Reference] = Field(default_factory=list)
    aspect_ratio: AspectRatio | None = None
    context: MediaContext
    created_at: datetime = Field(default_factory=utc_now)


class MediaPlan(InputModel):
    media_plan_id: str = Field(default_factory=lambda: str(uuid4()))
    story_id: Name
    requests: list[MediaRequest] = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class StoryboardPlan(MediaPlan):
    """A four-panel specialization of the existing media intent, not execution steps."""

    scene_id: Name
    requests: list[MediaRequest] = Field(min_length=4, max_length=4)

    def to_media_plan(self) -> MediaPlan:
        """Project to the M3 envelope without changing request identities or order."""
        return MediaPlan(
            media_plan_id=self.media_plan_id, story_id=self.story_id,
            requests=self.requests, created_at=self.created_at,
        )

    @model_validator(mode="after")
    def validate_panels(self) -> "StoryboardPlan":
        for number, request in enumerate(self.requests, start=1):
            if request.story_id != self.story_id or request.scene_id != self.scene_id:
                raise ValueError("All panels must belong to the storyboard Story and Scene")
            if request.media_type != MediaType.IMAGE or request.purpose != MediaPurpose.COMIC_PANEL:
                raise ValueError("All panels must be image requests with comic_panel purpose")
            if request.context.panel_number != number or request.context.panel_count != 4:
                raise ValueError("Panels must be ordered 1, 2, 3, 4 with panel_count 4")
        return self
