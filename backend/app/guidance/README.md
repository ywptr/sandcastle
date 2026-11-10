# M9B — Narrative guidance

```text
Story premise/objective + effective Canon + recent Scenes
+ audience/maturity + optional private feedback
        ↓ NarrativeSuggestionGenerator
        ↓ three concise advisory alternatives
        ↓ user selects/edits "What should happen next?"
        ↓ existing explicit Scene-generation action
```

Suggestions are not Canon, candidate facts, Scenes, forks, authority decisions or
Universe updates. Reading a profile or requesting suggestions writes nothing.
Choosing a suggestion only populates the existing editable textbox. It never
calls the Scene-generation endpoint automatically.

## Story profile

One optional `NarrativeGuidanceProfile` row per Story stores audience, content
maturity, optional tone/genre/notes and a lightweight private feedback summary.
It uses the existing Story ownership boundary; there is no identity system,
public review service, analytics or learning pipeline.

- **Audience**: `child`, `teen`, `adult` describes intended readers.
- **Maturity**: `general`, `mild`, `moderate`, `mature` is a content ceiling.
- Child supports general/mild; teen supports up to moderate; adult supports all.
  Adult does not imply sexual explicitness, graphic violence or a need to raise
  maturity. The deterministic fallback stays conservative for every rating.
- **Feedback**: optional author-supplied summary, average 1–5 with a positive
  count (maximum 1,000,000), plus up to ten short signal tags. Missing feedback
  means null average and zero count. This is separate from audience/maturity.
  Tags/ratings cannot override Canon, objective or audience suitability.

Existing Stories have virtual defaults `adult` + `general`, no feedback. No
synthetic profile rows or Story rewrites are required. Profile reads return null
timestamps until saved. The Scene form offers minimal audience/maturity controls;
tone, genre, notes and feedback are available through the profile API.

## Context and provider boundary

`NarrativeSuggestionGenerator.suggest(context, count=...)` is a dedicated
provider-neutral port. M2 `StoryGenerator` writes Scene prose and is deliberately
not reused for planning. Context contains plain structured data, not ORM objects:
Story title/premise/objective, approved **effective** Canon from M8/M9A (including
Universe pins and Story forks), Universe metadata, profile, optional feedback,
extra instructions and explicit priority/suitability constraints.

The SQL query selects only the latest four Scenes by default, at most five,
then returns them in narrative order. Each edited Scene excerpt is capped at
4,000 characters with a truncation flag. Superseded Canon is excluded. Effective
Canon is retained rather than silently dropping facts to meet a context budget.

The default is deterministic and provider-free. Its alternatives explore action,
questions, character response, consequences and approach; child language is
simpler, teen framing emphasizes age-appropriate choices, and adult framing may
include emotional costs without increasing explicitness. It does not pretend to
understand arbitrary prose: it avoids invented events, relationships or powers,
and does not echo raw notes, feedback or source passages into plot proposals.
It does not currently tailor its generic scaffolds to tone/genre/feedback.

Future generators receive those settings and must honor the context constraints.
The service validates structured output, exact count, nonblank fields, distinct
IDs/text and a total title/text budget of 200 whitespace-delimited words.
Malformed, duplicate, excessive or unavailable generator output returns 502.
There is no semantic contradiction detector or general censorship engine here;
no live model adapter, provider/model selection or provider calls were added.

## Authenticated API

All paths are under `/api/stories/{story_id}/guidance`:

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/profile` | Saved profile or nonpersisted defaults |
| PUT | `/profile` | Full replacement of editable profile fields |
| POST | `/next-scene` | Optional `{count: 3, recent_scene_count: 4, additional_instruction: null}` |

Count is 1–5; recent Scene count is 1–5. Extra instructions are limited to 1,000
characters, notes to 2,000. Unknown fields/provider selectors are rejected.
Inaccessible Stories return 404; authentication remains owned by IS.

The response contains Story ID and ephemeral `{id, title, text}` suggestions.
The compact frontend uses saved settings; edits must be saved before requesting
new suggestions. Generation retains the existing authority and Scene workflow.

## Migration and verification

Migration `e04c8a12b763` adds only the optional profile table after M9A. It uses a
Story primary/foreign key and database checks for audience, maturity compatibility
and feedback ranges. Existing Scene sequence indexes support the bounded history
query. Downgrade drops profile/settings/feedback only; export them first if needed.
Story, Universe, Canon, candidate and Artifact data are unchanged.

Focused tests: `python -B -m unittest discover -s tests -p test_guidance.py -v`.
The full suite includes SQLite upgrade/downgrade/model-drift checks and PostgreSQL
SQL compilation. Frontend tests exercise relative authenticated API requests and
selection handlers without automatic generation; lint/build validate integration.
No tests require a provider or IG server.

M9C will reuse the profile for media adaptation; no adaptation or shot planning
is implemented here. M10 will expose guidance through workflow/difficulty UX.
No public ratings, recommendation ML, Axtor expansion, IG, video, timelines,
Canon merging or deployment is included.

M13 adds [persistent Story language/genre context](../stories/README.md) to
guidance, including localized deterministic scaffolds; it never translates Canon.
