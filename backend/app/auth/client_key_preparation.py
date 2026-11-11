"""Offline Development key preparation. Deliberately disconnected from login and HTTP."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

BACKEND = Path(__file__).resolve().parents[2]
KEY_DIRECTORY = BACKEND / ".secrets" / "oauth-client-development"
KEY_FILE = KEY_DIRECTORY / "private-key.pem"
PUBLIC_FILE = BACKEND / "docs" / "m11-development-client-public.jwks.json"
DEVELOPMENT_TOKEN_ENDPOINT = "https://5480-deb13.lan.com:5180/api/auth/oauth2/token"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
PUBLIC_FIELDS = frozenset({"kty", "crv", "x", "y", "kid", "alg", "use"})


class KeyPreparationError(ValueError):
    """Only fixed, nonsecret diagnostic messages are emitted by this utility."""


def _secure_directory(path):
    # Reject symlinks in the entire path, including ancestors of the private directory.
    if any(parent.is_symlink() for parent in [path, *path.parents]):
        raise KeyPreparationError("Private storage must not contain symlinks.")
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise KeyPreparationError("Private storage requires current-user ownership and mode 0700.")


def _check_file(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
        raise KeyPreparationError("Private key requires a single regular owner-only file with mode 0600.")


def load_private_key(path):
    path = Path(path)
    try:
        _secure_directory(path.parent.parent)
        _secure_directory(path.parent)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            _check_file(os.fstat(source.fileno()))
            key = serialization.load_pem_private_key(source.read(8192), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
            raise KeyPreparationError("Development client key must use P-256.")
        return key
    except (OSError, ValueError, TypeError):
        raise KeyPreparationError("Development client key is unavailable or storage is unsafe.") from None


def public_jwks(key):
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise KeyPreparationError("Development client key must use P-256.")
    public = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    public = {name: public[name] for name in ("crv", "kty", "x", "y")}
    # Stable RFC 7638 SHA-256 public JWK thumbprint, with a Development-specific prefix.
    import base64
    thumbprint = base64.urlsafe_b64encode(hashlib.sha256(
        json.dumps(public, sort_keys=True, separators=(",", ":")).encode()).digest()).rstrip(b"=").decode()
    public.update(kid="sandcastle-dev-" + thumbprint, alg="ES256", use="sig")
    return {"keys": [public]}


def prepare_key(private_path=KEY_FILE, public_path=PUBLIC_FILE):
    """Create once, or verify/reuse. Never rotate or overwrite an existing private key."""
    private_path, public_path = Path(private_path), Path(public_path)
    try:
        _secure_directory(private_path.parent.parent)
        _secure_directory(private_path.parent)
        if not private_path.exists() and not private_path.is_symlink():
            if public_path.exists():
                raise KeyPreparationError("Public handoff exists without its private key; operator review is required.")
            key = ec.generate_private_key(ec.SECP256R1())
            descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "wb") as destination:
                _check_file(os.fstat(destination.fileno()))
                destination.write(key.private_bytes(serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
                destination.flush()
                os.fsync(destination.fileno())
        key = load_private_key(private_path)
        jwks = public_jwks(key)
        # Verify the exported public point using the JWT library's JWK parser.
        exported = jwt.PyJWK.from_dict(jwks["keys"][0], algorithm="ES256")
        if exported.key.public_numbers() != key.public_key().public_numbers():
            raise KeyPreparationError("Public/private key matching failed.")
        if public_path.exists():
            if json.loads(public_path.read_text()) != jwks:
                raise KeyPreparationError("Existing public handoff does not match; operator review is required.")
        else:
            public_path.parent.mkdir(parents=True, exist_ok=True)
            with public_path.open("x") as destination:
                destination.write(json.dumps(jwks, indent=2) + "\n")
        return jwks
    except (OSError, ValueError, TypeError):
        raise KeyPreparationError("Key preparation failed. Check custody, permissions, and public handoff consistency.") from None


def sign_assertion(key, *, client_id, token_endpoint, lifetime=60):
    """Offline capability only; caller must supply the IS-provisioned client ID later."""
    if not isinstance(client_id, str) or not client_id.strip():
        raise KeyPreparationError("An explicitly provisioned OAuth client ID is required.")
    if token_endpoint != DEVELOPMENT_TOKEN_ENDPOINT:
        raise KeyPreparationError("Assertion audience must be the exact approved Development token endpoint.")
    if type(lifetime) is not int or not 1 <= lifetime <= 60:
        raise KeyPreparationError("Assertion lifetime must be an integer from 1 to 60 seconds.")
    kid = public_jwks(key)["keys"][0]["kid"]
    issued = int(time.time())
    return jwt.encode({"iss": client_id, "sub": client_id, "aud": token_endpoint,
        "iat": issued, "exp": issued + lifetime, "jti": str(uuid4())}, key,
        algorithm="ES256", headers={"kid": kid, "typ": "JWT"})


def verify_assertion(token, jwks, *, client_id, token_endpoint):
    """Isolated profile check, not an IS verifier or replay store. Never sends a token."""
    try:
        if token_endpoint != DEVELOPMENT_TOKEN_ENDPOINT or set(jwks) != {"keys"} or len(jwks["keys"]) != 1:
            raise ValueError()
        public = jwks["keys"][0]
        if set(public) != PUBLIC_FIELDS or (public["kty"], public["crv"], public["alg"], public["use"]) != ("EC", "P-256", "ES256", "sig"):
            raise ValueError()
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "ES256" or header.get("kid") != public["kid"]:
            raise ValueError()
        payload = jwt.decode(token, jwt.PyJWK.from_dict(public, algorithm="ES256").key,
            algorithms=["ES256"], audience=token_endpoint, issuer=client_id, subject=client_id,
            options={"require": ["iss", "sub", "aud", "iat", "exp", "jti"], "strict_aud": True})
        if (type(payload["iat"]) is not int or type(payload["exp"]) is not int
                or not 1 <= payload["exp"] - payload["iat"] <= 60
                or not isinstance(payload["jti"], str) or not payload["jti"]):
            raise ValueError()
        return payload
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise KeyPreparationError("Client assertion failed isolated profile validation.") from None


def main():
    try:
        jwks = prepare_key()
    except KeyPreparationError:
        print("Development OAuth key preparation failed; inspect storage permissions and handoff consistency.")
        return 1
    print("Development OAuth public key ready. Private key retained in backend owner-only storage.")
    print("kid:", jwks["keys"][0]["kid"])
    print("Public JWKS:", PUBLIC_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
