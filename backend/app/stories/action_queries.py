from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AuthorityDecision,
    StoryAction,
)


def list_story_actions(
    db: Session,
    story_id: str,
) -> list[StoryAction]:
    statement = (
        select(StoryAction)
        .where(
            StoryAction.story_id == story_id
        )
        .order_by(
            StoryAction.created_at.desc()
        )
    )

    return list(
        db.scalars(statement).all()
    )


def get_latest_decision(
    db: Session,
    action_id: str,
) -> AuthorityDecision | None:
    statement = (
        select(AuthorityDecision)
        .where(
            AuthorityDecision.action_id
            == action_id
        )
        .order_by(
            AuthorityDecision.created_at.desc()
        )
        .limit(1)
    )

    return db.scalar(statement)