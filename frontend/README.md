# Local HTTPS development

Run the FastAPI backend on HTTP port 8012 and Vite with `npm run dev`.
From `backend/`, start the API with:

```sh
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload
```

The browser opens `https://5480-deb13.lan.com:5182`; Vite uses the existing mkcert
certificate/key in `/home/user/certs/sandcastle/`.

The hostname must resolve to `192.168.0.99` through your LAN DNS or client hosts
file, and the browser must trust this host's existing mkcert development CA.
Renew the certificate on the development host with:

```sh
mkcert -cert-file /home/user/certs/sandcastle/dev-cert.pem -key-file /home/user/certs/sandcastle/dev-key.pem 5480-deb13.lan.com localhost 192.168.0.99 127.0.0.1
```

Restart Vite after certificate renewal. Keep the private key and CA private key
off Git; only the CA certificate is needed for trust on another client.

Development API and login URLs are always relative to `/api`, even if an old
`VITE_API_BASE_URL` points at an HTTP backend. Vite proxies `/api/*` to
`http://127.0.0.1:8012/api/*` without rewriting the path or query string. Methods,
request cookies, and response Set-Cookie headers pass through; forwarded headers
preserve the browser-facing scheme. FastAPI owns `/api/auth/callback`.

Use these **local** settings (do not change production configuration):

```dotenv
# frontend/.env.local (optional in development)
VITE_API_BASE_URL=/api

# backend/.env
SANDCASTLE_AUTH_CALLBACK_URL=https://5480-deb13.lan.com:5182/api/auth/callback
SANDCASTLE_WEB_URL=https://5480-deb13.lan.com:5182
SANDCASTLE_COOKIE_SECURE=true
```

Restart/reload the backend after changing its environment. IS must permit the
exact callback URI above for the configured client; this repository does not
register or modify IS redirect URIs. Keep existing IS credentials private.

Session cookies remain HttpOnly, SameSite=Lax, and host-only. Secure is enabled
for this local HTTPS flow. No backend TLS or extra CORS allowance is needed.
`/api/auth/me` returning 401 is normal signed-out state; other HTTP failures and
network failures remain visible errors. Cookie credentials stay included.

Production builds still honor a nonempty `VITE_API_BASE_URL` when a separate API
origin is required, otherwise they default to `/api`. The existing production
Vercel rewrite is unchanged. Production builds do not read local TLS files.

```sh
npm test
npm run lint
npm run build
```

Tests use Node's built-in runner and Vite's TS/env transform; no new test
framework or browser dependency is required.


## M14 workspace

“Series” is presentation wording for the existing Story domain. Select a card in
**Browse series** to enter its workspace. The browser closes to give the editor
more room; reopen it to switch projects or create a series. Creation requires
only a title. Premise, language, and primary genre are prominent; objective and
secondary genres are secondary controls.

The old anchor navigation and stacked panels are replaced by local section state
(no router dependency): Overview, Scenes, Characters, Places, Canon, Universe,
Assets, Workflow & Difficulty, and Authority log. The navigation also keeps an
ordered scene outline visible. Selecting a scene opens its persistent content;
there is no new Episode model.

Desktop uses navigation / assistant / selected editor regions. The editor gets
more width than the assistant. **Focus editor** collapses the assistant. The
Series browser can be collapsed independently. Tablet and narrower desktop
windows use navigation plus assistant/editor stacked in the second region.
Mobile has a single primary region with Assistant, Outline (Story details), and
Scenes mode buttons. **Story tools** expands the full section menu; every section
remains reachable in Easy mode. Browse series and account controls remain in the
header. No separate billing Plan or Profile product has been created.

### Editing and actions

- Overview → **Edit details** edits title, premise, objective, language, primary
  genre, and secondary genres. “Not set” sends null for language/primary genre;
  unchecking all secondary genres sends `[]`. Empty premise/objective sends null.
  Language guides generated prose and suggestions and remains saved per Story.
- Taxonomy is centralized in `src/api/storyMetadata.ts`, mirroring M13. Tests
  compare it against `backend/app/stories/metadata.py`. Secondary genres are unique,
  exclude the primary genre, and are limited to three. No metadata endpoint exists
  to fetch this bounded vocabulary dynamically.
- Characters and Places show a list and one selected detail/editor with every
  existing persisted field. Newly created records become selected.
- Scenes show ordered selection, readable prose, direct editing, and manual
  creation. The assistant can suggest a next direction and generate a scene.
  Selecting a suggestion only fills an editable prompt. Generation respects the
  saved workflow and uses existing authority evaluation. It never approves Canon.
- Canon displays approved and superseded facts plus candidate review. Evidence,
  classification, reasoning, explicit conflict replacement, and uncertain proposal
  acceptance remain visible. Rejected/approved candidates can be inspected using
  the status filter. Extraction targets the selected scene (latest by default).
- Universe is read-only: Story membership and pinned Canon versions/data. It uses
  existing Universe and Canon-library reads; no membership mutations or new
  collaboration/tenant semantics are introduced.
- Assets lists registered media and saved reference bindings. Existing workflow
  reference ID controls are reachable from this section. Upload, registration,
  binding creation/deletion, and artifact refinement have no new UI here.
- Workflow & Difficulty retains existing configuration and preview operations.
  Easy keeps Standard and the difficulty selection prominent; Normal, Difficult,
  and Impossible progressively reveal controls using backend capability lists.
  Template descriptions and available capabilities are inspectable. Saving
  configuration does not execute a workflow. Difficulty is unrelated to billing.
- Authority log displays existing action decisions separately from story content.

Errors in Characters, Places, Canon, Scenes, Workflow, or the Authority log are
reported without blanking other sections. Retry reloads the reads; independent
optional sections also offer retry. Forms keep entered values after failed saves
and disable submission while saving. Saves and cancellation exit edit mode.
Unsaved editor drafts are local and do not survive section/project switches or
reloads. There is no autosave or persistent assistant chat history.

Native buttons, labeled forms/selects, fieldsets, status/error announcements,
visible focus indicators, current-section/record semantics, and 44px action
controls support keyboard and mobile use. Browser checks cover 320–1440px widths.

### Backend-driven limits and deferred mockup elements

No backend/schema, IS callback, IG execution, Axtor, or persistence changes are
part of M14. There is no general-purpose assistant endpoint; the assistant only
performs existing Guidance and Scene generation operations. Character-development
chat, export, distribution, credits, billing, allowances, publishing, Import Story
UI, a graph editor, persistent Episodes, and multi-LLM work remain deferred.
Versioned Canon library promotion/fork/version management and Universe editing
also remain API-only. Universe reads currently enumerate accessible Universes
and their memberships because there is no Story-specific membership endpoint.
A failed Universe dependency shows a local retry rather than affecting the Story.
The workspace does not provide drag-to-resize split regions.

### Validation and visual review

Run `npm test`, `npm run lint`, and `npm run build` from this directory.
The API test file covers auth/proxy behavior, workflow capability disclosure,
M13 metadata clearing and vocabulary parity, authenticated context reads, and
explicit candidate-review payloads.

An optional Playwright browser harness is included without adding an application
or test dependency. Supply an existing Playwright installation, for example:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs node tests/workspace.browser.mjs
```

`WORKSPACE_ORIGIN` defaults to `https://192.168.0.99:5182`;
`WORKSPACE_SCREENSHOTS` defaults to `/tmp/m14-visuals`. Chromium must be installed
for that Playwright installation; supply its required system libraries as needed.
The harness first checks the real signed-out screen and login redirect, then
intercepts API requests with isolated fixtures. It does not write development
Story data or prove live persistence. It exercises creation/switching, metadata,
Character/Place/Canon/Scene saves, conflict approval, generation, guidance,
Workflow/Difficulty, Universe/assets reads, mobile editing, partial-failure retry,
and horizontal overflow at 320, 390, 768, 1024, and 1440px.

M14 validation: all three required commands passed, lint without warnings.
The existing HTTPS server rendered the signed-out screen, returned expected
401 for `/api/auth/me`, redirected login to IS authorization (307), and connected
the Vite WebSocket. Authenticated IS completion and live backend saves remain
unverified because the browser had no authenticated session. No callback or
proxy configuration was changed. A full live HMR edit/revert was not exercised.
Backend tests were not run because backend files were unchanged.

Screenshots were captured under `/tmp/m14-visuals`: `series.png`, `desktop.png`,
`canon.png`, `scenes.png`, `workflow.png`, `mobile.png`, `mobile-editor.png`,
`sign-in.png`, and `partial-failure.png`. Authenticated screenshots use clearly
fictional fixtures, not live saved data. Visual review confirms warm neutral
surfaces, restrained purple accents, persistent desktop navigation, a larger
context editor, prominent creative actions, and single-region mobile content.
The referenced mockup image/PDF was unavailable in this session, so comparison
uses the written approved principles rather than direct mockup inspection.

Recommended follow-up: authenticated acceptance testing with a real IS session,
review against the supplied mockup files, then a separately scoped bounded
assistant-interaction milestone. M14 does not start M16 or multi-LLM work.
