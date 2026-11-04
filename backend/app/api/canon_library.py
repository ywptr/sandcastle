from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.canon import library_service as service
from app.canon.library_schemas import LibraryCreate, Promotion, VersionCreate, Attach, Fork, Move, LibraryResponse, VersionResponse, StoryReferenceResponse
from app.db.models import CanonObject, CanonObjectVersion

router = APIRouter(tags=["canon-library"])

@router.get("/canon/library", response_model=list[LibraryResponse])
def list_library(db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return list(db.scalars(select(CanonObject).where(CanonObject.user_id == identity.user_id).order_by(CanonObject.created_at, CanonObject.canon_object_id)))

@router.post("/canon/library", status_code=201, response_model=LibraryResponse)
def create_library(request: LibraryCreate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.create_object(db, identity.user_id, request.object_type, request.data)

@router.get("/canon/library/{object_id}", response_model=LibraryResponse)
def read_library(object_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.get_object(db, object_id, identity.user_id)

@router.get("/canon/library/{object_id}/versions", response_model=list[VersionResponse])
def list_versions(object_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    service.get_object(db, object_id, identity.user_id)
    return list(db.scalars(select(CanonObjectVersion).where(CanonObjectVersion.canon_object_id == object_id).order_by(CanonObjectVersion.version_number)))

@router.post("/canon/library/{object_id}/versions", status_code=201, response_model=VersionResponse)
def new_version(object_id: str, request: VersionCreate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.shared_version(db, object_id, identity.user_id, request.parent_version_id, request.data)

@router.post("/stories/{story_id}/canon/library/promote", response_model=StoryReferenceResponse)
def promote(story_id: str, request: Promotion, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.promote(db, story_id, identity.user_id, request.target_type, request.target_id)

@router.get("/stories/{story_id}/canon/references", response_model=list[StoryReferenceResponse])
def list_references(story_id: str, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    service.story(db, story_id, identity.user_id)
    return service.references(db, story_id)

@router.post("/stories/{story_id}/canon/references", status_code=201, response_model=StoryReferenceResponse)
def attach(story_id: str, request: Attach, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.attach(db, story_id, identity.user_id, request.canon_object_id, request.canon_version_id)

@router.post("/stories/{story_id}/canon/references/{reference_id}/fork", response_model=StoryReferenceResponse)
def fork(story_id: str, reference_id: str, request: Fork, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.fork(db, story_id, identity.user_id, reference_id, request.reason)

@router.patch("/stories/{story_id}/canon/references/{reference_id}", response_model=StoryReferenceResponse)
def move(story_id: str, reference_id: str, request: Move, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.move(db, story_id, identity.user_id, reference_id, request.canon_version_id)
