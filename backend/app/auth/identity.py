from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedIdentity:
    user_id: str
    email: str
    name: str | None