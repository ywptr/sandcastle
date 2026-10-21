from dataclasses import asdict

from itsdangerous import (
    BadSignature,
    SignatureExpired,
    URLSafeTimedSerializer,
)

from app.auth.identity import (
    AuthenticatedIdentity,
)


AUTH_FLOW_COOKIE = "sandcastle_auth_flow"
SESSION_COOKIE = "sandcastle_session"

AUTH_FLOW_MAX_AGE = 600
SESSION_MAX_AGE = 60 * 60 * 12


class AuthSessionManager:
    def __init__(
        self,
        secret: str,
    ) -> None:
        self.flow_serializer = (
            URLSafeTimedSerializer(
                secret,
                salt="sandcastle-auth-flow",
            )
        )

        self.session_serializer = (
            URLSafeTimedSerializer(
                secret,
                salt="sandcastle-session",
            )
        )


    def create_flow_token(
        self,
        *,
        state: str,
        code_verifier: str,
    ) -> str:
        return self.flow_serializer.dumps({
            "state": state,
            "code_verifier": code_verifier,
        })


    def read_flow_token(
        self,
        token: str,
    ) -> dict:
        return self.flow_serializer.loads(
            token,
            max_age=AUTH_FLOW_MAX_AGE,
        )


    def create_session_token(
        self,
        identity: AuthenticatedIdentity,
    ) -> str:
        return self.session_serializer.dumps(
            asdict(identity)
        )


    def read_session_token(
        self,
        token: str,
    ) -> AuthenticatedIdentity:
        payload = self.session_serializer.loads(
            token,
            max_age=SESSION_MAX_AGE,
        )

        return AuthenticatedIdentity(
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload.get("name"),
        )


def is_invalid_token(
    error: Exception,
) -> bool:
    return isinstance(
        error,
        (
            BadSignature,
            SignatureExpired,
        ),
    )