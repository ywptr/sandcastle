# M11 Development OAuth client key handoff

Status: **key preparation only; no authentication cutover or IS provisioning**.
The actual OAuth client ID and exact Nexus resource audience remain unset.

## Nonsecret inputs ready for the IS conversation

| Field | Prepared value |
| --- | --- |
| Environment | Sandcastle Development only |
| Client type | Confidential web OAuth client |
| Client authentication | `private_key_jwt` |
| Signing algorithm / curve | `ES256` / `P-256` |
| Public kid | `sandcastle-dev-nRE35Mf-lAcXtiRxymFGmbxAiPyzdCVCZ0RkAB2jI5I` |
| Target issuer | `https://5480-deb13.lan.com:5180/api/auth` |
| Expected exact assertion audience/token endpoint | `https://5480-deb13.lan.com:5180/api/auth/oauth2/token` — IS must confirm |
| Development origin | `https://5480-deb13.lan.com:5182` |
| Exact redirect URI | `https://5480-deb13.lan.com:5182/api/auth/callback` |
| Nexus Consumer API base | `https://5480-deb13.lan.com:5180/api/nexus/v1` |
| Required human scopes | `nexus:tenants:read nexus:membership:self nexus:access:evaluate nexus:entitlements:read` |
| Initial application operation | `sandcastle:tenant.access` |
| Assertion lifetime | Integer 1–60 seconds, default and maximum 60 |
| Replay prevention | Unique random UUID `jti` per assertion; IS must enforce single use |
| OAuth client ID | Await IS provisioning; no ID invented |
| Nexus resource audience | Await finalized IS contract; never inferred from API URL |

`sandcastle:tenant.access` establishes tenant/application eligibility only. It does
not authorize Story, Canon, Scene, Episode, or other Sandcastle resources.
The human scopes above are handoff requirements, not enabled application scopes.
Existing login continues requesting `openid profile email` only.

Inline public JWKS (the separate JSON artifact contains this same single key):

```json
{
  "keys": [
    {
      "crv": "P-256",
      "kty": "EC",
      "x": "hu0PRAqk53_oHUUDFqxZRZDB69SEka5nYdQN4y825ag",
      "y": "_7jTQ8AyOc3see8tqCdU-Vm2Lw-j3vvpUEpS68UmAMQ",
      "kid": "sandcastle-dev-nRE35Mf-lAcXtiRxymFGmbxAiPyzdCVCZ0RkAB2jI5I",
      "alg": "ES256",
      "use": "sig"
    }
  ]
}
```

Private-key custody: retained only in Sandcastle backend local secret storage,
`backend/.secrets/oauth-client-development/private-key.pem`, current backend OS user
UID 1000, file mode `0600`; both `.secrets/` and `oauth-client-development/` are
owner-only mode `0700`. This follows the existing ignored backend file-based secret
convention (`backend/.env`, mode `0600`) without adding the key to active login env.
The private key is not part of this handoff. No actual client assertion is exported.

## Existing authentication and compatibility

`app/auth/is_oidc.py::ISOIDCClient` uses HTTPX, authorization code + S256 PKCE,
`openid profile email`, and HTTP Basic token authentication (`client_secret_basic`).
`app/api/auth.py` owns `/api/auth/login`, `/api/auth/callback`, `/api/auth/me`, and
logout; callback exchanges the code, reads userinfo, and creates the existing signed
Sandcastle session. IS remains the identity provider. No Authlib or JWT assertion
library existed in the dependency list, and no client signing key/JWKS was found.

The inspected development `.env` still points `IS_ISSUER` at
`https://sandcastle-auth.vercel.app/api/auth`, with the Development origin/callback
shown above. These settings are unchanged. The frontend HTTPS Vite server on 5182
proxies `/api` to the native backend on `127.0.0.1:8012`.

Added PyJWT `[crypto]>=2.15.1,<3` (tested 2.15.1) using the existing
`cryptography` dependency (tested 48.0.1). Offline signing supplies explicit `ES256`,
matching `kid`, `iss=sub=client_id`, exact Development token-endpoint `aud`, integer
`iat`/`exp`, and random `jti`. Lifetime is bounded at creation and independently
checked by the isolated verifier. The verifier fixes the algorithm and validates
identity, expiration, audience, required claims, and public-key selection.
It is a test/readiness check, not an IS replay cache or a Sandcastle access-token
validator. No custom signature implementation is used.

HTTPX can carry an assertion as form fields in a future reviewed token-exchange
change, but the existing OAuth client does **not** yet issue/send `private_key_jwt`.
The preparation module is not imported by application startup, auth config, the
existing OAuth client, or frontend code. It contains no network calls.

## Public registration decision and remaining IS dependencies

Current official [Better Auth client documentation](https://better-auth.com/docs/plugins/oauth-provider/clients#private-key-jwt)
describes inline `jwks` with `adminCreateOAuthClient` and `private_key_jwt`.
Prefer that approved administrative path **only after IS confirms its pinned
provider version and controlled admin interface support it**. Sandcastle has not
inspected or modified IS internals, registered a client, or published a JWKS URL.
No dynamic registration or public endpoint has been enabled.

If IS's pinned interface cannot accept inline keys, stop for review of an HTTPS
JWKS publication design: a public-only immutable JSON artifact under a controlled
HTTPS Sandcastle origin, verified TLS/trust and IS reachability, an explicit key
rotation/cache policy, and a check excluding all private parameters. The concrete
host/path and IS allowlist must be approved separately; no URL is assumed here.

IS#0001 must provide:

1. IS#0001-D trusted local HTTPS recovery and confirmed discovery/token endpoints.
2. Pinned Better Auth support and approval for inline public-JWKS registration.
3. The provisioned Development OAuth client ID and accepted ES256/kid profile.
4. Maximum 60-second assertions and server-side `jti` replay rejection confirmation.
5. The finalized exact Nexus resource audience, human scopes and application operation.
6. A separate approved Sandcastle M11 cutover plan before any issuer/client/auth-method
   changes, Nexus requests, tenancy migration, or ownership changes.

## Key lifecycle and offline validation

From `backend/`, prepare or verify the same existing key:

```sh
.venv/bin/python -B -m app.auth.client_key_preparation
.venv/bin/python -B -m unittest discover -s tests -p test_oauth_client_key_preparation.py -v
```

Preparation uses `cryptography.ec.generate_private_key(SECP256R1())` with system
secure randomness. It writes PKCS#8 PEM directly to an exclusively created file;
private material is never printed or placed in a temporary handoff file. The stable
kid is the RFC 7638 SHA-256 public JWK thumbprint with a Development prefix. Public
coordinates are exported using PyJWT, parsed back, and matched to the private key's
public point. JWKS contains exactly `kty`, `crv`, `x`, `y`, `kid`, `alg`, and `use`.

Existing private material is reused, never silently rotated. Unsafe ownership,
permissions, symlinks, hardlinks, another curve, a mismatched public handoff, or a
public handoff without its private key fail closed. Loss of the private key after
registration requires explicit IS-coordinated replacement; do not delete the public
handoff and rerun generation as an implicit rotation. Retain this ignored backend
key in controlled local custody; no remote backup or transmission was performed.
The backend OS account and administrators remain trusted under this file-based model.

Tests generate ephemeral synthetic keys and client IDs, never require provisioned IS,
and never contact IS. Coverage includes signatures, incorrect key/kid, malformed,
expired/future/wrong-identity assertions, missing claims, >60-second lifetimes,
wrong/exact audiences, unique jti, public-only export, stable reuse, unsafe storage,
Git/frontend/output exclusion, and existing HTTP Basic/PKCE compatibility. Synthetic
assertions are used only in memory and are not included in this handoff.

Validation results for this preparation:

- Focused key and existing OAuth transport tests: 9 passed.
- Full backend including session/authentication/ownership regressions: 207 tests,
  passed with 1 opt-in PostgreSQL bootstrap skip.
- Actual private PEM/base64 payload/private JWK scalar exclusion scan: passed for
  298 repository, existing frontend build and test-log files; private storage is
  excluded from Git. Repeated preparation retained the same inode and key bytes.
- `git diff --check`: passed. No frontend source/bundle changes were made.
- No real client assertions were sent, no IS provisioning/API calls were made, no
  database migration ran, and no active authentication settings were changed.
- Work remains local and uncommitted; no push or deployment was performed.
