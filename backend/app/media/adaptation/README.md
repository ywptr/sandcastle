# M9C — Audience-aware media adaptation

```text
Story truth / saved Scene + effective Canon
           + M9B audience/maturity profile
                     ↓
           ShotPlanner / adaptation service
                     ↓
           visual instructions + audit provenance
                     ↓
           existing M4A storyboard / M3 MediaRequests
                     ↓
           future IG execution (not implemented here)
```

Adaptation changes **depiction**, never Story truth, Canon, candidate facts,
Universe state or Scenes. A sensitive event can remain verbatim in the audit
plan while being implied or off-screen visually. IG receives already-compiled
visual intent; it does not interpret audience policy, Canon or narrative meaning.

## Representation and context

`MediaAdaptationPlan` is ephemeral: IDs, audience/maturity, format hint,
sensitivities, ordered shots, issues, notes, context digest and timestamp.
`AdaptedShot` contains sequence, exact original narrative beat and source offsets,
visual instruction, framing, selected Character/Place IDs, existing M3 `Reference`
DTOs, sensitivity tags, depiction strategy and rationale. Sensitive source beats
remain visible in the authorized preview; this API is not image moderation.

The provider-neutral `ShotPlanner.adapt(context)` port receives saved Scene text,
the same M9B profile (including tone, genre and notes), M8/M9A effective approved
Canon and M6 references. No ORM state is exposed to external providers. A future
semantic adapter can implement the port; no model/provider SDK or API is called.

The service validates identity, source spans, narrative coverage/order, selected
entities/references and profile/context hashes. Stale Scene edits, profile changes,
Canon changes or different selections require a fresh preview. Artifact bytes and
storage locators are never resolved. Existing source/reference IDs remain intact;
no Artifact, binding, lineage or approval records are created.

## Initial deterministic behavior

Sensitivity tags: `violence`, `intimacy`, `injury`, `horror`, `substance_use`,
`other_sensitive`. An empty list means none detected. Narrow English keyword
patterns are supplemented by explicit additive `sensitivity_hints`; hints cannot
remove an automatically detected tag. False positives favor conservative framing.
This is not a universal content classifier or a provider-specific safety filter.

Strategies: `direct`, `implied`, `reaction`, `cutaway`, `aftermath`, `silhouette`,
`offscreen`, `symbolic`. Ordinary beats can remain direct. Recognized sensitive
beats use indirect framing:

- Child: off-screen action and restrained response, without disturbing detail.
- Teen, or general/mild maturity: reaction, implication and restrained aftermath.
- Adult moderate/mature: obscured silhouette, cutaway and aftermath; never an
  automatic increase to explicit sexual or graphic depiction.
- Intimacy: environmental cutaway and implied transition for every profile. The
  planner does not infer ages, consent, relationships, an embrace or new actions.

Exact source beats and rationale preserve what occurred internally. The planner
never invents deaths, recovery, props or causal outcomes to make framing easier.
Selected entities propagate across shots because per-beat entity resolution does
not yet exist. Tone/genre/notes are available to the port but are not semantically
interpreted by the deterministic implementation. Free-form additional instructions
are hashed as context and deliberately not forwarded into visual prompts.

## Continuity boundary

Read-only capability/state checks catch explicit selected-subject locomotion
contradictions (`can_walk`, `can_run`, mobility/capability restrictions, dead but
acting). Explicit eye/hair color, age and alive/dead statements reuse M7's scalar
comparator against effective Canon. Detected issues produce a conservative static
cutaway and an issue containing source/Canon IDs. **Adapted storyboard compilation
is blocked until those issues are reviewed.** M7 remains the Canon authority;
M9C neither resolves a conflict nor silently changes its underlying fact.

Complex prose, pronouns, unscoped legacy facts, metaphor, multilingual sensitivity
and semantic contradictions require review or a future semantic planner. The
initial deterministic path is not a guarantee of semantic safety for arbitrary
text or Artifact pixels. Scene input is limited to 60,000 characters and output
to 240 shots; unsupported/invalid planner output fails clearly.

## M4A integration

`create_four_panel_storyboard(..., adaptation=plan, options=original_options)`
validates current context, groups shots in order into four panels, or repeats
framing for sparse shot sequences. All source shots remain represented. The same
M3 MediaRequest construction and M4A panel-order contract are reused. MediaContext
adds only `adaptation_id` and `adapted_shot_sequences` for provenance.

The adapted compiler uses **only visual instructions/framing** in prompts. It does
not append raw Scene, premise, objective, character descriptions, Canon prose or
free-form instructions that could reintroduce explicit details. Stable identity,
outfit, place, style and Artifact references still propagate. The original plan
holds narrative provenance; future execution snapshots retain submitted prompts.

The existing M4A path without adaptation remains available and unchanged. Clients
seeking audience-aware depiction must choose the adapted path explicitly. A
storyboard still describes intent, not four required provider calls. Shot plans
are independent of comic panel count and can later inform other formats.

## Authenticated API

Under `/api/stories/{story_id}/scenes/{scene_id}`:

| Method | Path | Result |
| --- | --- | --- |
| POST | `/media/adapt` | Ephemeral `MediaAdaptationPlan`, including review issues |
| POST | `/storyboard/four-panel/adapted` | Fresh server-side adaptation → existing four-panel plan |

Both accept optional `AdaptationOptions`: existing M3 entity/artifact selections,
aspect ratio, `output_format` (`webtoon` or `image`), additive sensitivity hints,
and up to 1,000 characters of additional visual instruction. Video/provider/model
selection is rejected. No client-supplied adapted instructions are accepted here.
Ownership/Story–Scene relationship checks return 404 for inaccessible resources;
invalid input or unresolved adaptation issues return 422; invalid/unavailable
planner output returns 502. Neither route executes media generation.

## Persistence, verification and deferrals

No tables or migrations: source content/profile/Canon are already durable;
previews do not justify additional persistence. Tests cover no-write behavior,
profile/Canon/reference propagation, source provenance, sensitive treatment,
stale plans, API ownership, and compatibility with existing M4A planning.

Run `python -B -m unittest discover -s tests -p test_adaptation.py -v` and the full
backend suite. No live provider or IG is required. Backend-only: the current
frontend has a prose Scene editor but no storyboard/adaptation preview surface;
a shot editor or new media workspace is deliberately not introduced.

M10 may expose/configure these choices through difficulty/workflow UX. IG calls,
video, image moderation, Canon mutations, Axtor changes and timeline support are
not included. Do not deploy or modify IG as part of M9C.
