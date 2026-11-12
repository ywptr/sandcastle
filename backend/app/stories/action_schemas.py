from datetime import datetime

from pydantic import BaseModel


class StoryActionCreate(BaseModel):
    action_type: str
    request: str


class AuthorityDecisionResponse(BaseModel):
    decision_id: str
    action_id: str
    outcome: str
    reason: str
    confidence: float | None
    evaluator: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class StoryActionResponse(BaseModel):
    language_context: dict | None = None
    action_id: str
    story_id: str
    action_type: str
    request: str
    status: str
    created_at: datetime
    decision: AuthorityDecisionResponse

class StoryActionListItem(BaseModel):
    language_context: dict | None = None
    action_id: str
    story_id: str
    action_type: str
    request: str
    status: str
    created_at: datetime
    decision: AuthorityDecisionResponse | None