from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now


class NarrativeGuidanceProfile(Base):
    __tablename__ = "narrative_guidance_profiles"
    __table_args__ = (
        CheckConstraint("audience IN ('child','teen','adult')", name="ck_guidance_audience"),
        CheckConstraint("maturity_rating IN ('general','mild','moderate','mature')", name="ck_guidance_maturity"),
        CheckConstraint("(audience != 'child' OR maturity_rating IN ('general','mild')) AND (audience != 'teen' OR maturity_rating != 'mature')", name="ck_guidance_compatibility"),
        CheckConstraint("rating_count >= 0 AND (average_rating IS NULL OR (average_rating >= 1 AND average_rating <= 5))", name="ck_guidance_feedback_range"),
        CheckConstraint("(rating_count = 0 AND average_rating IS NULL) OR (rating_count > 0 AND average_rating IS NOT NULL)", name="ck_guidance_feedback_summary"),
    )
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True)
    audience: Mapped[str] = mapped_column(String(20), default="adult")
    maturity_rating: Mapped[str] = mapped_column(String(20), default="general")
    tone: Mapped[str | None] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(255))
    guidance_notes: Mapped[str | None] = mapped_column(Text)
    average_rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback_tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
