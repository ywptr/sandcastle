# M7: continuity and Canon intelligence

```text
Saved Story / Scene text (or an explicit manual proposal)
    -> CanonExtractor: validated structured facts and evidence
    -> subject resolution against existing M2 objects
    -> approved Canon comparison
    -> pending CanonCandidate (new / consistent / conflict / uncertain)
    -> explicit owner approval or rejection
    -> existing CanonEntry model
```

Sandcastle owns narrative meaning and continuity. No Axtor, IG, Artifact image
understanding, shared Canon, or universe integration is involved. Extraction and
classification never mutate approved Canon or create Characters/Places. Visual
references remain separate from Canon evidence.

## Existing model and minimal schema extension

`CanonEntry` remains the authoritative Story-level Canon record with `approved`
and `superseded` status. M7 adds nullable `subject_id` and `fact_type` fields;
existing `type` identifies the subject type. Old entries remain valid. New
Character/Place entries should use stable subject IDs and short property keys
such as `eye_color`, rather than relying on display names.

The dormant `CanonCandidate` model is completed rather than duplicated. Its
historical migration `e5a5b285762e` was empty, so new migration `b7e193d2c540`
creates the table and adds the two CanonEntry columns without editing history.
Candidate fields include actor ownership, Story/Scene IDs, type/subject ID/name,
fact type/key/value, exact evidence, full source snapshot, source hash, structured
extraction data, extraction confidence, classification/reasoning/comparison
snapshot, review state/timestamps/note, approved-entry ID, and superseded IDs.

Review **status** is pending, approved, or rejected. Continuity **classification**
is independently new, consistent, conflict, or uncertain. Confidence describes
the extractor's proposal, not a guarantee that the statement is true.

## Extraction boundary and supported grammar

The existing `CanonExtractor` protocol returns validated `ExtractedCanonFact`
objects (or machine-readable dictionaries validated by the service). Tests inject
fakes. No provider is required or initialized for M7. M2's Scene writer returns
prose rather than structured facts, so it is not reused as an unsafe JSON parser.
The existing optional legacy adapter is not selected by M7's composition; no live
model calls are performed. Provider/model schemas do not enter Canon services.

The default deterministic extractor recognizes explicit English forms such as:

- `Mara has green eyes.` / `Mara has black hair.`
- `Mara is 35 years old.` / `Mara is alive.` / `Mara is dead.`
- `Mara is gentle.` / `Mara wears a yellow coat.` / `Mara owns a silver key.`
- `Mara can fly.` / `Mara is a captain.` / `Mara became captain.`
- `Mara is married to Alex.`
- `Old Harbor has a cold climate.` / `Old Harbor is controlled by the guild.`
- `Rule resurrection: magic cannot revive the dead.`
- `Event evacuation: citizens left at dawn.` / `Timeline dawn: the gates opened.`

This is a bounded grammar, not universal natural-language understanding. Other
facts can be proposed manually or supplied through the extraction port. Unsupported
prose may yield an empty list. Fact types remain short, extensible strings.
Evidence from extraction must occur in the saved source; missing/malformed evidence
or invalid structured output fails the whole batch before persistence. No more
than 100 facts are accepted per extraction. Story extraction reads premise and
objective; Scene extraction reads current saved Scene content.

Named Characters/Places resolve only when exactly one existing name matches after
case/whitespace normalization. Supplied IDs must belong to the Story. Missing or
ambiguous names stay unresolved/uncertain; extraction never creates domain objects.
Approval may explicitly select an existing subject ID to resolve ambiguity.

## Comparison and re-analysis

Comparison uses only currently approved Canon for the same subject/type/property.
Known scalar keys (`age`, `height_cm`, `alive`, `eye_color`, `hair_color`) have
conservative normalization. Equal scalar values are consistent; differing known
values conflict. Unparseable scalar values are uncertain. With no relevant Canon,
a resolved explicit fact is new. Inferred facts, tentative values such as "possibly", low-confidence extraction,
and unresolved subjects remain uncertain.

Equal normalized unstructured statements are consistent. Different prose may
be compatible, so it remains uncertain unless a `SemanticCanonComparator` is
explicitly injected into service-level re-analysis. No semantic provider adapter
is configured by default. Comparison is not a general reasoning engine.

Legacy `character.<unique_name_slug>.<key>` or ID-qualified keys can match an
existing subject. Unscoped Character/Place keys cannot safely be assigned to a
particular subject and produce uncertainty. Legacy location/rule/outfit type
aliases are considered conservatively; arbitrary prose is not semantically
rewritten or migrated.

Candidate listing/reading returns the last saved analysis and `analyzed_at`.
Explicit reclassification refreshes pending candidates. Continuity reports also
refresh pending analysis before counting, and approval always rechecks current
Canon. Re-analysis never alters reviewed candidates or approved Canon. Changed
Story/Scene source marks an extracted candidate uncertain; stale-source approval
is refused until extraction is run again. Manual proposals retain their manual
origin even when optionally associated with a Scene.

## Review and history

Approval/rejection and Canon edits serialize on the parent Story row on PostgreSQL.
Approval updates the candidate and Canon in one transaction:

- New: create an approved CanonEntry linked from the candidate.
- Consistent: reuse an existing approved entry; do not duplicate it.
- Conflict: require `replace_conflicts=true`, supersede the identified current
  entries, and create the replacement. Old values remain in superseded rows.
- Uncertain: require `accept_uncertain=true`; replacing any identified current
  entries additionally requires `replace_conflicts=true`.

Character/Place identity must be resolved before approval. Ambiguous unscoped
legacy Canon is not silently reassigned or superseded. Explicit uncertainty
acceptance may establish a scoped fact without rewriting unidentified legacy
records; richer reconciliation remains future work.

The candidate keeps its source/extraction snapshot, exact compared Canon values,
superseded IDs, reviewer note/time, and approved-entry link. Later manual Canon
edits cannot erase the candidate's saved comparison snapshot. Rejection changes
no Canon. Repeated approval/rejection is idempotent for that terminal decision;
rejecting an approved candidate or approving a rejected one returns 409. M8
branching/version semantics are deliberately not implemented.

Deduplication uses owner, Story, source kind/Scene, normalized full-source hash,
subject identity, fact type/key/value, and evidence. Repeated unchanged extraction
returns existing candidates, including reviewed ones, without resetting decisions.
Exact normalized duplicates within one batch are collapsed. Changed source may
produce a new proposal. Story-row serialization and a unique database constraint
protect normal concurrent extraction; global semantic deduplication is not attempted.

## Authenticated API

All paths below have prefix `/api/stories/{story_id}`. Story ownership is checked
before content access. Missing/inaccessible Stories, Scenes, subjects, and
candidates return 404. Invalid request data returns 422, review conflicts return
409, and invalid extractor output returns 502. No endpoint calls IG or Axtor.

| Method | Path | Operation |
| --- | --- | --- |
| POST | `/scenes/{scene_id}/canon/candidates/extract` | Extract/persist Scene candidates |
| POST | `/canon/candidates/extract` | Extract/persist Story candidates |
| POST | `/canon/candidates` | Explicit manual proposal |
| GET | `/canon/candidates` | List; optional status, classification, scene_id filters |
| GET | `/canon/candidates/{candidate_id}` | Read evidence and analysis |
| POST | `/canon/candidates/reclassify` | Refresh pending analysis; optional scene_id query |
| POST | `/canon/candidates/{candidate_id}/approve` | Explicit review/approval |
| POST | `/canon/candidates/{candidate_id}/reject` | Reject; optional note |
| GET | `/canon/continuity` | Current pending counts/issues; optional scene_id query |

The old `/scenes/{scene_id}/canon/extract` route remains a compatibility alias.
An extraction call needs no request body and does not approve anything.

Manual proposal example:

```json
{
  "type": "character",
  "subject_id": "existing-character-id",
  "fact_type": "physical_trait",
  "key": "eye_color",
  "value": "blue",
  "evidence": "The author explicitly proposes changing Mara's eyes to blue."
}
```

Intentional conflict approval:

```json
{"replace_conflicts": true, "note": "Intentional revision of current Story continuity"}
```

Default approval uses `{}`; uncertainty acceptance and subject disambiguation
are optional explicit fields `accept_uncertain` and `subject_id`. Reports return
`counts`, `total`, and concise conflict/uncertainty issues for pending candidates.
Use the read-candidate endpoint for full provenance. Reports do not extract new
facts or perform a global audit of all approved Canon.

## Validation and limits

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_canon_intelligence.py -v
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests use signed test identities, isolated SQLite databases, deterministic/fake
extractors, and an injected semantic comparator. Migration checks cover historical
Canon preservation, review provenance, upgrade/downgrade, model drift, and
PostgreSQL SQL compilation. No deployed database is migrated automatically. Apply
`b7e193d2c540` to the intended development database before using the updated Canon
routes. Out-of-band prototype candidate tables need reconciliation before applying
the migration. Downgrade removes M7 candidate/review metadata while preserving the
underlying Canon rows; export review history first if it must be retained.

A dedicated live PostgreSQL run and a review UI are not included. Image fact
extraction, a universal ontology, automatic contradiction resolution, Canon
branching, shared universes, workflow graphs, Axtor, IG execution, and video remain
deferred. The local HTTPS/auth bootstrap setup is unchanged.
