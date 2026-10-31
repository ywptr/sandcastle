from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.scene import Scene
from app.db.models.story import Story
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
    source_action_id: str,
    content: str,
) -> Scene:
    scene = Scene(
        story_id=story_id,
        source_action_id=source_action_id,
        sequence_number=get_next_sequence_number(
            db,
            story_id,
        ),
        content=content,
    )

    db.add(scene)
    db.commit()
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
        premise=story.premise,
        objective=story.objective,
        canon=[
            {
                "type": entry.type,
                "key": entry.key,
                "value": entry.value,
            }
            for entry in canon_entries
        ],
        previous_scenes=[
            scene.content
            for scene in existing_scenes
        ],
        request=request,
    )

    content = await generator.generate_scene(
        context
    )

    return create_scene(
        db,
        story_id=story.story_id,
        source_action_id=action_id,
        content=content,
    )