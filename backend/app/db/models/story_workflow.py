from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now


class StoryWorkflow(Base):
    __tablename__ = "story_workflows"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy','normal','difficult','impossible')", name="ck_workflow_difficulty"),
        CheckConstraint("template_version >= 1", name="ck_workflow_template_version"),
    )
    story_id: Mapped[str] = mapped_column(String(36), ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True)
    workflow_template_id: Mapped[str] = mapped_column(String(100))
    template_version: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(20))
    configuration: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
