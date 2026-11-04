from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now

class CanonObjectVersion(Base):
    __tablename__ = "canon_object_versions"
    __table_args__ = (UniqueConstraint("canon_object_id", "version_number", name="uq_canon_object_version"),)
    canon_version_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    canon_object_id: Mapped[str] = mapped_column(String(36), ForeignKey("canon_objects.canon_object_id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    parent_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("canon_object_versions.canon_version_id"))
    data: Mapped[dict] = mapped_column(JSON)
    created_by_story_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stories.story_id"))
    fork_reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
