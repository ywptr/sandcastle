from sqlalchemy.orm import Session

from app.db.models import Story


def create_story(
    db: Session,
    user_id: str,
    *,
    title: str,
    premise: str | None = None,
    objective: str | None = None,
) -> Story:
    story = Story(
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
