from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now

class StoryCanonReference(Base):
    __tablename__ = "story_canon_references"
    __table_args__ = (UniqueConstraint("story_id", "target_type", "target_id", name="uq_story_canon_target"),)
    reference_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    canon_object_id: Mapped[str] = mapped_column(String(36), ForeignKey("canon_objects.canon_object_id"))
    canon_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("canon_object_versions.canon_version_id"))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
