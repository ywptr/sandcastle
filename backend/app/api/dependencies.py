import os

from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import SessionLocal

from app.auth.adapters.ig import IGIdentityProvider
from app.auth.port import (
    AuthenticatedIdentity,
    IdentityProviderUnavailable,
    IdentityRejected,
)
from app.auth.config import load_auth_config
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import (
    SESSION_COOKIE,
    AuthSessionManager,
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def get_identity_provider() -> IGIdentityProvider:
    return IGIdentityProvider(
        base_url=os.environ[
            "IG_AUTH_BASE_URL"
        ]
    )


async def get_current_identity(
    request: Request,
) -> AuthenticatedIdentity:
    session_token = request.cookies.get(
        "ig_session"
    )

    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    provider = get_identity_provider()

    try:
        return await provider.resolve_identity(
            session_token
        )

    except IdentityRejected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    except IdentityProviderUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )

def get_current_identity(
    request: Request,
) -> AuthenticatedIdentity:
    token = request.cookies.get(
        SESSION_COOKIE
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    config = load_auth_config()

    sessions = AuthSessionManager(
        config.auth_secret
    )

    try:
        return sessions.read_session_token(
            token
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )
