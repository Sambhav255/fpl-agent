# Engineering decisions

## Repository and storage — 2026-10-09

Preserve the original root specifications and maintain working copies in `docs/`. Use a shared checkout with explicit file ownership for authorized parallel implementation. Persist versioned JSON entities in SQLite through SQLAlchemy; keep immutable source bytes and analytical Parquet under ignored local data storage.

## Contracts and manager state — 2026-10-09

Generate frontend schemas from Pydantic contracts. Record financial provenance, confirmation timestamps, and the transfer ledger explicitly. Separate lineup analysis from transfer analysis so unknown finances do not prevent useful lineup recommendations. Unknown hit totals remain unavailable. A marked real-world club transfer exception may retain an existing squad; proposed transfer squads obey club limits.

## Forecast integrity — 2026-10-09

Missing minutes, points, goals, and assists remain missing rather than becoming zero. Drop unknown minute labels from availability training; genuine zero minutes remains a non-appearance. TFT encoders use only information published by the forecast deadline, masking unavailable history. Bind strict training to panel checksums and audited replay timing. Publish model runs atomically from staging directories after checksum validation. Synthetic optional-library tests are installation checks, not live training evidence.

## Planner semantics — 2026-10-10

Save manager corrections only from explicitly confirmed facts. Selling estimates remain unknown until accepted; acceptance never creates a purchase price. Compare marginal chip uplift across eligible weeks. Include a weekly HiGHS candidate alongside horizon candidates, independently validate saved plans, and label bounded search without claiming global optimality. Advanced model adapters enforce artifact eligibility; they do not authorize promotion.

## Repository hygiene — 2026-10-10

Use Ruff for Python and pinned Prettier for frontend formatting. Exclude generated API artifacts from formatting. Preserve private session notes under ignored `docs/local/` and maintain current public handoffs. CI uses offline fixtures and synthetic demo state with a production frontend. Preserve lockfiles and local data. Do not invent a license or remote, or push as part of repository preparation.

The dependency audit identified an unpatched development-only ESLint dependency advisory. Preserve the compatible framework rather than applying the suggested major downgrade; recheck upstream when updating dependencies. Advanced models remain inactive until genuine data and chronological evaluation meet release requirements.

## Personal workspace and model status — 2026-10-10

Keep the personal default in ignored local environment configuration. Loading a saved profile is a GET, never an automatic public reimport. Model registry display is independent of the manager workspace; diagnostic evaluation does not imply activation. Preserve private state on repeated same-event/same-ownership imports and reject ambiguous replacements. Conditional lineup watchlists may describe price thresholds but never substitute unknown selling values or enable blocked transfer recommendations.

## Intelligence upgrade — 2026-10-10

Apply the v2 intelligence kit without replacing the app or its data. Prioritise objective correctness, prospective collection, honest real-data experiments and operational serving over cosmetic changes. Keep default champion promotion strict while allowing explicit future-live experimental challenger selection with real availability timestamps. Capture football versions without silently advancing current manager snapshots. Social access remains disabled; implement and test authored offline examples independently.

## 2026-10-12: scoped experiments and stale manager state

Advanced projections carry an explicit player universe. Recommendation, lineup and saved-plan validation restrict candidates to that universe and reject missing scheduled exposures; unforecasted players are never zero-score candidates. Every owned player must be covered. Baseline retains the full catalogue.

Football collection is a separate recoverable job and CLI. It retains observations without refreshing the active dataset or editing manager state. Repeating a completed capture starts a new capture; simultaneous identical requests deduplicate. Live social capabilities are reported unavailable and influence remains zero.

Official data now identifies GW7. Refreshing fixtures and prices intentionally preserved the GW6 private corrections; those corrections cannot be silently carried into GW7. The saved deadline report is historical. Reconciliation is needed before new legal personal transfer recommendations.

Independent review fixes: rollover confirmation is explicit at the API boundary; unrelated selling rows retain their prior market anchors. Availability scenario endpoints use a separate typed projection field so scoring components still sum to the expected value. Unstarted fixture placeholders are pending observations with null normalised outcomes, not nonappearance labels; raw immutable source statistics remain unchanged.

## 2026-10-12 — Canonical documentation and session entrypoint

Keep original product specifications only in docs/ and strategy upgrades only in docs/intelligence_upgrade/. Removed byte-identical duplicate folders/files and redundant combined copies. START_HERE.md is the tool-independent agent entrypoint; BUILD_STATUS.md reports the current integrated state rather than a contradictory chronological log. Preserve unique original prompts as reference and older status locally. Runtime data, dependencies and currently generated Next.js builds are preserved to keep the existing local application usable.
## Learning upgrade replay decisions — 2026-10-12

The supplied learning upgrade is indexed under `docs/learning_upgrade/`; original input files remain intact. Implement the isolated D04 replay engine first while leaving D02/D03 visibly pending; the full first learning release requires all three. Use one editing agent in this checkout.

Replay caps planning to provider support and remaining season instead of forcing every policy to one event. Greedy explicitly retains its one-event comparator definition. Full proposed paths are validated before executing only their first week. Forecast-path totals and scored-event totals are separate.

Strict replay requires a retained manifest digest from a trusted frozen reference, bound source/model/policy/mapping bytes, exact forecast/catalogue/schedule, actual availability timestamps and matching implementation. Historical reconstructed timing uses a simulated fitting-label cutoff separately from actual artifact creation. Existing `retrospective_assumed` callers remain unverified for compatibility; they cannot establish prospective evidence. A manifest proves consistency with the reference and recorded timestamps, not independent external timestamp attestation. D02 must supply automatic capture and immutable references before claiming a prospective benchmark. No new rule, chip or financial-transition behaviour is introduced.


## Learning upgrade D02 — 2026-10-12

Store decision and outcome data in additive SQLite entities. Freeze the recommendation and candidate set before the event deadline, including source/model/state fingerprints and forecast path. User selection, confirmed execution and paper action remain separate append-only reports; confirmation can only reference a frozen candidate and cannot be silently revised. Public manager state is not mutated by learning records. Outcome collection requires official event finalization and complete fixture-level coverage, retains provider bytes, and creates immutable revisions when upstream results change. Incomplete schedules or player coverage are unavailable and not scored. Synthetic-demo decisions cannot attach official labels. This additive choice does not alter FPL rules or financial transitions.


## Learning upgrade D03 — 2026-10-12

Generate one-event expanding folds with two minimum earlier training events and separate validation/calibration events. Purge every partition by label availability relative to the next event origin, and omit folds whose timing leaves an empty block. Keep the existing registered model configuration fixed during research evaluation. Score every eligible held-out event before fitting the serving artifact. Then build a new immutable serving refit from all final labels available by the captured fit cutoff, with no training-set calibration and no automatic promotion. This is the smallest chronological extension that preserves the existing CatBoost heads and their input contract; broad forecasting and ablations remain separate D05 work.


## Learning upgrade D05 — 2026-10-12

Keep small explicit collections as default. Add opt-in full-bootstrap membership capture, with a hard 1,000-player cap, exact sorted membership digest and bootstrap source binding; reject selector mixtures. Do not infer historical membership from today's universe. Compare a predeclared sequence of feature additions on common chronological folds, using validation for early stopping and held-out blocks only for reporting. Keep the existing full feature set fixed for serving rather than choose it by test performance. No automatic promotion.

## 2026-10-12 — learning research and publication boundaries

- Use budget-bounded financial-state dynamic programming for exact declared small-universe sequence checks. Retain the default bounded league planner and report scope/exhaustion honestly; never claim a full-league global MILP result.
- Freeze prices in RL research candidate continuations; explicit price paths belong to the numerical sequence planner. Stable hashed paper acquisition IDs preserve trajectory reproducibility without changing live transfer IDs.
- Fit real shared masked PPO policies and fitted-Q baselines, preselect the serving seed and retain numerical planning as champion. Synthetic paths and training seeds are not independent real football seasons.
- Keep optional RL/deep imports out of baseline startup. Normal policy training uses the existing recoverable local queue; a bounded explicit synthetic installation check may run directly. Worker publication, cancellation and implementation fingerprints gate cataloguing.
- Local review schedules are disabled by default. Scheduler execution is an explicit operator process and never edits finance, executes transfers or promotes a model. A cancelled review interval does not requeue itself.
- Authored semantic labels remain explicitly separate from independently double-reviewed human labels. No reviewed semantic model or live social provider was invented.
- Multilead TFT uses training-only global target normalization and contiguous non-feature window IDs to support unseen forecast origins. Marginal quantiles remain fixture marginals; no sum is labelled squad uncertainty.
- Complete Bayesian component sampling still declares temporal concession/BPS/partial-universe approximations. Research mean blends clear inherited model evidence and cannot inherit another family's artifact checksum.

## 2026-10-12 — advanced artifact adaptation

Multilead TFT adaptation follows the returned series/lead index, checks every known future fixture and rejects target-bearing decoder inputs. Legacy TFT remains one-event. Complete Bayesian adaptation requires an immutable scoring-profile payload, canonical mapping and a fit cutoff no later than the posterior fit; it never fills missing profiles with zeros. Both are inactive standalone contracts until qualified artifact registration. Common forecasts retain family/artifact/universe metadata instead of defaulting advanced outputs to baseline metadata.

Mean ensemble weights are fit on validation only, purged against held-out origins and retained with an immutable evaluation report. Inference verifies all payload hashes and physical artifact availability, ignores zero-weight unavailable families and exposes no unevaluated probability/quantile blend. Base forecast provenance still requires audit; experimental status never implies automatic promotion.

## 2026-10-12 — Audited advanced shadows and prospective journal seals

Advanced Bayesian/TFT/ensemble serving is opt-in shadow only. A local operator review publishes a fresh immutable qualified copy and cannot backdate the original artifact or bypass verified live provenance. Queued publication binds source bytes, frozen inputs, artifact/member checksums and implementation bytes. Research discovery remains distinct from release qualification; the baseline stays default. Ensemble output identities are deterministic; unvalidated probability/quantile mixtures remain absent.

Prospective journal replay uses a separately sealed pre-deadline reference to an already captured evidence packet. Sealing records actual local time and exact journal/manifest/policy bindings. Old unsealed decisions cannot be retroactively qualified. Finalized labels remain caller-supplied and execution records remain separate from paper replay. Local capture does not claim external timestamp authority.

Large financial sequence catalogues use lazy roll/one/two-replacement edges across the supplied universe, including chip weeks, while carrying the full financial state. Exhausted small-universe enumeration retains its exact label; restricted league searches never report an optimality gap of zero. This reversible scaling choice avoids rejecting a catalogue outright but does not implement a global full-league optimizer.

## 2026-10-12 — Repository organisation

Keep current entrypoints/status separate from historical narratives and unchanged source packages. Archive the original learning package under `docs/reference/supplied/` with a byte-checksum manifest; keep its combined specification there after verifying the maintained duplicate was identical apart from the corrected handoff path. Rebase historical Markdown links and index history explicitly. Keep backend/frontend modules, operator script paths, ignored runtime/private data and generated builds in place so existing services and commands remain valid.

Move the original design-only OpenAPI snapshot to `docs/reference/contracts/`. Generate the runtime OpenAPI and TypeScript bindings together offline via `scripts/generate_api.py` and `npm run generate:api`, using an in-memory store and the installed locked backend environment. This removes reliance on an arbitrary running API process and avoids reading private manager state for contract generation.
