# Current build status

Updated 2026-10-14 UTC (13 October locally). Read [START_HERE](START_HERE.md), [the ChatGPT report](CHATGPT_PROGRESS_REPORT.md) and [the real experiment report](experiments/2026-10-13-real-football-finalized/README.md). Earlier audits and checks remain historical; they do not override this status.

## Prospective replay continuation — 14 October UTC

Automated evidence capture, queued baseline forecast, analysis, journal production and policy-specific seals now run through `scripts/run_prospective_journal.py`; no manual replay JSON/Parquet is required. Capture completes before prediction, includes retained exact package bytes, and never gives an older forecast newly verified timestamps. Default baseline queue fingerprints are preserved. Replay packets publish atomically and retries preserve immutable artifacts. Backup includes capture/seal references; team deletion removes their private SQLite records.

Finalized outcome ingestion now reconciles exact official totals, duplicates/types, fixture membership and minutes, preserves unknown participation, and excludes changed schedules including former blanks. The strict adapter rederives one explicit revision from retained checked bootstrap, fixture and live-result bytes. `scripts/evaluate_journal_replay.py` stores immutable paper comparisons under ignored DATA_DIR and leaves actual execution/manager state unchanged.

Actual production3163/API8163 integration: 667 players, six forecast events, 4,002 fixture means, five independently validated plans, three seals. Both browser projects displayed the journal; a fresh official status retained GW7 pending and its 17 October 10:00 UTC deadline. Future labels remain absent. Final fresh checks: **464 base/11 skips, 480 RL/7 skips, CLI14, Ruff126 files/mypy81 sources in both environments, frontend format/lint/types/unit13/production build, production browser16/6 personal-state skips**. Optional libraries remain absent from the actual base worker. [Immutable continuation report and commands](experiments/2026-10-14-prospective-replay/README.md). Durable ignored backup: data/research/prospective-replay-2026-10-14/. Initial timing/default-payload failures were fixed; ENOSPC attempts and successful full reruns are recorded. Earlier stage evidence below is preserved rather than described as newly run.

## Implemented and exercised

Reviewed `dbc14d900acb5279586698120302cbf36391b119` matched the initially clean HEAD. Inspected [Actions run 38323280394](https://github.com/Sambhav255/fpl-agent/actions/runs/38323280394), which used that exact commit, and fixed optional-Gym metadata typing with compatible `dict[str, Any]`. Checks were not suppressed. Separate locked base/RL environments reproduced verification without replacing the existing environment.

The baseline tool, private corrections/gates, manual execution, immutable journals, outcome revisions, recoverable jobs and numerical planner remain intact. New real football commands capture the prospectively defined full official universe, evaluate chronological CatBoost folds, refit separately, produce immutable release/input packets and fit genuine held-out baseline/CatBoost mean weights. Historical assumptions are preserved; future shadow publication has actual timestamps. Source/model/input/mapping/scoring/horizon checksums and mutation fences protect registration, queueing and worker publication. Baseline/CatBoost ensemble members work through serving, including a frozen baseline member.

An initial 667-player capture excluded 667 preliminary GW6 labels. A later actual provider check finalized GW6; the new capture retained 3,883 finalized fixture labels over GW1–6, 669 sources and the same 667-player universe. Captured 2026-10-13T21:35:15Z; next GW7 deadline 2026-10-17T10:00:00Z. Missing historical rows remain missing. The separate current refit follows two untouched evaluation origins, GW5–6: 1,334 common rows, CatBoost RMSE 2.1914 versus reconstructed app baseline 2.3841. Rolling comparators have lower MAE. Six events/two dependent tests do not justify promotion or calibrated confidence.

Registered real 2024/25 archive ablations and direct leads 1–8 freeze future features at their original origin, purge partitions by label availability and retain a separate inactive refit. Fixed feature/configuration selection never uses final test results. The archive scoring era and assumed schedule/publication timing prevent current-era serving qualification.

Complete Wildcard/Free Hit ownership/XI/captain candidates replace the old two-move chip restriction. Sparse constraints avoid the dense full-catalogue matrix. Finances, selling values, inventory and Free Hit restoration are independently replayed. Ordinary large-catalogue replacements remain capped at two; sequence search remains bounded without a global certificate. Current-season eight-lead baseline forecasts and evaluated archive multilead forecasts each produced 36 four/six/eight-event comparisons; all selected plans passed validation. Current benchmark found 15-player Wildcards and 14-player Free Hits; archive found 15 and 11. These are forecast-path comparisons, not realized strategy gains.

Official-points historical episode adapters and reproducible episode serialization support real Gymnasium/PPO/fitted-Q research without inventing unavailable scoring components. Five fixed 64-step CPU seeds used development GW2–3/test GW4–5, 40 covered players, common paper starts and one actual season path. PPO mean 98 net points versus 101 for same-menu/unrestricted numerical comparators; keep/fitted-Q 98. No winning seed, independent-season confidence claim or live team exploration. Numerical planner remains champion; RL stays inactive shadow.

## Previous-stage verification (13 October)

| Check | Actual result |
| --- | --- |
| Locked base backend | 413 passed / 11 skips |
| Locked RL backend | 429 passed / 7 skips |
| Root CLI tests | 14 passed |
| Ruff lint/format; mypy | Passed; 78 source files in both environments |
| Frontend lint/format/types/unit/build | Passed; 13 unit tests; final production build |
| Final production browser/API/worker | 14 passed / 6 explicit personal-state skips |
| Positive real integration | 667 CatBoost and 667 ensemble forecasts displayed; queued worker analysis; four plans independently validated; pre-deadline GW7 paper journal |

Base skips Gymnasium, learning and historical-adapter modules (one skip per module), plus a Torch case and seven shared Bayesian/TFT/opt-in cases. RL enables 16 additional actual cases; those seven shared cases remain skipped. No optional library was installed to hide typing failures. The locked stack emits 115 deprecation warnings; checks/assertions remain enabled. Browser timing failures were fixed by awaiting actual responses; the shadow selector uses its accessible combobox name. Full evidence and reproduction commands are in [the report](experiments/2026-10-13-real-football-finalized/README.md) and [verification](learning_upgrade/VERIFICATION_REPORT.md). These were executed in the previous stage; the continuation results above are fresh. Older 414/3 and organisation counts remain historical.

## Runnable handoff and limits

Previous-stage verified isolated preview: **http://127.0.0.1:3162**, API8162 and a separate worker, build `.next-real-finalized`, `DATA_DIR=/private/tmp/fpl-real-finalized`. Recheck processes before reuse. Durable ignored copies are `data/research/real-football-finalized-2026-10-13/` and the earlier `data/research/real-football-2026-10-13/`; original personal state, artifacts and existing services are preserved. Standard startup remains `bash scripts/dev.sh`. No account action, paid data, deployment, Git push or champion promotion occurred.

TFT stays inactive: six current-era finalized events are below its eight-event chronological minimum. Current CatBoost supports one lead; longer current forecasts remain the labelled conditional baseline. Real Bayesian/TFT calibration and complete release qualification remain gated; their optional research infrastructure is intact. Independently reviewed social labels/configured semantic extraction and actual private financial/chip reconciliation remain unavailable. Personal state is never inferred from research portfolios. Actual execution stays unknown; paper selection is separate.

Next concrete step: after GW7 is officially finalized, score the already frozen shadow forecasts/paper journal before refitting. Capture a new verified revision, advance chronological folds and reassess champions. Do not backdate missed origins or treat reconstructed research as strict prospective evaluation.
