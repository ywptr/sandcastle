from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class UniverseCanonReference(Base):
    __tablename__ = "universe_canon_references"
    __table_args__ = (UniqueConstraint("universe_id", "canon_object_id", name="uq_universe_canon_object"),)
    reference_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    universe_id: Mapped[str] = mapped_column(String(36), ForeignKey("universes.universe_id"), index=True)
    canon_object_id: Mapped[str] = mapped_column(String(36), ForeignKey("canon_objects.canon_object_id"))
    canon_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("canon_object_versions.canon_version_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
