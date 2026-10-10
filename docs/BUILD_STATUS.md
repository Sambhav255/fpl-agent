# Build status — Cursor handoff

Updated 2026-10-10 after a full check of the running app and public team 6340295. Start with [CURSOR_HANDOFF.md](CURSOR_HANDOFF.md). The baseline app is running. Advanced models are not activated. No commit was made.

## Ownership

Lead: contracts/manifests/locks/generatedtypes/integration/docs. A Gibbs backend,data,jobs; B James domain/planner; C Schrodinger frontend; D Laplace features/models/evaluation. All implementation agents completed, released ownership and closed. Independent reviewer Galileo reviewed correctness/integration/leakage; lead fixed material domain/integration findings and requested final followup. No parallel application editing should continue while Cursor takes over.

## Milestones

| Milestone | Actual state |
|---|---|
|0 setup/demo|Implemented, runnable, lockeddependencies, health/demo/browser/build checked|
|1 rules/state|Implemented, official2026/27configuration, meaningful money/transfer/scoring/chip tests|
|2 providers/import|Implemented/cache/rawsnapshots/validatedURLs; live6340295import verified|
|3 baseline/decisions|Implemented, actual projection→worker→legal lineup/alternatives→save/reload checked|
|4 historical/CatBoost|Strictpipeline and actual retrospective diagnostic training/evaluation; strictdeadlineverifiedactivation blocked by source timing/deadline data|
|5 horizon|Implemented1–8event boundedbeam/HiGHScandidates, independentlyvalidated; frozenprices/unfittedterminalpolicy and expectedautosubobjective omission disclosed|
|6 Bayesian|Realoptionalimplementation and synthetic actualsampling smoke passed; realtraining/calibratedminutes/fullscoring/simulationintegration incomplete|
|7 TFT/ensemble|Synthetic fit/reload passed; deadline-safe one-step encoders implemented; multiweek decoder, adapters, real training, and activation incomplete|
|8 chips/release|Rules/transitions/inventory/persistedplans/export implemented; finaladvancedrelease and remainingacceptance incomplete|

## Verification actually run

Cursor continued from the handoff on 2026-10-09 and fixed the outstanding review findings.

- Full backend: `uv run pytest -q` — **166 passed, 2 skipped**. The previous failure `test_double_blank_and_missing_statistics` now passes.
- `uv run ruff check .` — pass.
- `uv run mypy src` — pass, 31 source files.
- Optional real-library smoke: `FPL_OPTIONAL_SMOKE=1 uv run --all-extras pytest -q tests/test_models.py tests/test_features.py tests/test_evaluation.py` — **27 passed**. PyMC sampling and TFT fit/reload remain synthetic installation checks, not registered models.
- A timestamped TFT panel built a `TimeSeriesDataSet` (12 training samples, 4 validation samples, one batch). That check did not train or register a model. Unseen origin series are encoded as missing categories.
- Earlier frontend lint/typecheck, 7 unit tests, production build, Playwright 6/6, API smoke, and live team 6340295 smoke were already recorded before the review-fix pass. API health during that pass: status ok, database ok, schema version 1. Web http://127.0.0.1:3000 returned 200.

2026-10-10, same checkout, services left running:

- `uv run pytest -q` — **166 passed, 2 skipped**.
- `npm run lint`, `npm run typecheck`, and `npm run test` — pass, 7 unit tests.
- `npm run test:e2e` — **6 passed** (desktop and mobile). Demo tests wrote only team 0.
- `python3 scripts/live_smoke.py --team-id 6340295` — pass. Saved state stayed version 2, Gameweek 5 public picks, bank and chip fields unknown.
- Official history, transfers, and Gameweek 5 picks were fetched through the provider. A Gameweek 6 transfer search was run in memory from those published figures and reconstructed purchase prices. It was not saved and no transfer or chip was submitted.

## Model status

Only the labelled approximate baseline is active. The six review findings below are fixed in code. They do not make an advanced model eligible for release.

- Missing minutes, points, goals, and assists stay missing for both null and non-finite values. A missing minute total is `missing_statistic`, not an appearance.
- Unknown minute labels are excluded from availability heads and from appearance calibration. A real zero stays a non-appearance.
- TFT training keeps explicit missing target rows and gives them zero loss weight, so a gap is not closed by dropping the event.
- Each TFT forecast deadline gets an encoder built only from point versions published by that deadline. A later revision is excluded. If no earlier version was stored, the step is masked.
- Strict training rejects a panel unless `audit.json` carries that parquet's checksum and every row's `replay_timing` and `timing_verified` match the audit. Approximate training accepts only a uniform `conservative_assumed` panel, and only with `--allow-approximate`.
- Bayesian, TFT, and CatBoost runs stage files and publish them after checksum verification. A repeat run reuses the completed directory.

The existing CatBoost diagnostic at `data/models/catboost/b7e63558b354da060b283edb/` is still inactive and retrospective. Its archive audit has no panel checksum, so a new training attempt on that parquet is rejected until the archive is ingested again. MAE was worse than recent points. No superiority claim.

Real Bayesian and TFT training on deadline-verified data is not done. Ensemble activation still needs eligible out-of-fold forecasts and an untouched held-out comparison. Expected autosub and vice fallback are still absent from the optimiser objective. Bayesian minutes and full points scoring are still partial. The TFT path is still a one-event decoder, not a fixed multiweek decoder.

## Running services

Root `bash scripts/dev.sh` is still serving web http://127.0.0.1:3000 and API http://127.0.0.1:8000/docs. SQLite is `data/app.sqlite`. Do not restart unless a later change is imported by the API or worker. User workspace 6340295 and its saved plan were left in place.

## Exact next steps

1. Obtain a historical bundle whose source versions and deadlines are actually verified, ingest it, and write the checksum-bound audit. Do not relabel the current Vaastav archive as verified.
2. Wire Bayesian and TFT `ProjectionRun` adapters only after those models have genuine evaluation artifacts. Keep them inactive until a held-out comparison justifies promotion.
3. Add expected autosub and vice fallback to the optimiser objective, with tests, without double-counting availability.
4. Selling prices are still not stored for team 6340295. The Gameweek 6 plan used published gameweek prices as purchase prices and was not written back. Confirm those selling prices in the app before treating a later saved plan as budget-checked. Do not submit transfers or chips.

No advanced-model release signoff.

2026-10-10 Codex resumed Cursor planner plan. Existingtransfercap/weeklycandidate/chip/UI implementation found; financialstate stillunknown. Lead owns planner/API/frontendfixes andverification. NativeMLadapteragent owns NEW strategy_adapters.py/test_strategy_adapters.py/ML_INTEGRATION.md only. Fixing sell-estimatekind, marginalchipscoring, weeklyHiGHScandidate, savedweeklyplan support. User clarified MLstrategies are mainpriority; baseline must remainlabelled untilvalidatedmodelsready.
