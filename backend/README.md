# Sandcastle backend

Use Python 3.12+ and run commands from `backend/`:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

Set `DATABASE_URL` to a PostgreSQL URL and configure the IS variables listed in
`app/auth/config.py`. Keep credentials in an ignored `.env` file. IS owns user
identity; Sandcastle stores its subject as each Story's owner. Use the same
browser host for the GUI `/api` rewrite and authentication callback in production.
For local HTTPS development, use the Vite `/api` proxy rather than an absolute
HTTP API origin. See [the local HTTPS setup](../frontend/README.md#local-https-development)
for the callback, return URL, and Secure-cookie settings. FastAPI remains HTTP
on port 8000; IS configuration is managed separately.

## Structured authoring

All routes below are prefixed with `/api` and require a valid Sandcastle session
established through IS. Access to another user's Story returns 404.

| Resource | Routes | Editable fields |
| --- | --- | --- |
| Story | `POST /stories`, `GET /stories`, `GET/PATCH /stories/{story_id}` | title, premise, objective |
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
The OpenAI adapter is initialized only on demand and requires `OPENAI_API_KEY`,
`SANDCASTLE_TEXT_MODEL`, and the installed SDK. Without them, this endpoint returns
503 and manual authoring remains available. Generation never promotes prose to
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
