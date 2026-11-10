# M10 — Workflow templates and difficulty

```text
Difficulty → capability exposure
Versioned Workflow Template → curated configuration
Story Workflow → pinned template + validated Story configuration
Explicit action → existing Sandcastle domain service
```

Difficulty is **not subscription**. It does not represent quotas, storage,
commercial access, billing or execution permission from Axtor. No payment or
subscription data is introduced.

## Capability contract and UI

`registry.py` owns the monotonic capability mapping used by backend validation
and frontend disclosure:

| Level | Added controls |
| --- | --- |
| Easy | Curated Standard v1, audience, suggestions, simple workflow summary |
| Normal | Template choice, audience/maturity/tone/genre, guidance count/history, Canon checkpoints, media framing, structured world editors |
| Difficult | Supported step enable/disable and ordering; additive sensitivity hints |
| Impossible | All preceding controls plus explicit Character/Place/Artifact selections |

The Story workspace uses one flow, not four applications. Easy hides advanced
world/configuration surfaces; it still exposes explicit continuity checking and
Canon proposal review. Normal reveals selected controls. Difficult/Impossible
use a vertical step list, never a node graph. Impossible does not expose a way to
disable audience constraints, add executable code, or turn on live IG execution.
Changing difficulty/template resets **draft** settings to template defaults; Save
is required. It does not erase narrative data or automatically run any step.

## Curated built-ins and version pins

Four code-defined built-ins initially ship at v1:

- **Standard Story**: balanced, user-led process; optional media planning.
- **Guided Story**: five recent Scenes of suggestion context rather than four.
- **Canon Strict**: pending new/conflicting/uncertain facts require review before
  workflow media planning.
- **Webtoon**: webtoon adaptation context, 3:4 panel framing, four-panel planning.

Only Standard is selectable in Easy. Other templates require Normal or above.
Version identity is `(workflow_template_id, template_version)`. Retain shipped
versions unchanged; publish a new entry to update a template. Existing saved
Stories retain their version **and full configuration snapshot** until explicitly
changed. Existing unsaved Stories lazily resolve Standard v1, not a moving
"latest" alias. No backfill or synthetic workflow records are needed.

`StoryWorkflow` persists one Story FK/PK, template ID/version, difficulty, typed
configuration serialized as JSON, and timestamps. Built-ins do not need database
rows. New and legacy Stories have usable defaults before any workflow save.

## Supported structure and validation

Supported steps are narrative guidance, Scene creation, Canon extraction, Canon
review, continuity checking, media adaptation, storyboard planning and a deferred
media-execution entry. Scene creation is required. Media execution is unavailable
and cannot be enabled. Unknown steps, arbitrary JSON keys, custom code/provider
fields, duplicate steps/order entries and invalid values are rejected.

All steps appear once in the process order, including disabled entries. Enabled
steps obey dependencies: guidance precedes Scene creation; creation precedes
extraction/adaptation; extraction precedes review; continuity checking precedes
adaptation; adaptation precedes storyboard planning. A required review checkpoint
also places review before adaptation. Storyboard requires adaptation enabled.
A checkpoint requires review and continuity steps enabled. Disabled independent
steps may be moved without creating execution behavior.

Configuration is deliberately limited to implemented capabilities:

- Guidance: 1–5 alternatives and 1–5 recent Scenes, forwarded to M9B.
- Review: pause before media for selected pending classifications; no automatic
  Canon approval. Conflict classification is unchanged at every difficulty.
- Media: existing aspect-ratio validation and image/webtoon format hints. Panel
  count remains exactly four; video and provider selection are unavailable.
- Adaptation: additive M9C sensitivity hints only, never a safeguard bypass.
- References: existing M3/M6 stable Character/Place/Artifact selections. Domain
  services validate availability and ownership when used.

## Service integration and explicit actions

`perform_step` delegates one user-requested action to existing services. It is not
a workflow-run engine, scheduler, event listener or arbitrary DAG executor. Order
is validated orchestration intent, not proof that a user has completed previous
steps. Native domain prerequisites (saved Scene, ownership, etc.) remain required.
Scene creation continues through the existing manual editor/Generate action;
workflow actions cannot automatically create Scenes.

M7 extraction/review/reporting, M8/M9A effective Canon, M9B suggestion generation,
and M9C adaptation retain authority over their own behavior. Canon checkpoints
refresh M7's pending classifications before workflow media previews. Selected
classes with pending proposals return 409. Review is explicit, transactional and
uses the existing M7 approval/rejection endpoints. Conflicts require replacement
consent; uncertain approval requires separate consent. Existing subject resolution
and M8 fork requirements remain in force; this UI does not add a library/fork editor.

Workflow storyboard actions always adapt through M9C before calling M4A. They do
not use the raw legacy storyboard path or call IG. Original domain APIs remain
available for compatibility; difficulty is a configuration/UX contract, not a new
authorization or billing layer over every pre-existing endpoint. Workflow-specific
checkpoint enforcement applies to workflow actions.

## Authenticated API

| Method | Route | Contract |
| --- | --- | --- |
| GET | `/api/workflows/difficulties` | Levels and capability lists |
| GET | `/api/workflows/templates` | Built-in versioned templates |
| GET | `/api/workflows/templates/{id}?version=1` | Explicit version |
| GET | `/api/stories/{id}/workflow` | Effective saved/default workflow, definitions and capabilities |
| PUT | `/api/stories/{id}/workflow` | `{difficulty, workflow_template_id, template_version, configuration?}` |
| POST | `/api/stories/{id}/workflow/steps/{step_id}` | Explicit action with optional `{scene_id}` |

Omitting configuration in PUT resets to the selected template's defaults. Access
to another user's Story returns 404. Template catalogues require authentication.
Unavailable/disabled steps or unresolved checkpoints return 409; invalid structure
returns 422. Selecting/saving a workflow never performs domain/media actions.

## Migration and verification

`f15d7b92a640` adds only `story_workflows` after `e04c8a12b763`. Story, Scene,
Canon/candidate, Universe, Artifact and version rows are untouched. Downgrade
removes workflow configuration only; export it first if needed. Automated tests
exercise upgrade/downgrade, model drift, PostgreSQL offline SQL, and preservation
of existing narrative/Canon/Universe data.

Run `python -B -m unittest discover -s tests -p test_workflows.py -v` and the full
backend suite. Frontend tests cover capability disclosure and authenticated API
routing; lint/build cover the workspace integration. No live provider is required.

Custom executable nodes, plugins, marketplace/team templates, a graph runner,
LangGraph/n8n, subscription gating, Axtor policy nodes, IG execution and video are
future work. M10 does not begin M11 or deploy anything.

M13 narrative-guidance actions receive current [Story language/genre](../stories/README.md)
through the shared guidance service; templates and selection behavior are unchanged.
