"""Read existing authoring data and compile instructions. Never execute media jobs."""
from sqlalchemy.orm import Session

from app.canon.service import list_canon_entries
from app.artifacts.resolver import explicit_artifact_references, resolve_applicable_references
from app.db.models.canon_entry import CanonEntry
from app.db.models.character import Character
from app.db.models.place import Place
from app.db.models.scene import Scene
from app.db.models.story import Story
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.schemas import (
    MediaContext, MediaPlan, MediaPurpose, MediaRequest, MediaType,
    Reference, SceneImageOptions, SceneImagePlanInput,
)
from app.stories.scene_service import get_scene
from app.stories.service import get_story
from app.world.service import list_characters, list_places


def _require_story(db: Session, story_id: str, user_id: str) -> Story:
    story = get_story(db, story_id, user_id)
    if story is None:
        raise MediaDomainNotFound("Story not found")
    if not story.title.strip():
        raise InvalidMediaIntent("Story title cannot be blank")
    return story


def _build_instruction(
    story: Story,
    scene: Scene | None,
    characters: list[Character],
    places: list[Place],
    canon: list[CanonEntry],
    *,
    visual_moment: str | None = None,
) -> str:
    lines = [
        "Create a single image depicting the following narrative moment.",
        "Use the supplied visual references where available.",
        f"Title: {story.title}",
    ]
    if story.premise:
        lines.append(f"Premise: {story.premise}")
    if story.objective:
        lines.append(f"Narrative objective: {story.objective}")
    if scene is not None:
        lines.extend([f"Moment: {scene.title or f'Scene {scene.sequence_number}'}",
                      scene.content if visual_moment is None else visual_moment])
    elif visual_moment is not None:
        lines.append(visual_moment)
    if characters:
        lines.append("Visual subjects:")
        for character in characters:
            lines.append(f"- {character.name}")
            for label, value in (
                ("Description", character.description), ("Appearance", character.appearance),
                ("Outfit", character.outfit), ("Personality", character.personality),
            ):
                if value:
                    lines.append(f"  {label}: {value}")
    if places:
        lines.append("Environment:")
        for place in places:
            lines.append(f"- {place.name}")
            for label, value in (
                ("Description", place.description), ("Appearance", place.appearance),
                ("Atmosphere", place.atmosphere),
            ):
                if value:
                    lines.append(f"  {label}: {value}")
    if canon:
        lines.append("Established facts to preserve in the depiction:")
        lines.extend(f"- {entry.value}" for entry in canon)
    return "\n".join(lines)


def _select_visual_context(
    db: Session, story: Story, options: SceneImageOptions,
) -> tuple[list[Character], list[Place], list[CanonEntry], list[Reference]]:
    characters = list_characters(db, story.story_id)
    places = list_places(db, story.story_id)
    if options.character_ids is not None:
        available = {character.character_id for character in characters}
        if not set(options.character_ids) <= available:
            raise MediaDomainNotFound("Character not found in story")
        characters = [c for c in characters if c.character_id in options.character_ids]
    if options.place_ids is not None:
        available = {place.place_id for place in places}
        if not set(options.place_ids) <= available:
            raise MediaDomainNotFound("Place not found in story")
        places = [p for p in places if p.place_id in options.place_ids]

    # Selection only: this layer neither evaluates continuity nor changes Canon.
    canon = sorted(
        (entry for entry in list_canon_entries(db, story.story_id) if entry.status == "approved"),
        key=lambda entry: (entry.type, entry.key, entry.canon_entry_id),
    )
    references = []
    for character in characters:
        references.append(Reference(kind="character", reference_id=character.character_id))
        if character.outfit.strip():
            # M2 stores outfit on Character, so its stable reference is that Character ID.
            references.append(Reference(kind="outfit", reference_id=character.character_id))
    references.extend(Reference(kind="place", reference_id=place.place_id) for place in places)
    artifact_keys = sorted({(ref.kind, ref.reference_id) for ref in options.artifact_references})
    references.extend(Reference(kind=kind, reference_id=ref_id) for kind, ref_id in artifact_keys)

    references.extend(resolve_applicable_references(
        db, story_id=story.story_id, user_id=story.user_id,
        character_ids=[character.character_id for character in characters],
        place_ids=[place.place_id for place in places],
    ))
    references.extend(explicit_artifact_references(db, story.user_id, options.artifact_ids))
    return characters, places, canon, references


def _scene_image_requests(
    db: Session, story: Story, scene_id: str, options: SceneImageOptions,
    *,
    visual_moments: list[str] | None = None,
    purpose: MediaPurpose = MediaPurpose.SCENE,
) -> list[MediaRequest]:
    scene = get_scene(db, story.story_id, scene_id)
    if scene is None:
        raise MediaDomainNotFound("Scene not found in story")
    if not scene.content.strip():
        raise InvalidMediaIntent("Scene content cannot be blank")

    characters, places, canon, references = _select_visual_context(db, story, options)

    return [MediaRequest(
        media_type=MediaType.IMAGE,
        purpose=purpose,
        prompt=_build_instruction(story, scene, characters, places, canon, visual_moment=moment),
        story_id=story.story_id,
        scene_id=scene.scene_id,
        references=references,
        aspect_ratio=options.aspect_ratio,
        context=MediaContext(
            scene_sequence_number=scene.sequence_number,
            canon_entry_ids=[entry.canon_entry_id for entry in canon],
        ),
    ) for moment in (visual_moments if visual_moments is not None else [scene.content])]


def _scene_image_request(
    db: Session, story: Story, scene_id: str, options: SceneImageOptions,
) -> MediaRequest:
    return _scene_image_requests(db, story, scene_id, options)[0]


def create_scene_image_request(
    db: Session,
    *,
    story_id: str,
    scene_id: str,
    user_id: str,
    options: SceneImageOptions | None = None,
) -> MediaRequest:
    story = _require_story(db, story_id, user_id)
    return _scene_image_request(db, story, scene_id, options or SceneImageOptions())


def create_media_plan(
    db: Session,
    *,
    story_id: str,
    user_id: str,
    intent: SceneImagePlanInput,
) -> MediaPlan:
    """One image request per Scene in caller order; no panel/storyboard inference."""
    story = _require_story(db, story_id, user_id)
    return MediaPlan(
        story_id=story.story_id,
        requests=[_scene_image_request(db, story, scene_id, intent) for scene_id in intent.scene_ids],
    )
