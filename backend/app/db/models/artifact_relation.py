from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class ArtifactRelation(Base):
    __tablename__ = "artifact_relations"
    __table_args__ = (
        UniqueConstraint("parent_artifact_id", "child_artifact_id", "relation_type", name="uq_artifact_relation_edge"),
        CheckConstraint("parent_artifact_id <> child_artifact_id", name="ck_artifact_relation_not_self"),
        CheckConstraint("relation_type IN ('derived_from','reference_input')", name="ck_artifact_relation_type"),
    )

    relation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    parent_artifact_id: Mapped[str] = mapped_column(String(36), ForeignKey("artifacts.artifact_id"), index=True)
    child_artifact_id: Mapped[str] = mapped_column(String(36), ForeignKey("artifacts.artifact_id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
