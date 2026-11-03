# Media Orchestrator (M3)

```text
Story / Canon / Scene semantics (Sandcastle)
    -> Media Orchestrator
    -> provider-neutral MediaRequest / MediaPlan
    -> future IG/control-plane API client
```

Sandcastle owns story and canon semantics. The orchestrator reads existing M1/M2
objects and translates selected context into a visual instruction, stable
references, framing, and provenance. IG/control-plane owns execution and provider
infrastructure. It does not need to interpret Story, Canon, Character, Outfit,
Place, or Scene objects: the instruction contains the depiction details. A future
API client will resolve visual inputs and map the request to the execution API.

**M3 performs no actual media generation.** It makes no provider/API calls,
changes no authoring data, evaluates no continuity, and never promotes prose to
Canon. It introduces no persistence, migration, storage, queue, or workflow engine.

## DTOs and service

- `MediaType`: image and video. Scene-image and four-panel image planning are
  implemented; video remains vocabulary only.
- `MediaPurpose`: semantic intent, including scene, reference, cover, comic panel,
  and video scene. Other purposes reserve vocabulary, not executable workflows.
- `Reference`: a `(kind, reference_id)` pair. Character and Place use their existing
  IDs. Outfit uses its owning Character ID because M2 stores outfit on Character.
  Generated/uploaded artifact IDs are opaque; there are no URLs or storage details.
- `MediaRequest`: request ID, media type, purpose, prompt, Story/Scene IDs,
  references, optional aspect ratio, provenance context, and creation timestamp.
- `MediaPlan`: an ordered, nonempty collection of requests for one Story.

`create_scene_image_request(db, story_id=..., scene_id=..., user_id=..., options=...)`
checks Story ownership, scopes the Scene and selected world references to that
Story, and compiles its current saved content. It selects approved Canon only;
continuity evaluation and Canon mutation belong outside this layer.

M2 has no Scene/Character/Place associations. Omitted `character_ids` or `place_ids`
therefore select all of that Story's corresponding objects. Explicit lists select
subsets; `[]` selects none. Selection does not infer who appears in prose. Canon
currently includes all approved facts for the Story, without semantic filtering.

Artifact references are deduplicated and sorted. No artifact existence, access,
storage, or lineage is resolved in M3. A future resolver/execution client must
validate artifact access before reading any visual input. Outfit references track
the current Character outfit, not an immutable outfit revision.

## Authenticated API

Both endpoints require the existing IS-derived Sandcastle session and return 200.
Missing/inaccessible Stories or references return 404; malformed intent or empty
domain content returns 422. Unauthenticated requests return 401.

```text
POST /api/stories/{story_id}/scenes/{scene_id}/media/image-request
```

An empty JSON body `{}` uses the existing Story world and no preferred framing.
An explicit selection can use:

```json
{
  "character_ids": ["character-id"],
  "place_ids": ["place-id"],
  "aspect_ratio": "4:5",
  "artifact_references": [
    {"kind": "uploaded_artifact", "reference_id": "opaque-artifact-id"}
  ]
}
```

```text
POST /api/stories/{story_id}/media-plans
```

```json
{"scene_ids": ["first-scene-id", "second-scene-id"], "aspect_ratio": "9:16"}
```

A plan produces one image request per Scene, in caller order, with shared
selection/framing options. It accepts 1–20 unique Scene IDs. This proves multiple
requests without splitting Scenes into panels or inferring a storyboard.

Requests contain no ORM instances, user credentials, provider/model configuration,
or infrastructure fields. Story/Scene IDs and `context` are Sandcastle provenance;
they do not impose story-domain logic on IG/control-plane.

## Lifetime and next boundary

DTOs are returned to the caller only; IDs are not persisted or retrievable.
Repeated calls over unchanged data/options produce the same instructions,
reference ordering, and context, but fresh IDs/timestamps. Durable plans, execution,
artifact tracking, and revision snapshots have no demonstrated need in M3 and are
deferred. M4A adds ephemeral four-panel planning below. M4B can introduce persistence
when approved plans must survive execution. Video/refinement/provider strategies
remain future work; no media execution is implemented here.

Run focused tests from `backend/`:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_media.py -v
```


## Four-panel storyboard planning (M4A)

```text
Story / Scene + selected world and approved Canon
    -> Four-Panel Storyboard Planner
    -> StoryboardPlan (a MediaPlan specialization)
    -> 4 ordered MediaRequests (image / comic_panel)
    -> future M4B IG execution
```

`create_four_panel_storyboard` reuses M3 context selection, stable references,
and the visual instruction compiler. The authenticated API is:

```text
POST /api/stories/{story_id}/scenes/{scene_id}/storyboard/four-panel
```

Send `{}` for defaults or the same selection/artifact/framing options as M3:

```json
{
  "character_ids": ["character-id"],
  "place_ids": ["place-id"],
  "aspect_ratio": "4:5",
  "artifact_references": [
    {"kind": "uploaded_artifact", "reference_id": "opaque-artifact-id"}
  ]
}
```

The 200 response is a `StoryboardPlan`, extending `MediaPlan` with a Scene ID
and exactly four `requests`. Each request contains its own Story/Scene IDs,
`media_type=image`, `purpose=comic_panel`, and `context.panel_number` (1–4),
`panel_count=4`, and a descriptive `panel_role`. These optional context fields
leave existing M3 requests valid. `to_media_plan()` projects to the strict M3
schema without changing IDs, timestamps, requests, or order. No duplicate panel
request hierarchy is introduced.

There is no established provider-independent LLM storyboard abstraction, so
planning is deterministic text composition. It partitions saved prose in source
order using sentence/newline boundaries and, for sparse prose, semicolon clauses.
Four or more units are grouped into four contiguous beats without dropping units.
With one to three units, existing moments are reused through distinct establishing,
medium, detail, and closing framings rather than inventing narrative events.
These are composition defaults, not a required escalation/resolution arc. They
are heuristic and do not provide semantic screenplay analysis or continuity scoring.
The source excerpt, approved facts, and identity details constrain each prompt;
only that panel's excerpt is presented as the moment to depict.

As in M3, omitted selections include all Story Characters/Places; `[]` includes
none. Because M2 has no per-beat entity links, all selected identity and artifact
references conservatively propagate unchanged to each panel. Shared descriptions
are reference context, not instructions to insert extra characters or events.
Outfit references still use Character IDs. No references are fetched or resolved.

The default aspect ratio is `1:1` per panel; callers may override it. This does
not select a grid, a vertical webtoon layout, or an execution strategy. Four panel
intents do **not** imply four independent provider calls: M4B may compile them
into one composite image or separate images.

No provider execution occurs, no persistence or migration is added, and no
Canon/Scene data is changed. Storyboards remain disposable previews with fresh
IDs/timestamps and deterministic instructions. Editing, reordering, per-panel
regeneration, durable approval, and artifact lineage are deferred; the M3 request
IDs and explicit panel order leave those extensions possible. M4B will execute
the approved plan through IG. M5 video is deferred because IG currently has no
video capability.

Run focused validation from `backend/`:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_storyboard.py -v
```

## Durable execution boundary (M4B)

M3/M4A previews are unchanged. [M4B execution](EXECUTION.md) accepts explicit user
approval of a returned plan, persists exact panel request snapshots, and uses an
injected execution client to submit/synchronize results. The IG adapter currently
fails closed for live HTTP because safe service-caller authentication is absent.
Execution/Artifact metadata is durable; media bytes are not stored in PostgreSQL.
