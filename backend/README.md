# Sandcastle backend

Use Python 3.12+ and run commands from `backend/`:

Follow [native development database setup](DEVELOPMENT.md) before migrations.
Local development uses only `sandcastle_dev` on `5480-deb13`, separate from
cloud production and preview configuration.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload
```

Set `DATABASE_URL` to a PostgreSQL URL and configure the IS variables listed in
`app/auth/config.py`. Keep credentials in an ignored `.env` file. IS owns user
identity; Sandcastle stores its subject as each Story's owner. Use the same
browser host for the GUI `/api` rewrite and authentication callback in production.
For local HTTPS development, use the Vite `/api` proxy rather than an absolute
HTTP API origin. See [the local HTTPS setup](../frontend/README.md#local-https-development)
for the callback, return URL, and Secure-cookie settings. FastAPI remains HTTP
on port 8012; IS configuration is managed separately.

## Structured authoring

M11A tenant context is blocked on an implemented IS/Nexus consumer contract.
See [the tenant contract inspection and handoff](app/auth/M11A.md) for verified
upstream capabilities, session/revocation limits, and deferred Story migration.
Authenticated context currently has no `tenant_id`; Stories remain user-owned.

All routes below are prefixed with `/api` and require a valid Sandcastle session
established through IS. Access to another user's Story returns 404.

| Resource | Routes | Editable fields |
| --- | --- | --- |
| Story | `POST /stories`, `GET /stories`, `GET/PATCH /stories/{story_id}` | title, premise, objective, language, primary_genre, secondary_genres |
| Character | `GET/POST /stories/{story_id}/characters`, `PATCH .../characters/{character_id}` | name, description, appearance, outfit, personality |
| Place | `GET/POST /stories/{story_id}/places`, `PATCH .../places/{place_id}` | name, description, appearance, atmosphere |
| Canon | `GET/POST /stories/{story_id}/canon`, `PATCH .../canon/{entry_id}` | type, key, value; approved/superseded status on update |
| Scene | `GET/POST /stories/{story_id}/scenes`, `GET/PATCH .../scenes/{scene_id}` | optional title, required content on create |

PATCH requests update only supplied fields. Titles/names and Canon fields cannot
be blank. Story premise/objective and Scene title can be cleared with `null`.
IDs, ownership, source actions, and sequence numbers are assigned server-side.
Scenes are listed in sequence order. Scene creation locks the parent Story on
PostgreSQL before allocating the next sequence number.

Character/Place edits and Scene prose never silently update Canon. Users create
or edit authoritative facts explicitly. Superseded facts remain visible but are
excluded from Scene generation context. Existing `character` Canon entries are
not automatically converted into Character records.

## Optional Scene generation

`POST /stories/{story_id}/scenes/generate` accepts `{"request":"Continue..."}`.
The existing `StoryGenerator` interface receives the saved Story, Characters,
Places, approved Canon, and the current content of all previous Scenes.
SC#0000 resolves the authenticated user’s `creative_writer` role through encrypted
database-backed OpenAI, Anthropic, or Google configuration. Without a usable
configuration, this endpoint returns 503 and manual authoring remains available.
Environment API keys/model variables no longer enable generation. Generation never promotes prose to
Canon. The local authority gate and Action log remain in place.

M7 enables structured Canon extraction and explicit candidate review behind the
existing ownership boundary; see [Canon intelligence](app/canon/README.md).
The historical empty candidate migration remains unchanged, and M7 adds its table
through a new migration.

## Validation

```sh
.venv/bin/python -B -m unittest discover -s tests -v
alembic heads
alembic check
```

The tests use signed test-user sessions, an isolated SQLite database with foreign
keys enabled, and a fake generator. They exercise authenticated API CRUD,
ownership, validation, persistence, edited generation context, and Canon isolation.
Migration tests compile the entire history to PostgreSQL SQL and apply, check,
and reverse the new revision on a temporary database. They do not contact IS,
OpenAI, or a deployed database. `alembic check` outside tests inspects the configured
database; run it only against your intended development database.

The historical owner migration requires existing Stories to have valid owners
before making `user_id` non-null. It does not backfill legacy data. No migrations
are automatically applied during application startup.

## Media Orchestrator (M3)

The [Media Orchestrator](app/media/README.md) translates saved story-domain context
into provider-neutral `MediaRequest` and `MediaPlan` DTOs. Authenticated Scene-image
request and multi-Scene plan endpoints perform no generation or persistence.
Sandcastle owns semantics; a future IG/control-plane API client will own the
execution boundary. See the linked documentation for selection, reference, and
API contracts.


## Four-panel storyboards (M4A)

`POST /api/stories/{story_id}/scenes/{scene_id}/storyboard/four-panel` accepts `{}`
or M3 reference/framing options and returns exactly four ordered image requests
with `comic_panel` purpose. The deterministic planner reuses the Media Orchestrator
and reads current saved Scene content and approved Canon without modifying either.
See [the storyboard contract](app/media/README.md#four-panel-storyboard-planning-m4a)
for short-Scene behavior, selection defaults, and panel metadata.

No provider calls, persistence, or execution strategy are introduced. M4B will
execute the approved plan through IG; M5 video is deferred because IG currently
has no video capability.

## Durable storyboard execution (M4B)

The [execution contract](app/media/EXECUTION.md) adds explicit approval, durable
per-panel request snapshots, an injectable `MediaExecutionClient`, request-driven
status synchronization, and external-image Artifact metadata. Apply migration
`8f31c2d9a670` to your development database before using the execution routes.
Generated bytes remain outside PostgreSQL; Story/Canon/planning retain narrative
ownership and do not depend on IG transport.

Live IG execution is currently **disabled**: the inspected API requires browser
sessions and lacks service-caller/actor authentication. The documented IG media
submission also has a missing database-session argument. The adapter is tested
offline and does not forward passwords/cookies or invent a token mechanism.
See the linked document for exact external dependencies and API/error behavior.
M5 remains blocked on IG video capability.

## Artifact references and refinement previews (M6)

[Artifacts, bindings, and lineage](app/artifacts/README.md) add metadata registration
for uploaded/external images, reusable Story/Character/Place/style bindings,
multi-parent provenance, and provider-neutral `image_refinement` previews.
Applicable bindings now enter M3 Scene requests and M4A four-panel plans using
stable local Artifact IDs, with no storage locators in those requests.

Apply migration `a42d7e90c681` to a development database before using these APIs.
Generated artifacts and existing execution snapshots are preserved. No bytes are
uploaded or stored in PostgreSQL; references never become Canon automatically.
There is no live refinement, storage integration, or IG authentication change.
M5 video and M7 Canon intelligence remain deferred.


## Continuity and Canon intelligence (M7)

[Canon intelligence](app/canon/README.md) extracts bounded structured facts from
saved Story/Scene text, resolves existing subject IDs, and classifies proposals
against approved Canon. Candidates remain pending until explicit approval or
rejection. Conflict replacement supersedes current entries while retaining their
values and candidate review provenance. No image/reference fact becomes Canon
automatically, and no provider is required for deterministic extraction.

Migration `b7e193d2c540` creates the candidate table and adds nullable subject/fact
metadata to existing Canon entries. API operations include extraction, manual
proposals, filtered listing, reclassification, review, and lightweight continuity
counts/issues. Apply the migration to the intended development database before
using these APIs. M8 branching and M4B/M5 live media integrations remain deferred.

### M8 — reusable Canon Library

Characters and Places can be explicitly promoted, shared through pinned versions,
and forked before Story-specific changes. Existing Story subject IDs remain valid.
See [Canon Library](app/canon/LIBRARY.md) for APIs, M7/M6 integration and migration
`c81f24a709de`. No automatic version following, Universe scope, or provider calls.

### M9A — Shared Universe / World foundation

Optional account-owned Universes pin existing M8 Canon versions. Member Stories
inherit effective Canon without copies, can override pins or explicitly fork, and
publish discoveries only through explicit promotion. See [Universe foundation](app/universes/README.md)
for APIs, precedence, stable subject IDs and migration `d93b71c602fa`.

### M9B — Narrative guidance

Stories can save separate audience/maturity settings and optional private feedback.
Provider-neutral next-scene guidance returns short alternatives without creating
Scenes or changing Canon. The Scene form can place a selected alternative into
its existing editable request textbox. See [Narrative guidance](app/guidance/README.md)
for APIs, the deterministic fallback, context limits and migration `e04c8a12b763`.

### M9C — Audience-aware media adaptation

Ephemeral shot plans preserve original narrative beats while producing explicit,
audience-aware visual treatments. Adapted four-panel planning reuses M4A/M3 and
keeps raw sensitive prose out of compiled prompts. See [Media adaptation](app/media/adaptation/README.md)
for APIs, continuity review issues, deterministic limitations and reference flow.
No persistence, frontend media workspace, provider execution or video is added.

### M10 — Workflow templates and difficulty

Stories now have version-pinned workflow configuration with curated Standard,
Guided, Canon Strict and Webtoon templates. Easy/Normal/Difficult/Impossible
control capability disclosure independently of subscriptions. Explicit workflow
actions reuse existing Canon, guidance and adaptation services; no graph runner
or IG execution is added. See [Workflows](app/workflows/README.md) and migration
`f15d7b92a640`.

### M12A — Import Story analysis

Authenticated `POST /api/stories/import/analyze` interprets pasted summaries,
drafts or notes into bounded, evidence-backed proposals without database writes.
It requires an optional configured text provider and adds no schema migration.
See [Import analysis](app/story_import/README.md) for contracts, limits and M12B
review boundaries. An ImportProposal is not Canon and is not a Story until the
user accepts it in a later persistence workflow.

### M13 — Story language and genre

[Persistent Story metadata](app/stories/README.md) documents shared language/genre
validation, PATCH semantics, legacy defaults and generation/guidance behavior.
Apply `7c2e91a4b830` only to verified development `sandcastle_dev`.


### SC#0000 — multi-provider LLM configuration

[AI provider architecture, security, CLI and operations](app/llm/README.md) describes
the user-scoped BYOK settings and role resolver. OpenAI, Anthropic and Google support
both Scene generation and M12A Import analysis; Guidance and active Canon extraction
remain deterministic. Domain capability protocols remain intact.

Apply migration `8d40f6a2c910` to verified `sandcastle_dev`. Configure the backend-only
`SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY`, then explicitly configure each user's
provider credentials/model through authenticated `/api/settings/llm` or
`scripts/configure-llm-provider.py`. No environment key is automatically imported.
`OPENAI_API_KEY` and `SANDCASTLE_TEXT_MODEL` are no longer runtime composition inputs.
No production configuration was changed. Clients using the old environment-only
setup must explicitly configure BYOK before AI requests will succeed.

The CLI requires an exact IS subject, securely prompts for the key, and supports
safe `--show`, `--disable`, `--enable`, and confirmed `--remove-credentials`. It uses
the same transactional encryption service as the API. No local user directory or
tenant credentials were introduced. Media execution/IG remains separate.

### SC#0001 — Narrative-to-Media production planning

[Production translation](app/media/production/README.md) turns one saved Scene into
an editable Webtoon panel plan, Short Drama shot plan, or Story Reel beat plan.
It uses the SC#0000 `narrative_media_translator` role with the user's existing
provider credentials. Drafts are ephemeral; explicit approval stores immutable
revisions and provider-neutral MediaPlan manifests. No media generation or IG call
occurs. Scene, Canon, M9C audience treatment and the M4A quick planner remain separate.

Migration `9e51b7c3d021` adds approved snapshots and the new bounded role. Apply only
to verified development `sandcastle_dev` using DEVELOPMENT.md. The Scene workspace
now includes Production and approved history. Source/context changes require a new
adaptation rather than silent revision of old approval. Timing is estimated.

Production schema application is a separate operator action using the default
[fresh-terminal Vercel production migration procedure](PRODUCTION_MIGRATIONS.md).
Never apply production migrations during development acceptance or deployment.

SC#0004 adds [Creative Direction onboarding](app/creative_direction/README.md): a
versioned style registry, provider-neutral ephemeral recommendations using the
creative_writer role, atomic ordinary Story creation with approved direction, and
append-only direction revisions. Migration `a062c8d4e132` follows `9e51b7c3d021`.
Development application is restricted to verified `sandcastle_dev`; production
application remains the separate documented operator procedure.
