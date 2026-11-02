from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class CanonCandidate(Base):
    __tablename__ = "canon_candidates"

    canon_candidate_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    story_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stories.story_id"),
        index=True,
    )

    scene_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scenes.scene_id"),
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(255),
    )

    value: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="proposed",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )