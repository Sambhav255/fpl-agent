# B10 offline social subsystem

Implemented 10 October 2026 within the Social agent's assigned paths. This is a
conservative deterministic extraction baseline and descriptive sample aggregation,
not a trained NLP model, activated feed, or football forecast.

## Lead integration contract

Import from `fpl_app.social`: `Capability`, `SocialPost`, `SourceProfile`, `Extractor`,
`SocialStore`, `Coverage`, `aggregate`, `RedditAdapter`, and `XAdapter`.
Records are frozen Pydantic models with forbidden extra fields and aware timestamps.
Access flags default false, including training and external processing. No network
client, credentials, external LLM, NLP downloads or new dependencies are used.
Reddit/X adapters always return unavailable and raise on fetch. These are disabled
official-provider placeholders, not implemented live clients.

Use a dedicated SQLite path for `SocialStore`, separate from the existing private app
state and separate for synthetic versus permissioned datasets. Call `close()` afterward.
No API, job, frontend, shared-schema, manifest, private-state or shared build-status
changes were made. Lead owns endpoint/status wiring and the build-status update.

- `review(profile)` records manually reviewed category, roles, evidence, reviewer,
  topic scope, effective/review/expiry timestamps and version. No real experts are
  pre-vetted. Unknown authors/topics stay unknown; explicit crowd review is required.
  Classification is frozen as known at each claim's observation time. Later reviews
  cannot promote earlier claims. Consolidate author IDs only using reviewed identity
  evidence; this subsystem never infers anonymous cross-platform identities.
- `Extractor(aliases)` takes aliases mapping to candidate canonical player IDs.
  Ambiguous names abstain. The caller supplies the season-specific entity dictionary;
  synthetic names are never registered as real player mappings.
- `ingest(post, capability, extractor, now)` requires matching capability/provider,
  storage/inference/derived-feature rights and finite retention. Manual ingestion does
  not confer read rights. Synthetic posts require the synthetic label. IDs must be
  provider-prefixed. Explicit context IDs preserve dependent source lineage. Future
  observation/edit times and stale observations are rejected. Replacing a post removes
  its old claims. Serialize writes in the future worker; no shared API concurrency
  contract is implemented here.
- `claims(as_of)` purges expired posts and their context-dependent descendants before
  returning retained claims. `delete(post_id)` removes text/claims and context
  descendants; ID-only tombstones block reingestion. `purge_expired(capability, now)`
  also handles revoked storage rights. Schedule cleanup even without UI reads.
  This mutable store is not a historical replay archive: future as-of queries perform
  destructive expiry cleanup, so do not use them to simulate forecasts.
- `aggregate(store, player_id, topic, horizon, group, coverage, as_of)` recomputes from
  retained claims, so deletions cannot leave a cached vote. Supply truthful bounded
  coverage. Missing/empty/stale coverage yields no distribution or ESS. Future windows
  are unavailable. Conditional, quoted, question, negated and abstained claims do not
  become actionable votes. Groups, topics and horizons remain separate.

## Baseline scope and assumptions

Claims retain spans/offsets, attribution, questions, negation, conditions, limited
explicit horizons, funding dependencies and abstention reasons. Explicit action grammar,
aliases and simple singular pronouns are supported. Funding includes “Palmer is
brilliant, but sell him to fund Salah.” Unresolved multi-player clauses abstain.
Recognized humour/sarcasm markers abstain. Availability reports retain context without
inferring start probabilities or updating availability scenarios.

Evidence families use supplied report/original identifiers or normalized exact-text
hashes as a conservative fallback. No embeddings or paraphrase clustering exist.
Author/family duplicates collapse; conflicting actions within an author/family become
unclear. Weight is reciprocal author-family count times reciprocal family-author count,
bounding prolific authors and copied reports. These are illustrative predeclared
weights, not learned reliability. Engagement is unused.

ESS is computed over resulting **author weights**, not independent evidence. Two
authors repeating one report can have author ESS 2 and only one evidence family;
both counts are exposed. No confidence intervals, population sentiment, momentum,
freshness decay, source reliability or predictive improvement are asserted. Freshness
is limited to caller coverage windows. `points_adjustment` is constrained to zero.
No social features enter training, and no implicit processing rights are inferred.

## Verification actually run

From `backend`, with the existing virtualenv:

```sh
.venv/bin/pytest tests/test_social.py -q
.venv/bin/ruff check src/fpl_app/social tests/test_social.py
.venv/bin/ruff format --check src/fpl_app/social tests/test_social.py
.venv/bin/mypy src/fpl_app/social
```

**22 passed**; focused lint, format check and typecheck passed (7 source files).
Authored synthetic cases cover aliases, ambiguous surnames, attribution/quotes,
negation/contractions, questions, conditions, funding, multiple players and jokes.
Lifecycle/aggregation checks cover edits, descendant deletion, tombstones, expiration,
reopening SQLite, access flags, topic reviews as-of, future timing/coverage, copied
reports, prolific authors, contradictions and expert/crowd separation.
No live-provider, application-wide or frontend checks were run for this isolated change.

## Blockers and concrete next steps

Live access requires current terms verification, exact-use approvals, credentials,
retention/processing rights, cost caps and bounded sampling, followed by official
collection in a recoverable worker. These adapters cannot enable live collection.
No current provider policy or pricing was re-verified for this offline implementation.

Extraction release requires independently adjudicated held-out permitted text,
reviewer agreement, entity precision/recall, action macro F1 and error breakdowns.
Authored development fixtures are not an adjudicated benchmark: **no 95% precision
claim is made**. Arbitrary syntax, complex quotation scope/pronouns, implicit actions,
unmarked sarcasm, paraphrases and full temporal interpretation remain unsupported.

Lead next step: wire disabled status and retained synthetic claims under existing
API/status ownership with visible synthetic labels and unavailable coverage. Before
live analytics, add recoverable ingestion/retention jobs, comprehensive rights
revocation, edit invalidation for separately retained quoted context, and reviewed
identity/entity validation. Forecast influence requires permitted chronological
ablation and calibration; B11 remains unavailable.
