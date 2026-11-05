from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.character import Character
from app.db.models.place import Place


def list_characters(db: Session, story_id: str) -> list[Character]:
    from app.universes.resolver import inherited_subjects
    return list(db.scalars(select(Character).where(Character.story_id == story_id)
                          .order_by(Character.created_at, Character.character_id))) + inherited_subjects(db, story_id, "character")


def list_places(db: Session, story_id: str) -> list[Place]:
    from app.universes.resolver import inherited_subjects
    return list(db.scalars(select(Place).where(Place.story_id == story_id)
                          .order_by(Place.created_at, Place.place_id))) + inherited_subjects(db, story_id, "place")


def create_character(db: Session, story_id: str, **values) -> Character:
    character = Character(story_id=story_id, **values)
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


def create_place(db: Session, story_id: str, **values) -> Place:
    place = Place(story_id=story_id, **values)
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


def get_character(db: Session, story_id: str, character_id: str) -> Character | None:
    local = db.scalar(select(Character).where(Character.story_id == story_id, Character.character_id == character_id))
    if local is not None:
        return local
    from app.universes.resolver import inherited_subjects
    return next((row for row in inherited_subjects(db, story_id, "character") if row.character_id == character_id), None)


def get_place(db: Session, story_id: str, place_id: str) -> Place | None:
    local = db.scalar(select(Place).where(Place.story_id == story_id, Place.place_id == place_id))
    if local is not None:
        return local
    from app.universes.resolver import inherited_subjects
    return next((row for row in inherited_subjects(db, story_id, "place") if row.place_id == place_id), None)


def update_character(db: Session, character: Character, **changes) -> Character:
    from app.canon.library_service import editable_reference, record_edit
    ref = editable_reference(db, character.story_id, "character", character.character_id)
    record_edit(db, ref, structure=changes)
    for field, value in changes.items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character


def update_place(db: Session, place: Place, **changes) -> Place:
    from app.canon.library_service import editable_reference, record_edit
    ref = editable_reference(db, place.story_id, "place", place.place_id)
    record_edit(db, ref, structure=changes)
    for field, value in changes.items():
        setattr(place, field, value)
    db.commit()
    db.refresh(place)
    return place
