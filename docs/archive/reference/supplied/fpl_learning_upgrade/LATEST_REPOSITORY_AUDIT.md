# Latest repository audit

Repository: https://github.com/Sambhav255/fpl-agent

Reviewed commit: `840c1185d005270717c7453fb278dc30a03c05f3`, committed at 12 October 2026, 05:14 UTC. Previous audit: `e759bcfb299d3f818d2e80ebb017796874cf8019`. The comparison contains two new commits.

## Assessment

There is meaningful backend progress. The old finding that all prediction jobs directly call the baseline is no longer accurate. The funding counterexample is repaired. The social subsystem exists, although it remains an offline grammar baseline with disabled live adapters. Current state integrity checks are stronger.

The app is still an experimental strategy assistant. It has no implemented reinforcement learning policy, no automatic learning lifecycle, no audited season policy benchmark and no full financial or chip optimisation across future events. Forecast sophistication and measured strategy quality must be evaluated separately.

I retrieved 103 files at the pinned commit, covering backend source and tests, scripts, implementation documents, project instructions and CI. I parsed 78 Python files and ran focused synthetic behaviour probes. I did not access your ignored local database, trained binary artifacts, personal current squad or live services. Real training numbers below are repository reported experiments, not retraining performed during this audit.

## Improvements to retain

| Area | What is now implemented | Remaining boundary |
| --- | --- | --- |
| Forecast routing | Worker invokes `forecast_job`; Football CatBoost has a real adapter | Baseline remains default; Bayesian and TFT are not live routed adapters |
| Immutable serving | Manifest, model files, feature frames, mappings, source bytes and universe are checked | This proves provenance and compatibility, not predictive advantage |
| Funding transfers | Ownership, legal XI and captain are jointly valued in candidate MILP | Candidate generation is not a full sequence optimiser |
| Exact oracle | Small declared universes and at most two events | It cannot certify global performance of the eight event planner |
| Collection | CLI, immutable collections and recoverable jobs; pending/preliminary/final rows distinguished | Current selected universe has only 30 players; collector union limit is 100 |
| Football features | Position, club, opponent, venue and rule era are categorical inputs | Only eight numeric lag fields; substantial football context is still absent |
| Replay | Evolving transfer inventory, independent plan validation and exact supplied stats scoring | Policy horizon is forcibly one; no audited evolving price history |
| Injury horizon | Future unknown availability is no longer repeated as zero | Numeric future values are conditional available scenarios, not calibrated unconditional means |
| Social | Reviewed source roles, author/family bounded aggregation, deletable lineage | Grammar only; no live sources or source accuracy learning |
| Manager state | Explicit event review and stale state blocks | User must confirm new private state; collection cannot infer it |

## Material next findings

| ID | Priority | Finding and evidence | Required change |
| --- | --- | --- | --- |
| C01 | P0 | `evaluation/strategy.py:83` overwrites requested horizon with one | Pass supported horizon to policy, validate its full proposed path, execute only first event |
| C02 | P0 | `models/football_catboost.py:408` fixes development/test partitions to GW1 through GW5 | Generate folds from finalized available events; separate evaluated artifacts and latest serving refit |
| C03 | P0 | Replay checks `source_cutoff` and caller timestamps, but not `prediction_origin` or bound artifact evidence | Add explicit audited prospective and assumed retrospective modes with origin validation |
| C04 | P0 | `collection_frames` creates future features only for the next event; manifest support is one | Implement lead specific features and evaluated horizon support; never stretch the one event artifact by renaming it |
| C05 | P0 | No decision journal and outcome reconciliation pipeline in the source tree | Freeze predictions and actions before deadlines, join finalized results and record revisions |
| C06 | P1 | Full sequence search remains width six with accrued point pruning and frozen prices | Add dynamic financial MILP and continuation value; benchmark against exact small cases |
| C07 | P1 | Future chips forbidden both by planner generation and `validate_plan` expected chip logic | Extend preferences and validator to a legal chip schedule before solving dates |
| C08 | P1 | Future conditional availability points enter the mean point objective | Require explicit scenario mode or calibrated recovery mixture; compare endpoints for flagged players |
| C09 | P1 | Thirty selected players and a single 30 row current test are narrow and biased | Capture a broad prospectively defined universe, compare by relevant subgroups and event blocks |
| C10 | P1 | `MatchStats` defaults components to zero; replay requires caller supplied stats | Reconcile against official fixture point totals; do not manufacture absent statistics as zero |
| C11 | P1 | Auxiliary probabilities use clipped regressors plus additive calibration offsets | Fit and evaluate appropriate binary heads and minutes mixture with broader calibration data |
| C12 | P1 | `social/extraction.py` uses explicit action grammar; conditional claims excluded from consensus | Build a labelled semantic benchmark and conditional evidence views before any forecast feature use |
| C13 | P1 | Social source groups exist but historical topic accuracy weighting does not | Add resolved claim registry, shrinkage and chronological source reliability evaluation |
| C14 | P1 | No Gymnasium, PPO or learning journal implementation exists | Build the environment after replay and financial correctness; keep RL a separate challenger |

P0 means required for a trustworthy learning release. P1 means required for the broader season strategy and RL release. These are implementation priorities, not measured quality scores.

## Behaviour reproduced against actual source

### Funding fix works

The same controlled 18 player case used in the earlier audit now produces:

| Strategy | Expected points |
| --- | ---: |
| Keep | 84 |
| Old squad proxy comparator | 94 |
| New planner | 101 |
| Exact small oracle | 101 |

The new candidate objective recognises that selling a costly reserve goalkeeper can fund a starting midfielder. This is a verified software improvement. It is not proof of an average seven point improvement on real teams.

### Injury correction is a conditional scenario

For a player with current availability zero, GW8 has zero points. GW9 through GW15 have approximately 3.56 points, `appearance_probability=null`, and separate zero/available endpoints. This is more honest than treating a current flag as permanent. It also means an injured player can receive their fully available future value in the deterministic planner. The application must not describe this number as a calibrated expected recovery forecast.

### Replay does not evaluate the requested horizon

A policy called through `replay_policy` with a requested six event horizon receives `horizon_events=1`. The planner being compared therefore has no opportunity to use its longer forecast path in replay. Executing one action each event is correct; forcing planning to one event is the limitation.

### Future prediction origin is accepted by assumed replay

A synthetic run with `prediction_origin` on 11 October is accepted at a 10 October deadline if its `source_cutoff` and caller availability fields are earlier. The current replay explicitly disclaims audited provenance, so this is a missing strict replay gate rather than proof of leaked production forecasts. A new strict benchmark must reject this case. A reconstructed historical model can be fitted today for research, provided a separate simulated information origin is honestly declared; it must not claim the artifact existed at the past deadline.

Reproduction and raw output are in `verification/`. Storage checksum and clock functions were substituted to accommodate the audit runtime. Optimisation, contracts, domain scoring and replay were imported from the pinned source without substitution.

## What the current models demonstrate

The repository reports a current season artifact at actual origin 12 October 2026, 04:31 UTC. Fitting and lag history use 150 final GW1 to GW5 labels, with 30 preliminary GW6 rows excluded. The 30 row GW5 assumed timing test reports CatBoost RMSE 4.5017 versus population comparator 4.4634, and MAE 3.7520 versus 3.7444. There is no demonstrated current season advantage.

The older 2024/25 archive experiment reports CatBoost RMSE 2.1496 versus rolling points 2.1791, while MAE is worse, 1.1825 versus 1.1261. Empirical coverage of its nominal 80 percent interval is 31.4 percent. These are mixed diagnostic results under reconstructed timing and an older scoring regime. They do not justify current live promotion or precise confidence claims.

The fixed GW1 to GW5 partition has another consequence: even after later finalized events arrive, rerunning this function does not fit the points model on those new events. Future lag inputs may update, but the model fitting partition stays unchanged. There must be a separate latest data refit after honest evaluation. Adding the new test week to training before scoring its frozen forecast would invalidate the prospective comparison.

Do not delete strict provenance rules to manufacture a stronger model badge. Also do not wait indefinitely for perfect historical snapshots. Qualified reconstruction is useful for development, latest known outcomes are valid for future fitting, and new prospective capture builds the missing evidence over time.

## Verification evidence

Hosted workflow: https://github.com/Sambhav255/fpl-agent/actions/runs/38207057987

When inspected, locked installation, backend checks, frontend checks/build, and browser/persistence checks had completed successfully. The workflow job was still completing cache cleanup, so the overall run conclusion had not been reported. Prior two workflow runs were cancelled, not failed.

The latest build document records 292 backend tests, three skipped, 13 root CLI tests and 16 browser tests. Hosted step success corroborates the verification stages, but this audit did not independently rerun those counts. Offline dependency installation locally could not complete because the required packages were absent from cache. No permission or dependency restriction was bypassed.

The local audit parsed 78 Python files and reproduced four probes. It did not run the full locked suite, train model heads, serve an API, test SQLite concurrency or confirm the state of services on your Mac. Codex must perform those checks in your actual checkout and save reproducible evidence before declaring a milestone done.

## Immediate next move

Implement the decision journal, finalized outcome pipeline, dynamic evaluation/refitting and real receding horizon replay first. Then add a rules accurate simulator and train an RL challenger. Preserve baseline operation, opt in experimental forecasts, money unknowns, immutable artifacts and manual account execution throughout.
