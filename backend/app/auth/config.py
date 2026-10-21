import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    issuer: str
    client_id: str
    client_secret: str
    auth_secret: str
    callback_url: str
    web_url: str
    cookie_secure: bool


def load_auth_config() -> AuthConfig:
    _validate_required_environment()
    return AuthConfig(
        issuer=os.environ["IS_ISSUER"].rstrip("/"),
        client_id=os.environ["IS_CLIENT_ID"],
        client_secret=os.environ["IS_CLIENT_SECRET"],
        auth_secret=os.environ[
            "SANDCASTLE_AUTH_SECRET"
        ],
        callback_url=os.environ[
            "SANDCASTLE_AUTH_CALLBACK_URL"
        ],
        web_url=os.environ[
            "SANDCASTLE_WEB_URL"
        ].rstrip("/"),
        cookie_secure=_read_bool(
            "SANDCASTLE_COOKIE_SECURE"
        ),
    )


def _read_bool(name: str) -> bool:
    return os.environ.get(
        name,
        "false",
    ).lower() in {
        "1",
        "true",
        "yes",
    }

def _validate_required_environment() -> None:
    required = (
        "IS_ISSUER",
        "IS_CLIENT_ID",
        "IS_CLIENT_SECRET",
        "SANDCASTLE_AUTH_SECRET",
        "SANDCASTLE_AUTH_CALLBACK_URL",
        "SANDCASTLE_WEB_URL",
    )

    missing = [
        name
        for name in required
        if not os.environ.get(name)
    ]

    if missing:
        raise RuntimeError(
            "Missing authentication configuration: "
            + ", ".join(missing)
        )