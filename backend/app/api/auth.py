from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse

from app.auth.config import load_auth_config
from app.auth.is_oidc import (
    ISAuthenticationError,
    ISOIDCClient,
)
from app.auth.pkce import (
    create_code_challenge,
    create_code_verifier,
    create_state,
)
from app.auth.session import (
    AUTH_FLOW_COOKIE,
    AUTH_FLOW_MAX_AGE,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    AuthSessionManager,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


def build_auth_services():
    config = load_auth_config()

    return (
        config,
        ISOIDCClient(config),
        AuthSessionManager(
            config.auth_secret
        ),
    )


@router.get("/login")
async def login():
    config, oidc, sessions = (
        build_auth_services()
    )

    state = create_state()
    verifier = create_code_verifier()

    challenge = create_code_challenge(
        verifier
    )

    flow_token = sessions.create_flow_token(
        state=state,
        code_verifier=verifier,
    )

    response = RedirectResponse(
        oidc.build_authorization_url(
            state=state,
            code_challenge=challenge,
        )
    )

    response.set_cookie(
        AUTH_FLOW_COOKIE,
        flow_token,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        max_age=AUTH_FLOW_MAX_AGE,
        path="/api/auth",
    )

    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
):
    config, oidc, sessions = (
        build_auth_services()
    )

    flow_token = request.cookies.get(
        AUTH_FLOW_COOKIE
    )

    if not flow_token:
        raise HTTPException(
            status_code=400,
            detail="Missing authentication flow",
        )

    try:
        flow = sessions.read_flow_token(
            flow_token
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Authentication flow expired",
        )

    if flow["state"] != state:
        raise HTTPException(
            status_code=400,
            detail="Invalid authentication state",
        )

    try:
        access_token = (
            await oidc.exchange_code(
                code=code,
                code_verifier=(
                    flow["code_verifier"]
                ),
            )
        )

        identity = await oidc.get_identity(
            access_token
        )

    except ISAuthenticationError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    session_token = (
        sessions.create_session_token(
            identity
        )
    )

    response = RedirectResponse(
        config.web_url
    )

    response.delete_cookie(
        AUTH_FLOW_COOKIE,
        path="/api/auth",
    )

    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )

    return response


@router.get("/me")
async def me(
    request: Request,
):
    config, _, sessions = (
        build_auth_services()
    )

    token = request.cookies.get(
        SESSION_COOKIE
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    try:
        identity = (
            sessions.read_session_token(
                token
            )
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    return {
        "user_id": identity.user_id,
        "email": identity.email,
        "name": identity.name,
    }


@router.post("/logout")
async def logout():
    config = load_auth_config()

    response = RedirectResponse(
        config.web_url,
        status_code=303,
    )

    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
    )

    return response