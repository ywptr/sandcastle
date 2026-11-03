from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class ReferenceBinding(Base):
    """Story-scoped use of reusable media identity, not a Canon assertion."""
    __tablename__ = "reference_bindings"
    __table_args__ = (
        UniqueConstraint("story_id", "artifact_id", "target_type", "target_id", "role", name="uq_reference_binding_target"),
        CheckConstraint("target_type IN ('story','character','place')", name="ck_reference_binding_target"),
        CheckConstraint("role IN ('character_identity','outfit','place','visual_style','general')", name="ck_reference_binding_role"),
    )

    reference_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), ForeignKey("artifacts.artifact_id"), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(30))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
