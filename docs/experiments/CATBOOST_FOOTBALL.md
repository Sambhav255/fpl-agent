# Football CatBoost experiments

Executed 10 October 2026; inactive, qualified research challengers. Only the new football feature/model/test files are integration inputs. No registry, worker, dependencies, state, or activation was changed.

## Immediate current-event artifact

`data/models/football_catboost/20261010T070056-0125fbba/` contains genuinely fitted and reloaded CatBoost full-points mean, minutes, appearance, 60-minute, start, and 10/50/90 quantile heads. `forecast_origin.json` binds the artifact manifest checksum, frozen future features, explicit mappings, forecasts, and actual origin **2026-10-10T07:00:56.684088+00:00**. It contains 30 current-ID fixture forecasts for GW6. Inputs were captured at 06:56:35 UTC, before that origin. Artifacts are ignored local files.

The official collection `5ca9f12d261942b69ba6c69e693cb1bb` has season `2026/27`, 30 selected players and 150 labels. Current IDs/positions came from its retained, validated bootstrap snapshot, without names or cross-season matching. Player keys are `official_fpl:2026/27:element:ID`. Club keys use the same provider/season namespace. Rules feature is `fpl-2026-27`; this is an explicit current-era target, not rescoring old-era outcomes.

Training: GW1–2, 60 rows; early-stopping validation: GW3, 30 rows; probability adjustment calibration: GW4, 30 rows; untouched diagnostic test: GW5, 30 rows. Simulated historical label availability is kickoff plus one day, and origins are actual event deadlines. Historical schedule and role reconstruction uses current snapshots. Those are assumptions, not evidence of original publication. Actual labels were captured today and are usable to fit a future forecast today. This distinction is retained in provenance and actual artifact availability.

| GW5 comparator | RMSE | MAE |
| --- | ---: | ---: |
| Football CatBoost | 4.5017 | 3.7520 |
| Training population mean | **4.4634** | **3.7444** |
| Rolling five-match points | 4.7221 | 3.9750 |
| Zero | 6.6608 | 5.1667 |

This model is worse than population prediction on both primary errors. It has poor ranking separation and a selected-player sample with no useful coverage of nonappearance. All appearance probabilities are one, so they are not credible injury forecasts. Means are unconditional on appearance and must not be multiplied by an availability probability. User-confirmed current-event hard nonappearance can replace the forecast with zero once as a separate documented decision override.

`docs/local/deadline-catboost.json` holds the current ranking, IDs, captured news, prices, raw forecasts, metrics, origin and the user-confirmed Tzolis override. Asked-for means: Haaland 6.726, M. Sangaré 6.717, João Pedro 6.715, Belloumi 6.638, Rogers and Palmer 6.495, Groß 6.346, Schade 6.288. These small differences are not persuasive captain or transfer evidence. Legal Keep/transfer comparisons require the lead-owned optimiser and confirmed state; this model task does not invent those outputs.

## Primary broad archive experiment

`data/models/football_catboost/20261010T065733-e27601b0/` uses the retained pinned source `data/research/pinned-2024-25/merged_gw.csv`. Git commit: `a59a43a8343d960a58cbe7a1f9fba2d2ce431856`. Raw SHA256: `5bbbcba6353b4c72ad273adcc8e3aa451946a826564679788f45b1cb3325b84e`. The source JSON checksum is preserved. No floating reference was fetched by training. Commit time is not original field publication evidence.

Train GW1–6; validation GW7–8; calibration GW9–10; test **GW11–16**, not only the final two. Rows with label availability crossing the next partition origin are purged from development partitions. Train/validation/calibration information boundaries include all early-stopping and probability adjustment labels. Test metrics are per fixture, with event/position/appearance and lag-defined likely-starter subgroups. Test features may use prior test-event observations usable at each subsequent origin; the fitted model never learns those test targets.

| Broad test comparator | RMSE | MAE |
| --- | ---: | ---: |
| Football CatBoost | **2.1496** | 1.1825 |
| Rolling five-match points | 2.1791 | **1.1261** |
| Training population mean | 2.4182 | 1.5315 |
| Zero | 2.6974 | 1.2100 |

CatBoost improves RMSE slightly but worsens MAE against rolling points. Nominal 80% interval coverage is only **31.4%**, so these intervals are poorly calibrated. No confidence claim or promotion is justified. Detailed probabilities, minutes, quantile pinball, subgroups and event errors are in `evaluation.json`; interval coverage is empirical diagnostic coverage, not a confidence level.

Historical origins are earliest event kickoff minus 48 hours. Prior outcomes enter only after kickoff plus seven days and only from earlier events; both fixtures of a double share the event origin. Categorical position, club, opponent, home and rule era are fixture context assumed reconstructed from final archive fields. They are not historically verified snapshots. Lagged points/minutes/start/appearance/60-minute features contain no xP, same-event outcomes, future realised statistics, price, ownership or injury fields. Missing history is explicitly flagged; missing rows are never manufactured zeros or blanks.

## Adapter and manifest contract

`train_experiment(csv_path, output_root, source_commit)` verifies the pinned commit and payload checksum and writes a unique immutable run. `train_collection_experiment(envelope, output_root, rules_version, bootstrap)` verifies the collection fingerprint and live mode, constructs explicit current season mappings, fits separate partitions and writes a frozen future bundle. Caller supplies the bootstrap parsed from the collection's validated retained snapshot; use `load_collection` to verify source references first.

`forecast_frozen(run_dir, features, mappings, prediction_origin)` verifies all model/evaluation/feature/mapping checksums, artifact existence before origin, exact feature/rule compatibility, frozen origin, source availability, one-event horizon and explicit same-season current-ID mappings. It returns per-fixture means, minutes, auxiliary probabilities and sorted quantiles, never an availability-scaled mean. Missing mappings, cross-season mappings, incompatible era, duplicate fixture, future source and corrupted files fail visibly.

Required frozen columns: categorical/numeric `FEATURES`, `player_id`, `player_key`, `event`, `fixture_id`, `decision_cutoff`, `source_available_at`, `source_ref`, `feature_version`. Explicit mapping columns: `current_player_id`, `player_key`, `season`, `source_ref`. `collection_frames` is the current-origin builder; lead-owned job/store integration should retain bundle checksums and its origin rather than accept arbitrary paths or user timing assertions.

Initial immutable manifests use `family`, `files`, `artifact_id`, `mode`, `artifact_available_at`, `available_at`, `training_cutoff`, `current_training_data_available_at`, `supported_horizon`, `feature_version`, `mapping_version`, `rules_version`, `provenance`, `evaluation_reference` and all partition boundaries. In these first manifests `training_cutoff` is the simulated development-label boundary; live eligibility must use **max(training_cutoff, current_training_data_available_at)**. Future writes additionally alias `model_family`, `artifacts`, `data_mode=live`, preserve the simulated boundary in `information_cutoff`, and use actual current data availability for `training_cutoff`. Existing frozen manifests were not mutated.

Remaining limitations: one-event horizon, selected universe only, no full minutes mixture, weak small-sample probability adjustment, no contemporary injury model, no strategy replay, no verified historical schedule/role versions, no scoring-era generalisation, no baseline app adapter comparison, no prospective outcomes yet, no calibrated confidence or champion activation. The immediate integration step is lead-controlled opt-in routing with checksum-bound bundle references, current confirmed absence handling, independent legal plan validation and visible experimental labels.

## Checks

Real archive and official collection fits completed. Every model head saved/reloaded with exactly equal test predictions; frozen current forecasts generated successfully. Four focused tests cover future and same-event outcome exclusion, unknown-history distinction, pin mismatch, artifact creation time, reproducible reload/forecast, explicit mappings, rule mismatch, future source rejection, coherent probabilities/quantiles and corrupted artifact rejection. Synthetic test fits are mechanics checks, not performance evidence. Scoped Ruff and mypy checks pass.
