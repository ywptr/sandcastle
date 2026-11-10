# SC#0000 — user-scoped LLM providers

Sandcastle retains `StoryGenerator`, `StoryImportAnalyzer`,
`NarrativeSuggestionGenerator`, and `CanonExtractor`. The shared LLM layer owns
settings, encryption, role selection, and operation-scoped adapter construction;
it does not introduce a universal text-generation protocol.

Scene writing and Import analysis route through OpenAI, Anthropic, or Google.
Scene context compilation (Canon, Characters, Places, prior Scenes, language and
genre) is unchanged. Import remains analysis-only: the request is an untrusted JSON
data envelope separate from system instructions, bounded to 40,000 characters.
Every adapter produces a typed ImportAnalysis, which M12A revalidates for exact
evidence, taxonomy, candidates and deduplication. No import persistence was added.
Guidance and the active Canon extractor remain deterministic, as do continuity
classification and workflow planning. The unused optional OpenAI Canon adapter now
requires explicit credentials/model; it is not wired into routing.

## Persistence and isolation

Migration `8d40f6a2c910` follows M13 `7c2e91a4b830` and adds:

- `llm_provider_configs`: UUID, scope_type/scope_id, stable provider ID, enabled,
  nullable encrypted credential envelope, bounded non-secret configuration,
  created/updated timestamps. Unique scope/provider constraint.
- `llm_role_bindings`: scope_type/scope_id/role primary key, provider, optional model,
  updated timestamp. Roles are `creative_writer` and `story_importer`.

Only `scope_type=user` is accepted, including database checks. `scope_id` is the IS
subject already used for Story ownership. There is no shadow User table. Settings
APIs never accept an owner/scope ID; the authenticated session supplies it. Keys
are not selected from another user's Story or browser payload.

After M11, tenant scope could use a canonical tenant UUID, with a deliberate
constraint migration and trusted tenant resolution. Resolution could eventually
use user overrides, tenant defaults, then platform defaults. None of that fallback
or billing is implemented, and user keys must never be automatically converted to
tenant credentials. Provider adapters and domain services need not change.

## Encryption and lifecycle

`cryptography` Fernet (supported dependency range `>=46,<49`, validated with 48.0.1)
provides authenticated encryption. The envelope includes version, user scope,
provider and API key; decryption checks all identity fields to reject ciphertext
copied to another owner/provider. PostgreSQL stores only encrypted envelopes.

Configure the Sandcastle-specific master key outside PostgreSQL:

```text
SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY=<Fernet key>
```

Generate a Fernet key using `Fernet.generate_key()` in a secure operator environment
and place it directly into the protected backend secret configuration. Keep its
backup separate from the database and never reuse IG's key. Development uses ignored
`backend/.env` (mode 600); production uses the backend secret manager/environment.
No deployment variables were changed for SC#0000. Missing/invalid keys make secret
writes/use unavailable without breaking manual authoring or safe settings reads.

Supplying credentials replaces the encrypted secret; omitting them preserves it.
`null`/empty credential payloads are invalid. Disable preserves the key. Explicit
removal erases it and disables the provider. Re-enable preserves the existing
credential. Provider-key rotation is a normal replacement. Old encrypted values
are not retained by this subsystem; separately revoke old keys at the provider.
Master-key rotation is an operator maintenance operation, not an automatic action:
retain the old key while re-encrypting or replacing all stored credentials. Merely
changing the master key makes old credentials unusable. Database backups retain
historical ciphertext and require appropriate retention controls.

No stored credential or ciphertext is returned, even masked. Settings validation
errors are deliberately sanitized because normal FastAPI validation includes input
values. SecretStr/repr exclusions, fixed provider errors, no raw upstream bodies,
no provider diagnostics persistence, and no CLI exception dumps prevent ordinary
application leakage. Do not enable external request-body/header tracing for secret
settings/provider calls. Infrastructure logging policies remain an operator duty.

## Resolution and models

An explicit role binding uses that provider/model, or the provider default when
model is null. An unusable explicit binding returns 503; it does not silently
switch vendors. Without a binding, selection is deterministic: OpenAI, Anthropic,
Google, skipping disabled/credentialless/model-less configurations. There are no
post-failure retries/fallbacks. No configured provider is required for non-AI work.

`config` permits only `default_model`; APIs validate a bounded opaque model ID,
never a URL. Model IDs/availability/structured-output support are ultimately
validated by the selected official provider API. Sandcastle has no universal model
catalog, automatic model substitutions, arbitrary base URLs, health probes, or
request-time vendor/model overrides on Story endpoints. Configure a model that
supports the requested capability; invalid/unavailable models fail safely.

## Provider contracts and library choices

Inspected official documentation on 2026-11-10:

- [OpenAI Responses structured output](https://developers.openai.com/api/docs/guides/structured-outputs):
  retain the existing optional OpenAI Python SDK, explicit key/model/base URL,
  `responses.create` for Scenes and `responses.parse(text_format=ImportAnalysis)`
  for Import. `store=false`, 60-second timeout, zero SDK retries. SDK imports occur
  only when OpenAI is selected, so a missing SDK does not prevent backend startup.
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages) and
  [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs):
  use the existing HTTPX dependency with fixed `/v1/messages`, `x-api-key`, and the
  supported `2023-06-01` compatibility API version. Import uses
  `output_config.format` JSON Schema and a separate `system` message. Transport
  schema removes unsupported length/numeric/default constraints, retains them as
  descriptive guidance, and always applies original Pydantic validation afterward.
- [Gemini generateContent REST](https://ai.google.dev/api/generate-content):
  use HTTPX with fixed `generativelanguage.googleapis.com/v1beta/models/...`, key
  in `x-goog-api-key` (never the query string), `systemInstruction`, and JSON output
  using `generationConfig.responseMimeType/responseJsonSchema` for Import.

HTTPX is already part of Sandcastle. Small official REST adapters avoid adding two
SDK dependency trees. SDK and HTTP details remain adapter-local. No provider client
or decrypted key is globally cached; per-call clients close after completion. REST
adapters disable redirects/environment proxies, attach no browser cookies, and do
not retry. Truncation, refusals/blocks, invalid JSON/schema/evidence and HTTP errors
fail closed. Provider calls use bounded output tokens (8,000 Scenes, 12,000 Import).
No live provider call was made during automated or manual validation.

The OpenAI SDK follows the repository's existing unpinned dependency convention;
no SDK upgrade was requested by this task. Installed validation version was 3.46.0.

## Authenticated API

All routes below are prefixed `/api/settings/llm`; reads return `Cache-Control: no-store`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/providers` | Three supported providers and current user's safe metadata |
| GET | `/providers/{provider}` | Safe metadata; an unconfigured provider has empty settings |
| PUT | `/providers/{provider}` | Supplied enabled/config/credentials fields only |
| DELETE | `/providers/{provider}/credentials` | Explicit deletion and disable |
| GET | `/roles` | Explicit preference and effective local provider/model selection |
| PUT | `/roles/{role}` | Bind provider/optional model, or `{ "provider": null }` for Automatic |

PUT provider accepts `enabled`, `config: {default_model}`, and optional
`credentials: {api_key}`. Config replaces the bounded non-secret config; omission
keeps it. Unknown providers/roles/fields, tenant scope, and custom URLs are rejected.
Role selection requires an enabled credentialed provider and an effective model.
Reads report local configuration availability, not provider health or account quota.
The Settings UI has no generic JSON/config editor or raw upstream errors.

## Secure CLI

From `backend/` with the normal private configuration loaded:

```sh
.venv/bin/python scripts/configure-llm-provider.py --user-id '<exact-IS-subject>' --provider openai
.venv/bin/python scripts/configure-llm-provider.py --user-id '<exact-IS-subject>' --provider anthropic --show
.venv/bin/python scripts/configure-llm-provider.py --user-id '<exact-IS-subject>' --provider google --disable
.venv/bin/python scripts/configure-llm-provider.py --user-id '<exact-IS-subject>' --provider google --enable
.venv/bin/python scripts/configure-llm-provider.py --user-id '<exact-IS-subject>' --provider google --remove-credentials
```

Default operation prompts with getpass for a hidden key (blank preserves), model
(blank preserves current), and enabled state. An optional `--default-model` is
non-secret. Rotate by configuring again. `--show` never decrypts. Removal requires
interactive `REMOVE`; disabling and removal are distinct operations. Writes require
an interactive terminal, and getpass echo-fallback warnings abort rather than
reading insecure input. No key argument, environment key ingestion, stdin secret
channel, or noninteractive secret mode exists.

The CLI prints database, host, user scope, exact subject and provider before writing,
verifies connected database/user, and uses the same transactional settings service
as the API. Errors roll back and print fixed messages. There is no User table to
validate IS subjects against: operators must obtain the exact subject from trusted
IS identity evidence. Existing Story ownership may corroborate it but does not
prove identity. The CLI does not create identities or default to the first owner.

Normal development permits only psycopg, `127.0.0.1:5432`, database/login
`sandcastle_dev`, matching DEVELOPMENT.md. Any deliberate remote operational use
requires both `--allow-production-write` and exact
`--confirm-database-target HOST:PORT/DATABASE`; connected identity must still match.
Do not use those overrides for development. No remote/cloud write was performed.
Future tenant CLI mode must be added explicitly after M11; no tenant flags exist now.

## Migration from environment credentials

`OPENAI_API_KEY` and `SANDCASTLE_TEXT_MODEL` no longer compose Scene/Import clients.
There is no environment fallback and no automatic copy into PostgreSQL. Existing
users must configure BYOK explicitly and choose a model. Manual authoring remains
available while configuration is missing (AI requests return 503). Keep provider
keys out of normal production environment variables once migrated. This is an
intentional operational change; operators must configure the encryption key and
user credentials before expecting AI generation. No production variables or keys
were changed or removed by this task.

## Validation

Focused suites: `test_llm_settings.py`, `test_llm_adapters.py`, `test_llm_cli.py`,
`test_llm_migrations.py`; existing Scene/context/M13 and M12A suites remain active.
Tests use fake credentials/providers and isolated SQLite, including malformed
credential validation, tampered/wrong-scope ciphertext, rotation/omission/removal,
request-scoped routing, no fallback, sanitized failures, secure CLI I/O and rollback.
Migration tests include upgrade/downgrade preservation, offline PostgreSQL SQL, and
the opt-in disposable-schema full-history bootstrap on verified sandcastle_dev.
The actual CLI was exercised there with an ephemeral encryption key and invalid
synthetic provider credentials; its synthetic scope was removed afterward.

Provider settings were browser-tested on existing HTTPS Vite using API fixtures,
including secret-input clearing and desktop/mobile screenshots. Full live IS-user
settings/persistence acceptance remains unverified without an authenticated session.
No approved real development provider credentials were supplied, so there were no
billable provider smoke tests. IG, production/Preview/Neon, IS configuration,
Difficulty semantics and media execution were not modified.

## Change inventory

- `README.md`
- `backend/DEVELOPMENT.md`
- `backend/README.md`
- `backend/alembic/versions/8d40f6a2c910_llm_provider_settings.py`
- `backend/app/api/llm_settings.py`
- `backend/app/api/stories.py`
- `backend/app/canon/adapters/openai_extractor.py`
- `backend/app/db/models/__init__.py`
- `backend/app/db/models/llm.py`
- `backend/app/llm/README.md`
- `backend/app/llm/__init__.py`
- `backend/app/llm/cli.py`
- `backend/app/llm/errors.py`
- `backend/app/llm/providers/__init__.py`
- `backend/app/llm/providers/anthropic.py`
- `backend/app/llm/providers/google.py`
- `backend/app/llm/providers/http.py`
- `backend/app/llm/resolver.py`
- `backend/app/llm/schemas.py`
- `backend/app/llm/secrets.py`
- `backend/app/llm/service.py`
- `backend/app/main.py`
- `backend/app/stories/adapters/openai_generator.py`
- `backend/app/stories/generation.py`
- `backend/app/stories/prompts.py`
- `backend/app/story_import/README.md`
- `backend/app/story_import/analyzer.py`
- `backend/app/story_import/openai_analyzer.py`
- `backend/app/story_import/prompts.py`
- `backend/pyproject.toml`
- `backend/scripts/configure-llm-provider.py`
- `backend/tests/test_llm_adapters.py`
- `backend/tests/test_llm_cli.py`
- `backend/tests/test_llm_migrations.py`
- `backend/tests/test_llm_settings.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_story_import.py`
- `backend/tests/test_story_metadata_migrations.py`
- `frontend/README.md`
- `frontend/src/App.css`
- `frontend/src/App.tsx`
- `frontend/src/api/sandcastle.ts`
- `frontend/src/components/AIProviderSettings.tsx`
- `frontend/tests/api.test.mjs`
- `frontend/tests/providers.browser.mjs`

Observed completion validation: full backend suite ran 153 tests successfully
(one expected opt-in skip); focused LLM suites passed 23 tests, including seven
CLI tests. The separate opted-in PostgreSQL fresh-schema bootstrap passed both
tests; historical migration regressions passed all nine tests. Frontend unit tests,
lint (no warnings), production build, AI Providers browser harness and the M14
workspace browser regression passed. Browser fixture checks covered narrow widths
without horizontal overflow. Screenshots: `/tmp/sc0000-visuals/ai-providers-desktop.png`
and `/tmp/sc0000-visuals/ai-providers-mobile.png`. The real development API remained
healthy. Changed-file secret-literal scanning and `git diff --check` passed.


## SC#0001 consumer extension

The bounded role `narrative_media_translator` now routes the semantic
NarrativeMediaTranslator capability through the same encrypted provider settings.
All three providers return format-specific structured proposals. No credential
handling or fallback policy is duplicated. See [production translation](../media/production/README.md).

## SC#0002 personal AI settings and future workspace sources

Personal BYOK is permanent. Settings distinguishes Supported (adapter exists),
Connected (encrypted key saved, not live-verified), Enabled (eligible), and Selected
(chosen for a task). No settings load/save makes a billable validation request.
The three task labels map to `creative_writer` (Creative writing),
`story_importer` (Story import), and `narrative_media_translator` (Production planning).
Automatic selects enabled, configured personal providers in OpenAI → Anthropic →
Google order before execution. It never fails over after a provider failure.
An explicit unavailable binding remains unavailable instead of silently changing.

`LLMActorContext` and `resolve_provider_for_role` isolate source selection from
adapter construction. Only `UserProviderSource` is installed today: user role
binding → user configured provider → unavailable. Current APIs reject scope and
identity fields; tenant writes remain forbidden. Future resolution may add trusted
Nexus-derived tenant role/default sources, then platform-managed sources. Neither
exists today, and browser-supplied tenant IDs cannot establish that authority.
Domain services and adapters need not change when an authorized source is added.
User keys must never automatically become shared tenant keys.

The CLI accepts `--is-subject` as an alias for `--user-id`: both mean the IS OIDC
`sub` used as Sandcastle user identity, not email or a locally created user. Existing
CLI safety, secure input, rotation, removal confirmation, and transaction rules
are unchanged. No email lookup or tenant mode is provided.

SC#0002 validation: focused LLM/CLI/readiness suites passed 28 tests. Full backend
regression passed 177 tests with one expected opt-in PostgreSQL bootstrap skip.
No migration was added; Alembic head remains `9e51b7c3d021`. No production environment
was fetched, credential configured, provider invoked, or production migration run.
See the canonical [production Alembic procedure](../../PRODUCTION_MIGRATIONS.md)
for future explicit operator updates, separate from development acceptance.

## SC#0004 recommendation consumer

Creative Direction recommendation reuses `creative_writer` through a semantic
CreativeDirectionRecommender adapter. No new role, key, provider routing preference,
or tenant/default provider was introduced. The internal capability argument selects
adapter construction only; it is not accepted by Story request payloads. Registry
browsing is provider-free. Missing provider returns 503; the frontend offers manual
creation without steering beginners into API-key setup. See
[Creative Direction](../creative_direction/README.md).
