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
