from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class MediaExecution(Base):
    __tablename__ = "media_executions"
    __table_args__ = (
        UniqueConstraint("user_id", "storyboard_plan_id", "panel_number", name="uq_media_execution_plan_panel"),
        CheckConstraint("panel_number BETWEEN 1 AND 4", name="ck_media_execution_panel"),
        CheckConstraint("status IN ('pending','submitted','running','completed','failed')", name="ck_media_execution_status"),
    )

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.scene_id"), index=True)
    storyboard_plan_id: Mapped[str] = mapped_column(String(255))
    media_request_id: Mapped[str] = mapped_column(String(255))
    panel_number: Mapped[int]
    backend_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    external_execution_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Historical approval data: never reconstructed from mutable authoring objects.
    plan_digest: Mapped[str] = mapped_column(String(64))
    request_snapshot: Mapped[dict] = mapped_column(JSON)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
