from datetime import datetime

from pydantic import ConfigDict

from app.validation import InputModel, Name, PatchModel


class CharacterCreate(InputModel):
    name: Name
    description: str = ""
    appearance: str = ""
    outfit: str = ""
    personality: str = ""


class CharacterUpdate(PatchModel):
    name: Name | None = None
    description: str | None = None
    appearance: str | None = None
    outfit: str | None = None
    personality: str | None = None


class CharacterResponse(CharacterCreate):
    model_config = ConfigDict(from_attributes=True)
    character_id: str
    story_id: str
    created_at: datetime
    updated_at: datetime


class PlaceCreate(InputModel):
    name: Name
    description: str = ""
    appearance: str = ""
    atmosphere: str = ""


class PlaceUpdate(PatchModel):
    name: Name | None = None
    description: str | None = None
    appearance: str | None = None
    atmosphere: str | None = None


class PlaceResponse(PlaceCreate):
    model_config = ConfigDict(from_attributes=True)
    place_id: str
    story_id: str
    created_at: datetime
    updated_at: datetime
