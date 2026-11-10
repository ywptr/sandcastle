from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now


class CreativeDirectionSnapshot(Base):
    __tablename__ = "creative_direction_snapshots"
    __table_args__ = (UniqueConstraint("story_id", "revision", name="uq_direction_story_revision"),)
    direction_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    direction_json: Mapped[dict] = mapped_column(JSON)
    style_snapshot: Mapped[dict] = mapped_column(JSON)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
