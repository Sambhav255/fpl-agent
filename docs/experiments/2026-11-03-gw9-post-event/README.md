# GW9 post-event review and model work — 3 November 2026 UTC

## Result status and capture

All ten GW9 fixtures have `finished_provisional=true`, with scores and player outcomes available. At capture, official `finished=false` and `data_checked=false`; every fixture's strict `finished` flag is also false. These are **provisional post-event measurements**, not finalized scorecards. The finalization gate was invoked on all three original bundles and remained pending. No forecast was backdated or overwritten.

The full official capture retained **670 players, 672 source snapshots and 5,890 player-fixture rows**: **5,220 final revisions for GW1–8 and 670 preliminary GW9 rows**. Historical membership gaps remain missing. The new capture is separate from the original pre-GW9 sources. The personal app state was not rewritten; personal results, screenshots and account details are only in ignored local records.

## Frozen model comparison

The three genuine pre-deadline bundles contain 28 player-mean streams and one team-goal stream. This report uses the exact same **610-player intersection** across every stream. Original family coverage varies; full-coverage and matched metrics, signed error, rank correlation, positions, missing IDs and largest errors are retained in [metrics.json](metrics.json). Likely starters and likely forwards use the immutable pre-GW9 five-match minutes threshold of 60; no subgroup was chosen from GW9 minutes.

| Frozen stream | MAE, all 610 | RMSE, all 610 | RMSE, likely starters (171) | RMSE, likely forwards (18) |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1.2827 | 2.0001 | 2.7928 | 3.9479 |
| football_catboost | 1.1748 | 1.9288 | 2.7774 | 3.6260 |
| tft_research | 1.2632 | 2.0367 | 2.8954 | 3.8504 |
| baseline_catboost_blend | 1.1749 | 1.9252 | 2.7735 | 3.6327 |
| three_family_research_blend | 1.1491 | 1.9560 | 2.8265 | 3.7422 |
| full_second_seed | 1.1573 | 1.9122 | 2.8104 | 3.7506 |
| validation_fit_ensemble | 1.1536 | 1.9123 | 2.8045 | 3.7673 |
| full_second_seed_news_zero | 1.0547 | 1.8911 | 2.7941 | 3.7506 |
| validation_fit_ensemble_news_zero | 1.0509 | 1.8899 | 2.7880 | 3.7673 |

The validation-selected full-context second-seed model lowers matched RMSE by **4.39%** relative to baseline on this one provisional event. Original CatBoost lowers it by **3.56%**; TFT is worse than baseline on RMSE. The raw eight-variant ensemble is almost tied with its selected single model. Known-zero-news sensitivity improves the selected model to **1.8911**, while baseline's own availability handling leaves it unchanged at **2.0001**. The lowest observed stream is `full_shallow_regularized_news_zero` at **1.8893**; that descriptive result does not replace the validation-selected model.

The likely-starter results are much less convincing: original CatBoost RMSE is 2.7774 against baseline 2.7928, and CatBoost MAE is worse (2.2379 versus 2.1292). Among only 18 likely forwards, CatBoost RMSE is 3.6260 against baseline 3.9479, while MAE is worse (3.0274 versus 2.9526). Global gains therefore do not establish reliable transfer or captain selection gains. The 610 player rows are dependent observations from one event; no significance or rank-improvement claim is made.

Bayesian **team-goal** means scored RMSE **0.9165 goals**, MAE **0.7703**, over 20 team scores. These units cannot be compared with FPL point RMSE. A frozen same-origin naive team-goal comparator is absent, so this event does not establish a Bayesian advantage. Full Bayesian player-point scoring remains unavailable. TFT prospective mean forecasts were scored; prospective quantile/probability calibration is unavailable from these mean-only retained streams. Historical TFT interval results do not substitute for it. RL/fitted-Q have no retained GW9 policy rollout from the same manager state and cannot receive an invented prospective score; their previous historical evaluation still favors the numerical optimiser.

## Error analysis and changes

Of the matched players, 318 recorded zero minutes. Baseline's mean overprediction there is 0.7479 points; CatBoost's is 0.5450 and selected full-context's is 0.5068. For the 200 players who actually played 60+ minutes, every family underpredicted on average (baseline −0.9344, CatBoost −0.9252, full-context −0.8574). These realized-minutes slices are diagnostic, not forecast-time eligibility criteria.

The largest missed haul across the major models was Van Hecke's 15 points: baseline predicted 4.25, original CatBoost 4.81, TFT 3.38 and selected full-context 3.70. Means should not be fitted to reproduce one realized haul. The evidence motivates separating sparse zero outcomes from nonzero scoring, improving opportunity features, and tracking decision losses separately from universe-wide errors.

Implemented and executed:

1. Source-bound offline post-event diagnostics, clearly separated from final training labels; same-player comparisons, predeclared subgroups, signed errors, rank correlation and missing-data handling.
2. Advancing finalized-event folds, replacing the fixed GW1–8 research-only runner. A refit cannot consume a finalized prospective event until its saved benchmark bundles have final scorecards.
3. A points-hurdle challenger: `P(points != 0) × E(points | points != 0)`. It preserves negative disciplinary outcomes even at zero minutes. This is not an appearance probability, and availability is not multiplied again.
4. A multiscale opportunity challenger: prior three-match appearances/60-minute rates, exponentially weighted minutes, and up-to-ten-match points/xG/xA. Current-event and late statistics remain excluded.
5. Event aggregation now sums both fixture means in doubles and rejects missing/nonfinite predictions rather than allowing duplicates or fabricated zero means.
6. Retained implementation bytes/hashes and exact checkpoint reload checks. Old forecasts and artifacts remain intact.
7. Worker completion of registered final cross-family/subgroup reviews, with durable publication alongside the final scorecard. The local research worker is running; it retries scoring every six hours after the configured first check. It is not an operating-system service and does not survive shutdown automatically.

## Actual new fitting

The final experiment fitted **5,195 historical rows, GW1–8 only**. GW9's 670 preliminary rows were excluded from all targets. Training uses GW1–4, validation GW5–6 and an explicitly exploratory GW7–8 test. These historical blocks have already been inspected; neither new historical model selection nor a tiny improvement is fresh forward proof.

| Configuration | Validation RMSE, GW5–6 | Exploratory RMSE, GW7–8 |
| --- | ---: | ---: |
| points_position | 2.1780 | 2.1263 |
| opportunity_fixture | 2.1494 | 2.0809 |
| plus_xg_xa | 2.1549 | 2.0889 |
| plus_defensive_actions | 2.1558 | 2.0878 |
| full_context | 2.1175 | 2.0592 |
| full_shallow_regularized | 2.1283 | 2.0699 |
| full_deeper_regularized | 2.1246 | 2.0551 |
| full_second_seed | 2.1160 | 2.0551 |
| opportunity_multiscale | 2.1160 | 2.0607 |
| points_hurdle | 2.1149 | 2.0536 |

The points hurdle won validation at **2.1149**, compared with the prior selected model's **2.1160**. Its exploratory RMSE is **2.0536**, compared with **2.0551**; the new validation-fitted ensemble scores **2.0517**. These differences are very small. Production remains baseline; the numerical optimiser remains the strategy champion.

A separate latest-data refit and pre-deadline freeze now supply **23 canonical GW10 streams**: ten configurations plus a fitted ensemble, eleven paired official-zero-chance sensitivities and a fresh baseline. Other development-run forecasts were retained but excluded from the canonical registered analysis plan. Forecasts cover 670 players. The baseline can use current public season aggregates that include provisional GW9; trained challengers use finalized GW1–8 targets only. This input distinction remains explicit. The next-event immutable subgroup plan was retained before the GW10 deadline, 6 November at 18:30 UTC. Automatic scoring begins after the frozen final kickoff plus its buffer, currently 9 November at 08:30 UTC.

## Verification and remaining work

New checks: **512 backend tests passed / 3 skipped**, **16 operator tests passed**, Ruff lint/format and mypy (**86 source files**) passed. Tests include provisional/final separation, missing outcomes, actual queue/worker publication, source/schedule validation, fold advancement, score-before-refit gating, negative hurdle outcomes, timing exclusions and double-fixture aggregation. An earlier full-suite run encountered the intentional implementation-hash guard while source edits were still in progress; the final full suite ran against stable sources and passed. Frontend code was unchanged and frontend/browser checks were not rerun this stage.

Still pending externally: official GW9 finalization, then final scorecards and the registered final comparison. Bayesian full player scoring, strict TFT historical provenance and current private financial reconciliation remain unavailable. The worker completes final scoring automatically while running; adding GW9 to any later training capture remains gated on final scoring first. No transfers, chips, promotion, publishing or account integration occurred.

See [verification.json](verification.json) for actual software checks, model artifact checksums and canonical forecast identities. Official source endpoints: [bootstrap](https://fantasy.premierleague.com/api/bootstrap-static/), [fixtures](https://fantasy.premierleague.com/api/fixtures/), [GW9 outcomes](https://fantasy.premierleague.com/api/event/9/live/).

## All 28 original streams

| Frozen stream | MAE, all 610 | RMSE, all 610 | RMSE, likely starters (171) | RMSE, likely forwards (18) |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1.2827 | 2.0001 | 2.7928 | 3.9479 |
| baseline_catboost_blend | 1.1749 | 1.9252 | 2.7735 | 3.6327 |
| baseline_catboost_blend_news_zero | 1.0657 | 1.8949 | 2.7543 | 3.6327 |
| baseline_news_zero | 1.2827 | 2.0001 | 2.7928 | 3.9479 |
| football_catboost | 1.1748 | 1.9288 | 2.7774 | 3.6260 |
| football_catboost_news_zero | 1.0616 | 1.8963 | 2.7568 | 3.6260 |
| full_context | 1.1486 | 1.9167 | 2.8125 | 3.7526 |
| full_context_news_zero | 1.0547 | 1.8967 | 2.7974 | 3.7526 |
| full_deeper_regularized | 1.1418 | 1.9092 | 2.8008 | 3.7305 |
| full_deeper_regularized_news_zero | 1.0510 | 1.8894 | 2.7850 | 3.7305 |
| full_second_seed | 1.1573 | 1.9122 | 2.8104 | 3.7506 |
| full_second_seed_news_zero | 1.0547 | 1.8911 | 2.7941 | 3.7506 |
| full_shallow_regularized | 1.1615 | 1.9107 | 2.8011 | 3.7697 |
| full_shallow_regularized_news_zero | 1.0521 | 1.8893 | 2.7871 | 3.7697 |
| opportunity_fixture | 1.1571 | 1.9296 | 2.7822 | 3.7391 |
| opportunity_fixture_news_zero | 1.0510 | 1.8991 | 2.7605 | 3.7391 |
| plus_defensive_actions | 1.1738 | 1.9365 | 2.8128 | 3.6966 |
| plus_defensive_actions_news_zero | 1.0647 | 1.9035 | 2.7886 | 3.6966 |
| plus_xg_xa | 1.1918 | 1.9452 | 2.8157 | 3.7188 |
| plus_xg_xa_news_zero | 1.0710 | 1.9122 | 2.7922 | 3.7188 |
| points_position | 1.2044 | 1.9702 | 2.8194 | 3.9877 |
| points_position_news_zero | 1.0673 | 1.9242 | 2.7931 | 3.9877 |
| tft_research | 1.2632 | 2.0367 | 2.8954 | 3.8504 |
| tft_research_news_zero | 1.1567 | 1.9988 | 2.8620 | 3.8504 |
| three_family_research_blend | 1.1491 | 1.9560 | 2.8265 | 3.7422 |
| three_family_research_blend_news_zero | 1.0770 | 1.9244 | 2.7993 | 3.7422 |
| validation_fit_ensemble | 1.1536 | 1.9123 | 2.8045 | 3.7673 |
| validation_fit_ensemble_news_zero | 1.0509 | 1.8899 | 2.7880 | 3.7673 |
