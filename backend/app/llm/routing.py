"""Scope-source boundary. Only the authenticated user's personal source is enabled.

A future source must receive trusted Nexus-derived context after M11; request JSON
must never create tenant authority. No tenant/platform source is installed today.
"""
from dataclasses import dataclass, field
from typing import Literal, Protocol
from sqlalchemy.orm import Session
from app.auth.identity import AuthenticatedIdentity
from app.db.models.llm import LLMProviderConfig
from app.llm.errors import SettingsInvalid
from app.llm.schemas import Provider, validate_scope
from app.llm.service import select_provider


@dataclass(frozen=True)
class LLMActorContext:
    user_id: str

    def __post_init__(self):
        validate_scope(self.user_id)

    @classmethod
    def from_identity(cls, identity: AuthenticatedIdentity):
        return cls(identity.user_id)


@dataclass(frozen=True)
class ProviderSelection:
    scope_type: Literal["user"]
    scope_id: str
    provider: Provider
    model: str
    configuration: LLMProviderConfig = field(repr=False, compare=False)


class ProviderSource(Protocol):
    def resolve(self, db: Session, actor: LLMActorContext, role: str) -> ProviderSelection | None: ...


class UserProviderSource:
    def resolve(self, db, actor, role):
        selected = select_provider(db, actor.user_id, role)
        if selected is None:
            return None
        config, model = selected
        return ProviderSelection("user", actor.user_id, config.provider, model, config)


def resolve_provider_for_role(db: Session, actor_context: LLMActorContext, role: str) -> ProviderSelection | None:
    if not isinstance(actor_context, LLMActorContext):
        raise SettingsInvalid("Trusted authenticated user context is required")
    # Keep an explicit single source until M11 supplies trusted tenant identity and
    # a reviewed policy for unavailable explicit user bindings. No fake fallback.
    return UserProviderSource().resolve(db, actor_context, role)
