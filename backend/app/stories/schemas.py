from datetime import datetime

from pydantic import BaseModel

from app.validation import InputModel, Name, PatchModel


class StoryCreate(InputModel):
    title: Name
    premise: str | None = None
    objective: str | None = None


class StoryResponse(BaseModel):
    story_id: str
    user_id: str
    title: str
    premise: str | None
    objective: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class StoryUpdate(PatchModel):
    nullable_fields = {"premise", "objective"}
    title: Name | None = None
    premise: str | None = None
    objective: str | None = None
