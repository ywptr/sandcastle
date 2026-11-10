from datetime import datetime
from uuid import uuid4
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now


class ApprovedMediaAdaptation(Base):
    """Append-only approved plan/manifest snapshots. No draft or media-byte storage."""
    __tablename__ = "approved_media_adaptations"
    __table_args__ = (
        UniqueConstraint("scene_id", "target_format", "revision", name="uq_adaptation_scene_revision"),
        UniqueConstraint("user_id", "plan_id", "snapshot_digest", name="uq_adaptation_approval"),
        CheckConstraint("target_format IN ('webtoon','short_drama','story_reel')", name="ck_adaptation_format"),
        CheckConstraint("revision >= 1", name="ck_adaptation_revision"),
    )
    adaptation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.scene_id"), index=True)
    target_format: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer)
    plan_id: Mapped[str] = mapped_column(String(36))
    source_digest: Mapped[str] = mapped_column(String(64))
    context_digest: Mapped[str] = mapped_column(String(64))
    snapshot_digest: Mapped[str] = mapped_column(String(64))
    plan_json: Mapped[dict] = mapped_column(JSON)
    manifest_json: Mapped[dict] = mapped_column(JSON)
    compiler_version: Mapped[str] = mapped_column(String(40))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
