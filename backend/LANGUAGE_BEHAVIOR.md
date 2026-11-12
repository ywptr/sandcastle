# C2 language behavior contract

## Existing fields and operations inspected

Story.language is a nullable bounded code: en/id/ja/ko/zh-CN/fr/de/es/und. It is returned by creation, list/read and PATCH. UI locale is separate browser preference sandcastle.uiLocale. CreativeDirectionSnapshot.direction_json.language_at_approval is historical immutable provenance. ImportProposal.story.detected_language is advisory; import remains analysis-only with verbatim evidence.

RecommendationInput.language constrains a proposed Story language; its model-authored rationale is an existing assistant response. SceneGenerationContext.language currently governs prose regardless of instruction language. Narrative guidance is deterministic localized advisory scaffolding, not an LLM. Production translation generates typed proposals, preserving exact source excerpts; technical directions may be English.

OpenAI/Anthropic/Google adapters accept explicit instructions through shared compiled prompts or typed envelopes. There is no general-purpose chat service, statistical detector or provider-specific language capability discovery. Story metadata PATCH has no revision counter; add optional expected_updated_at, used by modern language editing, while preserving legacy callers. Creative Direction expected_revision stays independent.

## Deterministic precedence

UI: English first visit; explicit en/id/auto preference authoritative. Never use UI locale for language resolution.

New creation: language_mode=automatic is creation-only. Server detects premise; creator sees and confirms concrete language before creation. Recompute on submission and reject a stale/inconclusive confirmation. Explicit selection bypasses uncertainty. Persist approved concrete Story.language, not a moving Auto lock. Legacy requests without language_mode retain nullable semantics.

Production: typed operation output_language > saved concrete Story.language > detected premise only in new automatic creation > disclosed English fallback for legacy null/und. Natural-language instructions cannot change this precedence. Operation overrides never mutate Story language or Canon.

Conversation: explicit response_language > confidently detected current message > client-supplied confirmed conversation_preference > disclosed saved-Story-language fallback, otherwise English. Apply to recommendation rationale, advisory suggestions and bounded generation receipts. Scene prose is production content; localized application receipts are not invented AI chat.

## Detection, uncertainty and validation

Use server-side langdetect character-ngram statistical profiles with deterministic seed 0, explicit codes and und. No browser-language assumption or frontend regex is authoritative. Ignore quoted/code material for dominance when meaningful surrounding prose exists. Short/ambiguous, closely balanced mixed and unsupported text require creator review for automatic creation. Relative model scores are not calibrated probabilities. Bound input, cache detector only, never raw text/results.

Check sufficiently long generated prose, recommendation rationale and production dialogue/captions/voiceover/on-screen text against the effective language. Exclude IDs, exact source excerpts, names and technical directions. Clear mismatches fail before Scene persistence or plan approval; ambiguous/short outputs are disclosed as unverified. Do not silently overwrite approved content or automatically retry/spend on another model.

## Provenance / compatibility

One additive nullable JSON Story.language_provenance column: source, effective/previous code, detector version/score/status where relevant, timestamp. No raw detection text or logs. A second additive nullable JSON StoryAction.language_context column records operation provenance. Existing rows are not rewritten; legacy language codes remain authoritative. Approved Creative Direction retains language_at_approval. Scene action audit and production plan JSON carry operation resolution; advisory responses expose it without adding chat persistence.

Optional Story expected_updated_at rejects stale modern edits with 409; old callers remain valid. The editor retains a stale draft while fetching the latest saved values; replacement requires an explicit creator action. No automatic rebase/approval, style/culture inference or translation of stored canon/characters. No unrelated migration is needed. Test migrations in isolation / sandcastle_dev only; never implicitly migrate production.

## Scope / acceptance

Eight existing language targets through configured OpenAI/Anthropic/Google text adapters and deterministic guidance. No universal language/model-quality claim. Unknown/unsupported/ambiguous prompts are explicit review/fallback states; unsupported override codes are rejected. Import preserves original evidence and does not create a Story. Existing production excerpt, revision and staleness safeguards remain.

Controlled adapter and API tests, including cross-owner requests, are required. No live AI spending is authorized; actual authenticated/provider quality remains unverified unless separately exercised with authorization.

## Validation and release boundary

218 backend tests passed (one pre-existing opt-in PostgreSQL test skipped). Frontend checks and nine browser suites passed. The C2 browser flow uses real signed-session validation, services, statistical detection and isolated SQLite persistence with test identities and controlled providers. Unauthorized/cross-owner requests are rejected. No paid provider generation, real authenticated IS login, development/production migration or deployment occurred. Apply migration b174d9e5f243 to a verified target before release; real provider/model quality remains unverified.
