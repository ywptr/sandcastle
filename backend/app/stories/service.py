from sqlalchemy.orm import Session
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from app.stories.schemas import StoryCreate

from app.db.models import Story


def create_story(
    db: Session,
    user_id: str,
    *,
    title: str,
    premise: str | None = None,
    objective: str | None = None,
    language: str | None = None,
    primary_genre: str | None = None,
    secondary_genres: list[str] | None = None,
) -> Story:
    metadata = StoryCreate(title=title, premise=premise, objective=objective, language=language, primary_genre=primary_genre, secondary_genres=secondary_genres or [])
    story = Story(
        language=metadata.language, primary_genre=metadata.primary_genre, secondary_genres=metadata.secondary_genres,
        user_id=user_id,
        title=title,
        premise=premise,
        objective=objective,
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    return story


def get_story(
    db: Session,
    story_id: str,
    user_id: str,
) -> Story | None:
    return (
        db.query(Story)
        .filter(
            Story.story_id == story_id,
            Story.user_id == user_id,
        )
        .first()
    )


def list_stories(
    db: Session,
    user_id: str,
) -> list[Story]:
    return (
        db.query(Story)
        .filter(
            Story.user_id == user_id
        )
        .order_by(
            Story.created_at.desc()
        )
        .all()
    )


def update_story(db: Session, story: Story, **changes) -> Story:
    try:
        validated = StoryCreate.model_validate({**{key: getattr(story, key) for key in StoryCreate.model_fields}, **changes})
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    changes = {key: getattr(validated, key) for key in changes}
    for field, value in changes.items():
        setattr(story, field, value)
    db.commit()
    db.refresh(story)
    return story
