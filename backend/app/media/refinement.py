"""Preview refinement intent only; preserve source provenance without execution."""
from sqlalchemy.orm import Session

from app.artifacts.resolver import explicit_artifact_references
from app.artifacts.service import get_artifact
from app.media.schemas import (
    MediaContext, MediaPurpose, MediaRequest, MediaType, Reference, RefinementInput,
)
from app.media.service import InvalidMediaIntent, MediaDomainNotFound, _build_instruction, _require_story, _select_visual_context
from app.stories.scene_service import get_scene


def create_refinement_request(
    db: Session, *, artifact_id: str, user_id: str, intent: RefinementInput,
) -> MediaRequest:
    source = get_artifact(db, artifact_id, user_id)
    if source.media_type != "image":
        raise InvalidMediaIntent("Refinement requires an image artifact")
    context = MediaContext(source_artifact_id=source.artifact_id)
    references = [Reference(kind="artifact", reference_id=source.artifact_id, role="source")]
    lines = [
        "Refine the source image according to the following instruction.",
        "Preserve source identity and visual details except where the instruction requests a change.",
        f"Refinement instruction: {intent.instruction}",
    ]
    if intent.story_id is not None:
        story = _require_story(db, intent.story_id, user_id)
        scene = None
        if intent.scene_id is not None:
            scene = get_scene(db, story.story_id, intent.scene_id)
            if scene is None:
                raise MediaDomainNotFound("Scene not found in story")
        characters, places, canon, selected = _select_visual_context(db, story, intent)
        references.extend(selected)
        context.canon_entry_ids = [entry.canon_entry_id for entry in canon]
        context.scene_sequence_number = scene.sequence_number if scene else None
        lines.extend(["Saved narrative context (guidance, not a Canon update):",
                      _build_instruction(story, scene, characters, places, canon)])
    else:
        if intent.scene_id is not None:
            raise InvalidMediaIntent("Scene context requires a Story")
        if intent.character_ids or intent.place_ids:
            raise InvalidMediaIntent("Character or Place selection requires a Story")
        references.extend(explicit_artifact_references(db, user_id, intent.artifact_ids))
        references.extend(Reference(kind=ref.kind, reference_id=ref.reference_id)
                          for ref in sorted(intent.artifact_references, key=lambda ref: (ref.kind, ref.reference_id)))
    # The source is not redundantly added as an unbound general reference.
    references = [ref for index, ref in enumerate(references)
                  if index == 0 or not (ref.kind == "artifact" and ref.reference_id == source.artifact_id
                                        and ref.binding_id is None)]
    return MediaRequest(
        media_type=MediaType.IMAGE, purpose=MediaPurpose.IMAGE_REFINEMENT,
        story_id=intent.story_id, scene_id=intent.scene_id, prompt="\n".join(lines),
        references=references, aspect_ratio=intent.aspect_ratio, context=context,
    )
