# M13 — persistent Story language and genres

Story language is persistent project metadata and generated story content should follow it unless the user explicitly changes it.

Genre guides creative behavior but is not Canon.

## Contract and storage

Authenticated Story POST, GET/list and PATCH expose `language`, `primary_genre`,
and `secondary_genres`. Ownership and all existing IS/authority boundaries remain
unchanged; M11 is still blocked. Existing clients may omit all three fields.

```json
{"title":"Taman","language":"id","primary_genre":"romance","secondary_genres":["drama"]}
```

Language codes are bounded to `en`, `id`, `ja`, `ko`, `zh-CN`, `fr`, `de`, `es`,
and `und` (indeterminate). Surrounding whitespace and case normalize, including
`ZH-cn` to `zh-CN`; display labels and unsupported codes return 422. This deliberately
small product vocabulary lives in `metadata.py`. Expand the shared Literal and
language names together, add localized guidance scaffolds, tests and future UI
labels when introducing another language. No language detection occurs on writes.
`null` means unspecified, and `und` also imposes no output-language instruction.
Neither value guesses a language from existing content. UI/browser language never
overrides a specified Story language.

The shared M12A genre taxonomy is `fantasy`, `science_fiction`, `mystery`,
`thriller`, `romance`, `horror`, `adventure`, `drama`, `comedy`, `historical`,
`slice_of_life`, `other`, `unknown`. Primary genre is nullable. Secondary genres
are an ordered JSON array of at most three taxonomy values, unique and excluding
the primary genre. Duplicates are rejected, not silently removed.

PATCH updates only supplied fields; `language` and `primary_genre` may explicitly
be cleared with null; `secondary_genres` is replaced with an array (empty to clear,
never null). Validation checks the merged persisted state. When changing primary
to an existing secondary, supply a compatible replacement secondary list in the
same PATCH. Invalid values/merged combinations return 422 without writes.

Migration `7c2e91a4b830` follows `f15d7b92a640`, adding nullable String(16) language,
nullable String(30) primary genre and non-null SQLAlchemy JSON secondary genres
with Python and database defaults of `[]`. PostgreSQL and SQLite are supported.
Historical Stories receive null/null/[] without inference, translation, provider
calls or changes to prose, Canon or owners. Downgrade removes only these columns
and consequently discards this metadata.

## Creative context

Scene generation receives structured language and genre fields on
`SceneGenerationContext`. The adapter compiles an explicit output-language rule
that takes precedence over a request written in another language, and soft genre
instructions for tone, pacing, plot and style. Legacy null/und language adds no
language instruction. Generating a Scene never changes Story metadata or Canon.
Provider compliance is not guaranteed by a prompt; tests use fakes, not live models.

Narrative guidance receives the same fields and provider-neutral constraints.
The deterministic fallback retains existing audience-specific English scaffolds
for null/und/en and uses conservative localized scaffolds for other supported
languages. Genre identifiers provide a soft tone/pacing cue. These scaffolds do
not offer semantic genre-specific plot understanding; localized variants use
simple, gentle language for all audiences. Stored Canon, feedback and prose are
never translated. The older optional guidance-profile free-text `genre` remains
an advisory note for compatibility; Story taxonomy fields provide stable project
context, and neither can override Canon/audience/maturity constraints.

M10 narrative-guidance actions call the same service and therefore receive fresh
Story metadata. Existing scene-generation actions also use the shared service.
No templates, workflow selection, execution policy, Canon extraction or media
adaptation are redesigned.

## M12A and future M12B

M12A and Story persistence now share the same Language and Genre types. Previously
M12A accepted any syntactically lowercase two/three-letter language identifier;
M13 deliberately bounds this to supported codes, adds `zh-CN`, and instructs the
analyzer to return `und` for unsupported/indeterminate languages. Duplicate genre
suggestions are now rejected. Source-derived text is still not translated.

Future mapping, after explicit user review:

```text
ImportProposal.story.detected_language → Story.language
ImportProposal.story.primary_genre → Story.primary_genre
ImportProposal.story.secondary_genres → Story.secondary_genres
```

M12A remains analysis-only with no database dependency or writes. M12B acceptance,
transactions and persistence are not implemented. Genre is separate from Canon,
never supplies facts and never becomes an Axtor policy rule.

## Validation and M14

Run `test_story_metadata.py`, `test_story_metadata_migrations.py` and the full
backend suite. The PostgreSQL bootstrap test is opt-in:

```sh
SANDCASTLE_TEST_POSTGRES_BOOTSTRAP=1 .venv/bin/python -B -m unittest discover -s tests -p test_story_metadata_migrations.py -v
```

It reads private local `.env`, verifies loopback/database/role `sandcastle_dev`,
creates a uniquely named temporary schema, applies the entire history, verifies
legacy defaults and M13 downgrade/upgrade, checks drift, and removes that schema.
It never creates/drops a database or touches public application rows. Ordinary
tests use isolated SQLite and offline PostgreSQL SQL compilation. Historical
SQLite migration fixtures need the existing synthetic pre-M13 baseline because
the historical owner migration uses PostgreSQL ALTER COLUMN syntax.

M13 is backend-first; no frontend changes. M14 can add a Story overview/settings
language selector (separate from UI language), primary selector and three-value
secondary selector, explicit clear/update actions, and reviewed import mappings.
Show legacy unspecified values without inference, describe genre as advisory,
and allow coordinated primary/secondary replacement. Broader translation UX,
automatic workflow recommendations and import persistence remain deferred.
