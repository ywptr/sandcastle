# Native development database

The approved development topology is native processes on Debian host
`5480-deb13`, sharing the host PostgreSQL engine while using separate databases
and roles per application. Sandcastle does not need a PostgreSQL container.

| Component | Development target |
| --- | --- |
| PostgreSQL | `127.0.0.1:5432` on `5480-deb13` |
| Database / owner / login role | `sandcastle_dev` |
| Driver | SQLAlchemy `postgresql+psycopg` |
| Backend | Native Uvicorn, HTTP port 8012 |
| Frontend | Native Vite, HTTPS `5480-deb13.lan.com:5182` |

Loopback refers to the host running the native backend. It would refer to a
container itself if a container were introduced; do not reuse this address for
container networking or create a second database server as a workaround.
The [frontend README](../frontend/README.md) describes TLS and the `/api` proxy.

## Private configuration

Keep development secrets in ignored `backend/.env`, mode 600. Both application
startup and Alembic load this file; exported shell values take precedence.
`.env.local` is not automatically loaded by this Python application.

```dotenv
DATABASE_URL=postgresql+psycopg://sandcastle_dev:<URL-encoded-development-password>@127.0.0.1:5432/sandcastle_dev
```

The placeholder is not a usable credential. Preserve approved IS issuer/client,
callback and cookie settings; database setup does not register IS clients or users.
Never put credentials in frontend variables, command arguments, Git, or logs.
Do not source a private dotenv file as shell code.

Local development, Vercel Preview and production are independent environments.
Production keeps its existing cloud PostgreSQL/Neon configuration and GUI `/api`
rewrite. The previous local `.env` contained a Neon URL whose production/preview
classification was unverified; it must not be used for development migrations.
A distinct Preview database/branch has not been verified. No Vercel variables or
Neon branches are modified by local setup.

## Provision or recreate

An administrator must first inspect database ownership, role attributes, existing
tables and connections. Reuse an existing correct database/role without resetting
its password. For a missing role, use an administrator's local `psql` session:

```sql
CREATE ROLE sandcastle_dev LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
-- Use psql's interactive password command; never put a real password in SQL files.
\password sandcastle_dev
CREATE DATABASE sandcastle_dev OWNER sandcastle_dev;
REVOKE ALL ON DATABASE sandcastle_dev FROM PUBLIC;
```

Connect to `sandcastle_dev` as its owner and revoke public schema creation:

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

PostgreSQL grants CONNECT to PUBLIC by default. Verify that Sandcastle cannot
connect to other applications' databases and that other application roles cannot
connect to this database. A grant directly to Sandcastle cannot override PUBLIC
access elsewhere; changes to another application's database require that owner's
separate approval. No cross-application role memberships should be present.

Recreation is explicitly destructive and is not part of normal startup. Obtain
approval for the exact local target, stop Sandcastle and disconnect its clients,
then have the administrator drop and recreate **only** `sandcastle_dev` owned by
the existing role. Preserve its password and other databases. Repeat the full
migration history below; never manually create domain tables or stamp an empty
database as current.

## Verify target and migrate

From `backend/`, use the existing virtual environment. This read-only check loads
the private file without printing its URL:

```sh
.venv/bin/python -B - <<'PY'
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
load_dotenv('.env')
url = make_url(os.environ['DATABASE_URL'])
assert url.drivername == 'postgresql+psycopg'
assert url.host == '127.0.0.1' and url.port == 5432
assert url.database == url.username == 'sandcastle_dev'
with create_engine(url).connect() as connection:
    row = connection.execute(text('SELECT current_database(), current_user')).one()
    assert tuple(row) == ('sandcastle_dev', 'sandcastle_dev')
    print('Verified development database and user:', *row)
PY
.venv/bin/alembic heads
.venv/bin/alembic current
.venv/bin/alembic upgrade head
.venv/bin/alembic current
.venv/bin/alembic check
```

Current repository head is `9e51b7c3d021` (SC#0001, after SC#0000 `8d40f6a2c910`). Recheck it before future work.
Stop on unexpected identity, nonlocal URL, unknown schema/history, migration
failure or drift. Do not edit historical migrations or bypass failures by manual
table creation. Normal application startup does not run migrations.

## Start and validate

```sh
cd /home/user/src/sandcastle/backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload
# In a separate terminal:
cd /home/user/src/sandcastle/frontend
npm run dev
```

Check port ownership before starting; do not kill another application's process.
`GET /health` and `/openapi.json` should return 200. Signed-out
`GET /api/auth/me` and `/api/stories` should return 401. Health alone does not
test database connectivity: perform the target query above and a read-only query
of `stories`. Interactive login requires the existing approved IS development
setup and remains separate from database validation. Do not fabricate IS users.

## Tests and disposable data

```sh
cd /home/user/src/sandcastle/backend
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s tests -p test_migrations.py -v
```

Existing tests override the connection with isolated SQLite databases and compile
the complete PostgreSQL migration SQL offline. They do not run destructive tests
against `sandcastle_dev`. Applying the history to the verified development server
is a separate real-PostgreSQL validation; passing SQL compilation alone is not.

`sandcastle_dev` contains disposable development data. Never copy production data
into it automatically. Future sample content should be explicit synthetic
fixtures or manually created development Stories; no seed system is introduced.
IS remains the identity provider and Story owners remain IS subjects. IG live
execution stays disabled/deferred; Axtor and tenancy behavior are unchanged.
pgAdmin is an optional inspection tool, never a runtime dependency.

## Observed setup validation — 2026-11-07

- Host PostgreSQL is 17.11 (Debian 17.11-0+deb13u1), listening on loopback
  and the existing private Docker gateway `172.30.0.1`, port 5432. Sandcastle
  uses only `127.0.0.1`.
- Existing database and login role `sandcastle_dev` were reused. The database
  was empty; its owner was already correct. No role/password/host grants or
  other application databases were changed. The role has no superuser,
  CREATEDB, CREATEROLE or BYPASSRLS privileges and no role memberships.
- Both directions of CONNECT between Sandcastle and `is_dev`, `ig_dev`,
  `axtor_dev` are denied. PUBLIC has no CREATE on Sandcastle's public schema.
  PostgreSQL administrative/template database CONNECT defaults remain unchanged;
  they confer no access to other applications' databases.
- Ignored `backend/.env` now selects only the loopback development database
  using psycopg, with mode 600. Stale cloud database aliases were removed;
  existing authentication settings were preserved. No production URL was used
  for a connection or migration, no cloud configuration changed, and no data
  was imported.
- `alembic current` was empty before initialization. All 14 existing revisions
  applied from base to `f15d7b92a640`. Afterwards current and heads match;
  `alembic check` reports no new upgrade operations. No migrations were added
  or edited.
- All 20 model tables are present and owned by `sandcastle_dev`, including
  `stories`, `characters`, `places`, `scenes`, `canon_entries`,
  `canon_candidates`, `media_executions`, `artifacts`, `canon_objects`,
  `canon_object_versions`, `universes`, and `story_workflows`. The application's
  SQLAlchemy Session successfully queried Stories (zero rows).
- Native backend startup succeeded on `127.0.0.1:8000`. `/health` and
  `/openapi.json` returned 200; signed-out `/api/auth/me` and `/api/stories`
  returned 401. No login or live IS request was performed. Normal startup has
  no automatic migrations. The temporary smoke-test backend was stopped.
- Full backend suite: 110 tests passed. Focused migration suite: 9 tests passed.
  These use their existing isolated fixtures, never persistent `sandcastle_dev`.
  Real PostgreSQL bootstrap and drift validation were performed separately above.
- An existing pgAdmin connection to `sandcastle_dev` as `sandcastle_dev` was
  visible in PostgreSQL activity. No pgAdmin UI inspection was performed.
- Interactive IS login, cloud Preview database provenance, and browser UI
  acceptance remain unverified. This task adds no product or identity behavior.


## SC#0000 provider settings

Provider settings add two tables through `8d40f6a2c910`. Reuse the verification
procedure above before migration. No automatic startup migration was added.
Credentials belong to an exact IS subject (`scope_type=user`), with no new User
or tenant model. Set `SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY` privately in the
backend environment before real credential writes. It must be Sandcastle-specific,
separate from IG and PostgreSQL, and backed up securely. No real key was created or
written to the development .env during implementation; CLI validation used an
ephemeral key and removed its synthetic test scope.

Use the [secure provider CLI](app/llm/README.md#secure-cli) for explicit configuration.
Development target safety matches the psycopg/loopback/database/role checks above;
the CLI also queries `current_database()` and `current_user()` before writing.
It permits deliberate remote operational use only with both
`--allow-production-write` and `--confirm-database-target HOST:PORT/DATABASE`.
Those flags are not part of normal development and were never used in validation.
There is no command-line/stdin API-key option or automatic environment key import.

Validation applied the revision to existing verified `sandcastle_dev`, then ran
Alembic heads/current/upgrade/current/check with no drift. The opt-in PostgreSQL
bootstrap ran the complete history in a disposable schema and removed it. The CLI
was exercised with invalid test provider keys in a synthetic scope, then that scope
was removed. No live provider, production/Preview/Neon, other-app database, or IS
configuration was used or modified.


## SC#0001 production-plan validation

`9e51b7c3d021` adds immutable approved adaptation snapshots and expands the bounded
LLM-role check. The normal verified-target migration sequence above applies. No
new credential or environment variable is needed. No startup auto-migration was added.

Validation upgraded the verified local database from `8d40f6a2c910`, then checked
heads/current/upgrade/current/check with no drift. The existing fresh-bootstrap suite
also exercised the full history in a disposable PostgreSQL schema. A separate smoke
test used synthetic Story/Scene/Canon/Character/Place data and a fake text translator
to verify all formats, approval/reload, idempotency, revisions and stale flags against
PostgreSQL. The complete synthetic fixture was removed. No provider, IG, media-byte
storage, production/Preview/Neon, or other-application database was used.

## Production schema updates

All future production Alembic updates follow the canonical
[production migration procedure](PRODUCTION_MIGRATIONS.md): a fresh temporary
terminal, current production env pulled from the verified backend Vercel project,
and explicit non-secret hostname/database verification before `alembic upgrade head`.
Development acceptance remains isolated to `sandcastle_dev`. Production application
is a separate operator action, never part of implementation tests or deployment.

## SC#0004 development migration

Creative Direction snapshots require `a062c8d4e132` after `9e51b7c3d021`. Development
validation positively checked local `127.0.0.1:5432`, database/login `sandcastle_dev`,
and SQL `current_database()/current_user` before applying the migration. Heads,
current, upgrade head, current, and check completed without schema drift. The
opt-in PostgreSQL fresh-schema bootstrap also exercised the chain in an isolated
schema within sandcastle_dev. No production environment or database was used.
Any later production application must follow the canonical procedure linked in this document;
this implementation acceptance is not authorization to migrate production.
