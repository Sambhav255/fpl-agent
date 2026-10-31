# GW9 model review — 31 October 2026 UTC

This is a new executed review. Sources, private portfolios, checkpoints and reproduction scripts are retained under ignored `data/research/gw9-models-2026-10-31/`. No FPL account action or champion promotion occurred. Earlier reports remain unchanged.

## Current capture and fitting

The existing backend collector captured the full 669-player official universe, 671 source snapshots and 5,220 finalized player-fixture labels across GW1–8. Capture completed at 01:56:25 UTC, before the GW9 deadline at 11:00 UTC. Missing historical rows were retained as missing rather than fabricated zero appearances. Source envelopes bind original bytes, capture/availability times, mappings and hashes.

| Executed path               | New result                                                                                                                          | Limit                                                                                             |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Existing baseline           | 4,014 forecasts across six events                                                                                                   | Heuristic means; future availability conditional; defensive contributions not explicitly forecast |
| Football CatBoost           | Four expanding chronological test origins, GW5–8; separate latest-data refit and reload                                             | Historical publication, membership and schedules reconstructed; inactive research                 |
| TFT mean and quantile heads | Genuine CPU fit, checkpoint reload, untouched GW7–8 test, separate current refit; 610 players with complete explicit GW1–8 coverage | Two epochs, one lead; retrospective timing assumptions; qualification remains blocked             |
| Bayesian team goals         | Fit on GW1–6, score GW7–8, separate GW1–8 refit                                                                                     | Partial team-goal model; complete player scoring gate fails missing explicit components           |
| Mean ensembles              | Nonnegative weights fitted on GW5–6; tested on GW7–8                                                                                | No test-based model selection or automatic promotion                                              |
| Fitted-Q and MaskablePPO    | Actual training on GW2–6; five fixed 64-step PPO seeds; GW7–8 test                                                                  | Bounded 40-player hypothetical research universe, one actual season/path                          |

CatBoost's four-fold RMSE was **2.1405**, against **2.3660** for the reconstructed app baseline and **2.2749** for rolling points. Rolling minutes/points had lower MAE than CatBoost. These are retrospective assumed evaluations, not prospective forecast scores.

A descriptive GW7–8 subgroup check used only prior five-match minutes to identify plausible starters. Across 356 such rows, CatBoost RMSE was 3.2581 versus reconstructed baseline 3.3388. Across the **38 forward rows**, CatBoost scored **3.9749**, baseline **3.9297**, and rolling points **3.5896**. The global win therefore does not establish a forward-selection advantage. This check did not retune features or weights on the test.

On identical 1,220 player-event rows in GW7–8, CatBoost RMSE was **2.1548**, TFT **2.2270**, and reconstructed baseline **2.4005**. The predeclared baseline/CatBoost blend scored **2.1547**; its validation weights were baseline 0.03506 / CatBoost 0.96494. The separate three-family sensitivity blend assigned baseline 0.01063 / CatBoost 0.42000 / TFT 0.56937 and scored **2.1639** on the untouched test. It is not promoted. TFT's 10th–90th interval coverage was 0.8131 on this small test; no calibrated confidence claim follows.

Bayesian team-goal test RMSE was **1.1937**, versus **1.1750** for a simple training-set home/away average. The first current refit failed the strict unrounded convergence threshold (R-hat 1.0133). A retained extended refit with 3,000 draws / 2,000 tune steps per chain passed: maximum all-parameter R-hat **1.00243**, minimum bulk ESS **1805**, zero divergences. Two chains remain a limitation. Convergence does not establish predictive advantage or complete FPL scoring.

The actual-timestamp TFT split and release audit were invoked and blocked: current captures do not establish original historical availability. The research fit separately declares kickoff+one-day label timing and reconstructed current schedule assumptions; it never relabels those assumptions verified. The complete Bayesian profile gate also ran and rejected incomplete scoring components. Neither failed gate was disabled.

Five PPO seeds averaged **9.2 fewer net points** than the numerical comparator on the single two-event test path; accepted invalid actions were zero. Fitted-Q was also evaluated. The numerical strategy champion remains in place; no best seed was selected for promotion.

## Genuine prospective feedback

Four retained live pre-GW7 journals were scored against a new exact official finalized revision, each with complete 667-player coverage. The saved ensemble RMSE was **2.04765**; saved baselines scored **2.10696** and **2.12377** (two baseline captures were identical). Capture origins differ, so this is not a perfectly matched-origin comparison or a promotion test. The ensemble journal is scored as frozen; no backdating, refitting or claim of actual execution was added. The main personal database's journal was copied into the isolated study for scoring rather than rewriting its original record.

## Ongoing review operation

The normal worker now checks enabled review schedules once per minute. Disabled schedules remain opt-in. Scheduling failures are logged without private details and do not prevent ordinary queued work. Existing durable ticks/leases/idempotency still govern execution. A user-authorized weekly review was enabled locally with full-universe collection and CatBoost chronological evaluation/refit. Its first actual recoverable job **succeeded**, and the private manager-state fingerprint remained unchanged. Reviews run while the local worker is running; this is not an operating-system service that survives shutdown. The usual `bash scripts/dev.sh` launcher starts the worker.

The recurring path currently automates saved-journal scoring and CatBoost capture/evaluation/refit. The advanced Bayesian/TFT research review above is a manually executed experiment; incomplete qualification evidence prevents claiming automatic qualified advanced-model learning or serving.

## Initial verification

- Backend learning-review and queue tests: **16 passed**, including normal-worker schedule polling/idempotency and scheduler-failure isolation.
- Ruff lint and format check passed for the two changed Python files.
- Mypy passed for the changed worker entry point.
- Current candidate portfolios passed existing squad/formation/club/bench/captain validators, integer budget checks and free-transfer accounting. These validate conditional screenshot inputs, not current private account execution.
- Full application and browser suites were not rerun during this initial phase; the final release checks below were subsequently executed.

Next: retain the new GW9 forecasts as prospective evidence, score them only after official finalization, extend chronological evaluation and resolve advanced-model provenance/component gaps before any promotion. Reassess the private team at its actual current event before serving these forecasts through the personal app; that state was deliberately not inferred from a public deadline squad.

## Additional registered experiments and prospective benchmark

Eight fixed variants were registered before fitting. Training used GW1–4; validation used GW5–6; GW7–8 was an explicitly exploratory historical test because those blocks were already inspected. Model selection used validation RMSE only. Separate current refits used the finalized data available at the actual capture. Saved checkpoints were reloaded and future outputs matched exactly.

| Variant                               | Validation RMSE | Exploratory test RMSE |
| ------------------------------------- | --------------: | --------------------: |
| Points / position                     |          2.1780 |                2.1263 |
| Opportunity / fixture                 |          2.1494 |                2.0809 |
| Add xG / xA                           |          2.1549 |                2.0889 |
| Add defensive actions                 |          2.1558 |                2.0878 |
| Full team / rest context              |          2.1175 |                2.0592 |
| Shallow, stronger regularization      |          2.1283 |                2.0699 |
| Deeper, stronger regularization       |          2.1246 |                2.0551 |
| Full context, second predeclared seed |      **2.1160** |                2.0551 |

The validation-selected configuration was the second predeclared seed with full context. The validation-fitted eight-variant mean ensemble scored exploratory test RMSE **2.0547**. This modest retrospective change is not proof of prospective improvement. The earlier development run stopped at the ensemble's validation-metadata guard; required partition/timing metadata was supplied before the successful durable run, and the guard stayed enabled.

Three immutable GW9 benchmark bundles now contain **28 player-mean streams and one Bayesian team-goal stream**. They include the original families, eight new variants, fitted blends, and paired known-news zero-availability sensitivity. FPL player points and team goals are scored in their own units. Means are never confused with TFT medians or quantiles.

The benchmark was published before the 31 October 11:00 UTC deadline. It first checks results at **3 November 12:00 UTC**, then retries every six hours while its local worker runs. Official `finished` and `data_checked` must both be true. Missing outcomes and changed fixtures are explicit; no missing player becomes a zero. Common-player metrics support fair comparisons among families with different coverage. Scoring archives its sources and writes new immutable scorecard revisions without changing any original prediction.

A separate local research worker is running with the benchmark DATA_DIR. A real pre-event scoring job completed as **pending_finalization**, and the scorecard export correctly contained zero scored events. After finalization, `scripts/research/score_forecasts.py --export PATH` exports the retained scorecards for review before the next refit. This local process does not survive computer shutdown automatically.

A separate immutable analysis plan was registered before the deadline: report all players, all forwards, players with at least 60 prior five-match mean minutes, and forwards meeting that minutes threshold. Membership comes from the frozen future feature panel. Subgroup comparisons must use identical covered IDs. GW9 must not be used to refit the weights it is evaluating.

## Final repository verification

| Check actually run                           | Result                                                                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Full installed backend suite                 | **498 passed / 3 skipped**, 132 dependency warnings                                                                      |
| Backend Ruff lint / format                   | Passed; 131 files formatted                                                                                              |
| Backend mypy                                 | Passed; 84 source files                                                                                                  |
| Root operator / export tests                 | **16 passed**                                                                                                            |
| Frontend lint / final typecheck / formatting | Passed                                                                                                                   |
| Frontend unit tests                          | **13 passed**, six files                                                                                                 |
| Next.js 16.4.3 production build              | Passed, including an isolated API target                                                                                 |
| Production desktop / mobile Playwright       | **12 passed / 10 explicit configuration-dependent skips**                                                                |
| Actual isolated API + worker smoke           | Passed: demo, forecasts, recommendations, save/reload, version conflicts, unknown-finance lineup-only and plan staleness |
| Runtime npm audit                            | **0 vulnerabilities**                                                                                                    |
| Full npm audit                               | **18 moderate development-tool findings**, no high/critical findings                                                     |
| Python dependency compatibility              | Passed: 108 installed packages                                                                                           |
| Current navigation links / Git whitespace    | Passed                                                                                                                   |

The browser run used isolated demo state, with private-team and reviewed real-shadow fixtures intentionally unconfigured. Both captured desktop and mobile planner screenshots were inspected. No claim of live personal-team browser verification follows. The frontend source now uses standard generated type paths; old local build-directory entries were removed from TypeScript configuration after preserving a private backup.

The security pass upgraded Next.js and its matching ESLint configuration to **16.4.3**, applied compatible transitive fixes, and retained the remaining moderate minimatch tooling findings rather than forcing major tool downgrades. [Official Next.js advisory](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr).

Current documentation and the operator index were consolidated. Private session originals and the duplicate root handoff were preserved under ignored local backups. The source exporter now rejects known credential formats and unexpected generated/private paths, excludes ignored local state and Git history, emits file checksums and produces deterministic archives. Existing repository history still includes earlier personal notes; publication should use the audited source snapshot described in [HANDOFF](../../HANDOFF.md).
