"""Fernet envelopes are authenticated and bound to scope/provider identity."""
import json
import os
from cryptography.fernet import Fernet


class SecretUnavailable(Exception):
    pass


KEY_ENV = "SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY"


def encryption_key_status() -> str:
    """Validate configuration without exposing key material or accessing storage."""
    value = os.environ.get(KEY_ENV)
    if not value:
        return "missing"
    try:
        Fernet(value.encode("ascii"))
    except (ValueError, UnicodeError):
        return "malformed"
    return "valid"


def main() -> int:
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    status = encryption_key_status()
    print(f"{KEY_ENV}: {status}")
    return 0 if status == "valid" else 1


def cipher():
    try:
        return Fernet(os.environ["SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY"].encode("ascii"))
    except Exception:
        raise SecretUnavailable("Provider encryption is unavailable. Contact the application operator.") from None


def encrypt_credentials(scope_id: str, provider: str, api_key: str) -> str:
    return cipher().encrypt(json.dumps({"version": 1, "scope_type": "user", "scope_id": scope_id,
        "provider": provider, "api_key": api_key}, separators=(",", ":")).encode()).decode("ascii")


def decrypt_credentials(scope_id: str, provider: str, token: str) -> str:
    try:
        data = json.loads(cipher().decrypt(token.encode("ascii")))
        if (data["version"], data["scope_type"], data["scope_id"], data["provider"]) != (1, "user", scope_id, provider):
            raise ValueError()
        key = data["api_key"]
        if not isinstance(key, str) or not key:
            raise ValueError()
        return key
    except Exception:
        raise SecretUnavailable("Provider credentials cannot be opened. Reconfigure credentials or contact the operator.") from None


if __name__ == "__main__":
    raise SystemExit(main())
