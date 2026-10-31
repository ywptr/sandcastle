from datetime import datetime

from pydantic import BaseModel

from app.stories.action_schemas import (
    StoryActionResponse,
)


class SceneResponse(BaseModel):
    scene_id: str
    story_id: str
    source_action_id: str | None
    sequence_number: int
    title: str | None
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class SceneGenerateRequest(BaseModel):
    request: str


class SceneGenerateResponse(BaseModel):
    action: StoryActionResponse
    scene: SceneResponse | None