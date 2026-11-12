from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from app.validation import InputModel
from app.languages.service import LanguageOptions

Audience = Literal["child", "teen", "adult"]
Maturity = Literal["general", "mild", "moderate", "mature"]
ShortNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class GuidanceProfileInput(InputModel):
    audience: Audience = "adult"
    maturity_rating: Maturity = "general"
    tone: ShortNote | None = None
    genre: ShortNote | None = None
    guidance_notes: Annotated[str, StringConstraints(max_length=2000)] | None = None
    average_rating: float | None = Field(default=None, ge=1, le=5, allow_inf_nan=False)
    rating_count: int = Field(default=0, ge=0, le=1000000)
    feedback_tags: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_profile(self):
        if self.audience == "child" and self.maturity_rating not in {"general", "mild"}:
            raise ValueError("Child audience supports general or mild content")
        if self.audience == "teen" and self.maturity_rating == "mature":
            raise ValueError("Teen audience supports up to moderate content")
        if (self.average_rating is None) != (self.rating_count == 0):
            raise ValueError("Feedback requires both a rating average and a positive count, or neither")
        return self


class GuidanceProfileResponse(GuidanceProfileInput):
    story_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class SuggestionOptions(LanguageOptions):
    count: int = Field(default=3, ge=1, le=5)
    recent_scene_count: int = Field(default=4, ge=1, le=5)
    additional_instruction: Annotated[str, StringConstraints(max_length=1000)] | None = None


class Suggestion(InputModel):
    id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=700)]


class SuggestionResponse(BaseModel):
    story_id: str
    language_context: dict | None = None
    strategy: str = "deterministic"
    suggestions: list[Suggestion]
