"""Machine-readable extraction boundary; no provider dependency in Canon services."""
from typing import Protocol

from pydantic import Field, ValidationInfo, field_validator

from app.validation import InputModel, Name, NonBlank, ShortType


class ExtractedCanonFact(InputModel):
    type: ShortType
    subject_id: Name | None = None
    subject_name: Name | None = None
    fact_type: ShortType = "statement"
    key: Name
    value: NonBlank
    evidence: NonBlank
    explicit: bool = True
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("type", "key", "fact_type")
    @classmethod
    def canonical_field(cls, value: str, info: ValidationInfo) -> str:
        value = "_".join(value.casefold().split())
        return {"location": "place", "rule": "world"}.get(value, value) if info.field_name == "type" else value


class CanonExtractor(Protocol):
    async def extract(self, *, story_title: str, scene_content: str) -> list[ExtractedCanonFact]:
        ...
