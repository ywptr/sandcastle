from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class UniverseStoryMembership(Base):
    __tablename__ = "universe_story_memberships"
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True)
    universe_id: Mapped[str] = mapped_column(String(36), ForeignKey("universes.universe_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
