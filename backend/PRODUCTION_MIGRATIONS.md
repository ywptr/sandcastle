# Standard production Alembic procedure

This is the default operational procedure for **all future** Sandcastle production
Alembic updates, including SC milestones, M11, and Story/Canon/production-plan
schema changes. Production application is a separate, explicit operator action.
Implementation acceptance validates only `sandcastle_dev`; it never silently
migrates production. No startup, Vercel build/deployment, or normal test suite may
run production migrations.

## Prepare a fresh temporary terminal

Use a newly opened temporary terminal, never a long-lived development shell.
Disable tracing and restrict new file permissions. From the repository root:

```sh
cd ~/src/sandcastle
set +x
umask 077
vercel link
```

Verify the intended Vercel team and **Sandcastle backend/API project**, not just
the GUI project. Linking alone is not proof of the database target. Do not overwrite
an unexplained existing `.env.production.local`: stop and resolve it first.

```sh
vercel env pull .env.production.local --environment=production
chmod 600 .env.production.local
git check-ignore .env.production.local
unset DATABASE_URL
set -a
source backend/.venv/bin/activate
source .env.production.local
set +a
```

These `source` commands require Bash. The virtual environment actually lives in
`backend/.venv`. Loading this freshly generated, trusted Vercel file is a narrow
production-session exception to the development dotenv guidance. Never source an
untrusted file. Do not echo environment values, enable shell tracing, paste a
production URL/password, or copy the URL into commands. The encryption master key
and other pulled secrets must also remain private.

**Stop if the pull fails or DATABASE_URL is absent.** Vercel Secret environment
variables can be withheld from `env pull`; do not downgrade their protection or
substitute a development/stale URL. A separately reviewed operational access
procedure is needed if the linked project cannot supply the production URL.
Prevent Alembic's local dotenv fallback by checking the exported value first:

```sh
if [ -z "${DATABASE_URL:-}" ]; then
    echo 'STOP: production DATABASE_URL was not loaded.'
    rm -f .env.production.local
    exit 1
fi
cd backend
alembic current
alembic heads
```

These commands inspect revision state; **do not run upgrade yet**. Record the
repository head(s). If any command fails, stop. Multiple unexplained heads require
review before proceeding.

## Mandatory target verification

Obtain the expected Neon hostname and database name from independently trusted
production inventory. They are not inferred from the linked Vercel project or
from successful local `sandcastle_dev` tests. Run this helper with the actual
expected non-secret names (the placeholders below are not valid targets):

```sh
python scripts/inspect-database-target.py \
  --expect-host '<intended-production-neon-host>' \
  --expect-database '<intended-production-database>'
```

Optionally add `--expect-user '<expected-database-login>'`. The helper parses only
the **exported** DATABASE_URL with SQLAlchemy; it never loads dotenv, connects,
or migrates. It prints only driver, hostname, database, and database user, never
password, full URL, or connection query parameters. It requires the repository's
`postgresql+psycopg` driver and exits nonzero for missing, malformed, or mismatched
targets. Do not print the URL to diagnose a failure.

**A human must explicitly confirm that the printed hostname AND database are the
intended Sandcastle production Neon target.** A matching helper result only
compares supplied names; it does not establish that those names are production.
If target identity cannot be positively verified, STOP. Do not migrate.

## Apply only after human confirmation

After the operator has explicitly confirmed the target, run separately:

```sh
alembic upgrade head
alembic current
alembic heads
```

Confirm the resulting current revision matches the expected repository head.
Do not automatically retry failed migrations, stamp revisions, downgrade, or
continue after an error; investigate through a reviewed recovery plan.

## End the session

Remove the pulled file **before** closing this temporary terminal, on success or
failure. From `backend/`:

```sh
rm -f ../.env.production.local
exit
```

The file is Git-ignored and must never be committed or retained by default.
Closing the terminal ends the loaded production environment; never continue
normal development in it. If stopping earlier from repository root, remove
`.env.production.local` there before `exit`.

Flow: fresh terminal → verify backend Vercel link → pull current production env →
activate backend venv/load temporary env → inspect revisions → safe target
inspection → human confirmation → upgrade → verify head → remove file → exit.

References: [Vercel env CLI](https://vercel.com/docs/cli/env),
[Vercel link](https://vercel.com/docs/cli/link), and
[Secret environment variables](https://vercel.com/docs/environment-variables/sensitive-environment-variables).
