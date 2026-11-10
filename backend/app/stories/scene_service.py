from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.scene import Scene
from app.db.models.story import Story
from app.world.service import list_characters, list_places
from app.stories.generator import (
    SceneGenerationContext,
    StoryGenerator,
)


def list_scenes(
    db: Session,
    story_id: str,
) -> list[Scene]:
    return (
        db.query(Scene)
        .filter(
            Scene.story_id == story_id
        )
        .order_by(
            Scene.sequence_number.asc()
        )
        .all()
    )


def get_next_sequence_number(
    db: Session,
    story_id: str,
) -> int:
    current = (
        db.query(
            func.max(
                Scene.sequence_number
            )
        )
        .filter(
            Scene.story_id == story_id
        )
        .scalar()
    )

    return (current or 0) + 1


def create_scene(
    db: Session,
    *,
    story_id: str,
    source_action_id: str | None = None,
    title: str | None = None,
    content: str,
) -> Scene:
    # Lock the parent row on PostgreSQL so sequence allocation is serialized.
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    scene = Scene(
        story_id=story_id,
        source_action_id=source_action_id,
        sequence_number=get_next_sequence_number(db, story_id),
        title=title,
        content=content,
    )
    db.add(scene)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(scene)
    return scene


async def generate_scene(
    db: Session,
    *,
    story: Story,
    action_id: str,
    request: str,
    canon_entries: list,
    generator: StoryGenerator,
) -> Scene:
    existing_scenes = list_scenes(
        db,
        story.story_id,
    )

    context = SceneGenerationContext(
        title=story.title,
        language=story.language, primary_genre=story.primary_genre, secondary_genres=list(story.secondary_genres),
        premise=story.premise,
        objective=story.objective,
        canon=[
            {
                "type": entry.type,
                "key": entry.key,
                "value": entry.value,
            }
            for entry in canon_entries if entry.status == "approved"
        ],
        previous_scenes=[
            scene.content
            for scene in existing_scenes
        ],
        request=request,
        characters=[
            {field: getattr(character, field) for field in
             ("name", "description", "appearance", "outfit", "personality")}
            for character in list_characters(db, story.story_id)
        ],
        places=[
            {field: getattr(place, field) for field in
             ("name", "description", "appearance", "atmosphere")}
            for place in list_places(db, story.story_id)
        ],
    )

    content = await generator.generate_scene(
        context
    )

    if not content or not content.strip():
        raise ValueError("Generator returned empty scene content")

    return create_scene(
        db,
        story_id=story.story_id,
        source_action_id=action_id,
        content=content,
    )

def get_scene(
    db: Session,
    story_id: str,
    scene_id: str,
) -> Scene | None:
    return (
        db.query(Scene)
        .filter(
            Scene.story_id == story_id,
            Scene.scene_id == scene_id,
        )
        .first()
    )


def update_scene(db: Session, scene: Scene, **changes) -> Scene:
    for field, value in changes.items():
        setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return scene
