from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class Scene(Base):
    __tablename__ = "scenes"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "sequence_number",
            name="uq_scene_story_sequence",
        ),
    )

    scene_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    story_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stories.story_id"),
        index=True,
    )

    source_action_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("story_actions.action_id"),
        nullable=True,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )