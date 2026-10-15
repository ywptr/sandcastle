from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class StoryAction(Base):
    __tablename__ = "story_actions"

    action_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    story_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stories.story_id"),
        index=True,
    )

    action_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    request: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )