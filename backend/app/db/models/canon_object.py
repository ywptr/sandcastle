from datetime import datetime
from uuid import uuid4
from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
from app.db.types import utc_now

class CanonObject(Base):
    __tablename__ = "canon_objects"
    __table_args__ = (CheckConstraint("object_type IN ('character','place')", name="ck_canon_object_type"),)
    canon_object_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    object_type: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
