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

- `MediaType`: image and video. Only Scene-image planning is implemented.
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
deferred. M4 can build four-panel planning on these DTOs and introduce persistence
when approved plans must survive execution. Video/refinement/provider strategies
remain future work; no M4 behavior is implemented here.

Run focused tests from `backend/`:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_media.py -v
```
