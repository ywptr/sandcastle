from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanonEntry


def create_canon_entry(
    db: Session,
    *,
    story_id: str,
    entry_type: str,
    key: str,
    value: str,
) -> CanonEntry:
    entry = CanonEntry(
        story_id=story_id,
        type=entry_type,
        key=key,
        value=value,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry


def list_canon_entries(
    db: Session,
    story_id: str,
) -> list[CanonEntry]:
    statement = (
        select(CanonEntry)
        .where(
            CanonEntry.story_id == story_id
        )
        .order_by(CanonEntry.created_at)
    )

    return list(
        db.scalars(statement).all()
    )