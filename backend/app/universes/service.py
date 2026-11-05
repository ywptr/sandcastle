"""Universe ownership, explicit pins, and membership. No automatic publication."""
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import Universe, UniverseStoryMembership, UniverseCanonReference
from app.canon import library_service as library


def get_universe(db, universe_id, user_id, *, lock=False):
    query = select(Universe).where(Universe.universe_id == universe_id, Universe.user_id == user_id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if row is None:
        raise HTTPException(404, "Universe not found")
    return row


def list_universes(db, user_id):
    return list(db.scalars(select(Universe).where(Universe.user_id == user_id).order_by(Universe.created_at, Universe.universe_id)))


def create_universe(db, user_id, **values):
    row = Universe(user_id=user_id, **values)
    db.add(row)
    db.commit()
    return row


def update_universe(db, universe_id, user_id, **values):
    row = get_universe(db, universe_id, user_id, lock=True)
    for key, value in values.items():
        setattr(row, key, value)
    db.commit()
    return row


def attach_story(db, universe_id, story_id, user_id):
    library.story(db, story_id, user_id)
    get_universe(db, universe_id, user_id, lock=True)
    current = db.get(UniverseStoryMembership, story_id)
    if current:
        if current.universe_id != universe_id:
            raise HTTPException(409, "Remove the existing Universe membership before attaching another")
        return current
    row = UniverseStoryMembership(story_id=story_id, universe_id=universe_id)
    db.add(row)
    db.commit()
    return row


def remove_story(db, universe_id, story_id, user_id):
    library.story(db, story_id, user_id)
    get_universe(db, universe_id, user_id, lock=True)
    row = db.get(UniverseStoryMembership, story_id)
    if row is None or row.universe_id != universe_id:
        raise HTTPException(404, "Story membership not found")
    db.delete(row)
    db.commit()


def list_members(db, universe_id, user_id):
    get_universe(db, universe_id, user_id)
    return list(db.scalars(select(UniverseStoryMembership).where(UniverseStoryMembership.universe_id == universe_id).order_by(UniverseStoryMembership.story_id)))


def list_references(db, universe_id, user_id):
    get_universe(db, universe_id, user_id)
    return list(db.scalars(select(UniverseCanonReference).where(UniverseCanonReference.universe_id == universe_id).order_by(UniverseCanonReference.reference_id)))


def pin(db, universe_id, user_id, object_id, version_id, *, promote=False):
    get_universe(db, universe_id, user_id, lock=True)
    obj = library.get_object(db, object_id, user_id)
    version = library.get_version(db, obj, version_id)
    existing = db.scalar(select(UniverseCanonReference).where(UniverseCanonReference.universe_id == universe_id,
        UniverseCanonReference.canon_object_id == object_id))
    if existing:
        if existing.canon_version_id == version_id:
            return existing
        if not promote:
            raise HTTPException(409, "This Universe already pins this object; explicit pin update is required")
    if version.created_by_story_id:
        if not promote:
            raise HTTPException(409, "Story-specific versions require explicit promotion to Universe")
        # Publish a fixed baseline; future Story branch changes remain independent.
        version = library.append_version(db, obj, version.data, version,
            reason="Explicit promotion to Universe " + universe_id)
    row = existing or UniverseCanonReference(universe_id=universe_id, canon_object_id=object_id, canon_version_id=version.canon_version_id)
    row.canon_version_id = version.canon_version_id
    db.add(row)
    db.commit()
    return row


def move_pin(db, universe_id, user_id, reference_id, version_id):
    get_universe(db, universe_id, user_id, lock=True)
    row = db.get(UniverseCanonReference, reference_id)
    if row is None or row.universe_id != universe_id:
        raise HTTPException(404, "Universe Canon reference not found")
    obj = library.get_object(db, row.canon_object_id, user_id)
    version = library.get_version(db, obj, version_id)
    if version.created_by_story_id:
        raise HTTPException(409, "Promote this Story-specific version before updating a shared pin")
    row.canon_version_id = version_id
    db.commit()
    return row
