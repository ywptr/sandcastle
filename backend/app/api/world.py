from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.api.stories import require_story
from app.auth.identity import AuthenticatedIdentity
from app.world.schemas import (
    CharacterCreate, CharacterResponse, CharacterUpdate,
    PlaceCreate, PlaceResponse, PlaceUpdate,
)
from app.world import service

router = APIRouter(prefix="/stories/{story_id}", tags=["world"])


@router.get("/characters", response_model=list[CharacterResponse])
def list_characters_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    return service.list_characters(db, story_id)


@router.post("/characters", response_model=CharacterResponse, status_code=201)
def create_character_endpoint(
    story_id: str,
    request: CharacterCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    return service.create_character(db, story_id, **request.model_dump())


@router.patch("/characters/{character_id}", response_model=CharacterResponse)
def update_character_endpoint(
    story_id: str,
    character_id: str,
    request: CharacterUpdate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    character = service.get_character(db, story_id, character_id)
    if character is None:
        raise HTTPException(404, "Character not found")
    return service.update_character(db, character, **request.model_dump(exclude_unset=True))


@router.get("/places", response_model=list[PlaceResponse])
def list_places_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    return service.list_places(db, story_id)


@router.post("/places", response_model=PlaceResponse, status_code=201)
def create_place_endpoint(
    story_id: str,
    request: PlaceCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    return service.create_place(db, story_id, **request.model_dump())


@router.patch("/places/{place_id}", response_model=PlaceResponse)
def update_place_endpoint(
    story_id: str,
    place_id: str,
    request: PlaceUpdate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    require_story(db, story_id, identity)
    place = service.get_place(db, story_id, place_id)
    if place is None:
        raise HTTPException(404, "Place not found")
    return service.update_place(db, place, **request.model_dump(exclude_unset=True))
