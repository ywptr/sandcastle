"""Structured production meaning, separate from M9C treatment and provider payloads."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4
from pydantic import Field, StringConstraints, model_validator
from app.validation import InputModel, Name
from app.db.types import utc_now
from app.stories.schemas import StoryCreate
from app.world.schemas import CharacterResponse, PlaceResponse
from app.canon.schemas import CanonEntryResponse
from app.guidance.schemas import GuidanceProfileInput
from app.media.schemas import Reference, MediaPlan
from app.workflows.schemas import WorkflowConfiguration

TargetFormat = Literal["webtoon", "short_drama", "story_reel"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Framing = Literal["wide", "full", "medium", "close_up", "detail", "overhead"]


class ProductionWarning(InputModel):
    code: Literal["missing_visual_information", "ambiguous_character_presence", "unclear_location", "timing_too_dense",
                  "too_much_dialogue", "unsupported_action", "continuity_uncertainty"]
    message: Text


class VisualBeat(InputModel):
    narrative_purpose: Text
    source_excerpt: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    visual_description: Text
    character_ids: list[Name] = Field(default_factory=list, max_length=30)
    place_ids: list[Name] = Field(default_factory=list, max_length=10)
    artifact_ids: list[Name] = Field(default_factory=list, max_length=20)
    continuity_notes: list[Note] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def unique_ids(self):
        for field in (self.character_ids, self.place_ids, self.artifact_ids):
            if len(field) != len(set(field)):
                raise ValueError("References must be unique")
        return self


class WebtoonPanel(VisualBeat):
    panel_number: int = Field(ge=1, le=12, strict=True)
    dialogue: Note = ""
    caption: Note = ""
    framing: Framing = "medium"


class WebtoonProduction(InputModel):
    target_format: Literal["webtoon"]
    panels: list[WebtoonPanel] = Field(min_length=1, max_length=12)
    reading_order: Literal["top_to_bottom", "left_to_right", "right_to_left"] = "top_to_bottom"
    layout_hint: Note = "Vertical sequence; execution grouping is undecided."


class DramaShot(VisualBeat):
    shot_number: int = Field(ge=1, le=24, strict=True)
    estimated_duration: int = Field(ge=1, le=30, strict=True)
    shot_scale: Framing = "medium"
    camera_direction: Note = ""
    performance_direction: Note = ""
    dialogue: Note = ""
    voiceover: Note = ""
    audio_or_ambience: Note = ""


class ShortDramaProduction(InputModel):
    target_format: Literal["short_drama"]
    target_duration_seconds: int = Field(ge=1, le=120, strict=True)
    shots: list[DramaShot] = Field(min_length=1, max_length=24)
    audio_direction: Note = ""


class ReelBeat(VisualBeat):
    beat_number: int = Field(ge=1, le=20, strict=True)
    duration: int = Field(ge=1, le=15, strict=True)
    on_screen_text: Note = ""
    voiceover: Note = ""
    transition_hint: Note = ""


class StoryReelProduction(InputModel):
    target_format: Literal["story_reel"]
    target_duration_seconds: int = Field(ge=1, le=90, strict=True)
    beats: list[ReelBeat] = Field(min_length=1, max_length=20)
    narration_text_strategy: Text
    visual_strategy: Text


Production = Annotated[WebtoonProduction | ShortDramaProduction | StoryReelProduction, Field(discriminator="target_format")]


def units(production):
    if production.target_format == "webtoon":
        return production.panels
    if production.target_format == "short_drama":
        return production.shots
    return production.beats


class ProductionProposal(InputModel):
    summary: Text
    production: Production
    continuity_notes: list[Note] = Field(default_factory=list, max_length=20)
    warnings: list[ProductionWarning] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def ordered_and_timed(self):
        items = units(self.production)
        number = {"webtoon": "panel_number", "short_drama": "shot_number", "story_reel": "beat_number"}[self.production.target_format]
        if [getattr(item, number) for item in items] != list(range(1, len(items) + 1)):
            raise ValueError("Production beats must be consecutively numbered in display order")
        if self.production.target_format != "webtoon":
            duration = sum(getattr(item, "estimated_duration" if self.production.target_format == "short_drama" else "duration") for item in items)
            if duration != self.production.target_duration_seconds:
                raise ValueError("Target duration must equal the sum of estimated beat durations")
        return self


class WebtoonProposal(ProductionProposal):
    production: WebtoonProduction


class ShortDramaProposal(ProductionProposal):
    production: ShortDramaProduction


class StoryReelProposal(ProductionProposal):
    production: StoryReelProduction


def proposal_type(target_format):
    return {"webtoon": WebtoonProposal, "short_drama": ShortDramaProposal, "story_reel": StoryReelProposal}[target_format]


class ReferenceBindingContext(InputModel):
    binding_id: Name
    artifact_id: Name
    target_type: Literal["story", "character", "place"]
    target_id: Name
    role: Literal["character_identity", "outfit", "place", "visual_style", "general"]



class ContinuityContext(InputModel):
    story: StoryCreate
    characters: list[CharacterResponse]
    places: list[PlaceResponse]
    canon: list[CanonEntryResponse]
    references: list[Reference]
    reference_bindings: list[ReferenceBindingContext] = Field(default_factory=list)
    guidance: GuidanceProfileInput
    workflow_configuration: WorkflowConfiguration


class InstructionOverride(InputModel):
    beat_number: int = Field(ge=1, le=24, strict=True)
    instruction: Text


class CompiledInstruction(InputModel):
    beat_number: int
    compiled: str
    override: str | None = None
    effective: str


class MediaProductionPlan(ProductionProposal):
    plan_id: UUID = Field(default_factory=uuid4)
    story_id: Name
    scene_id: Name
    target_format: TargetFormat
    source_digest: Digest
    context_digest: Digest
    continuity_context: ContinuityContext
    instruction: Note | None = None
    overrides: list[InstructionOverride] = Field(default_factory=list, max_length=24)
    compiler_version: Literal["production-v1"] = "production-v1"
    compiled_instructions: list[CompiledInstruction] = Field(default_factory=list, max_length=24)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def format_matches(self):
        if self.target_format != self.production.target_format:
            raise ValueError("Plan and production formats must match")
        indices = [item.beat_number for item in self.overrides]
        if len(indices) != len(set(indices)) or any(index > len(units(self.production)) for index in indices):
            raise ValueError("Override must identify a unique existing beat")
        return self


class TranslationRequest(InputModel):
    target_format: TargetFormat
    instruction: Note | None = None


class ReviewRequest(InputModel):
    plan: MediaProductionPlan


class ApprovalRequest(ReviewRequest):
    approved: Literal[True]


class ApprovedProduction(InputModel):
    adaptation_id: str
    revision: int
    plan: MediaProductionPlan
    manifest: MediaPlan
    source_changed: bool
    context_changed: bool
    approved_at: datetime


class CompiledProduction(InputModel):
    plan: MediaProductionPlan
    manifest: MediaPlan
