# M12A — Import Story analysis

`POST /api/stories/import/analyze` requires the existing signed Sandcastle session.
It accepts pasted text only:

```json
{"content":"Mara follows a signal beneath the ice.","source_type":"summary"}
```

`source_type` is required and is `summary`, `draft`, or `notes`. Content must be
nonblank and at most **40,000 Unicode characters**, including whitespace; it is
never truncated or stripped. Empty/oversized/invalid requests return 422. Unknown
fields, including `user_id`, `tenant_id`, and `url`, are rejected. Authentication
and user ownership are unchanged; M11 is still blocked. There is no frontend,
file upload, URL fetching, chunking, or persistent import record.

## Proposal contract

The response is a typed `ImportProposal` (also documented in `/openapi.json`):

- `source_type` and server-computed `source_hash` (SHA-256 of exact UTF-8 content).
- `story`: nullable proposed title/premise/objective, detected language, advisory
  primary genre and up to three secondary genres, and source evidence.
- `characters` (up to 50): name and optional description, appearance, outfit,
  personality. Unknown attributes stay null.
- `places` (up to 50): name and optional description, appearance, atmosphere.
- `canon_candidates` (up to 100): type, optional subject name, fact type, key,
  value, classification, reasoning, and evidence. No database IDs or review actions.
- `events` (up to 100): description and `backstory`, `current`, or `unresolved` kind.
- `proposed_scenes` (up to 50) and `proposed_episodes` (up to 30): optional title,
  source-derived summary, and evidence. These identify scene-like sequences or
  actual chapter/episode boundaries; they do not generate prose or episodes.
- `unresolved_threads` (up to 50): questions with evidence, separate from facts.
- `contradictions` (up to 30): description, `clear`/`uncertain` classification,
  and at least two excerpts. These are review aids, not authoritative conclusions.
- `warnings` (up to 20): bounded advisory strings.

All proposal text is bounded: names 255, narrative fields 2,000, fact types 50
characters. Every source-derived item, including Story metadata, requires 1–5
verbatim source excerpts of at most 500 characters each. The server rejects the
entire result if evidence is absent, blank or not found in the original text.
Contradictions require at least two excerpts. Excerpts explain the source, but do
not prove an interpretation is correct. No full source snapshot is echoed.
Normalized exact duplicate Character/Place names with identical attributes are
merged and evidence combined (up to five excerpts). Incompatible duplicates fail
with 502 instead of silently discarding contradictory attributes. Alias resolution
and distinct people sharing a name require later review.

## Analyzer and provider

`StoryImportAnalyzer.analyze(request)` is the provider-neutral asynchronous port.
`ImportAnalysis` is the provider output; the service independently revalidates it,
checks source evidence, deduplicates entities and adds source metadata. Neither
port nor service receives a database session or authenticated identity.

The initial optional OpenAI adapter uses Responses structured output with a
Pydantic schema, following the [official structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs).
Install the already-declared SDK via backend dependencies and configure private
`OPENAI_API_KEY` and `SANDCASTLE_TEXT_MODEL` with a model supporting structured
outputs. These are the existing text-generation settings; there is no hard-coded
model or new provider dependency in domain logic. Imported content is sent to the
configured provider for analysis. The adapter sets `store=False`, uses no tools,
limits output to 12,000 tokens, disables retries and uses a 60-second SDK timeout.
Refusal, incomplete output, provider errors, malformed schemas or invalid evidence
return a sanitized 502; absent credentials/model/SDK return 503. There is no
simplistic deterministic fallback claiming equivalent semantic understanding.
Successful responses have `Cache-Control: no-store`.

Trusted system instructions and the JSON user-data envelope are separate messages.
Instructions embedded in imported prose remain untrusted content. No service
calls, database operations or tool execution are exposed to the model. Prompt
separation cannot guarantee semantic accuracy: the validated result remains a
human-reviewed proposal, never an executable operation.

Language and genre are model suggestions, not deterministic classifiers. Language
uses the shared bounded M13 codes `en`, `id`, `ja`, `ko`, `zh-CN`, `fr`,
`de`, `es`, or `und` when indeterminate/unsupported (previously arbitrary
syntactically valid two/three-letter codes were accepted). Genre uses the shared
enum fantasy, science_fiction, mystery, thriller, romance, horror, adventure, drama,
comedy, historical, slice_of_life, other, unknown. Secondary genres are unique and
exclude primary genre. Mixed/short text and genre ambiguity may
produce uncertain suggestions. No semantic accuracy claim is made from fake tests.

## Canon intelligence and persistence boundary

M7's `ExtractedCanonFact` vocabulary/validation is reused through an in-memory
conversion: type, subject name, property key/value, evidence, and explicit flag.
Import classification is **explicit / inferred / uncertain / conflicting**, which
is different from M7's **new / consistent / conflict / uncertain** comparison to
saved Canon. Do not equate them. M12A has no saved Story/approved Canon against
which to compare and never calls candidate persistence, approval, guidance writes,
authority, IG, or Axtor services. No IDs are fabricated. Contradictions concern
only the imported material, not an existing Story's Canon.

**An ImportProposal is not Canon and is not a Story until the user accepts it in a
later persistence workflow.**

The route has no database dependency. It writes no Story, Character, Place, Scene,
Canon entry/candidate, Universe, Workflow, Artifact or execution. Repeated analysis
may produce different model suggestions but cannot mutate application state.
Tests install a failing database dependency, prohibit SQL during repeated calls,
and compare all isolated database table rows before/after. Adapter tests mock SDK
calls, including prompt separation, refusal and incomplete output. No automated
test contacts live providers or the persistent `sandcastle_dev` database.

```sh
cd backend
.venv/bin/python -B -m unittest discover -s tests -p test_story_import.py -v
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/alembic heads
```

No migration is needed. M12B should review ownership readiness separately, display
editable proposals and source excerpts, revalidate accepted payloads, resolve
entity references, and persist selected items transactionally only after explicit
acceptance. Candidate approval must remain distinct from import acceptance; no
automatic promotion to Canon. Bind review to the exact source hash and provide
idempotency for acceptance. Those workflows are not implemented here.

Historical M12A validation (before M13): 12 focused Import tests and all 122 backend tests passed. The installed
SDK successfully generated the strict structured-output schema without defaults.
`alembic heads` remains `f15d7b92a640`; no migration or persistent database command
was run for M12A. Whitespace validation passed. No live provider quality test or
browser test is claimed; no frontend was added.

M13 now provides [persistent Story metadata](../stories/README.md). Future M12B
maps `proposal.story.detected_language`, `primary_genre` and `secondary_genres`
to Story fields only after user review. M12A continues to perform no writes.
