from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class Artifact(Base):
    """Metadata pointing to external media; never image bytes or a local filename."""
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("execution_id", "external_reference", name="uq_artifact_execution_reference"),
    )

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.scene_id"), index=True)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("media_executions.execution_id"), index=True)
    media_type: Mapped[str] = mapped_column(String(30), default="image")
    source: Mapped[str] = mapped_column(String(30), default="generated")
    external_reference: Mapped[str] = mapped_column(String(255))
    external_artifact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retrieval_reference: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
