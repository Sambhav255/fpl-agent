# Operator commands

Run commands from the repository root unless a command explicitly changes directory. Use the installed `backend/.venv/bin/python` for research commands. Existing top-level command paths remain stable.

| Area                         | Entry points                                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Local app                    | `dev.sh`, `dev.py`                                                                                                        |
| Verification                 | `check.sh`, `smoke.py`, `live_smoke.py`, `generate_api.py`                                                                |
| Source packaging             | `export_source.py`                                                                                                        |
| Official collection          | `collect_football.py`                                                                                                     |
| Football fitting and serving | `train_current_football.py`, `prepare_football_forecast.py`, `release_football_shadow.py`, `prepare_advanced_forecast.py` |
| Historical experiments       | `run_football_experiment.py`, `run_historical_strategy.py`, `report_real_experiments.py`                                  |
| Decision replay              | `run_prospective_journal.py`, `prepare_journal_replay.py`, `seal_journal_replay.py`, `evaluate_journal_replay.py`         |
| Policy and social research   | `train_strategy.py`, `benchmark_social.py`, `benchmark_season_planning.py`, `benchmark_historical_planning.py`            |
| Scheduled learning           | `review_learning.py`; enabled schedules are also polled by the normal worker                                              |
| Deadline benchmarks          | `research/deadline_experiments.py`, `research/freeze_review.py`, `research/score_forecasts.py`                            |
| Post-event diagnostics       | `research/post_event_review.py` — source-bound provisional/final comparisons and registered worker follow-up             |
| Rolling model evaluation     | `research/rolling_experiments.py --collection-id ID --work-once` — fixed configurations, earlier inner validation and outer event tests |
| Frozen selection diagnostics | `research/selection_review.py --help` — reconstruct eligibility from retained collections and register canonical shortlists |
| Documentation verification   | `check_docs.py` — archive reconstruction/checksums, preserved experiments and local links |

`deadline_bayesian.py` is a retained GW6-specific historical experiment. Use the current model modules and retained-review workflow for new events; its old deadline assumptions are not current defaults.

## Frozen deadline experiments

Use a dedicated ignored `DATA_DIR` so research stays separate from personal app state:

```sh
export DATA_DIR="$PWD/data/research/my-deadline-study"
backend/.venv/bin/python scripts/collect_football.py --include-all --parquet
backend/.venv/bin/python scripts/research/deadline_experiments.py --collection-id COLLECTION_ID --work-once
```

The experiment command registers its fixed settings, queues recoverable work, evaluates its historical splits, fits a separate current model, and publishes immutable next-event predictions. Its historical event blocks remain exploratory if already inspected. It cannot publish a prospective benchmark after the actual deadline.

The normal worker checks registered benchmarks after the final scheduled fixture plus a buffer and retries every six hours until official finalization and complete coverage. It must be running with the **same DATA_DIR**:

```sh
(cd backend && uv run --no-sync python -m fpl_app.jobs.worker)
```

For a manual finalized-results check:

```sh
backend/.venv/bin/python scripts/research/score_forecasts.py --work-once
backend/.venv/bin/python scripts/research/score_forecasts.py --export "$DATA_DIR/scorecards.json"
```

`--benchmark-id ID --work-once` can check one benchmark explicitly; unfinished events remain pending. Predictions are never rewritten by scoring. Inspect `forecast_benchmark_outcome` records before fitting the next model. Missing outcomes and changed schedules remain explicit, with matched-universe metrics for fair comparisons.

`research/freeze_review.py` additionally freezes the prior full review artifacts when that DATA_DIR contains the retained baseline/CatBoost/TFT/ensemble analysis files. It records Bayesian **team goals** separately from complete player points.

## Post-event review and advancing experiments

Capture all official data first, preserving the previous collection and forecasts. Use `deadline_experiments.py --collection-id COLLECTION_ID --advance --work-once` to register current finalized-event folds plus multiscale opportunity and points-hurdle challengers. Eight finalized events are required. A prospective event's retained benchmarks must have final scorecards before its targets enter this path. Previously inspected historical blocks remain exploratory. A current refit is separate from the scored historical model; no champion is promoted.

For source-bound review of an existing analysis plan:

```sh
backend/.venv/bin/python scripts/research/post_event_review.py \
  --event 9 --analysis-plan "$DATA_DIR/analysis/prospective-analysis-plan.json" \
  --output "$DATA_DIR/analysis/post-event-review" --register-followup
```

`--offline` reuses retained sources. `--team-from-main-store` optionally retains public picks/history/transfers for the one saved personal team in the research store; it does not edit personal state. Keep these outputs ignored. An explicit analysis plan selects its canonical benchmark IDs, so retained development runs do not enter its comparison. No plan means all retained bundles for the event are compared, with repeated names qualified by benchmark ID.

The review reports provisional metrics while official gates are pending, and never publishes these as finalized labels. `--register-followup` retains the plan so the normal research worker publishes `forecast_event_review` artifacts together with later final scorecards. The worker must run with this same DATA_DIR and network access. Inspect those immutable artifacts after official finalization; the local worker is not an always-on system service.

`score_forecasts.py --export PATH` exports both the retained `scorecards` and registered `event_reviews`. A benchmark filter applies to both. Exporting does not turn provisional reviews into final outcomes.

Selection reviews are exported as `selection_reviews` too. To register a new comparison, pass `selection_review.py` an existing `--analysis-plan`, its actual `--method-manifest`, `--comparator`, `--challenger`, a fixed `--study-id` and ignored `--output` directory. Optional `--score --offline` evaluates a past event from retained sources. Late registration remains retrospective. Eligibility is reconstructed from the checksum-verified collection referenced by the frozen forecasts; arbitrary feature panels are not accepted. A study fixes its method, comparator and primary hypothesis, with one canonical plan per event. Reuse an existing plan for later outcome revisions rather than registering a new origin. Final reviews publish through the matching worker.

Rolling evaluation preserves implementation bytes and checksum-verified per-fold checkpoints. It runs as a recoverable `rolling_experiment` job. Historical results remain exploratory; there is no serving refit, outer-driven tuning or automatic promotion. See [the roadmap](../docs/ROADMAP.md) for current priorities.


## Same-state forecast and policy comparison

`research/compare_paper_policies.py --input INPUT.json --output NEW_REPORT.json`
extends legal replay across declared forecast streams. The JSON contains a fixed
`initial_state`, `settings`, and named `candidates`; each candidate supplies `policy`
(`keep` or `planner`) and `origins` following the existing `ReplayOrigin` contract.
Keep and roll use the same `keep` policy and coincide under identical forecasts.
Use the same `planner` with different forecast runs to isolate model benefit.

The comparison rejects mismatched catalogue/prices, schedules, deadlines, origin
information, outcome coverage or outcome values before running any policy.
Each policy is independently validated; reports retain lineup/captain/bench,
committed and incremental hits, state before/after transfers and the next origin's
financial inventory. Private state and trajectories stay in ignored data. Output
creation is exclusive and never overwrites earlier reports. Unknown finances remain
unavailable; reconstructed or synthetic inputs do not become prospective evidence.
Strict inputs retain the existing manifest/seal requirements. This command neither
trains nor selects/promotes a winning model.

Sequence search now seeds bounded larger restructures when at least three free
transfers remain, and its lazy ordinary menu permits up to the remaining inventory
(at most five), or two replacements for lower inventory. Current-event transfer
limits and independent financial/chip validation still apply. Search reports remain
bounded: a small synthetic exact-oracle match does not certify a full real catalogue.

## Model-improvement research and worker health

The [master-plan execution record](../docs/experiments/2026-11-03-master-plan/README.md)
tracks completed tasks, actual measurements and remaining gates. These commands
retain research artifacts and do not promote models or execute transfers.

- `backend/.venv/bin/python scripts/research/opportunity_comparison.py --help`:
  register and run the legacy/binary opportunity comparison on a read-only SQLite
  backup; a fresh output directory is required.
- `backend/.venv/bin/python scripts/research/ingest_season.py --help`: normalize
  pinned retained archive bytes, preserve unknown timing and verify retries.
- `backend/.venv/bin/python scripts/research/simple_experiments.py --help`:
  register/enqueue Ridge and LightGBM comparisons over a verified rolling panel.
  Install LightGBM with `(cd backend && uv sync --locked --all-extras)` to preserve
  existing optional packages, or `uv sync --locked --extra research` in a dedicated
  research environment. The ordinary baseline does not import LightGBM.
- `backend/.venv/bin/python scripts/research/oof_ensemble.py --help`: register
  prior-OOF-only convex weights; the first week is development warmup, and current
  outer labels cannot fit their own weights.
- `backend/.venv/bin/python scripts/social_manual.py --help`: manually import
  reviewed authored/permissioned evidence into a dedicated deletable social
  database, inspect availability branches, or delete posts. Import uses actual
  observation time. Direct points adjustment remains zero. The committed example
  is explicitly synthetic; it is not real social evidence.
- `DATA_DIR=/absolute/intended/data backend/.venv/bin/python scripts/worker_status.py`:
  read independent worker heartbeats in that store. A missing heartbeat can also
  mean an older worker; confirm its process/database and restart it with current
  code and the same exported `DATA_DIR`. A heartbeat expires after 90 seconds;
  this is local process health, not a supervised service.

Scheduled reviews now reuse checksum-verified fits when finalized revisions,
historical exposures, mappings, deadlines and implementation are unchanged.
A new capture timestamp alone does not retrain a model. New finalized or corrected
labels must pass the shared scoring guard before fitting. Scores must bind the
original forecast and be observed at least as late as the consumed label capture.
A conservative revision rejection requires rescoring; it never edits old forecasts.

## 4 November continuation: direct leads, weekly errors and recovery

The [latest execution record](../docs/experiments/2026-11-04-master-plan/README.md)
contains actual measurements and task dispositions. Use a separate absolute
`DATA_DIR`; these commands do not change manager state or promote models.

```sh
export DATA_DIR="$PWD/data/research/master-plan-2026-11-04"
backend/.venv/bin/python scripts/research/score_forecasts.py \
  --collection-id c6bbb35e50154cdda728d4e40e3f33f3 --work-once
backend/.venv/bin/python scripts/research/multilead_experiments.py --help
backend/.venv/bin/python scripts/research/weekly_error_report.py \
  --event 9 --output "$DATA_DIR/weekly-report"
backend/.venv/bin/python scripts/worker_status.py
```

The collection-bound scoring command runs only the needed independently fenced
child jobs, verifies their final receipts against the consumed collection, and
reuses completed identical jobs. A corrected/fresh collection gets its own scoring
identity. The scheduled review performs this stage before a fresh fit or cached-fit
reuse. Automatic benchmark polling now rechecks final bundles each six-hour slot;
finalization no longer disables later correction checks permanently.

`multilead_experiments.py --collection-id ID --work-once` registers fixed direct
point/minute methods for leads 1/2/3/4/6/8 and queues recoverable work. It cannot
update player features with intervening results. Complete target events are purged
before both later origins; missing doubles stay incomplete. Current GW1–9 data
supports evaluation for leads 1/2 only. Longer leads are explicitly unavailable,
not silently filled with one-week values. The report is research-only; it publishes
no serving forecast and does not alter the existing GW10 comparison. Retried jobs
use their original retained protocol/payload and verified checkpoints; rerunning
the registration CLI creates a newly timestamped protocol, not a backdated retry.

`weekly_error_report.py` reads retained verified official snapshots, without network
requests. Optional repeated `--benchmark-id ID` selects streams; repeated
`--previous-report PATH` supplies content-verified earlier reports for descriptive
drift. Event revisions count once. Missing probability/component/decision evidence
remains unavailable; diagnostic associations do not identify causes or execution
losses. A final scoring job also publishes its own weekly report when the stricter
source/timing evidence is present. Legacy evidence gaps are disclosed explicitly.

The health API (`/api/v1/health`) includes `worker` liveness and learning receipts.
The existing response remains an open dictionary, so schema regeneration produced
no type diff. [Optional macOS worker supervision](../docs/operations/WORKER_RUNTIME.md) documents
`scripts/macos_worker.py`; generation never installs or starts a service. An older
already-running process must restart with current code and the intended DATA_DIR
to provide these features. Do not start duplicate workers for the same store.

## Additional master-plan operators — 6 November

- `research/expand_seasons.py --season 2022-23 --season 2023-24 --revision FULL_SHA --output NEW_IGNORED_DIRECTORY`
  captures only the fixed Vaastav provider, retains file observation times and
  hashes, then uses existing normalization. Retries verify bytes offline; partial
  acquisitions are preserved and require a fresh directory. Fixture coverage is
  reported explicitly, including incomplete seasons. Historical publication timing
  remains assumed.
- `research/link_archive_people.py --bundle NORMALIZED_SEASON_DIRECTORY --bundle OTHER_SEASON_DIRECTORY --output NEW.json`
  verifies source checksums and emits separate research person links without
  rewriting source bundles. Code/name conflicts remain unresolved.
- `research/assess_candidate.py --input REGISTERED_GATE_AND_EVIDENCE.json --output NEW.json`
  assesses `{"gate": {...}, "evidence": {...}}` with type-specific contracts. It
  never activates a model. Forecast loss reductions and decision points retain
  different units; eight prospective event blocks remain mandatory.
- `run_football_experiment.py` now accepts an explicit season from its checksum-bound
  `source.json`, instead of forcing all archive identities into 2024–25. New runs
  retain implementation bytes, lockfile and runtime identities before fitting.
  Existing studies are unchanged; archive fits remain reconstructed research,
  not qualified current-season forecasts or calibrated joint scenarios.

## Weekly all-player model competition

The [measured competition](../docs/experiments/2026-11-06-weekly-tournament/README.md)
uses the existing worker and benchmark scorer. Set an absolute `DATA_DIR` consistently
for capture, registration, workers and reports. Research extras are optional:
`(cd backend && uv sync --locked --all-extras)` preserves the installed optional stack.

For a manually selected full-universe collection:

```sh
backend/.venv/bin/python scripts/research/score_forecasts.py --collection-id COLLECTION_ID --work-once
backend/.venv/bin/python scripts/research/weekly_tournament.py \
  --collection-id COLLECTION_ID --study-id DECLARED_STUDY --work-once
```

This runs the exact queued job, not unrelated queued work. Six registered mean
methods, fixed equal means, baseline and separate official-zero sensitivities
freeze before the real deadline. Repeating a published study/event returns
`already_frozen`; new hypotheses require an honestly timestamped separate study.
Native checkpoints, calibration/preprocessing, raw/projected auxiliary predictions
and implementation/lock identities stay in ignored managed artifacts.

Configure subsequent events through the existing opted-in full-universe review:

```sh
backend/.venv/bin/python scripts/research/configure_tournament.py --enable --study-id DECLARED_STUDY
backend/.venv/bin/python scripts/research/configure_tournament.py --disable
backend/.venv/bin/python scripts/worker_status.py
```

Configuration updates use version checks. Disabling stops new competition jobs;
existing frozen benchmarks still score. This setting does not create a review
schedule or install a service: a review already collecting/refitting the full
universe and a worker using the same DATA_DIR must be running. The default local
store is now opted into `weekly-backend-2026-11-06`. The previous event must finalize
before the next study; current source/fixture gaps cannot become synthetic zeros.

To derive additional diagnostics from retained native-unit checksums:

```sh
backend/.venv/bin/python scripts/research/report_tournament.py \
  --directory MANAGED_TOURNAMENT_DIRECTORY --output NEW_DIAGNOSTICS.json
```

`news_sensitivity.py --benchmark-id ID` can freeze the explicitly labelled official-zero
scenario for an existing parent; it never edits the parent or scales point means by
appearance again. This overlay is automatic in new tournament jobs. All reported
auxiliary probabilities/quantiles are shared across point methods, not independent
model evidence. Current refits remain uncalibrated; event quantiles/appearance for
doubles are omitted rather than fabricated by summing marginal quantiles.
