from datetime import datetime

from pydantic import BaseModel


class CanonCandidateResponse(BaseModel):
    canon_candidate_id: str
    story_id: str
    scene_id: str
    type: str
    key: str
    value: str
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }