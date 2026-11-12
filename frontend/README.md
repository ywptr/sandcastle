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

## SC#0000 — AI Providers

Open **Settings → AI → My AI Providers** in the account header. These are account settings, independent
of the active Story and available even before the first series exists. Cards for
OpenAI, Anthropic, and Google Gemini show support, saved enabled state, credential
presence, and default model. No provider is called to display settings.

Enter a provider model ID and your own API key, enable the provider, and save.
The password input is not React state and is cleared on submission, including
failed submissions. Saved keys are never retrieved or stored in browser storage.
Leaving it blank preserves the existing server-side secret; removing a credential
requires an explicit confirmation and also disables that provider. Disabling alone
preserves its key. Removal does not revoke the original key at its provider.

**Advanced routing** (Difficult/Impossible Settings detail) selects Automatic/OpenAI/Anthropic/Google
for Creative writing, Story import, and Production planning. The current effective provider/model is
shown. Automatic follows a fixed order: OpenAI, Anthropic, Google, considering only
enabled providers with credentials and a configured model. Explicit bindings do
not fall back if disabled/unconfigured. No provider is retried or replaced after
an invocation fails. Settings disclosure follows Difficulty as described below; story creation needs no
provider/model selection. Story Import has an analysis-only entry from Home; full import review/persistence remains deferred.

The backend requires `SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY` for credential
writes/use; see [backend AI configuration](../backend/app/llm/README.md). Encryption
setup belongs on the backend. Do not put keys in Vite variables. Old OpenAI key/model
environment variables no longer enable Scene or Import generation.

`tests/providers.browser.mjs` is an optional Playwright fixture harness using the
same `PLAYWRIGHT_MODULE`, `WORKSPACE_ORIGIN`, and `WORKSPACE_SCREENSHOTS` conventions
as the M14 harness. It checks settings saves, secret omission/clearing, advanced
preferences, explicit removal, failures, studio return, and mobile overflow.

## SC#0001 — Scene Production

Open a saved Scene, then **Production · Webtoon / Short Drama / Story Reel**.
Choose a format and optional production direction, then prepare a plan using the
account's `narrative_media_translator` role. The Settings → AI advanced routing
preferences includes this role; no separate credential is needed.

Translation creates an ephemeral structured interpretation, never media or a new
Scene. Webtoon uses 1–12 ordered panels; Short Drama uses shots with camera,
performance, dialogue/audio and estimated durations; Story Reel uses readable
text/voice/visual beats and transitions. Totals are planning estimates. Cards allow
structured edits, reorder, add/remove viewpoints and valid Character/Place selections.

Easy initially shows a compact summary, count, identity/location and advisory warnings;
**Review plan** reveals editing. Normal opens structured review automatically.
Difficult makes detailed references/camera controls prominent and permits separately
labeled presentation overrides. Impossible also exposes the full structured plan
and provider-neutral manifest. No provider-native JSON is the primary authoring UI.

**Generation instructions** deterministically compiles current fields without another
model call. Edits invalidate its preview. Override text stays separate, and effective
instructions retain authoritative context. **Approve production plan** recompiles
on the server and stores an immutable snapshot. Approved history survives reload;
**Edit as new revision** edits a copy. Scene/context changes show stale warnings and
require a new adaptation. Narrative prose and Canon never change automatically.
Drafts do not survive Scene/workspace switches or reloads. Media execution remains
unavailable; no images/video are generated, displayed or copied by this milestone.

`tests/production.browser.mjs` uses the existing optional Playwright harness setup
(`PLAYWRIGHT_MODULE`, `WORKSPACE_ORIGIN`, `WORKSPACE_SCREENSHOTS`). It exercises all
three editors, loading/provider errors, timing totals, reorder, instruction inspection,
difficulty disclosure, overrides, approval/history/reload, stale-source warnings,
mobile overflow and normal Scene saves with isolated API fixtures. Screenshots are
fixture-based; they do not establish live IS/LLM acceptance.

## SC#0002 Settings

The account header opens Settings → General / AI / Account. AI has AI mode,
My AI Providers, and (at advanced detail) Advanced routing. These are personal,
account-wide credentials, never Story settings. Sandcastle Default is disabled
until trusted workspace AI exists; future Workspace Settings → AI stays separate.
Personal BYOK remains a permanent option.

Provider cards distinguish Supported, Connected (key saved, not live-verified),
Enabled, and Selected/Used for. Configure uses an empty password field; blank
submission retains a saved key. Submitting clears the secret input immediately.
Rotation replaces the key; removal requires confirmation and disables the provider.
No secrets are saved in browser storage or fetched back from the server.

Settings starts with the active Story Difficulty. General offers a temporary
Settings-only detail preference without changing Story Difficulty or routing.
Easy shows connection essentials, Normal adds task/provider summaries, Difficult
shows role routing and model preferences, and Impossible expands advanced controls.
Creative writing, Story import, and Production planning map to the existing three
semantic roles. Automatic chooses OpenAI → Anthropic → Google from eligible
personal providers before execution; there is no post-failure failover. Disabling
an explicitly bound provider makes affected tasks unavailable until corrected.

No tenant/platform credential source, live credential validation, full i18n, or
provider model catalog is implemented. Settings text is grouped for later UI
localization. Existing Scene production planning and authoring remain separate.

SC#0002 validation: frontend unit/API tests, lint, and production build pass.
The fixture browser harness `tests/providers.browser.mjs` covers all three role
preferences, Automatic, saved-key omission/rotation/removal, disabled routing,
secret clearing even on failure, all four detail levels, account navigation, and
320/390px overflow checks. Screenshots: `/tmp/sc0002-visuals/` (AI mode, provider
cards desktop/mobile, advanced routing). M14 and SC#0001 browser regressions also
pass against the established HTTPS frontend. Real IS sign-in entry/proxy/HMR were
checked; authenticated settings acceptance used fixtures, not live provider keys.

## SC#0004 Get Started and localization

Home asks what the creator wants to make, with Story, Webtoon Series, Short Drama
Series, and Story Reels Series. Enter an idea in any language, request one creative
recommendation, review the compact choices, then accept or Customize. No data is
persisted until approval. Easy makes starting decisions and asks for approval;
it does not merely hide fields. More story tools retains Canon, Places, Universe,
Assets, Workflow/Difficulty and authority history. Normal and higher show the full
workspace navigation; existing advanced capabilities and backend semantics remain.

Import an existing story is a prominent peer entry. It calls existing M12A analysis
and displays a read-only proposal summary/evidence. **It does not import or save
anything**. Full proposal review/application is deferred to SC#0005. Existing
structured Story creation remains accessible via Detailed story form.

If AI is unconfigured or fails, review clearly marked manual starting choices and
continue without connecting keys. No tenant/default AI is implied. Personal BYOK
Settings remains independent. Recommendation reuses `creative_writer`; it never
makes media calls or silently fails over. UI locale is never sent as Story language.

Customize has separate genre, Story language, rating and storytelling style, with
advanced secondary genres/tropes/culture/era/tone/visual controls. The searchable
style library is a native modal drawer (desktop) / full-width sheet (mobile), with
keyboard focus containment, Escape dismissal and focus return. Region only filters
styles. Details are text-only planning previews, not validated generated-media
examples. Approved Creative Direction stores the resolved style version/snapshot;
new approvals append revisions, preserving historical decisions.

The workspace Overview reads the approved snapshot and offers edits and a Create
adaptation entry to existing Scene → Production. All formats use the same Story.
There is no new Adaptation/Episode entity and no live IG/media execution. Approved
style is not yet automatically injected into writing or SC#0001 translation;
SC#0001's existing creative_direction extension remains ready for that follow-up.

### Interface language

`src/i18n/` is a small React context plus keyed English/Indonesian resources.
Precedence is explicit saved preference → English for new users. A saved Automatic
preference follows normalized browser language: `id-ID` becomes id, `en-GB` becomes
en, and unsupported primary browser languages use en. Automatic is now stored
explicitly as `auto` and follows browser languagechange. Existing `en`/`id` choices
are retained. Earlier Automatic selections removed the key, so they cannot be
distinguished from an absent preference; absent preferences now start in English.
Every missing translation falls back to English. `<html lang>` follows the UI.
Settings → General → Interface language offers Automatic, English and Indonesian.
Only the explicit locale is stored at `sandcastle.uiLocale` in localStorage; no
secrets or Story content are stored there. Storage denial still allows in-session
selection. This preference is device-local, not yet account-synced.

**UI language is independent of Story language.** Changing UI language never writes
Story metadata; selecting a style never changes Story/dialogue language, culture,
nationality or era. AI rationale/import evidence remain user-content in their source
language. Assistant request/response language semantics remain Story-driven.

Coverage includes Get Started, Import entry/status, recommendation/review/customize,
style library, creation/metadata forms, Series browser, account Settings navigation,
General/Account pages, workspace navigation/summary, and core assistant labels.
Existing deep Canon/Character/Place/Universe/Workflow/Guidance/Production editors,
advanced AI provider cards/routing, and backend error text remain partly English;
these are incremental localization gaps, not translated content guarantees.

Mobile layout uses one main creation region and a stacked Customize panel, tested
at 320/390px with Indonesian labels; native drawer focus and button wrapping remain
usable. Screenshots and acceptance harness: `/tmp/sc0004-visuals/` and
`tests/onboarding.browser.mjs`. Existing M14, provider Settings and production-plan
browser harnesses remain regression checks. All use fixture APIs for authenticated
editing; they do not make live billable/provider/media calls.


## Studio shell — Phase B1

The existing screens now share `components/studio/StudioShell.tsx`: a 68px branded
header, 206px persistent desktop sidebar, compact header UI-language selector and
an account menu with the existing Settings/sign-out actions. Below 951px, the same
navigation model renders inside a native modal drawer. At phone widths the header
is 61px. Keyboard focus wraps in both directions; Escape, close button, backdrop
and returning to desktop close the drawer and restore normal page interaction.
A skip link, current-page labels and visible focus styles support keyboard use.

`styles/studio-shell.css` defines the approved purple/white tokens and scoped shell
and shared-surface styles. The existing global stylesheet and feature layouts were
retained. A container query adapts the existing workspace when the shell or series
browser reduces its available width. Global navigation to Home, My Series, Story
Workspace, Characters, Story World (Canon), Library (existing asset metadata) and
Settings uses App's existing data; local Story tools still expose Scenes, Places,
Universe, Workflow/Difficulty and the authority log. Selecting a global destination
starts at the top of its content, beneath the sticky header. A selected Story is
required for its context-specific navigation entries.

Episode Editor, creative Templates, Export, Publish/Schedule, customer Billing and
Help are disabled and labeled as unavailable. Workflow templates remain accessible
in the existing Workflow controls. No mock quotas, purchases, media previews,
prototype styles, canned chat or domain localStorage state were added. The brand
uses locally authored SVG geometry; no embedded prototype illustration was reused.
No package, backend API, authentication or schema changes were needed.

Home, creation/import, Story Setup, new chat and Style Library redesigns remain
outside B1. The existing eight versioned presets, explicit creation/approval,
Canon review, provider settings, source evidence and production-plan behavior
remain authoritative. Language preferences follow the rules above; a UI-language
change never changes Story language or sends a generation request.

Validation: `npm test`, `npm run lint`, and `npm run build` (including TypeScript).
The B1 browser harness, alongside all existing browser suites, uses isolated API
fixtures for signed-in screens. Run with an externally supplied Playwright module:

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tests/studio-shell.browser.mjs
```

The B1 harness checks navigation, disabled/contextual destinations, skip link,
mobile keyboard/focus/close behavior, unsaved draft retention, responsive widths,
English default and saved language choices, unchanged Story language, and the
existing signed-out entry/IS authorize redirect. It does not complete live login.
See [B1 screenshot review](docs/design-reference/phase-b1-review/index.html) for
1440×900 and 390×844 before/after/reference captures and remaining differences.
