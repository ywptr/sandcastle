from datetime import datetime

from pydantic import BaseModel


class StoryCreate(BaseModel):
    title: str
    premise: str | None = None
    objective: str | None = None


class StoryResponse(BaseModel):
    story_id: str
    title: str
    premise: str | None
    objective: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }