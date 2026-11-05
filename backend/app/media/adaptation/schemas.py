from datetime import datetime
from typing import Annotated, Literal
from uuid import uuid4
from pydantic import Field, StringConstraints, model_validator
from app.validation import InputModel, Name, NonBlank
from app.db.types import utc_now
from app.guidance.schemas import Audience, Maturity
from app.media.schemas import Reference, SceneImageOptions

Sensitivity = Literal["violence", "intimacy", "injury", "horror", "substance_use", "other_sensitive"]
DepictionStrategy = Literal["direct", "implied", "reaction", "cutaway", "aftermath", "silhouette", "offscreen", "symbolic"]


class AdaptationOptions(SceneImageOptions):
    output_format: Literal["image", "webtoon"] = "webtoon"
    sensitivity_hints: list[Sensitivity] = Field(default_factory=list, max_length=6)
    additional_visual_instruction: Annotated[str, StringConstraints(max_length=1000)] | None = None


class AdaptationIssue(InputModel):
    code: Literal["canon_conflict", "context_ambiguous"]
    message: NonBlank
    canon_entry_ids: list[str] = Field(default_factory=list)
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)


class AdaptedShot(InputModel):
    sequence: int = Field(ge=1)
    narrative_beat: NonBlank
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    visual_instruction: NonBlank
    framing_hint: NonBlank
    character_ids: list[str] = Field(default_factory=list)
    place_ids: list[str] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    depiction_strategy: DepictionStrategy
    rationale: NonBlank


class MediaAdaptationPlan(InputModel):
    adaptation_id: str = Field(default_factory=lambda: str(uuid4()))
    story_id: Name
    scene_id: Name
    audience: Audience
    maturity_rating: Maturity
    output_format: Literal["image", "webtoon"]
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    shots: list[AdaptedShot] = Field(min_length=1, max_length=240)
    issues: list[AdaptationIssue] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    context_digest: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def ordered_shots(self):
        if [shot.sequence for shot in self.shots] != list(range(1, len(self.shots) + 1)):
            raise ValueError("Adapted shots must be consecutively ordered")
        if any(shot.source_end <= shot.source_start for shot in self.shots):
            raise ValueError("Invalid narrative source span")
        return self
