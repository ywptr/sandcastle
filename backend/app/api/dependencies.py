from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.auth.config import load_auth_config
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import SESSION_COOKIE, AuthSessionManager


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
