from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, field_validator

from app.validation import InputModel, Name

ReferenceRole = Literal["character_identity", "outfit", "place", "visual_style", "general"]
RelationType = Literal["derived_from", "reference_input"]
Locator = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]


class ArtifactRegistration(InputModel):
    source: Literal["uploaded", "external"]
    media_type: Literal["image"] = "image"
    retrieval_reference: Locator
    story_id: Name | None = None
    scene_id: Name | None = None
    external_reference: Name | None = None
    display_name: Name | None = None
    mime_type: Name | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("retrieval_reference")
    @classmethod
    def external_locator(cls, value: str) -> str:
        parsed = urlsplit(value)
        if not parsed.scheme or parsed.scheme.lower() in {"data", "file", "javascript"}:
            raise ValueError("Use an external media locator, not inline bytes or a local file")
        if parsed.username or parsed.password:
            raise ValueError("Do not embed credentials in a media locator")
        return value

    @field_validator("mime_type")
    @classmethod
    def image_mime_type(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("image/"):
            raise ValueError("Only image artifacts are supported")
        return value


class ReferenceBindingCreate(InputModel):
    artifact_id: Name
    target_type: Literal["story", "character", "place"]
    target_id: Name | None = None
    role: ReferenceRole
    label: Name | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ReferenceBindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reference_id: str
    user_id: str
    story_id: str
    artifact_id: str
    target_type: str
    target_id: str
    role: ReferenceRole
    label: str | None
    metadata: dict = Field(validation_alias="metadata_json")
    created_at: datetime


class ArtifactRelationCreate(InputModel):
    parent_artifact_id: Name
    relation_type: RelationType = "derived_from"


class ArtifactRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    relation_id: str
    user_id: str
    parent_artifact_id: str
    child_artifact_id: str
    relation_type: RelationType
    created_at: datetime
