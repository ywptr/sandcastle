"""Account-owned BYOK settings. Scope columns reserve an explicit M11 extension."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.types import utc_now


class LLMProviderConfig(Base):
    __tablename__ = "llm_provider_configs"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "provider", name="uq_llm_provider_scope"),
        CheckConstraint("scope_type = 'user'", name="ck_llm_provider_scope"),
        CheckConstraint("provider IN ('openai','anthropic','google')", name="ck_llm_provider_id"),
    )
    provider_config_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scope_type: Mapped[str] = mapped_column(String(20), default="user")
    scope_id: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(30))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LLMRoleBinding(Base):
    __tablename__ = "llm_role_bindings"
    __table_args__ = (
        CheckConstraint("scope_type = 'user'", name="ck_llm_role_scope"),
        CheckConstraint("role IN ('creative_writer','story_importer','narrative_media_translator')", name="ck_llm_role_id"),
        CheckConstraint("provider IN ('openai','anthropic','google')", name="ck_llm_role_provider"),
    )
    scope_type: Mapped[str] = mapped_column(String(20), primary_key=True, default="user")
    scope_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    role: Mapped[str] = mapped_column(String(40), primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
