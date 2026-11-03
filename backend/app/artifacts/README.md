# M6: references, lineage, and refinement planning

```text
Story / approved Canon + selected Characters / Places
    -> Reference Resolver (context selection, not storage)
    -> Media Orchestrator
    -> MediaRequest with stable Artifact IDs and roles
    -> future execution
    -> Artifact metadata
    -> ArtifactRelation lineage
```

## Responsibilities

- **Artifact** is durable media identity owned by an IS-derived Sandcastle user.
  Its `source` distinguishes generated, uploaded, and external media. It does not
  imply physical storage ownership. Story/Scene/execution links are optional
  provenance, not the Artifact's identity or exclusive scope.
- **ReferenceBinding** records how an Artifact is used by a Story-domain target.
  Each binding has its own stable ID, owner, Story scope, Artifact ID, target
  type/ID, role, optional label/metadata, and timestamp.
- **ArtifactRelation** records provenance edges between owned Artifact identities.
  Multiple parents are supported without storing a single parent on Artifact.
- **Refinement MediaRequest** is provider-neutral intent to derive new media from
  an existing image, not an execution or an observation about its pixels.

**References do not mutate Canon.** A picture used for Mara's appearance does not
make every visible detail a Canon fact. No extraction, contradiction checking,
scoring, or continuity resolution occurs here. Sandcastle stores no media bytes
in PostgreSQL, fetches no media bytes, and introduces no storage infrastructure.

## Registration and reuse

`POST /api/artifacts` registers metadata for media already stored elsewhere:

```json
{
  "source": "uploaded",
  "media_type": "image",
  "retrieval_reference": "https://media.example.test/already-stored/image.png",
  "mime_type": "image/png",
  "display_name": "Mara appearance",
  "metadata": {"credit": "Author"}
}
```

`source` may only be `uploaded` or `external`. Clients cannot register generated
outputs, assign an execution, or choose another owner. Generated artifacts still
come from execution completion. Optional Story/Scene provenance is validated;
Scene provenance requires an owned parent Story. Image MIME types and external
locators are accepted; inline data, local-file locators, and URL-embedded login
credentials are rejected. Locator existence, content, and availability are not
verified. No multipart upload, storage adapter, credentials, or download proxy is
implemented. Actual binary upload/storage remains a later infrastructure concern.

Use `GET /api/artifacts`, optionally filtered by `source` and/or `story_id`, and
`GET /api/artifacts/{artifact_id}`. Story filtering includes both original
provenance and contextual bindings. Existing M4B read/list routes continue to
work. Artifact reads authorize the Artifact owner independently of Story scope.
One Artifact can be bound to several targets and several owned Stories without
copying its media record. Shared ownership and shared Canon are not implemented.

## Bindings and deterministic selection

```text
POST   /api/stories/{story_id}/references
GET    /api/stories/{story_id}/references
DELETE /api/stories/{story_id}/references/{reference_id}
```

Example Character binding:

```json
{
  "artifact_id": "local-artifact-id",
  "target_type": "character",
  "target_id": "character-id",
  "role": "character_identity",
  "label": "Primary visual identity"
}
```

Targets are `story`, `character`, or `place`. Story targets default to the selected
Story ID. Character/Place targets must exist in that Story. Roles are
`character_identity`, `outfit`, `place`, `visual_style`, and `general`.
Character identity/outfit roles require a Character target; place roles require a
Place target. Style/general roles may annotate any valid target. Outfit remains
part of Character, so outfit bindings target the Character ID rather than a
fictional Outfit object or immutable outfit revision. M8 reusable/forkable Canon
objects are deferred.

Bindings are unique by Story, Artifact, target, and role; duplicate creation
returns 409. Deleting a binding does not delete its Artifact. Missing or
inaccessible Story/Artifact/target/binding returns 404, including another user's
resources. The Artifact owner and binding Story owner must be the current user.

M3 Scene requests, M4A four-panel plans, and context-aware refinement use the same
resolver. It includes:

- Story style/general bindings broadly;
- Character bindings only for selected Characters;
- Place bindings only for selected Places;
- additional explicitly supplied, owned image IDs in `artifact_ids`.

Omitted Character/Place selection retains M3's all-objects-in-this-Story default;
`[]` selects none. Unbound Artifacts, unrelated targets, another Story's bindings,
and another user's resources are not automatically included. No ranking or
embeddings are used. Binding selection has stable ordering. Different roles for
the same Artifact may legitimately produce more than one reference use.

Durable references use `Reference(kind="artifact", reference_id=<local Artifact
ID>, binding_id=<binding ID>, role=...)`. No retrieval locator, storage credentials,
or physical storage details enter Story/Canon or MediaRequest DTOs. The existing
M3 `artifact_references` field remains a legacy opaque pass-through for compatibility;
those IDs are not looked up, fetched, or treated as local Artifact identities.
New code should use durable bindings or `artifact_ids`. The IG adapter rejects
both unresolved legacy inputs and local Artifact references; no IG dependency is
solved here.

M2 still lacks per-beat entity resolution. Applicable selected bindings propagate
across all four M4A panels, without asserting that all selected subjects appear
in every panel. Future context ranking and per-panel selection are deferred.

## Refinement preview and provenance

```text
POST /api/artifacts/{artifact_id}/refinement
```

```json
{
  "instruction": "Keep Mara's identity and outfit unchanged. Change the background to a rainy night market.",
  "story_id": "story-id",
  "scene_id": "scene-id",
  "character_ids": ["character-id"],
  "place_ids": [],
  "artifact_ids": ["additional-owned-artifact-id"],
  "aspect_ratio": "4:5"
}
```

This returns an image `MediaRequest` with purpose `image_refinement`. Its first
reference is the owned source Artifact with role `source`;
`context.source_artifact_id` preserves provenance explicitly. Applicable bindings,
explicit additional references, and approved Canon context are included when
supplied. The instruction is preserved without image inspection or an LLM call.

Story/Scene context is optional: `MediaRequest.story_id` now permits null for a
standalone refinement preview. Existing storyboard plans and execution routes
still require owned Story/Scene scope. A Scene or Character/Place selection
requires Story context. Source Artifact provenance is not silently used to infer
new context. Fresh request IDs/timestamps may differ; instructions and reference
selection are deterministic for unchanged inputs.

**M6 performs no live refinement.** A preview creates no Execution, derived
Artifact, or lineage edge. When a later execution path supports refinement, the
request snapshot can preserve source IDs through execution and result creation;
the relation service can then record the derived/result relationship. Existing
M4B execution is still limited to approved four-panel plans and remains blocked
for live IG. Binding changes do not rewrite previously approved request snapshots.

## Lineage

```text
POST /api/artifacts/{child_artifact_id}/relations
GET  /api/artifacts/{artifact_id}/relations
```

```json
{"parent_artifact_id": "source-artifact-id", "relation_type": "derived_from"}
```

Both parent and child must belong to the current user. Types are `derived_from`
and `reference_input`; several parents may point to one child. Repeated identical
relations return the same relation ID; database uniqueness prevents duplicate
edges. Self-links are rejected both in service and database. A recursive
reachability check rejects direct and indirect cycles across both relation types.
Lineage changes use an owned-row lock on PostgreSQL; no general graph analytics
or workflow engine is introduced. GET lists incoming and outgoing edges for the
owned Artifact. Relationships are explicit user metadata, not Canon assertions.

## Migration and validation

Migration `a42d7e90c681` follows M4B. It makes Artifact provenance/external-reference
columns nullable, adds display name and source validation, and creates indexed
binding/relation tables with foreign keys and uniqueness checks. It changes no
Story or Canon tables and preserves generated Artifact identity and historical
execution snapshots. Online downgrade refuses while registered Artifacts require
the expanded schema; export/migrate those records before downgrading. It never
silently deletes uploaded/external Artifact metadata.

From `backend/`:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_references.py -v
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests use isolated SQLite databases, signed test-user sessions, and fake execution.
Migration validation covers historical data preservation, upgrade/downgrade,
downgrade protection, model drift, and PostgreSQL SQL compilation. A live
PostgreSQL upgrade is not performed without a dedicated development/test database.

IG authentication/execution blockers are intentionally out of scope. No IG code
is modified. M5 video remains deferred. M7 Canon intelligence, M8 reusable Canon,
storage infrastructure, automatic lineage creation from refinement results, UI,
and live execution are deliberately deferred.
