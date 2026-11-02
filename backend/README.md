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
For local Vite development, set `VITE_API_BASE_URL=http://localhost:8000/api` in
`frontend/.env.local` (Vite does not proxy `/api` by default).

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

Canon extraction and candidate review are deferred: their existing routes return
503 after ownership checks. The historical empty candidate migration is unchanged;
this milestone adds no candidate table or extraction UI.

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
