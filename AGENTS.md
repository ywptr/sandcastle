# Repository Guidelines

## Project Structure & Module Organization

Sandcastle manages structured story canon with a FastAPI backend and a React/TypeScript frontend.

- `backend/app/api/`: HTTP routes and dependencies.
- `backend/app/stories/`, `canon/`, `auth/`, and `authority/`: domain services, schemas, ports, and adapters.
- `backend/app/db/models/`: SQLAlchemy models; `backend/alembic/versions/`: database migrations.
- `frontend/src/components/`: story workspace UI; `frontend/src/api/sandcastle.ts`: API client and types.
- `frontend/src/assets/` and `frontend/public/`: bundled and public assets.
- `README.md`: product goals and planned workflows; verify implementation before assuming roadmap features exist.

## Build, Test, and Development Commands

Run backend commands from `backend/`, using Python 3.12+ and an activated virtual environment:

- `python -m pip install -e .`: install backend dependencies.
- `alembic upgrade head`: apply migrations to the configured development database.
- `uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload`: start the API locally on port 8012.

Run frontend commands from `frontend/`:

- `npm install`: install dependencies.
- `npm run dev`: start Vite, normally on port 5182.
- `npm run build`: type-check TypeScript and generate production assets.
- `npm run lint`: run Oxlint, including React Hooks rules.
- `npm run preview`: serve the production build locally.

## Coding Style & Naming Conventions

Use four-space indentation and `snake_case` for Python functions and modules; use `PascalCase` for classes. Use `PascalCase.tsx` for React components and `camelCase` for TypeScript functions. Existing application code generally uses double quotes and semicolons in TypeScript; match surrounding indentation. Keep routes thin and domain logic in services. No dedicated formatter is configured.

## Testing Guidelines

Backend automated tests live under `backend/tests/`. Run the backend test suite for affected backend changes, including migration tests where schema changes are involved.

Run frontend lint and production build checks for frontend changes.

For authentication, persistence, ownership, and external-service integrations, also perform targeted manual smoke tests when practical.

Document validation performed in pull requests.

## Commit & Pull Request Guidelines

History uses short, plain-language subjects such as “Add canon extractor backend”; follow that style. Keep commits focused. Pull requests should describe behavior changes, link related issues when applicable, list validation performed, and include screenshots for UI changes. Call out migrations and configuration changes.

## Security & Configuration

Keep secrets in ignored `.env` files. Configure `DATABASE_URL` and authentication variables defined in `backend/app/auth/config.py`.

Local development may use http://localhost:8012/api.
Production should use same-origin /api via the Sandcastle GUI Vercel rewrite to the API project.

Never place credentials in frontend environment variables.

## Architecture and Product Boundaries

- Sandcastle owns story, canon, continuity, scenes, characters, places, webtoon planning, and the creative authoring workflow.
- IS is the identity provider. Do not create a separate password or user system in Sandcastle.
- IG is the media-generation and control-plane service. Call IG through its API; do not import IG internals, access its database, or modify its repository from Sandcastle work.
- Axtor is the eventual authority boundary between proposed action and execution. Preserve the existing authority abstraction; do not build the full Axtor product inside Sandcastle V0.
- If another application needs a change, report the required external change and stop at the application boundary.
- Sandcastle is story-first, medium-second. Webtoon is the first output format; future outputs include short drama and short video. Story continuity is the product; media generation is an output capability.
- With IG's help, Sandcastle aims to produce webtoons and short videos that can later be published independently or through the Sociosight application.
- Scenes are editable narrative content. Canon is authoritative structured continuity. Scene edits must not silently mutate canon.
- Prefer guided authoring plus agentic input. Translate natural-language requests into bounded structured operations; the model must not directly manipulate the database.
- Keep AI provider and model selection abstract enough for multiple providers and future fallback, compare, best-of-N, ensemble, and role-based model strategies.
- Do not introduce LangGraph or n8n in V0 unless a real workflow requirement appears.
- Prefer complete vertical slices: model, migration, service, API, frontend, and validation.
- Treat the repository as source of truth; design notes and README roadmap items may be ahead of implementation.

## Production Alembic operations

Production Alembic updates must use the documented fresh-terminal Vercel
production-env procedure in [backend/PRODUCTION_MIGRATIONS.md](backend/PRODUCTION_MIGRATIONS.md).
Require explicit non-secret database-target verification before `alembic upgrade head`.
This is the default for all future migrations. Never silently migrate production
as implementation acceptance; validate development changes only in `sandcastle_dev`.

## Beginner experience and language

UI language is independent of Story language. Changing one must never silently
change the other. Easy mode makes decisions and asks for approval; it does not
merely hide advanced fields. Keep deeper tools reachable through progressive disclosure.
