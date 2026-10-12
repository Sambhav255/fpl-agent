# Build status

Updated 2026-10-10. The baseline application is implemented and locally verified. Advanced ML-backed strategy is the remaining product priority. No advanced model is active. Git preparation does not publish the application or submit FPL actions.

## Ownership

The lead owns integration, contracts, configuration, generated types, dependencies, and release checks. Earlier implementation agents completed their scoped backend, rules, frontend, and model work; independent review findings were addressed. Repository cleanup is performed in the existing checkout, preserving user changes and local data.

## Milestones

| Area | Current state |
| --- | --- |
| Local application | Next.js interface, FastAPI, SQLite and recoverable worker implemented |
| Rules and state | Season configuration, money, formations, transfers, chip inventory, captain fallback and substitutions tested |
| Import and providers | Validated public import, caching, immutable snapshots, manual corrections and unknown-state handling implemented |
| Baseline decisions | Labelled projections, legal lineup, transfer comparisons, weekly plans, persistence and stale-input checks implemented |
| Horizon planning | Up to eight events using bounded beam/HiGHS candidates; frozen prices and approximate terminal policy disclosed |
| Historical/CatBoost | Audit/features/training/evaluation pipeline and retrospective diagnostic artifact; strict activation blocked |
| Bayesian | Real optional sampling pipeline and strict adapter; calibrated minutes/full scoring and real evaluation incomplete |
| TFT/ensemble | Real optional one-event fit/inference pipeline, deadline encoders and adapters; multiweek decoder, real evaluation and ensemble activation incomplete |
| Git preparation | Source formatting, grouped ignores, documentation index, contributor guide and offline CI workflow added |

## Verification

Cleanup backend checks: **194 passed, 3 skipped**; Ruff lint and format checks passed; mypy passed for **34 source files**. Frontend lint, generated route types, typecheck, **11 unit tests**, and the production build passed. Typechecking the clean snapshot also passed without pre-existing Next.js output. Final production Playwright verification passed **14/14 tests** on desktop and mobile, including independent Models display, configured default profile without import, demo corrections, caps, saves, stale state and the real financial gate. Earlier runs exposed an over-specific selector, initial loading races, and a concurrent demo smoke collision; those were corrected, and the final suite ran serially without weakening assertions.

Previous milestone checks: frontend lint/typecheck, **9 unit tests**, production build and **10 production browser tests** passed. Optional real-library checks passed **41 tests** using synthetic fixtures. Public import and live unknown-price gate were verified without submitting transfers or changing unconfirmed private values. Synthetic optional training is not model-performance evidence.

CI is configured but has not yet run on a hosted Git provider. The frontend dependency audit reports five high-severity entries in the development-only Next.js ESLint dependency chain, rooted in the unpatched `braces` advisory. Production-only dependency audit passed with **zero vulnerabilities**. Actual API/worker integration smoke passed again after the API restart. Optional live public-team smoke also passed, including legal lineup persistence and preservation of manager finances.

## Personal-profile and Models fixes

Personal default configuration is read from ignored frontend environment settings; loading it never submits an import or overwrites state. Models now load independently of manager state, with refresh/error handling and clear inactive/diagnostic labels. Repeated identical public imports preserve private corrections and unknowns with CAS protection; changed season, event or ownership returns a review conflict. These behaviors have unit/API tests and independent review.

A private, timestamped baseline strategy report and conditional transfer watchlist are saved locally under ignored `docs/local/`, with live projection/analysis artifacts under `data/`. A legal lineup-only Keep plan is persisted; no transfer or chip was submitted. Selling prices have now been explicitly confirmed from the user’s transfer-page screenshot; private manager state version 8 is transfer-ready. Purchase prices remain unknown and were not inferred.

## Running services

Final production interface: http://127.0.0.1:3001 (built with `NEXT_BUILD_DIR=.next-release-v2`, served with `NEXT_BUILD_DIR=.next-release-v2 npm run start -- --port 3001` from `apps/web`). Development interface remains at http://127.0.0.1:3000. API was restarted with the tested import fix at http://127.0.0.1:8000; worker remains running. Temporary superseded production servers were stopped.

## Runtime and data

Use `bash scripts/dev.sh` from the repository root. Interface: http://127.0.0.1:3000; API: http://127.0.0.1:8000/docs. The local database is `data/app.sqlite`; source snapshots and analytical/model artifacts also live under ignored `data/`. Existing state and artifacts are preserved. Private historical session notes are retained under ignored `docs/local/`.

## Blockers and exact next steps

1. Obtain deadline-verified historical source bundles, fixtures, deadlines, and explicit cross-season player/club mappings; audit their immutable timestamps.
2. Complete calibrated Bayesian minutes/scoring and TFT multiweek decoding; run genuine chronological training, validation, and untouched-test evaluation.
3. Bind evaluated artifacts, mappings, source versions and input fingerprints into recoverable prediction jobs and registry eligibility; activate only after passing those checks.
4. Fit ensemble weights on eligible validation forecasts and report held-out strategy/model results honestly.
5. Confirm required private financial state in the interface before real transfer recommendations. Unknown values remain blocked.
6. Review the diff and dependency advisory. Existing history contains earlier personal notes; use the clean source snapshot for a new public repository unless publishing that history is intentional. No Git push is performed by this cleanup task.

## Intelligence upgrade — in progress

Upgrade kit imported under docs/intelligence_upgrade, originals preserved. Audit baseline e759bcf matches current HEAD; working tree was clean apart from the new kit. Reproduced actual synthetic search counterexample: Keep84, returned94, legal exhaustive funding pair101; injury flag incorrectly persists zero through eight events. These are software fixtures, not measured real-team improvements.

Ownership: lead shared contracts, API, jobs, router, CLI, registry, generated types and integration. Godel owns optimisation/planner plus new oracle/replay modules and tests. Confucius owns new prospective collection module/tests and collection report. Newton owns new football feature/CatBoost modules/tests and real experiment report. Peirce owns new social subsystem/tests and offline extraction report. No concurrent shared-file edits.

Next: fix and lock search regression; capture current football without overwriting manager state; fit a qualified real historical CatBoost challenger; freeze artifact selection in projection jobs; integrate collection jobs and offline social status; run independent review and full checks. B01–B06 first intelligence release is not complete. Social providers remain disabled. Existing advanced models are not promoted.

## Deadline decision run — 2026-10-10

Priority: personal GW6 transfer decision before 10:00 UTC. All 15 displayed selling values and the user-confirmed financial state are persisted through validated CAS API, state version 8. No account action performed. Private reports remain ignored under docs/local/.

Completed: Godel fixed synthetic funding oracle (84/94/101), ownership/XI/captain candidate objective and bounded replay; scoped 121 checks passed. Confucius captured official bootstrap, fixture and 30 selected player histories at 06:56 UTC: immutable collection 5ca9f12d261942b69ba6c69e693cb1bb, 150 labels, no historical publication claim. Newton fitted real archive/current-era football CatBoost experiments; current GW6 artifact 20261010T070056-0125fbba is experimental only. Tiny current test RMSE 4.502 versus population 4.463, so not promoted. Peirce delivered offline social baseline (22 tests), external adapters disabled, then independent review assigned.

Verification: full backend 248 passed, three skipped; source/test Ruff passed; backend-configured mypy passed 47 files. Deadline baseline one/two event plans were independently validated, but their model means are approximate and do not justify automatic adoption. Bayesian real team-goal diagnostic is running; full player scoring remains incomplete. TFT eligibility checks actually ran: five events below eight-event minimum, verified historical audit absent. No ensemble promotion.

Exact next steps: finish Bayesian diagnostics and sensible limited-transfer cross-model comparisons; review availability and held-out weaknesses; write personal decision report. Integrate compatible artifact schema and immutable forecast adapter/bundles (router currently baseline only; no silent fallback), collection jobs/CLI, social status API; regenerate contracts and restart API/worker, run UI/build/browser checks. Full multi-event financial MILP, future chip optimisation, audited evolving-policy replay and full Bayesian/TFT evaluation remain unfinished.

Deadline update: real Bayesian50-match team-goal fit completed at07:04UTC, converged (Rhat1.01, ESS534, zero divergences), still partial/unpromoted. Legal fixed comparisons and personal decision are retained in ignored docs/local/DEADLINE_DECISION.md. Frontend3000/3001 and API8000 returned200; statev8 and15selling prices verified. Advanced router integration and full upgrade remain pending.

## Resume — 2026-10-12 UTC / October 11 Chicago

Current repository HEAD a43db4f includes the preceding parallel work. No existing changes were discarded. Lead owns API/jobs/contracts/registry/UI integration. Newton now owns router/tests and a forecast preparation CLI; Confucius owns the collection CLI/root tests; Godel owns availability horizon corrections/tests; Peirce independently reviews correctness and leakage.

Fresh official collection 2978d1299a354ab6882cb4600de34e39 captured at04:21UTC:30players,180labels; GW6 rows are preliminary, not final outcomes. NextGW7 deadline2026-10-17T10:00Z. Lead refreshed active football data, preserving private state6340295v8 unchanged; active snapshot e3737218dc41498483b55abaad66ebf1 now differs from the saved GW6 manager snapshot. New personal recommendations must wait for review/reconciliation; no transfers or chips submitted.

Implemented collection API/worker jobs, disabled social status API, explicit scoped forecast coverage validation, Football CatBoost registry entry and honest Models-page label. Focused shared tests pass. Frontend lint/typecheck/11unit tests and isolated production build passed. Full backend/serving/browser checks await router agent completion; temporary full-suite failures during its partial edit were not accepted as a completed build.

Next: finish real router and immutable serving bundle integration, prepare a GW7 experiment using completed labels only, complete independent review, restart API/worker, regenerate API types and verify browser flow. Future injury availability must be an explicit scenario, not a fabricated calibrated recovery forecast. Full chip scheduling, complete Bayesian scoring, multiweek TFT and promoted ensemble remain pending.

## Integrated intelligence stage — verified 2026-10-12

Implemented and integrated: real Football CatBoost adapter, checksum-bound serving bundles, explicit experimental/default selection, source/feature/mapping/availability/deadline gates, known-absence replacement once with raw forecast provenance, and scoped candidate-universe validation for worker recommendations, lineup and saved plans. No uncovered player is treated as zero. Optional failures do not silently become advanced-model-labelled baseline forecasts.

Models page now lists the real Football CatBoost experiment and provides a one-event challenger-versus-baseline comparison through API/worker jobs. Personal default remains the ignored environment configuration for 6340295; loading never reimports. Collection has reproducible CLI, recoverable jobs, retained sources, typed positive-ID validation, status/coverage endpoints, optional Parquet and disabled social capabilities. Root CLI tests are included in CI/check.sh.

Latest real artifact: football_catboost/20261012T043103-339bf843, actual GW7 forecast origin2026-10-12T04:31:03Z. Training/future lags use150final GW1–5 labels;30preliminary GW6 rows excluded. Held-out assumed-timing GW5 sample30rows: CatBoostRMSE4.5017/MAE3.7520 versus populationRMSE4.4634/MAE3.7444. Not promoted. Fresh catalogue bootstrap exactly matches retained training collection source; serving is still blocked because the private manager state is GW6/stale. No bank, FT, selling value or chip was inferred for GW7.

Future baseline availability no longer repeats an injury-zero through eight events. Future values are explicitly conditional available-player planning scenarios, appearance probability unknown, and flagged-player zero/available endpoints separate from scoring components and confidence quantiles. This is a scenario correction, not calibrated recovery modelling (B07 remains partial).

Independent reviewer Peirce found two P1 finance issues. Fixed: new-event populated private confirmations require an explicit API rollover-review flag; Settings clears draft private confirmations and exposes the review checkbox. Selling-market anchors change only for explicitly accepted selling rows. Reviewer accepted both fixes; focused regression checks passed. Collector audit also identified an unstarted match placeholder; future normalisation marks pending_fixture with unknown points/minutes and separate pending coverage, retaining original source statistics. Immutable older collections were not rewritten; current model had excluded the entire preliminary event already.

Milestones: B01 working with exact synthetic oracle; B02 candidate objective/oracle/replay working but full multi-event MILP and chip scheduling incomplete; B03 collection integrated; B04 qualified real experiments completed without promotion; B05 routed experimental backend/UI integrated; B06 bounded replay machinery tested, no audited historical policy benchmark; B07 explicit scenarios only; B08/B09/B12 incomplete; B10 offline subsystem/status integrated without live access or accuracy claim; B11 unavailable.

Verification: backend full tests292passed3skipped (one existing FastAPI/Starlette deprecation warning), Ruff/check/format and mypy47source files; root CLI13tests; frontend lint/typecheck13unit tests and final production build; actual production desktop/mobile16browser tests passed (demo corrections, legal plan/save/reload, planner controls, independent model registry, default profile, stale financial/experimental gates). Actual API+worker source-only collection job succeeded and preserved personal state exactly. No cloud CI run, Git commit/push, account transfer or chip action was performed.

Running: development3000; final production3001 (NEXT_BUILD_DIR=.next-upgrade-final npm run start -- --port3001 from apps/web); API8000, separate worker. General startup remains bash scripts/dev.sh after locked dependency install; README documents experiment commands. Private reports/models/database remain ignored under docs/local and data.

Precise next actions: review the current public/deadline squad and private GW7 inputs in Settings before saving event7 (unknowns may remain for lineup-only analysis); validate/register the prepared bundle and compare its forecasts, keeping baseline default. Continue full multi-event financial/chip optimisation and broader prospective evaluation. Complete Bayesian full player-scoring pipeline, multiweek TFT and ensemble gates after sufficient audited data; TFT current-era five completed events remain below its eight-event chronological minimum. Do not describe the complete build or any model advantage as achieved.
