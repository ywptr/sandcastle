from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class Story(Base):
    __tablename__ = "stories"

    story_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
    )

    premise: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    objective: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    primary_genre: Mapped[str | None] = mapped_column(String(30), nullable=True)
    secondary_genres: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
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