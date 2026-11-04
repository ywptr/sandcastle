# Reusable Canon Library (M8)

**Reference until divergence; fork when divergence begins.**

```text
Canon Library → Canon Object → immutable Version → Story Reference
                                                       ↓
                                                explicit fork
```

The library belongs to an IS user, independently of Stories. Initially it supports
Characters and Places. Outfit remains a Character field; faction/object types,
team sharing and name-based identity deduplication are deferred.

## Compatibility and migration

Migration `c81f24a709de` adds three tables without rewriting existing rows.
Existing Character/Place IDs, M7 candidates/Canon history, M6 bindings, Scenes and
media selectors remain valid. Promotion is explicit: it registers a reusable
identity, snapshots the typed fields, approved subject-ID Canon facts, and current
visual bindings, then pins the existing local handle to version 1. No cross-Story
sharing is inferred from equal names. Unscoped legacy facts remain Story-local;
they are not silently assigned to a reusable subject.

Attaching to another Story creates a compatibility handle with a new local ID.
It is a projection of the pinned structure, not a second independent authoring
system. Existing media/M7 selectors continue using local stable IDs. The library
version is authoritative for linked subject facts. A Story no longer necessarily
owns the only representation of a Character/Place.

## Versions, sharing, and editing

Versions contain typed `structure`, structured `facts` (with source Canon IDs),
and `visuals` (Artifact/binding IDs and roles). IDs are stable; version numbers
increase per object under an object lock. Parent IDs preserve lineage. Historical
snapshots are append-only through services/API. Shared head is derived from the
highest shared version number; there is no auto-follow flag or mutable current
version pointer.

Shared update creates a new snapshot; existing pins do not move. Explicitly move
a Story reference to opt into that version. Full typed structure replacement is
used for shared updates; approved facts and visual baseline are inherited.

Story edits of linked shared structure/facts return **409: fork first**. Fork
creates a Story-specific version with parent/reason, changes only the requesting
reference and retains the local subject ID. Subsequent structure edits and M7
approvals append another version atomically with the Story change. A branch
cannot be attached to another Story or used as a shared-update source. Switching
pins is explicit and preserves the abandoned branch history.

## Continuity and inheritance

M7 resolves subject facts from the Story's pinned version, retaining Story-local
facts for unlinked subjects. Candidates retain local subject IDs; comparison
snapshots include the effective version ID. Review re-analyzes current pins.
Conflicts still require replacement consent; shared divergences additionally
require an explicit fork. Superseded local Canon rows and candidate history remain
available; another Story's source Canon is never superseded by a fork approval.

Forks inherit structured facts and visual-reference IDs as a fixed baseline.
Artifacts and bindings are not copied. Reference resolution checks Artifact
ownership and selected Character/Place IDs; unrelated references are excluded.
Later source-Story binding changes do not alter a pinned baseline; new local
bindings apply only to their Story. Visual Artifacts never become Canon facts.

## Authenticated API

All paths below use `/api`. Inaccessible objects, Stories, history and references
return 404. Sharing is within one authenticated account only.

| Method | Path | Input / behavior |
| --- | --- | --- |
| GET/POST | `/canon/library` | List / create `{object_type, data}` typed structure |
| GET | `/canon/library/{id}` | Object identity |
| GET | `/canon/library/{id}/versions` | Ordered full historical snapshots |
| POST | `/canon/library/{id}/versions` | `{parent_version_id, data}` shared update |
| POST | `/stories/{id}/canon/library/promote` | `{target_type, target_id}` existing local subject |
| GET/POST | `/stories/{id}/canon/references` | List / attach `{canon_object_id, canon_version_id}` |
| POST | `/stories/{id}/canon/references/{ref}/fork` | `{reason}` explicit divergence |
| PATCH | `/stories/{id}/canon/references/{ref}` | `{canon_version_id}` explicit pin change |

No automatic merges, branch rebases, provider execution or media storage changes
are included. M9 may add Universe scope above these identities; M10 may expose
these independent services through workflow/difficulty UX. Neither is implemented.

## Validation and rollback

Run `python -B -m unittest discover -s tests -v` from `backend/`.
Migration tests exercise upgrade/downgrade, model drift, PostgreSQL offline SQL,
and preservation of existing subjects, candidates and visual bindings. Downgrade
refuses populated library data: export and explicitly remove library records
before dropping these tables. Production databases must not be used for tests.
