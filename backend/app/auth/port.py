from typing import Protocol

from app.auth.identity import AuthenticatedIdentity

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