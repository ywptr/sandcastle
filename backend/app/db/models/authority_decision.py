from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class AuthorityDecision(Base):
    __tablename__ = "authority_decisions"

    decision_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    action_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("story_actions.action_id"),
        index=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(30),
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    evaluator: Mapped[str] = mapped_column(
        String(100),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )