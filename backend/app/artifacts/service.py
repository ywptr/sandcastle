from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.artifacts.schemas import ArtifactRegistration, ArtifactRelationCreate, ReferenceBindingCreate
from app.db.models.artifact import Artifact
from app.db.models.artifact_relation import ArtifactRelation
from app.db.models.reference_binding import ReferenceBinding
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.stories.service import get_story
from app.stories.scene_service import get_scene
from app.world.service import get_character, get_place


class ArtifactConflict(ValueError):
    pass


def _require_story(db: Session, story_id: str, user_id: str) -> None:
    if get_story(db, story_id, user_id) is None:
        raise MediaDomainNotFound("Story not found")


def get_artifact(db: Session, artifact_id: str, user_id: str) -> Artifact:
    artifact = db.scalar(select(Artifact).where(Artifact.artifact_id == artifact_id, Artifact.user_id == user_id))
    if artifact is None:
        raise MediaDomainNotFound("Artifact not found")
    return artifact


def list_artifacts(db: Session, user_id: str, *, story_id: str | None = None, source: str | None = None) -> list[Artifact]:
    if story_id is not None:
        _require_story(db, story_id, user_id)
    query = select(Artifact).where(Artifact.user_id == user_id)
    if story_id is not None:
        # Provenance OR contextual use; no copying Artifact identity across Stories.
        used = select(ReferenceBinding.artifact_id).where(
            ReferenceBinding.story_id == story_id, ReferenceBinding.user_id == user_id,
        )
        query = query.where(or_(Artifact.story_id == story_id, Artifact.artifact_id.in_(used)))
    if source is not None:
        query = query.where(Artifact.source == source)
    return list(db.scalars(query.order_by(Artifact.created_at, Artifact.artifact_id)))


def register_artifact(db: Session, user_id: str, registration: ArtifactRegistration) -> Artifact:
    if registration.story_id is not None:
        _require_story(db, registration.story_id, user_id)
    if registration.scene_id is not None:
        if registration.story_id is None:
            raise InvalidMediaIntent("Scene scope requires a Story")
        if get_scene(db, registration.story_id, registration.scene_id) is None:
            raise MediaDomainNotFound("Scene not found in story")
    values = registration.model_dump(exclude={"metadata"})
    artifact = Artifact(user_id=user_id, metadata_json=registration.metadata, **values)
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def create_binding(db: Session, story_id: str, user_id: str, intent: ReferenceBindingCreate) -> ReferenceBinding:
    _require_story(db, story_id, user_id)
    artifact = get_artifact(db, intent.artifact_id, user_id)
    if artifact.media_type != "image":
        raise InvalidMediaIntent("Visual references require image artifacts")
    target_id = intent.target_id
    if intent.target_type == "story":
        target_id = target_id or story_id
        if target_id != story_id:
            raise MediaDomainNotFound("Story target not found")
    elif intent.target_type == "character":
        if not target_id or get_character(db, story_id, target_id) is None:
            raise MediaDomainNotFound("Character target not found in story")
    elif intent.target_type == "place":
        if not target_id or get_place(db, story_id, target_id) is None:
            raise MediaDomainNotFound("Place target not found in story")
    expected = {"character_identity": "character", "outfit": "character", "place": "place"}
    if intent.role in expected and intent.target_type != expected[intent.role]:
        raise InvalidMediaIntent("Reference role does not match target type")
    binding = ReferenceBinding(
        user_id=user_id, story_id=story_id, artifact_id=artifact.artifact_id,
        target_type=intent.target_type, target_id=target_id, role=intent.role,
        label=intent.label, metadata_json=intent.metadata,
    )
    db.add(binding)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ArtifactConflict("This reference binding already exists") from error
    db.refresh(binding)
    return binding


def list_bindings(db: Session, story_id: str, user_id: str) -> list[ReferenceBinding]:
    _require_story(db, story_id, user_id)
    return list(db.scalars(select(ReferenceBinding).where(
        ReferenceBinding.story_id == story_id, ReferenceBinding.user_id == user_id,
    ).order_by(ReferenceBinding.target_type, ReferenceBinding.target_id, ReferenceBinding.role, ReferenceBinding.reference_id)))


def delete_binding(db: Session, story_id: str, reference_id: str, user_id: str) -> None:
    _require_story(db, story_id, user_id)
    binding = db.scalar(select(ReferenceBinding).where(
        ReferenceBinding.story_id == story_id, ReferenceBinding.reference_id == reference_id,
        ReferenceBinding.user_id == user_id,
    ))
    if binding is None:
        raise MediaDomainNotFound("Reference binding not found")
    db.delete(binding)
    db.commit()


def create_relation(db: Session, child_id: str, user_id: str, intent: ArtifactRelationCreate) -> ArtifactRelation:
    get_artifact(db, child_id, user_id)
    get_artifact(db, intent.parent_artifact_id, user_id)
    if child_id == intent.parent_artifact_id:
        raise InvalidMediaIntent("An Artifact cannot be its own parent")
    # Serialize lineage changes for this owner on PostgreSQL using a stable owned row.
    db.execute(select(Artifact.artifact_id).where(Artifact.user_id == user_id)
               .order_by(Artifact.artifact_id).limit(1).with_for_update())
    existing = db.scalar(select(ArtifactRelation).where(
        ArtifactRelation.parent_artifact_id == intent.parent_artifact_id,
        ArtifactRelation.child_artifact_id == child_id,
        ArtifactRelation.relation_type == intent.relation_type,
    ))
    if existing is not None:
        return existing
    descendants = select(ArtifactRelation.child_artifact_id.label("artifact_id")).where(
        ArtifactRelation.parent_artifact_id == child_id, ArtifactRelation.user_id == user_id,
    ).cte("descendants", recursive=True)
    descendants = descendants.union(select(ArtifactRelation.child_artifact_id).join(
        descendants, ArtifactRelation.parent_artifact_id == descendants.c.artifact_id,
    ).where(ArtifactRelation.user_id == user_id))
    if db.scalar(select(descendants.c.artifact_id).where(descendants.c.artifact_id == intent.parent_artifact_id).limit(1)):
        raise InvalidMediaIntent("Artifact relation would create a cycle")
    relation = ArtifactRelation(user_id=user_id, parent_artifact_id=intent.parent_artifact_id,
                                child_artifact_id=child_id, relation_type=intent.relation_type)
    db.add(relation)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ArtifactConflict("Artifact relation already exists") from error
    db.refresh(relation)
    return relation


def list_relations(db: Session, artifact_id: str, user_id: str) -> list[ArtifactRelation]:
    get_artifact(db, artifact_id, user_id)
    return list(db.scalars(select(ArtifactRelation).where(
        ArtifactRelation.user_id == user_id,
        or_(ArtifactRelation.parent_artifact_id == artifact_id, ArtifactRelation.child_artifact_id == artifact_id),
    ).order_by(ArtifactRelation.created_at, ArtifactRelation.relation_id)))
