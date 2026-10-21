from dataclasses import dataclass
from typing import Protocol


@dataclass
class AuthenticatedIdentity:
    user_id: str
    email: str
    name: str | None


class IdentityRejected(Exception):
    pass


class IdentityProviderUnavailable(Exception):
    pass


class IdentityProvider(Protocol):
    async def resolve_identity(
        self,
        session_token: str,
    ) -> AuthenticatedIdentity:
        ...