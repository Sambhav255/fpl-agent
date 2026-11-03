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
