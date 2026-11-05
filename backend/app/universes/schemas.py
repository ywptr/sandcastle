from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.validation import InputModel, Name, PatchModel
from app.canon.library_schemas import Attach


class UniverseCreate(InputModel):
    name: Name
    description: str = ""


class UniverseUpdate(PatchModel):
    name: Name | None = None
    description: str | None = None


class UniverseResponse(UniverseCreate):
    model_config = ConfigDict(from_attributes=True)
    universe_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    universe_id: str
    story_id: str
    created_at: datetime


class UniverseReferenceCreate(Attach):
    pass


class UniverseReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reference_id: str
    universe_id: str
    canon_object_id: str
    canon_version_id: str
    created_at: datetime
