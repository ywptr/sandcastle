"""Pinned immutable snapshots; existing Character/Place rows are local handles."""
from copy import deepcopy
from sqlalchemy import select, func
from fastapi import HTTPException
from pydantic import ValidationError
from app.db.models import CanonObject, CanonObjectVersion, StoryCanonReference, CanonEntry, Story, ReferenceBinding
from app.world.schemas import CharacterCreate, PlaceCreate
from app.world import service as world
from app.stories.service import get_story


def story(db, story_id, user_id):
    row = get_story(db, story_id, user_id)
    if row is None:
        raise HTTPException(404, "Story not found")
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    return row


def get_object(db, object_id, user_id):
    row = db.scalar(select(CanonObject).where(CanonObject.canon_object_id == object_id, CanonObject.user_id == user_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Canon object not found")
    return row


def get_version(db, obj, version_id):
    row = db.get(CanonObjectVersion, version_id)
    if row is None or row.canon_object_id != obj.canon_object_id:
        raise HTTPException(404, "Canon version not found")
    return row


def references(db, story_id):
    return list(db.scalars(select(StoryCanonReference).where(StoryCanonReference.story_id == story_id).order_by(StoryCanonReference.reference_id)))


def subject_reference(db, story_id, target_type, target_id):
    return db.scalar(select(StoryCanonReference).where(StoryCanonReference.story_id == story_id,
        StoryCanonReference.target_type == target_type, StoryCanonReference.target_id == target_id))


def reference(db, story_id, reference_id, user_id):
    story(db, story_id, user_id)
    row = db.get(StoryCanonReference, reference_id)
    if row is None or row.story_id != story_id:
        raise HTTPException(404, "Canon reference not found")
    get_object(db, row.canon_object_id, user_id)
    return row


def validated_data(kind, data):
    # Full replacement of typed structure; facts/visuals are managed separately.
    try:
        return (CharacterCreate if kind == "character" else PlaceCreate).model_validate(data).model_dump()
    except ValidationError as error:
        raise HTTPException(422, "Invalid typed Canon structure") from error


def append_version(db, obj, data, parent=None, story_id=None, reason=None):
    # Caller locks the object before allocating the monotonically increasing sequence.
    number = db.scalar(select(func.max(CanonObjectVersion.version_number)).where(CanonObjectVersion.canon_object_id == obj.canon_object_id)) or 0
    version = CanonObjectVersion(canon_object_id=obj.canon_object_id, version_number=number + 1,
        parent_version_id=parent.canon_version_id if parent else None, data=deepcopy(data),
        created_by_story_id=story_id, fork_reason=reason)
    db.add(version)
    db.flush()
    return version


def create_object(db, user_id, kind, data):
    structure = validated_data(kind, data)
    obj = CanonObject(user_id=user_id, object_type=kind, name=structure["name"])
    db.add(obj)
    db.flush()
    append_version(db, obj, {"structure": structure, "facts": [], "visuals": []})
    db.commit()
    return obj


def promote(db, story_id, user_id, kind, target_id):
    story(db, story_id, user_id)
    existing = subject_reference(db, story_id, kind, target_id)
    if existing:
        return existing
    target = (world.get_character if kind == "character" else world.get_place)(db, story_id, target_id)
    if target is None:
        raise HTTPException(404, "Subject not found")
    schema = CharacterCreate if kind == "character" else PlaceCreate
    structure = {key: getattr(target, key) for key in schema.model_fields}
    obj = CanonObject(user_id=user_id, object_type=kind, name=target.name)
    db.add(obj)
    db.flush()
    facts = [{"key": row.key, "value": row.value, "fact_type": row.fact_type, "source_entry_id": row.canon_entry_id}
             for row in db.scalars(select(CanonEntry).where(CanonEntry.story_id == story_id,
                 CanonEntry.subject_id == target_id, CanonEntry.status == "approved"))]
    visuals = [{"artifact_id": row.artifact_id, "binding_id": row.reference_id, "role": row.role}
               for row in db.scalars(select(ReferenceBinding).where(ReferenceBinding.story_id == story_id,
                   ReferenceBinding.target_type == kind, ReferenceBinding.target_id == target_id))]
    version = append_version(db, obj, {"structure": structure, "facts": facts, "visuals": visuals})
    ref = StoryCanonReference(story_id=story_id, canon_object_id=obj.canon_object_id,
        canon_version_id=version.canon_version_id, target_type=kind, target_id=target_id)
    db.add(ref)
    db.commit()
    return ref


def shared_version(db, object_id, user_id, parent_id, data):
    obj = get_object(db, object_id, user_id)
    parent = get_version(db, obj, parent_id)
    if parent.created_by_story_id:
        raise HTTPException(409, "A Story branch cannot become a shared update")
    snapshot = deepcopy(parent.data)
    snapshot["structure"] = validated_data(obj.object_type, data)
    version = append_version(db, obj, snapshot, parent)
    db.commit()
    return version


def attach(db, story_id, user_id, object_id, version_id):
    story(db, story_id, user_id)
    obj = get_object(db, object_id, user_id)
    version = get_version(db, obj, version_id)
    if version.created_by_story_id and version.created_by_story_id != story_id:
        raise HTTPException(409, "Story branches are private to their Story")
    # Wrappers preserve the existing selectors; no second authoring model is introduced.
    from app.db.models import Character, Place
    model = Character if obj.object_type == "character" else Place
    target = model(story_id=story_id, **version.data["structure"])
    db.add(target)
    db.flush()
    ref = StoryCanonReference(story_id=story_id, canon_object_id=object_id, canon_version_id=version_id,
        target_type=obj.object_type, target_id=target.character_id if obj.object_type == "character" else target.place_id)
    db.add(ref)
    db.commit()
    return ref


def move(db, story_id, user_id, reference_id, version_id):
    ref = reference(db, story_id, reference_id, user_id)
    obj = get_object(db, ref.canon_object_id, user_id)
    version = get_version(db, obj, version_id)
    if version.created_by_story_id and version.created_by_story_id != story_id:
        raise HTTPException(409, "Cannot pin another Story's branch")
    ref.canon_version_id = version_id
    target = (world.get_character if ref.target_type == "character" else world.get_place)(db, story_id, ref.target_id)
    for key, value in version.data["structure"].items():
        setattr(target, key, value)
    db.commit()
    return ref


def fork(db, story_id, user_id, reference_id, reason):
    if not reason.strip():
        raise HTTPException(422, "Fork reason is required")
    ref = reference(db, story_id, reference_id, user_id)
    obj = get_object(db, ref.canon_object_id, user_id)
    parent = get_version(db, obj, ref.canon_version_id)
    version = append_version(db, obj, parent.data, parent, story_id, reason)
    ref.canon_version_id = version.canon_version_id
    db.commit()
    return ref


def editable_reference(db, story_id, kind, subject_id):
    db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    ref = subject_reference(db, story_id, kind, subject_id)
    if ref:
        owner = db.get(Story, story_id).user_id
        get_object(db, ref.canon_object_id, owner)
        version = db.get(CanonObjectVersion, ref.canon_version_id)
        if version.created_by_story_id != story_id:
            raise HTTPException(409, "Fork this shared Canon reference before Story-specific editing")
    return ref


def record_edit(db, ref, *, structure=None, fact=None):
    if ref is None:
        return
    parent = db.get(CanonObjectVersion, ref.canon_version_id)
    obj = db.get(CanonObject, ref.canon_object_id)
    data = deepcopy(parent.data)
    if structure:
        data["structure"].update(structure)
    if fact:
        data["facts"] = [row for row in data["facts"] if row["key"] != fact["key"]] + [fact]
    version = append_version(db, obj, data, parent, ref.story_id, "Story edit")
    ref.canon_version_id = version.canon_version_id


def effective_entries(db, story_id, local):
    refs = references(db, story_id)
    targets = {(r.target_type, r.target_id) for r in refs}
    result = [row for row in local if (row.type, row.subject_id) not in targets or row.status != "approved"]
    for ref in refs:
        version = db.get(CanonObjectVersion, ref.canon_version_id)
        for index, fact in enumerate(version.data["facts"]):
            # Transient read DTO compatible with existing Canon consumers; never flushed.
            entry = CanonEntry(canon_entry_id=fact.get("source_entry_id") or f"{version.canon_version_id}:{index}",
                story_id=story_id, type=ref.target_type, subject_id=ref.target_id,
                fact_type=fact.get("fact_type"), key=fact["key"], value=fact["value"], status="approved",
                created_at=version.created_at, updated_at=version.created_at)
            entry.canon_version_id = version.canon_version_id
            result.append(entry)
    return result


def inherited_visual(db, story_id, user_id, binding_id, artifact_id, role):
    """Authorize a snapshot reference without requiring its original Story binding."""
    if get_story(db, story_id, user_id) is None:
        return False
    for ref in references(db, story_id):
        obj = db.get(CanonObject, ref.canon_object_id)
        if obj.user_id != user_id:
            continue
        version = db.get(CanonObjectVersion, ref.canon_version_id)
        if any(item["binding_id"] == binding_id and item["artifact_id"] == artifact_id and item["role"] == role
               for item in version.data["visuals"]):
            return True
    return False
