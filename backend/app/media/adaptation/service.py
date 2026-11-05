"""Load authoritative context and validate ephemeral adaptation results."""
import hashlib
import json
from app.guidance.service import get_profile
from app.media.adaptation.planner import AdaptationContext, ShotPlanner
from app.media.adaptation.schemas import AdaptationOptions, MediaAdaptationPlan
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.service import _require_story, _select_visual_context
from app.stories.scene_service import get_scene
from app.world.service import list_characters


class AdaptationUnavailable(ValueError):
    pass


def build_adaptation_context(db, *, story_id, scene_id, user_id, options):
    story = _require_story(db, story_id, user_id)
    scene = get_scene(db, story_id, scene_id)
    if scene is None:
        raise MediaDomainNotFound("Scene not found in story")
    if not scene.content.strip():
        raise InvalidMediaIntent("Scene content cannot be blank")
    if len(scene.content) > 60000:
        raise InvalidMediaIntent("Scene exceeds the initial adaptation limit of 60,000 characters")
    profile = get_profile(db, story_id, user_id)
    characters, places, canon, references = _select_visual_context(db, story, options)
    character_data = [{"id": row.character_id, "name": row.name, "appearance": row.appearance, "outfit": row.outfit} for row in characters]
    place_data = [{"id": row.place_id, "name": row.name, "appearance": row.appearance} for row in places]
    subject_names = {row.character_id: row.name for row in list_characters(db, story_id)}
    facts = [{"id": row.canon_entry_id, "subject_name": subject_names.get(row.subject_id), "type": row.type, "subject_id": row.subject_id,
              "key": row.key, "value": row.value, "version_id": getattr(row, "canon_version_id", None)} for row in canon]
    payload = {"story_id": story_id, "scene_id": scene_id, "content": scene.content,
               "profile": profile.model_dump(mode="json", exclude={"created_at", "updated_at"}),
               "characters": character_data, "places": place_data, "canon": facts,
               "references": [ref.model_dump() for ref in references], "options": options.model_dump()}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return AdaptationContext(story_id, scene_id, scene.content, profile, character_data, place_data, facts, references, options, digest)


def validate_plan(context, plan):
    if (plan.story_id, plan.scene_id, plan.context_digest, plan.audience, plan.maturity_rating, plan.output_format) != (
        context.story_id, context.scene_id, context.digest, context.profile.audience, context.profile.maturity_rating, context.options.output_format):
        raise InvalidMediaIntent("Adaptation identity/context changed; preview again before storyboard planning")
    expected_references = {ref.model_dump_json() for ref in context.references}
    for shot in plan.shots:
        if context.scene_content[shot.source_start:shot.source_end] != shot.narrative_beat:
            raise InvalidMediaIntent("Adaptation lost its original narrative source span")
        if not set(shot.character_ids) <= {row["id"] for row in context.characters} or not set(shot.place_ids) <= {row["id"] for row in context.places}:
            raise InvalidMediaIntent("Adapted shot contains an unavailable subject")
        if any(ref.model_dump_json() not in expected_references for ref in shot.references):
            raise InvalidMediaIntent("Adapted shot contains unavailable references")
    covered = sorted({(shot.source_start, shot.source_end) for shot in plan.shots})
    cursor = 0
    for start, end in covered:
        if any(not char.isspace() for char in context.scene_content[cursor:start]):
            raise InvalidMediaIntent("Adaptation omitted narrative content")
        cursor = max(cursor, end)
    if any(not char.isspace() for char in context.scene_content[cursor:]):
        raise InvalidMediaIntent("Adaptation omitted narrative content")
    if [shot.source_start for shot in plan.shots] != sorted(shot.source_start for shot in plan.shots):
        raise InvalidMediaIntent("Adaptation changed narrative order")
    return plan


def adapt_scene(db, *, story_id, scene_id, user_id, options=None, planner: ShotPlanner):
    options = options or AdaptationOptions()
    context = build_adaptation_context(db, story_id=story_id, scene_id=scene_id, user_id=user_id, options=options)
    try:
        output = planner.adapt(context)
        result = MediaAdaptationPlan.model_validate(output.model_dump() if isinstance(output, MediaAdaptationPlan) else output)
        return validate_plan(context, result)
    except Exception as error:
        raise AdaptationUnavailable("Shot planner returned invalid adaptation output; review the Scene or use a supported planner") from error
