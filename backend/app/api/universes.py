from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.canon.library_schemas import Move
from app.universes import service
from app.universes.schemas import (
    UniverseCreate, UniverseUpdate, UniverseResponse, MembershipResponse,
    UniverseReferenceCreate, UniverseReferenceResponse,
)

router = APIRouter(prefix="/universes", tags=["universes"])


@router.get("", response_model=list[UniverseResponse])
def list_universes(db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.list_universes(db, identity.user_id)


@router.post("", response_model=UniverseResponse, status_code=201)
def create_universe(request: UniverseCreate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.create_universe(db, identity.user_id, **request.model_dump())


@router.get("/{universe_id}", response_model=UniverseResponse)
def read_universe(universe_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.get_universe(db, universe_id, identity.user_id)


@router.patch("/{universe_id}", response_model=UniverseResponse)
def update_universe(universe_id: str, request: UniverseUpdate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.update_universe(db, universe_id, identity.user_id, **request.model_dump(exclude_unset=True))


@router.get("/{universe_id}/stories", response_model=list[MembershipResponse])
def list_members(universe_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.list_members(db, universe_id, identity.user_id)


@router.post("/{universe_id}/stories/{story_id}", response_model=MembershipResponse)
def attach_story(universe_id: str, story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.attach_story(db, universe_id, story_id, identity.user_id)


@router.delete("/{universe_id}/stories/{story_id}", status_code=204)
def remove_story(universe_id: str, story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    service.remove_story(db, universe_id, story_id, identity.user_id)
    return Response(status_code=204)


@router.get("/{universe_id}/canon/references", response_model=list[UniverseReferenceResponse])
def list_references(universe_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.list_references(db, universe_id, identity.user_id)


@router.post("/{universe_id}/canon/references", response_model=UniverseReferenceResponse, status_code=201)
def pin(universe_id: str, request: UniverseReferenceCreate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.pin(db, universe_id, identity.user_id, request.canon_object_id, request.canon_version_id)


@router.post("/{universe_id}/canon/references/promote", response_model=UniverseReferenceResponse, status_code=201)
def promote(universe_id: str, request: UniverseReferenceCreate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.pin(db, universe_id, identity.user_id, request.canon_object_id, request.canon_version_id, promote=True)


@router.patch("/{universe_id}/canon/references/{reference_id}", response_model=UniverseReferenceResponse)
def move_pin(universe_id: str, reference_id: str, request: Move, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.move_pin(db, universe_id, identity.user_id, reference_id, request.canon_version_id)
