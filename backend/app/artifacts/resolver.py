"""Select contextual uses of media identity, never resolve storage or inspect pixels."""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.artifacts.service import get_artifact
from app.media.errors import InvalidMediaIntent
from app.db.models.artifact import Artifact
from app.db.models.reference_binding import ReferenceBinding
from app.media.schemas import Reference


def explicit_artifact_references(db: Session, user_id: str, artifact_ids: list[str]) -> list[Reference]:
    references = []
    for artifact_id in sorted(set(artifact_ids)):
        artifact = get_artifact(db, artifact_id, user_id)
        if artifact.media_type != "image":
            raise InvalidMediaIntent("Visual references require image artifacts")
        references.append(Reference(kind="artifact", reference_id=artifact.artifact_id, role="general"))
    return references


def resolve_applicable_references(
    db: Session, *, story_id: str, user_id: str, character_ids: list[str], place_ids: list[str],
) -> list[Reference]:
    applicable = or_(
        (ReferenceBinding.target_type == "story") & (ReferenceBinding.target_id == story_id)
        & ReferenceBinding.role.in_(["visual_style", "general"]),
        (ReferenceBinding.target_type == "character") & ReferenceBinding.target_id.in_(character_ids),
        (ReferenceBinding.target_type == "place") & ReferenceBinding.target_id.in_(place_ids),
    )
    bindings = db.scalars(select(ReferenceBinding).join(Artifact).where(
        ReferenceBinding.story_id == story_id, ReferenceBinding.user_id == user_id,
        Artifact.user_id == user_id, Artifact.media_type == "image", applicable,
    ).order_by(ReferenceBinding.target_type, ReferenceBinding.target_id, ReferenceBinding.role,
               ReferenceBinding.reference_id))
    return [Reference(kind="artifact", reference_id=binding.artifact_id,
                      binding_id=binding.reference_id, role=binding.role) for binding in bindings]
