from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Story


def create_story(
    db: Session,
    *,
    title: str,
    premise: str | None = None,
    objective: str | None = None,
) -> Story:
    story = Story(
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
) -> Story | None:
    return db.get(
        Story,
        story_id,
    )


def list_stories(
    db: Session,
) -> list[Story]:
    statement = (
        select(Story)
        .order_by(Story.created_at.desc())
    )

    return list(
        db.scalars(statement).all()
    )