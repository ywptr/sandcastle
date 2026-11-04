from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.validation import InputModel, NonBlank

class LibraryCreate(InputModel):
    object_type: Literal["character", "place"]
    data: dict

class Promotion(InputModel):
    target_type: Literal["character", "place"]
    target_id: str

class VersionCreate(InputModel):
    parent_version_id: str
    data: dict

class Attach(InputModel):
    canon_object_id: str
    canon_version_id: str

class Fork(InputModel):
    reason: NonBlank

class Move(InputModel):
    canon_version_id: str


class LibraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    canon_object_id: str
    user_id: str
    object_type: str
    name: str
    created_at: datetime

class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    canon_version_id: str
    canon_object_id: str
    version_number: int
    parent_version_id: str | None
    data: dict
    created_by_story_id: str | None
    fork_reason: str | None
    created_at: datetime

class StoryReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reference_id: str
    story_id: str
    canon_object_id: str
    canon_version_id: str
    target_type: str
    target_id: str
    created_at: datetime
