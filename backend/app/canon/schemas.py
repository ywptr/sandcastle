from datetime import datetime

from typing import Literal

from pydantic import BaseModel

from app.validation import InputModel, Name, NonBlank, PatchModel, ShortType


class CanonEntryCreate(InputModel):
    type: ShortType
    key: Name
    value: NonBlank
    subject_id: Name | None = None
    fact_type: ShortType | None = None


class CanonEntryResponse(BaseModel):
    canon_entry_id: str
    story_id: str
    type: str
    key: str
    value: str
    subject_id: str | None
    fact_type: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CanonEntryUpdate(PatchModel):
    nullable_fields = {"subject_id", "fact_type"}
    subject_id: Name | None = None
    fact_type: ShortType | None = None
    type: ShortType | None = None
    key: Name | None = None
    value: NonBlank | None = None
    status: Literal["approved", "superseded"] | None = None
