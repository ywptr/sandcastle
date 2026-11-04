from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanonEntry, Story
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.world.service import get_character, get_place


def create_canon_entry(
    db: Session,
    *,
    story_id: str,
    entry_type: str,
    key: str,
    value: str,
    subject_id: str | None = None,
    fact_type: str | None = None,
) -> CanonEntry:
    _lock_and_validate(db, story_id, entry_type, subject_id)
    entry = CanonEntry(
        story_id=story_id,
        type=entry_type,
        key=key,
        value=value,
        subject_id=subject_id,
        fact_type=fact_type,
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

def get_canon_entry(db: Session, story_id: str, entry_id: str) -> CanonEntry | None:
    return db.scalar(select(CanonEntry).where(
        CanonEntry.story_id == story_id, CanonEntry.canon_entry_id == entry_id,
    ))


def update_canon_entry(db: Session, entry: CanonEntry, **changes) -> CanonEntry:
    _lock_and_validate(db, entry.story_id, changes.get("type", entry.type), changes.get("subject_id", entry.subject_id))
    for field, value in changes.items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


def _lock_and_validate(db: Session, story_id: str, entry_type: str, subject_id: str | None):
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    if subject_id is None:
        return
    getter = {"character": get_character, "place": get_place, "location": get_place}.get(entry_type)
    if getter is None:
        raise InvalidMediaIntent("Only Character and Place Canon supports a domain subject ID")
    if getter(db, story_id, subject_id) is None:
        raise MediaDomainNotFound("Canon subject not found in story")
