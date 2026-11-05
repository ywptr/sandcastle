# M9A — Shared Universe / World foundation

A Universe is an account-owned, durable world container. It has no owning Story.
Existing Stories remain standalone unless explicitly attached.

```text
Universe
  ↓ Universe pins of M8 Canon object/version IDs
Story (optional membership)
  ↓ Story version overrides / explicit M8 forks
Scene
```

## Persistence and membership

`Universe` stores ID, owner, name, description and creation/update timestamps.
`UniverseStoryMembership` has Story ID as its primary key: at most one Universe
per Story. Membership attachment is idempotent; moving between Universes requires
explicit removal first. Removing membership does not delete Story data, Scenes,
Canon history, Artifacts or Story forks. Only inherited context disappears.
Rejoining restores the same inherited subject IDs for the same Canon objects.
The membership foreign key cascades when a Story is deleted; Universe pins and
library versions do not depend on membership and remain intact. This milestone
adds no Story-deletion workflow or changes to pre-existing Story-deletion constraints.

`UniverseCanonReference` pins an existing M8 Canon object/version, with one pin
per object per Universe. There is no new Canon-object hierarchy and no inference
from names. Characters and Places are supported, matching M8. Outfits remain
Character fields; standalone world rules remain Story-local until a reusable
rule type exists. No synthetic Universes or automatic migration of Story data.

## Effective Canon and stable subjects

M8's `references` and `effective_entries` resolution now includes Universe pins.
An explicit Story reference to the same Canon object takes precedence over the
Universe reference, regardless of its version. Other Story-local approved facts
remain present. M7 reads this effective context, rather than just local tables.
Its classification/review lifecycle and historical snapshots remain unchanged.

Inherited Characters/Places are read-only transient projections through existing
world selectors, not copied database rows. Their Story-local UUIDs are derived
from the Story and Canon object IDs (not names or versions). The Story reference
API returns `inherited: true` and `universe_id`, alongside the Universe reference
ID usable with the existing M8 fork route.

A fork materializes the compatibility handle with the **same subject ID**, creates
a Story reference and appends a child version in one transaction. It returns a
new Story-reference ID for subsequent edits. Universe and other Stories retain
the shared pin. M7 candidates keep resolving across this transition; divergent
approval or direct inherited editing returns 409 until explicitly forked.
Read-only resolution and candidate extraction never publish or mutate Canon.

M6 visual references are inherited through existing version snapshots; Artifact
ownership still applies. They do not become Canon facts. Scene/media planning
uses the same effective selectors and requires no provider calls.

## Explicit pinning and promotion

Attaching a shared version to a Universe is explicit. Creating new library versions
does not automatically update a Universe pin. An explicit Universe pin update
changes inherited context for its member Stories; Story pins/forks remain fixed.

A Story branch cannot be pinned as shared Canon through normal attachment.
Explicit **promotion** publishes a new immutable shared snapshot parented to that
branch and pins it to the Universe. If this object already has a Universe pin,
promotion explicitly replaces that pin with the published snapshot. This is full
snapshot publication, not a merge. Story discoveries and approved M7 facts do not
automatically promote. Source versions, Story pins and review history are retained.

## Authenticated API

All routes use `/api`. Ownership is checked on Universe, Story, Canon object and
version scope. Inaccessible resources return 404; incompatible membership or
shared/branch operations return 409. No public/team sharing.

| Method | Route | Input / behavior |
| --- | --- | --- |
| GET/POST | `/universes` | List / create `{name, description}` |
| GET/PATCH | `/universes/{id}` | Read / edit metadata |
| GET | `/universes/{id}/stories` | List memberships |
| POST/DELETE | `/universes/{id}/stories/{story_id}` | Attach / remove membership |
| GET/POST | `/universes/{id}/canon/references` | List / pin `{canon_object_id, canon_version_id}` |
| POST | `/universes/{id}/canon/references/promote` | Explicitly publish/pin the supplied object/version |
| PATCH | `/universes/{id}/canon/references/{reference_id}` | Update pin `{canon_version_id}` to a shared version |

For inherited divergence, use M8's
`POST /stories/{story_id}/canon/references/{reference_id}/fork` with `{reason}`.
Explicit M8 Story pinning can also opt a Story out of future Universe pin updates.

## Migration and verification

`d93b71c602fa` adds three tables only, after `c81f24a709de`. Existing M1–M8 rows
and foreign keys are unchanged. Downgrade refuses populated Universes: export and
explicitly remove Universe records before dropping this scope. PostgreSQL offline
upgrade/downgrade SQL, SQLite round trips, model drift and legacy-data preservation
are exercised by `tests/test_migrations.py`.

Run `python -B -m unittest discover -s tests -p test_universes.py -v` and the full
backend suite. No provider configuration or running IG instance is required.

No alternate timelines, parallel universes, automatic merge/rebase, workflow
customization, Axtor, IG or video is implemented. M9B will add audience-aware
narrative guidance and next-scene suggestions. M9C will add media adaptation/shot
planning. M10 will expose these capabilities through difficulty/workflow UX.
