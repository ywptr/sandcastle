from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class CanonCandidate(Base):
    __tablename__ = "canon_candidates"
    __table_args__ = (
        UniqueConstraint("user_id", "story_id", "dedup_key", name="uq_canon_candidate_source_fact"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_canon_candidate_status"),
        CheckConstraint("classification IN ('new','consistent','conflict','uncertain')", name="ck_canon_candidate_classification"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_canon_candidate_confidence"),
    )

    canon_candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id"), index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenes.scene_id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    subject_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(50))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(30))
    source_snapshot: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    dedup_key: Mapped[str] = mapped_column(String(64))
    extraction_data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    classification: Mapped[str] = mapped_column(String(30), default="uncertain", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text)
    comparison_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    superseded_entry_ids: Mapped[list] = mapped_column(JSON, default=list)
    approved_canon_entry_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("canon_entries.canon_entry_id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
