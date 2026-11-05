from typing import Literal
from pydantic import Field, model_validator
from app.validation import InputModel
from app.media.schemas import AspectRatio
from app.media.adaptation.schemas import Sensitivity

Difficulty = Literal["easy", "normal", "difficult", "impossible"]
StepId = Literal["narrative_guidance", "scene_creation", "canon_extraction", "canon_review", "continuity_check", "media_adaptation", "storyboard_planning", "media_execution"]
ORDER = ["narrative_guidance", "scene_creation", "canon_extraction", "canon_review", "continuity_check", "media_adaptation", "storyboard_planning", "media_execution"]


class StepSetting(InputModel):
    step_id: StepId
    enabled: bool = True


class GuidanceSettings(InputModel):
    count: int = Field(default=3, ge=1, le=5)
    recent_scene_count: int = Field(default=4, ge=1, le=5)


class ReviewSettings(InputModel):
    require_before_media: bool = False
    review_new: bool = False
    review_conflicts: bool = True
    review_uncertain: bool = True


class MediaSettings(InputModel):
    aspect_ratio: AspectRatio = "1:1"
    output_format: Literal["image", "webtoon"] = "image"


class AdaptationSettings(InputModel):
    sensitivity_hints: list[Sensitivity] = Field(default_factory=list, max_length=6)


class ReferenceSettings(InputModel):
    character_ids: list[str] | None = None
    place_ids: list[str] | None = None
    artifact_ids: list[str] = Field(default_factory=list, max_length=50)


class WorkflowConfiguration(InputModel):
    steps: list[StepSetting] = Field(default_factory=lambda: [StepSetting(step_id=s, enabled=s != "media_execution") for s in ORDER])
    order: list[StepId] = Field(default_factory=lambda: list(ORDER))
    guidance: GuidanceSettings = Field(default_factory=GuidanceSettings)
    review: ReviewSettings = Field(default_factory=ReviewSettings)
    media: MediaSettings = Field(default_factory=MediaSettings)
    adaptation: AdaptationSettings = Field(default_factory=AdaptationSettings)
    references: ReferenceSettings = Field(default_factory=ReferenceSettings)

    @model_validator(mode="after")
    def safe_structure(self):
        if len(self.steps) != len(ORDER) or {s.step_id for s in self.steps} != set(ORDER):
            raise ValueError("Each supported step must appear exactly once")
        if len(self.order) != len(ORDER) or set(self.order) != set(ORDER):
            raise ValueError("Order must include each supported step exactly once")
        enabled = {s.step_id for s in self.steps if s.enabled}
        if "scene_creation" not in enabled:
            raise ValueError("Scene creation is required")
        if "media_execution" in enabled:
            raise ValueError("Live media execution remains unavailable")
        if "storyboard_planning" in enabled and "media_adaptation" not in enabled:
            raise ValueError("Storyboard planning requires adaptation")
        if self.review.require_before_media and not {"canon_review", "continuity_check"} <= enabled:
            raise ValueError("The review checkpoint requires Canon review and continuity checking")
        dependencies = [("narrative_guidance", "scene_creation"), ("scene_creation", "canon_extraction"),
                        ("canon_extraction", "canon_review"), ("scene_creation", "media_adaptation"),
                        ("continuity_check", "media_adaptation"), ("media_adaptation", "storyboard_planning"),
                        ("storyboard_planning", "media_execution")]
        if self.review.require_before_media:
            dependencies.append(("canon_review", "media_adaptation"))
        for before, after in dependencies:
            if before in enabled and after in enabled and self.order.index(before) >= self.order.index(after):
                raise ValueError(f"{before} must precede {after}")
        return self


class StoryWorkflowInput(InputModel):
    difficulty: Difficulty = "easy"
    workflow_template_id: str = "standard-story"
    template_version: int = Field(default=1, ge=1)
    configuration: WorkflowConfiguration | None = None


class WorkflowAction(InputModel):
    scene_id: str | None = None
