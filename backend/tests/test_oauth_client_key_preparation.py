"""Offline synthetic credentials only; no provisioning or IS requests."""
import base64
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from app.auth import client_key_preparation as prep
from app.auth.config import AuthConfig
from app.auth.is_oidc import ISOIDCClient

# Synthetic fixture only, never a claimed provisioned client ID.
CLIENT = "isolated-unit-test-client"
ENDPOINT = prep.DEVELOPMENT_TOKEN_ENDPOINT


class DevelopmentClientKeyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.private = self.root / "secrets" / "client" / "private-key.pem"
        self.public = self.root / "public.json"
        self.jwks = prep.prepare_key(self.private, self.public)
        self.key = prep.load_private_key(self.private)

    def token(self, **kwargs):
        return prep.sign_assertion(self.key, client_id=CLIENT, token_endpoint=ENDPOINT, **kwargs)

    def verify(self, token, jwks=None):
        return prep.verify_assertion(token, jwks or self.jwks, client_id=CLIENT, token_endpoint=ENDPOINT)

    def test_es256_signing_verification_and_point_match(self):
        token = self.token()
        claims = self.verify(token)
        self.assertEqual((claims["iss"], claims["sub"], claims["aud"]), (CLIENT, CLIENT, ENDPOINT))
        self.assertEqual(claims["exp"] - claims["iat"], 60)
        self.assertEqual(jwt.get_unverified_header(token)["alg"], "ES256")
        public = jwt.PyJWK.from_dict(self.jwks["keys"][0]).key
        self.assertEqual(public.public_numbers(), self.key.public_key().public_numbers())
        jwt.decode(token, public, algorithms=["ES256"], audience=ENDPOINT, issuer=CLIENT)

    def test_wrong_key_and_kid(self):
        other = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(prep.KeyPreparationError):
            self.verify(self.token(), prep.public_jwks(other))
        claims = self.verify(self.token())
        for key, kid in [(self.key, "wrong-kid"), (other, self.jwks["keys"][0]["kid"])]:
            token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": kid})
            with self.assertRaises(prep.KeyPreparationError):
                self.verify(token)

    def test_invalid_expired_future_long_lived_and_wrong_audience_assertions(self):
        baseline = self.verify(self.token()); now = baseline["iat"]
        changes = [{"iat": now - 100, "exp": now - 40}, {"iat": now + 100, "exp": now + 160},
            {"iss": "wrong"}, {"sub": "wrong"}, {"jti": ""}, {"iat": str(now)},
            {"exp": now}, {"exp": now + 61}, {"aud": ENDPOINT + "/"}, {"aud": [ENDPOINT]}]
        for change in changes:
            with self.subTest(fields=list(change)):
                token = jwt.encode({**baseline, **change}, self.key, algorithm="ES256", headers={"kid": self.jwks["keys"][0]["kid"]})
                with self.assertRaises(prep.KeyPreparationError):
                    self.verify(token)
        for token in ["not-a-jwt", self.token()[:-10] + "corrupted"]:
            with self.assertRaises(prep.KeyPreparationError):
                self.verify(token)
        del baseline["jti"]
        with self.assertRaises(prep.KeyPreparationError):
            self.verify(jwt.encode(baseline, self.key, algorithm="ES256", headers={"kid": self.jwks["keys"][0]["kid"]}))

    def test_signing_requires_client_id_exact_endpoint_and_maximum_60_seconds(self):
        for lifetime in [0, 61, -1, True, 1.5]:
            with self.subTest(lifetime=lifetime), self.assertRaises(prep.KeyPreparationError):
                self.token(lifetime=lifetime)
        claims = self.verify(self.token(lifetime=1))
        self.assertEqual(claims["exp"] - claims["iat"], 1)
        for audience in [ENDPOINT + "/", "https://sandcastle-auth.vercel.app/api/auth/oauth2/token", "https://5480-deb13.lan.com:5180/api/nexus/v1"]:
            with self.assertRaises(prep.KeyPreparationError):
                prep.sign_assertion(self.key, client_id=CLIENT, token_endpoint=audience)
        for client in [None, "", " "]:
            with self.assertRaises(prep.KeyPreparationError):
                prep.sign_assertion(self.key, client_id=client, token_endpoint=ENDPOINT)

    def test_unique_jti(self):
        self.assertEqual(len({self.verify(self.token())["jti"] for _ in range(100)}), 100)

    def test_public_export_exact_fields_stable_kid_and_no_rotation(self):
        self.assertEqual(set(self.jwks), {"keys"})
        self.assertEqual(len(self.jwks["keys"]), 1)
        self.assertEqual(set(self.jwks["keys"][0]), prep.PUBLIC_FIELDS)
        self.assertNotIn("d", self.jwks["keys"][0])
        before = self.private.read_bytes()
        self.assertEqual(prep.prepare_key(self.private, self.public), self.jwks)
        self.assertEqual(self.private.read_bytes(), before)
        self.assertEqual(json.loads(self.public.read_text()), self.jwks)
        self.public.write_text('{"keys": []}')
        with self.assertRaises(prep.KeyPreparationError):
            prep.prepare_key(self.private, self.public)
        self.assertEqual(self.private.read_bytes(), before)
        missing = self.root / "other-secrets" / "client" / "private-key.pem"
        with self.assertRaises(prep.KeyPreparationError):
            prep.prepare_key(missing, self.public)
        self.assertFalse(missing.exists())

    def test_restrictive_permissions_symlinks_hardlinks_and_curve(self):
        self.assertEqual(stat.S_IMODE(self.private.stat().st_mode), 0o600)
        for directory in [self.private.parent, self.private.parent.parent]:
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.private.chmod(0o644)
        with self.assertRaises(prep.KeyPreparationError):
            prep.load_private_key(self.private)
        self.private.chmod(0o600)
        self.private.parent.chmod(0o755)
        with self.assertRaises(prep.KeyPreparationError):
            prep.load_private_key(self.private)
        self.private.parent.chmod(0o700)
        alias = self.private.with_name("alias.pem"); alias.symlink_to(self.private)
        with self.assertRaises(prep.KeyPreparationError):
            prep.load_private_key(alias)
        os.link(self.private, self.private.with_name("hardlink.pem"))
        with self.assertRaises(prep.KeyPreparationError):
            prep.load_private_key(self.private)
        with self.assertRaises(prep.KeyPreparationError):
            prep.public_jwks(ec.generate_private_key(ec.SECP384R1()))

    def test_no_material_in_logs_git_frontend_or_cli_output(self):
        output, errors = io.StringIO(), io.StringIO()
        token = self.token(); private = self.private.read_bytes()
        with patch.object(prep, "prepare_key", return_value=self.jwks), redirect_stdout(output), redirect_stderr(errors):
            with self.assertNoLogs("app.auth.client_key_preparation", level="DEBUG"):
                self.assertEqual(prep.main(), 0)
        combined = (output.getvalue() + errors.getvalue()).encode()
        self.assertNotIn(private, combined); self.assertNotIn(token.encode(), combined)
        root = prep.BACKEND.parent
        ignored = subprocess.run(["git", "check-ignore", "backend/.secrets/oauth-client-development/private-key.pem"], cwd=root, capture_output=True)
        self.assertEqual(ignored.returncode, 0)
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
        self.assertFalse(any(p.startswith("backend/.secrets/") for p in tracked))
        paths = [root / p for p in tracked if p] + list((root / "frontend" / "dist").rglob("*"))
        for path in paths:
            if path.is_file():
                content = path.read_bytes()
                self.assertNotIn(private, content, str(path)); self.assertNotIn(token.encode(), content, str(path))
        for path in (root / "frontend" / "src").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"client_key_preparation", path.read_bytes())


class ExistingOAuthCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_basic_auth_pkce_and_callback_preserved(self):
        config = AuthConfig(issuer="https://identity.example.invalid/api/auth", client_id=CLIENT,
            client_secret="synthetic-test-secret", auth_secret="synthetic-session-secret",
            callback_url="https://5480-deb13.lan.com:5182/api/auth/callback",
            web_url="https://5480-deb13.lan.com:5182", cookie_secure=True)
        seen = []
        async def handle(request):
            seen.append(request)
            self.assertEqual(str(request.url), config.issuer + "/oauth2/token")
            expected = base64.b64encode(f"{CLIENT}:synthetic-test-secret".encode()).decode()
            self.assertEqual(request.headers["authorization"], "Basic " + expected)
            from urllib.parse import parse_qs
            body = parse_qs(request.content.decode())
            self.assertEqual(body["code_verifier"], ["synthetic-verifier"])
            self.assertEqual(body["redirect_uri"], [config.callback_url])
            self.assertNotIn("client_assertion", body)
            return httpx.Response(200, json={"access_token": "synthetic-token"})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("app.auth.is_oidc.httpx.AsyncClient", return_value=client):
            self.assertEqual(await ISOIDCClient(config).exchange_code(code="synthetic-code", code_verifier="synthetic-verifier"), "synthetic-token")
        self.assertEqual(len(seen), 1)
        self.assertIn("code_challenge_method=S256", ISOIDCClient(config).build_authorization_url(state="state", code_challenge="challenge"))
