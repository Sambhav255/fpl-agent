# Current verification evidence

Updated 2026-10-13. Read [BUILD_STATUS](../BUILD_STATUS.md), [implementation status](IMPLEMENTATION_STATUS.md) and [the immutable experiment report](../experiments/2026-10-13-real-football-finalized/README.md). Earlier counts are preserved in [verification history](../history/VERIFICATION_2026-10-12.md); they are not fresh results.

## Fresh locked verification

Actions run [38323280394](https://github.com/Sambhav255/fpl-agent/actions/runs/38323280394) used reviewed/current initial commit `dbc14d900acb5279586698120302cbf36391b119`. Its 401 backend passes/10 skips and14 CLI passes preceded an optional-Gym metadata annotation failure. The compatible explicit annotation fixed the typing issue. Initial clean-base reproduction passed401/10; the separate RL environment passed410/7. These were new executions, not inherited all-optional results.

After integration and the additional producer/episode/chip regressions:

| Check | Actual final result |
| --- | --- |
| Clean locked base suite | 413 passed / 11 skips |
| Clean locked RL suite | 429 passed / 7 skips |
| Root CLI tests | 14 passed |
| Ruff lint and format | Passed;120 backend files |
| Mypy | Passed;78 source files in both environments, separate caches |
| Frontend format/lint/types | Passed |
| Frontend unit tests | 13 passed with one worker |
| Production build | Passed;`.next-real-finalized` |
| Actual production API/worker/browser | 14 passed / 6 explicit personal-state skips, desktop/mobile |
| Independent real analysis replay | Four plans validated separately from actual worker publication |

Base skips three whole modules: Gymnasium environment(6 cases), policy learning(2) and historical adapters(7), counted as one skip each. RL enables those15 cases plus one Torch case. Seven shared Bayesian/TFT/opt-in cases remain skipped. Missing optional packages include platformdirs/xarray/pytorch-forecasting; no extras were installed merely to hide mypy. Both fresh environments retain the locked versions. The locked stack emits115 dependency deprecation warnings; no warning filters, mypy suppression or weakened assertions were added.

Frontend unit checks first hit two 5-second timeouts during concurrent load; the unchanged suite passed serially. Production browser checks first asserted while actual responses were loading; waits now bind the real workspace responses. The shadow selector is found by its accessible combobox name, avoiding nested option text changing label matching. No artificial response or checkpoint stub is used in the real-flow suite. An attempted stop of a browser PID was rejected by automatic review for insufficient ownership evidence; the run finished naturally. Later research API/worker restarts were authorized after session PID, command, cwd, port and isolated-database evidence established ownership. No personal process was terminated.

## Actual football evidence

Validated official capture froze all667 bootstrap players and669 source receipts with at least250ms pacing. The first revision excluded667 preliminaryGW6 labels. A later provider check finalizedGW6; new capture completed2026-10-13T21:35:15Z with3,883 final fixture labels overGW1–6. Next official deadline isGW7,2026-10-17T10:00:00Z. Previous source/model/report bytes remain intact.

Chronological current-era CatBoost evaluation compares identical1,334 player-fixture rows overGW5–6 with app baseline, rolling points/minutes and training-only shrinkage comparators. Latest serving fitting is separate and follows evaluation. A real archive experiment registers five football feature groups, evaluates direct leads1–8 with origin-frozen covariates, purges partitions and saves/reloads actual CatBoost payloads. Test data does not select configuration or weights. Archive scoring/timing limitations prevent current-era serving. Current CatBoost supports one lead; six final current-era events do not meet TFT's eight-event chronological minimum.

Reproducible producers build immutable model/input packets, mappings and source receipts. Baseline/CatBoost ensemble means use genuine earlier held-out weights and later untouched tests. Registration, queued worker inference and the production browser displayed667 CatBoost and667 ensemble forecasts. Actual analysis and separate validation accepted four plans; a pre-deadlineGW7 paper journal was frozen with actual execution still unknown. API and worker ran in a clean base environment with Torch/Gym/PyMC/TFT absent, proving the baseline and real CatBoost path remain usable.

Two planning matrices each cover36 roll/single/funding-pair/hit/Wildcard/Free Hit comparisons overfour/six/eight events. One uses actual current frozen baseline forecasts (future availability conditional); one uses actual evaluated archive multilead forecasts under explicitly different current financial rules. All chosen plans independently validate. Authored chip regressions separately verify full replacements, sale-profit budget, locks/exclusions/caps, inventory and Free Hit restoration. Sparse MILP parity is checked against enumeration; its certificate does not certify the full sequence. Global optimality is not claimed.

Real reconstructed RL uses finalized official totals with explicit price/schedule/missingness coverage. Five fixedCPU seeds, developmentGW2–3/testGW4–5 and common paper starts compare PPO/fitted-Q/greedy/keep/same-menu and unrestricted planners. One actual season,320 training steps and two test events remain weak evidence. PPO loses on mean net points; numerical planner stays champion. No actual team exploration, winning-seed selection or independent-season interval.

Historical label/schedule/role/price times remain assumptions. Actual future shadow capture is separate from strict prospective outcome evaluation, which cannot finish before future results. Bayesian/TFT real calibration/release qualification, independent social review and actual private state reconciliation remain gated. Detailed hashes, partitions, metrics by event/position/lead, uncertainty limits and commands are in [the report](../experiments/2026-10-13-real-football-finalized/README.md).

## Reproduction and retained artifacts

Use `UV_PROJECT_ENVIRONMENT=/private/tmp/fpl-research-base` and `.../fpl-research-rl` with `UV_CACHE_DIR=/private/tmp/fpl-research-uv-cache`; install `uv sync --locked --project backend` and the same command with `--extra rl`. From `backend`, run each interpreter's pytest/mypy, base Ruff and CLI tests as documented in the report. Frontend uses the existing npm scripts, serial Vitest and the final Playwright command with `REAL_SHADOW_TEAM_ID=2000000001` on production3162/API8162. The hypothetical portfolio is required; personal-state browser tests remain explicitly opted out.

Ignored durable stores: `data/research/real-football-finalized-2026-10-13/` and `data/research/real-football-2026-10-13/`. SQLite copies use consistent backups; original personal storage is unchanged. Public report payloads are checksum-bound and contain only public football facts or explicitly hypothetical portfolios. No account actions, paid data, deployment, Git push or champion promotion occurred. Recheck process ownership before reuse; do not rely on past PIDs.
