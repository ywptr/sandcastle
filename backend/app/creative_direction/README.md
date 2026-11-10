# Get Started and Creative Direction (SC#0004)

Sandcastle owns interpretation and creative choices; IG remains the later media
execution boundary. This milestone makes no media calls, creates no Episodes,
and stores no media bytes. M11/Nexus and M16 remain blocked independently.

## Product references and reconciliation

Reviewed [interactive Studio prototype](https://drive.google.com/file/d/1Sn-kldwNRNGfx6Mvcx_l_9T0mvSTyE_V/view)
and [Creative Direction handoff](https://docs.google.com/document/d/1hiG695VWKjA8Q3cDK5NlIgiRItDhqI591qgQ_77Fveo/edit).
Use their idea-first entry, four format choices, compact review and style drawer.
Do not copy prototype implementation, sample projects, fake AI chat, pricing,
quotas, publishing, or media execution. Preserve M14 workspace/domain contracts.
The handoff calls its styles proposed launch candidates, not empirically validated
media behaviors. Registry status is therefore `planning_preview`, visibly labeled
in the detail drawer. Text direction is editorial planning guidance, not a claim
of cultural authenticity or validated production quality.

## Semantic boundary and routing

`CreativeDirectionRecommender.recommend(data)` returns validated `Recommendation`.
The capability reuses the **creative_writer** role: recommendation is a creative
writing task and does not justify a new role/settings migration. The resolver
constructs operation-scoped OpenAI/Anthropic/Google recommendation adapters with
the same encrypted personal credentials and deterministic selection as SC#0000/2.
Provider details remain in adapters. One recommendation makes one structured text
call, with fixed official transports, existing timeouts and no automatic failover.
Trusted system instructions are separate from a serialized untrusted idea envelope.
No UI locale is sent. Explicit Story language, if supplied, is respected; otherwise
the model may infer language from the idea or leave it unspecified. The browser
renders a manual starting point after unavailable/failed recommendations, clearly
marked as non-AI; it never requires BYOK to create a Story.

Recommendation is ephemeral and authenticated. Unknown styles, malformed schemas,
format/language mismatch, unsafe provider errors, and invalid taxonomy fail safely.
Registry browsing never invokes a provider. No confidence score is claimed.

## Registry and taxonomy

`styles.json` is packaged backend product data with stable IDs/version `1.0.0`,
English/Indonesian names/descriptions and Indonesian detail guidance. Eight presets:

- `korean_romance_drama` — Korean Romance Drama
- `japanese_anime_inspired` — Japanese Anime Inspired
- `chinese_vertical_drama` — Chinese Vertical Drama
- `thai_lakorn` — Thai Lakorn
- `indian_bollywood_romance` — Indian Bollywood Romance
- `turkish_dizi_romance` — Turkish Dizi Romance
- `european_period_drama` — European Period Drama
- `american_cinematic_drama` — Hollywood / American Cinematic Drama

Each has region (browsing only), supported formats, narrative/dialogue/image/video
guidance, constraints and status. No ethnicity, nationality, religion, language,
culture or era is assigned from region/style. Do not overwrite registry versions
when behavior changes; publish a new version and retain approved snapshots.

Keep genre, secondary genres, tropes, style, rating, visual style, cultural setting,
era, language and tone independent. Existing M13 genre codes and three-secondary
limit remain unchanged, including historical/adventure/other/unknown. The handoff's
proposed 15-genre taxonomy was not silently substituted: Action & Adventure can be
expressed with existing adventure; expanded Family/Sports/Coming-of-Age categories
need a separate additive taxonomy review. No existing stored code was renamed.

Ratings: `all_ages`, `teen_13`, `young_adult_16`, `mature_18`. They are creative
classifications, never authorization for prohibited content. Visual style has its
own bounded choices; `match_style` is a separate stored value. Culture/era/tone are
optional bounded text; unspecified culture/era remain null. Period detail prompts
for era without blocking initial creation. Historical accuracy is not guaranteed.

## Approval and persistence

Migration `a062c8d4e132` follows `9e51b7c3d021`, adding only
`creative_direction_snapshots`: identity, authenticated user/Story, revision,
structured direction JSON, resolved versioned style snapshot, approval timestamp.
No giant prompt, new Story type, tenant ID, media blob, or Episode table is added.

`POST /api/stories/start` atomically creates an ordinary Story using the existing
StoryCreate schema and its approved direction. Failure rolls back both. Existing
POST /stories still supports advanced/manual callers and Stories without a direction.
`PUT` appends a snapshot; expected_revision and a unique Story/revision constraint
reject stale/concurrent approval. Past snapshots are never updated by the service.
Read returns latest; a dedicated history/rollback UI is deferred. Language at
approval is historical metadata; changing style never changes Story language,
Canon, Characters, Places, Scenes, or past production approvals. Subsequent Story
metadata language updates remain independent. The client strips the historical
language field before approving another revision.

## APIs

All routes require the current IS-authenticated user; identity/scope input is rejected.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/api/styles` | Versioned registry, no provider call |
| POST | `/api/styles/recommend` | Ephemeral typed recommendation; 503 if unconfigured, safe 502 on failure |
| POST | `/api/stories/start` | Atomic Story plus approved Creative Direction |
| GET | `/api/stories/{id}/creative-direction` | Latest approved snapshot or null; other user's Story is 404 |
| PUT | `/api/stories/{id}/creative-direction` | Append reviewed snapshot with expected_revision |

Existing M12A Import entry calls `/api/stories/import/analyze` and displays a
read-only proposal summary/evidence. It persists nothing. Full review/application
of import proposals remains SC#0005; analyzed text never becomes Canon automatically.

## Existing production architecture

Initial format is a planning preference, not a persistent Adaptation/Episode model.
Create adaptation directs the creator to Scene → Production on the **same Story**;
SC#0001 already creates format-specific approved plans for that Scene. It does not
create a duplicate Story. Story authoring works now; Webtoon/Short Drama/Reels are
planning-only. M4A quick planning and M4B execution approval semantics are untouched.

SC#0001's reserved `NarrativeMediaContext.creative_direction` is the downstream
extension point for these approved structured fields and resolved style snapshot.
It is deliberately not automatically populated in SC#0004: style-conditioned
writing/adaptation, digest/revision association and execution compilation require
follow-up validation. Neither existing prose nor production intent is rewritten.

IG owns generated media bytes/storage; Sandcastle stores semantic references and
associations. No duplicate persistent media storage is introduced here.

## Operations and validation

Apply development migrations only to positively verified local `sandcastle_dev`.
Any later production application is a separate explicit operator action under
[the canonical production procedure](../../PRODUCTION_MIGRATIONS.md); never migrate
production from acceptance, startup, tests or deployments.

## Implementation inventory and validation

Backend additions: `app/creative_direction/{schemas,registry,recommender,service}.py`,
packaged `styles.json`, `app/api/creative_direction.py`,
`app/db/models/creative_direction.py`, and migration `a062c8d4e132_creative_direction.py`.
Composition updates are in `app/main.py`, `app/llm/resolver.py`, model exports and
`pyproject.toml`. Focused API/migration tests are `test_creative_direction.py` and
`test_creative_direction_migrations.py`; historical migration fixtures exclude the
new table until its real revision is exercised.

Frontend additions: `api/creativeDirection.ts`, `GetStarted`, `CreativeOptions`,
`StyleLibrary`, `CreativeDirectionPanel`, `ImportStory`, and `i18n/{core,context,
resources,I18n}`. Updated App/main, StorySelector, StoryMetadataForm, StoryWorkspace,
AssistantPanel, SettingsPage and CSS. API/unit and onboarding/browser tests cover
the new slice; legacy harnesses account for the secondary Easy tools menu and
optional Creative Direction reads without dropping existing assertions.

Final results: 14 focused API/adapter/migration tests passed. Full backend suite:
191 tests passed, one expected opt-in skip. The separate opted-in PostgreSQL
fresh-bootstrap/migration regression passed both tests. Local Alembic heads/current/
upgrade/current/check verified `a062c8d4e132` with no drift. Frontend tests, lint
(with no warnings), and production build passed. Onboarding/localization, M14,
SC#0000/2 Settings, and SC#0001 browser suites passed. Real HTTPS sign-in entry,
401 proxy behavior, IS authorization redirect and HMR were checked by the M14
harness; authenticated editing used fixture APIs. No real authenticated provider
call or production database operation is claimed. Whitespace and changed-file
secret scans passed after reviewing synthetic test/documentation placeholders.

Known remaining gaps: downstream style-conditioned generation and editorial media
QA; complete Import review/persistence; account-synced locale; full deep-screen
localization; direction history/rollback UI; live IG execution and trusted tenant
AI. They are not implemented or implied by this onboarding milestone.
