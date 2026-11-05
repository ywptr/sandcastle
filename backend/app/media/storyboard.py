"""Deterministic prose-to-panel composition; no new events or media execution."""
import re

from sqlalchemy.orm import Session

from app.media.schemas import MediaPurpose, SceneImageOptions, StoryboardPlan
from app.media.service import (
    InvalidMediaIntent, MediaDomainNotFound, _require_story, _scene_image_requests,
)
from app.stories.scene_service import get_scene
from app.media.adaptation.schemas import AdaptationOptions, MediaAdaptationPlan
from app.media.adaptation.service import build_adaptation_context, validate_plan

# Composition defaults, not a required dramatic arc or execution strategy.
_PANEL_FOCUS = (
    ("establish", "Use a wide establishing view of the setting and initial visible state in this beat."),
    ("develop", "Use a medium view to show the action or observable state described in this beat."),
    ("focus", "Use a close view of an observable detail or reaction explicitly present in this beat."),
    ("close", "Use a closing view of the final described state, leaving the sequence ready to continue."),
)


def _visual_beats(content: str) -> list[str]:
    """Keep every source unit in order; sparse prose uses successive viewpoints."""
    units = [unit.strip() for unit in re.split(r"(?<=[.!?。！？])\s+|\n+", content) if unit.strip()]
    # Prefer clause boundaries to word-count chopping when prose has few sentences.
    if len(units) < 4:
        units = [part.strip() for unit in units for part in re.split(r"(?<=[;；])\s*", unit) if part.strip()]
    if len(units) >= 4:
        return [" ".join(units[i * len(units) // 4:(i + 1) * len(units) // 4]) for i in range(4)]
    # One to three units cannot support four invented events. Reframe existing moments.
    return [units[min(i * len(units) // 4, len(units) - 1)] for i in range(4)]


def create_four_panel_storyboard(
    db: Session,
    *,
    story_id: str,
    scene_id: str,
    user_id: str,
    options: SceneImageOptions | None = None,
    adaptation: MediaAdaptationPlan | None = None,
) -> StoryboardPlan:
    story = _require_story(db, story_id, user_id)
    scene = get_scene(db, story.story_id, scene_id)
    if scene is None:
        raise MediaDomainNotFound("Scene not found in story")
    if not scene.content.strip():
        raise InvalidMediaIntent("Scene content cannot be blank")

    options = options or SceneImageOptions()
    groups = None
    if adaptation is not None:
        adaptation_options = options if isinstance(options, AdaptationOptions) else AdaptationOptions(**options.model_dump(), output_format=adaptation.output_format)
        context = build_adaptation_context(db, story_id=story_id, scene_id=scene_id, user_id=user_id, options=adaptation_options)
        validate_plan(context, adaptation)
        if adaptation.issues:
            raise InvalidMediaIntent("Resolve adaptation continuity issues before compiling a storyboard")
        shots = adaptation.shots
        groups = [shots[i * len(shots) // 4:(i + 1) * len(shots) // 4] if len(shots) >= 4
                  else [shots[min(i * len(shots) // 4, len(shots) - 1)]] for i in range(4)]
    # This is individual-panel framing, not a composite layout or call count.
    options = options.model_copy(update={"aspect_ratio": options.aspect_ratio or "1:1"})
    beats = ["\n".join(f"{shot.framing_hint}: {shot.visual_instruction}" for shot in group) for group in groups] if groups else _visual_beats(scene.content)
    # Reuse M3's context selection, reference construction and instruction compiler.
    # Context is loaded once for all panels, keeping identity references consistent.
    requests = _scene_image_requests(
        db, story, scene_id, options, visual_moments=beats, purpose=MediaPurpose.COMIC_PANEL, visual_only=adaptation is not None,
    )
    for number, (request, (role, focus)) in enumerate(zip(requests, _PANEL_FOCUS), start=1):
        if adaptation is not None:
            group = groups[number - 1]
            request.context.adaptation_id = adaptation.adaptation_id
            request.context.adapted_shot_sequences = [shot.sequence for shot in group]
            refs = {ref.model_dump_json(): ref for shot in group for ref in shot.references}
            request.references = list(refs.values())
        request.context.panel_number = number
        request.context.panel_count = 4
        request.context.panel_role = role
        request.prompt = "\n".join([
            f"Panel {number} of 4 in an ordered visual sequence.",
            focus,
            "Depict only this panel's source beat. Preserve its meaning and temporal position.",
            "Do not invent actions, dialogue, outcomes, or a resolution absent from the source beat.",
            "Shared subject/environment descriptions and facts guide identity; they are not extra events.",
            request.prompt,
        ])
    return StoryboardPlan(story_id=story.story_id, scene_id=scene.scene_id, requests=requests)
