# SC#0001 — Narrative-to-Media Translation

Sandcastle interprets a narrative for a medium. IG will execute separately approved
media requests. This layer produces structured, editable production proposals;
it makes no image/video generation, IG, storage, or authority-service call.

## Domain boundary and existing planners

`NarrativeMediaTranslator.translate(NarrativeMediaContext)` returns a typed
`ProductionProposal`. `MediaProductionPlan` is the common review envelope. The name
avoids colliding with M9C's existing `MediaAdaptationPlan`, which remains an ephemeral,
deterministic audience/sensitivity treatment. Both are distinct from media execution.

M3's existing visual-context selection, effective approved Canon, subject identity,
reference resolution and provider-neutral MediaPlan/MediaRequest DTOs are reused.
M4A remains a separate deterministic **four-panel quick plan**, including its API
and M9C treatment path. It is not represented as equivalent to semantic translation.
There is no automatic deterministic substitute when this new LLM role is unavailable;
manual authoring and the existing quick-plan API remain usable. Existing M4B behavior
is unchanged. No Episode, tenant, provider credential, or workflow engine is added.

## Context and provider routing

`NarrativeMediaContext` contains the current owned Scene; Story title, premise,
objective, language and genres; effective approved Canon; full selected Character
and Place data; audience/maturity/guidance; saved/default workflow and difficulty;
and owner-authorized applicable Artifact/reference bindings. Existing workflow
reference selections are honored. Optional direction is bounded to 1,000 characters.
Scene content is limited to 40,000 characters and creative context to 160,000
characters; oversized context fails clearly instead of silently dropping Canon.

A reserved in-process `creative_direction` context extension allows future typed
storytelling/visual/cultural/era/tone direction without changing provider adapters.
No Creative Direction API, Bible, style library or Wizard is implemented now.

The new bounded SC#0000 role is `narrative_media_translator`. It uses the same encrypted
user configuration, deterministic selection and explicit role binding as writing and
Import. The existing provider CLI still configures reusable provider credentials;
role preference is set through the existing role API/UI. There is no new credential
or environment variable. A missing usable provider returns 503; invocation/schema
failure returns sanitized 502, persists no draft, and never triggers provider fallback.

OpenAI uses its existing Responses structured-output SDK pattern; Anthropic and
Google reuse SC#0000's fixed-endpoint HTTP transport, credential attachment, timeout,
refusal/truncation handling and credential-echo guard. Each requested format has a
specific Pydantic output schema, reducing unnecessary union complexity in provider
requests. One complete proposal uses one text-model request (16,000 output-token
ceiling), with zero automatic retries. There are no per-beat model calls or tools.

The trusted translator instructions and JSON narrative-data envelope are separate
messages. Prose, metadata, guidance and optional direction cannot become trusted
system instructions. Adapters validate typed outputs, and the service independently
revalidates the schema, requested format, exact source excerpts, and IDs. Exact
excerpts establish source grounding, not proof that a model correctly understood
causality or continuity. Human review remains required; no semantic quality or
prompt-injection immunity is claimed.

Dialogue, captions, voiceover and on-screen text normally retain Story language.
Unset/undetermined language retains the source language. Explicit user direction
may request a different presentation language. Technical instructions may be English.
Genre can influence pacing/framing but never changes Canon. Audience/maturity
constraints favor appropriate presentation without rewriting the narrative source.

## Format-specific plans

Every plan carries UUID `plan_id`, Story/Scene IDs, bounded target format, summary,
source/context digests, immutable-to-the-reviewer continuity context, warnings,
continuity notes, separate overrides, compiler version, derived instructions, and
creation timestamp. Ordered beats live in the appropriate format body:

| Format | Structure and initial bounds |
| --- | --- |
| `webtoon` | 1–12 ordered panels; reading order and layout hint |
| `short_drama` | 1–24 shots; each 1–30 seconds; total at most 120 seconds; overall audio direction |
| `story_reel` | 1–20 beats; each 1–15 seconds; total at most 90 seconds; narration/text and visual strategies |

Bounds keep review/output manageable; 20–60 seconds is a translation preference
when supported by the source, not a forced duration. Totals must equal estimated
beat durations. All timing is a production estimate, never frame-accurate or a
promise that a future execution provider supports that duration.

Each visual unit includes narrative purpose, exact source excerpt, visual description,
known Character/Place IDs, selected Artifact IDs and continuity notes. Webtoon adds
framing/dialogue/caption. Drama adds shot scale, camera/performance, dialogue,
voiceover and audio/ambience. Reel adds on-screen text, voiceover and transition.
Reel is independently modeled, not a renamed drama shot. Consecutive numbering,
bounded arrays/strings, strict positive integer durations, matching target format,
and unique/available reference IDs are enforced again for client-edited plans.

Warnings cover missing visual information, ambiguous presence/location, dense timing,
excess dialogue, unsupported action and continuity uncertainty. Model warnings survive
review/approval; server warnings are added for missing appearance/location and pending
conflicting/uncertain Canon proposals. They are advisory. Approval never resolves
Canon candidates or rewrites a Scene. No automatic semantic contradiction detector
or comprehensive narrative-coverage proof is introduced.

## Source integrity and lifecycle

`source_digest` is SHA-256 of compact sorted UTF-8 JSON with the Scene's exact
`content` and nullable `title`. Whitespace changes count. `context_digest` covers the
captured creative/Canon/reference/guidance/workflow-configuration snapshot. It does
not include the user's credential or provider selection. These are content digests,
not a new general Scene revision/archive system. The original full prose is not
separately archived by this subsystem.

Lifecycle:

```text
one text translation → ephemeral draft → structured edits → compile/review
→ explicit approval → immutable approved snapshot + manifest
```

Compile is deterministic and makes no model call. Drafts/review operations write no
rows. Draft approval fails with 409 if source/context has changed; create a new
adaptation instead. History remains readable, returns stored snapshots, and separately
flags Scene/context changes. A new translation never overwrites an approval.

`approved_media_adaptations` stores owner, Story/Scene, format/revision, plan UUID,
source/context/snapshot digests, typed plan JSON, compiled manifest JSON, compiler
version, approval and creation timestamps. It stores no media bytes. Revisions are
numbered per Scene/format under Story/Scene locks. Identical approval replay returns
the existing record. Editing/reapproving creates a new row; there is no update/delete
API for historical snapshots. Snapshot plus manifest commit atomically, with safe
rollback and conflict handling. The execution meaning of an old approval is never
reconstructed from changed authoring state or a future compiler version.

Migration `9e51b7c3d021` follows `8d40f6a2c910`, adds the snapshot table and expands
the role constraint. It preserves existing provider role settings. Downgrade requires
explicit removal of new translator role bindings first. As with any table-dropping
downgrade, retain backups of approved snapshots before an operational reversal.

## Compiler and overrides

`production-v1` compiles each reviewed beat into provider-neutral instructions:
moment/purpose, visuals, framing or camera/performance, timings, exact reviewed
speech/text, selected Character/Place context, approved Canon, continuity notes,
audience/language constraints, metadata-only reference IDs, and exclusions.
The model never supplies trusted compiler output. Compile/approval ignore submitted
compiled text and rebuild it from validated structure and authoritative context.

Overrides are indexed by beat and stored separately. Difficult/Impossible may add
an explicit presentation override; Easy/Normal requests containing overrides are
rejected. The original compiler output remains inspectable, and effective overridden
instructions still append authoritative Character/Place/Canon/audience context.
An override cannot mutate those records or remove the structured source. Future
execution must continue respecting that authority boundary; appended text alone is
not a technical guarantee of another model's compliance.

## Media manifest and future M16

Compilation creates a normal M3 MediaPlan with one MediaRequest per unit, preserving
references and production association. Webtoon uses `image`/`comic_panel`; Drama and
Reel use `video`/`video_scene`. MediaContext gains optional production format, beat
number and estimated duration fields. Webtoon retains the workflow's aspect ratio;
video planning uses vertical 9:16. IDs are deterministic for a compiled draft and
stable inside an approved snapshot. No execution client is invoked.

This is an execution-ready semantic input, not a claim of current live compatibility:
M4B persistence still supports exactly four image panels, its results remain
`ExecutionResult.images`, and the IG adapter remains live-disabled. A future M16
handoff must generalize approval/attempt association for variable units, validate
video/media capabilities and timings, resolve authorized local→IG Artifact IDs,
and establish service caller/actor/tenant authentication. It must consume the stored
manifest instead of translating narrative again. No existing four-panel execution
path is bypassed or repurposed here.

## Artifact authority rule

**Generated media through IG: IG owns bytes/storage. Sandcastle stores semantic
references and associations.** IG remains the authoritative media artifact store
for media generated through IG. Sandcastle must not persist duplicate media bytes
merely to display or associate generated output.

The existing Artifact table remains metadata-only, with optional real IG
`external_artifact_id`, Story/Scene ownership and bindings/lineage. Production plans
refer to owner-authorized local Artifact IDs, roles and bindings; they do not fetch
content, expose storage locators, guess IG IDs, or copy an IG Blob into Sandcastle
storage. Future output association should retain the approved plan/revision and IG
artifact identity. Any future portability/offline copy requires an explicit separate
product/architecture decision.

## API

All endpoints require the existing IS-derived session. Story/Scene ownership is
checked before selecting a provider. Another user's Story or approval returns 404.

| Method | Route (prefix `/api`) | Result |
| --- | --- | --- |
| POST | `/stories/{story_id}/scenes/{scene_id}/adaptations` | Ephemeral draft from `{target_format, instruction?}` |
| POST | `.../adaptations/compile` | Revalidated plan and provider-neutral manifest from `{plan}`; no LLM |
| POST | `.../adaptations/approve` | Immutable approval from `{approved: true, plan}` |
| GET | `.../adaptations` | Approved Scene history with stale flags |
| GET | `/media/adaptations/{adaptation_id}` | Owned stored snapshot and manifest |

No request-time provider/model option, raw provider JSON, IG operation, bytes upload,
or Episode endpoint is added. Translation/review responses use no-store. Validation
and transport failures leave narrative/domain state untouched.

## Scene UI and difficulty

Open Scenes → **Production · Webtoon / Short Drama / Story Reel**. Choose a format,
optionally describe production direction, and prepare a draft. The normal Scene
editor remains separate and unchanged. Production history loads only when opened.

- Easy: compact summary/count/characters/location/warnings, Review plan and Approve.
  Review exposes editable structure; capability is simplified, not removed.
- Normal: structured review opens automatically, including timings, dialogue,
  descriptions, framing, reorder/add/remove viewpoints and identity/source details.
- Difficult: detailed identity/reference/camera controls are prominent and explicit
  presentation overrides become available. Compiler inspection remains a separate
  action, never an extra translation call.
- Impossible: also inspect the full structured plan and raw provider-neutral manifest.
  This is not provider-native API JSON or the future AI Settings redesign.

Edits invalidate instruction previews. **Generation instructions** recompiles;
approval independently recompiles on the server. Reorder/remove preserves overrides
with the associated unit. Approved snapshots are read-only; **Edit as new revision**
creates a review copy. Source changes show a stale warning and disable approval of
the old draft. History survives reload and indicates changes independently. Draft
edits are local and disappear on workspace/Scene switch or reload; there is no draft
autosave. History initially loads all approved plans for the Scene (no pagination).

## Validation and limits

`test_production.py`, `test_production_adapters.py`, and
`test_production_migrations.py` cover authentication/ownership, all formats, context,
routing, provider failure, output/schema/evidence/ID validation, no story/Canon/media
mutation, metadata-only references, compiler determinism, override gating, approval
replay/revisions/rollback, stale flags and migration preservation. Tests use fake
credentials/transports. No live provider, media generation or IG calls are required.

`frontend/tests/production.browser.mjs` uses the existing optional Playwright harness
conventions. API fixtures exercise all editors, loading/errors, timing totals,
reordering, compiler inspection, difficulty disclosure, overrides, approval/reload,
history/staleness, mobile layout and ordinary Scene saves. Authenticated fixture
screenshots are not evidence of real IS/provider integration.


Subject-bound references include a metadata-only projection of binding ID, Artifact ID,
target type/ID and role, including pinned Canon visual bindings. The translator can
associate a reference with the correct identity instead of guessing from an opaque
binding ID. Review rejects a selected subject-bound Artifact when its target is not
in that beat (explicit unbound workflow references remain general references).
No arbitrary Artifact metadata, retrieval locator or content enters this projection.
Google translation explicitly requests only TEXT response modality; see the
[official generateContent reference](https://ai.google.dev/api/generate-content).
Historical approved instructions remain inspectable even when the source is stale.

## SC#0001 change inventory

The pre-existing SC#0000 working-tree changes were preserved. This milestone adds or
extends the following files:

- `README.md`
- `backend/DEVELOPMENT.md`
- `backend/README.md`
- `backend/alembic/versions/9e51b7c3d021_media_production.py`
- `backend/app/api/production.py`
- `backend/app/artifacts/README.md`
- `backend/app/db/models/__init__.py`
- `backend/app/db/models/llm.py`
- `backend/app/db/models/media_production.py`
- `backend/app/llm/README.md`
- `backend/app/llm/resolver.py`
- `backend/app/llm/schemas.py`
- `backend/app/main.py`
- `backend/app/media/EXECUTION.md`
- `backend/app/media/production/README.md`
- `backend/app/media/production/__init__.py`
- `backend/app/media/production/adapters/__init__.py`
- `backend/app/media/production/adapters/anthropic.py`
- `backend/app/media/production/adapters/google.py`
- `backend/app/media/production/adapters/openai.py`
- `backend/app/media/production/compiler.py`
- `backend/app/media/production/prompts.py`
- `backend/app/media/production/schemas.py`
- `backend/app/media/production/service.py`
- `backend/app/media/production/translator.py`
- `backend/app/media/schemas.py`
- `backend/tests/test_llm_migrations.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_production.py`
- `backend/tests/test_production_adapters.py`
- `backend/tests/test_production_migrations.py`
- `backend/tests/test_story_metadata_migrations.py`
- `frontend/README.md`
- `frontend/src/App.css`
- `frontend/src/api/production.ts`
- `frontend/src/api/productionEditing.ts`
- `frontend/src/api/sandcastle.ts`
- `frontend/src/components/AIProviderSettings.tsx`
- `frontend/src/components/ProductionWorkspace.tsx`
- `frontend/src/components/ScenePanel.tsx`
- `frontend/src/components/StoryWorkspace.tsx`
- `frontend/tests/api.test.mjs`
- `frontend/tests/production.browser.mjs`
- `frontend/tests/providers.browser.mjs`

## Observed completion validation

- Focused production suites: 19 tests passed.
- Full backend suite: 172 tests ran successfully, with one expected opt-in skip.
- Separate verified PostgreSQL fresh-schema bootstrap: both tests passed.
- Existing `sandcastle_dev`: heads/current/upgrade/current/check passed at
  `9e51b7c3d021`, with no drift.
- Disposable real-PostgreSQL persistence smoke: all formats, explicit approval,
  replay, reload, new revisions and stale flags passed using a fake text translator;
  all synthetic data was removed.
- Frontend tests, lint without warnings and production build passed.
- Production browser harness plus existing M14/SC#0000 browser regressions passed.
  Production captures are `/tmp/sc0001-visuals/webtoon-review.png`, `short_drama.png`,
  `story_reel.png`, `stale-history.png`, and `mobile-production.png`.
- Whitespace and changed-file secret-literal checks passed. No real provider key,
  encryption configuration, production/Preview/Neon, IG or IS settings were changed.

Full authenticated IS + real BYOK translation acceptance remains unverified because
no signed-in session or approved development provider credential was supplied.
Browser acceptance uses isolated API fixtures; it does not establish live model
interpretation quality. No billable LLM call, image/video generation, media content
read/copy or IG request was performed during validation.
