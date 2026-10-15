from datetime import datetime

from pydantic import BaseModel


class CanonEntryCreate(BaseModel):
    type: str
    key: str
    value: str


class CanonEntryResponse(BaseModel):
    canon_entry_id: str
    story_id: str
    type: str
    key: str
    value: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }