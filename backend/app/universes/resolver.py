"""Read-only inherited projections. No rows are copied until explicit divergence."""
from types import SimpleNamespace
from uuid import UUID, uuid5
from sqlalchemy import select

from app.db.models import (
    Universe, UniverseStoryMembership, UniverseCanonReference, CanonObject,
    CanonObjectVersion, Character, Place, Story, StoryCanonReference,
)

# Fixed application namespace gives stable UUIDs for each Story/object pair.
_SUBJECT_NAMESPACE = UUID("c8137aca-8c89-4fd4-b7e5-19b9828c09ee")


def inherited_references(db, story_id, local_refs):
    membership = db.get(UniverseStoryMembership, story_id)
    if membership is None:
        return []
    universe = db.get(Universe, membership.universe_id)
    story = db.get(Story, story_id)
    if story is None or universe.user_id != story.user_id:
        return []
    overridden = {ref.canon_object_id for ref in local_refs}
    pins = db.scalars(select(UniverseCanonReference).where(
        UniverseCanonReference.universe_id == universe.universe_id).order_by(UniverseCanonReference.reference_id))
    result = []
    for pin in pins:
        obj = db.get(CanonObject, pin.canon_object_id)
        if obj.user_id != story.user_id or obj.canon_object_id in overridden:
            continue
        result.append(SimpleNamespace(reference_id=pin.reference_id, story_id=story_id,
            canon_object_id=obj.canon_object_id, canon_version_id=pin.canon_version_id,
            target_type=obj.object_type,
            target_id=str(uuid5(_SUBJECT_NAMESPACE, story_id + ":" + obj.canon_object_id)),
            created_at=pin.created_at, inherited=True, universe_id=universe.universe_id))
    return result


def inherited_subjects(db, story_id, kind):
    local = list(db.scalars(select(StoryCanonReference).where(StoryCanonReference.story_id == story_id)))
    result = []
    for ref in inherited_references(db, story_id, local):
        if ref.target_type != kind:
            continue
        version = db.get(CanonObjectVersion, ref.canon_version_id)
        model = Character if kind == "character" else Place
        identity = {"character_id" if kind == "character" else "place_id": ref.target_id}
        result.append(model(story_id=story_id, **identity, **version.data["structure"],
            created_at=version.created_at, updated_at=version.created_at))
    return result


def materialize_reference(db, ref):
    """Only used by an explicit Story fork/pin operation, inside its transaction."""
    if not getattr(ref, "inherited", False):
        return ref
    version = db.get(CanonObjectVersion, ref.canon_version_id)
    model = Character if ref.target_type == "character" else Place
    identity = {"character_id" if ref.target_type == "character" else "place_id": ref.target_id}
    db.add(model(story_id=ref.story_id, **identity, **version.data["structure"]))
    db.flush()
    row = StoryCanonReference(story_id=ref.story_id, canon_object_id=ref.canon_object_id,
        canon_version_id=ref.canon_version_id, target_type=ref.target_type, target_id=ref.target_id)
    db.add(row)
    db.flush()
    return row
