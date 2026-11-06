# Build status

Updated **6 November 2026 UTC**. This is the current implementation summary.
[Start here](START_HERE.md) for navigation; the [experiment registry](experiments/README.md)
contains dated measurements and earlier verification records.

## Available

- Local Next.js interface, FastAPI backend, SQLite state and recoverable worker.
- Public squad import, manual financial corrections, stale-input checks, legal
  lineup/transfer/chip comparisons and saved plans. Transfers remain manual.
- Labelled approximate football baseline and numerical planner as champions.
- Immutable official captures, chronological model experiments, source-bound
  artifacts, finalized scoring and independent recommendation validation.
- Typed opportunity heads, historical calibration, coherent fixture minutes,
  signed points, pinned historical archives and explicit missingness/provenance.
- Opt-in weekly all-player competitions, worker heartbeat/recovery and separate
  point, opportunity, interval, selection and execution diagnostics.

## Latest model evidence

The [weekly backend competition](experiments/2026-11-06-weekly-tournament/README.md)
ran six actual mean variants, an equal-weight blend and the football baseline for
all **670 captured players**. Official-zero sensitivities give **16 new streams**;
the scorer also watches the original 23 canonical GW10 streams. **39 streams /
26,130 event-point forecasts** are frozen; GW10 actual outcomes remain pending.

Five historical GW5–9 folds / 3,341 event rows: CatBoost has the lowest RMSE
(**2.03905**), Extra Trees the lowest overall MAE (**1.14806**), and LightGBM the
lowest likely-starter MAE. Shared auxiliary heads beat matched rolling Briers and
slightly improve minutes MAE. Nominal 80% intervals cover **88.60%**; this is not
calibrated joint uncertainty. Latest-data auxiliary refits remain uncalibrated.

These are exploratory, reconstructed historical blocks, not prospective policy
wins. The [earlier continuation](experiments/2026-11-06-master-plan/README.md)
records multi-season acquisition, cross-season research links, direct-lead evidence
and negative results. No champion was promoted.

## Current limits

- Current-season qualified forecasts do not extend to all longer leads merely
  because reconstructed prior-season research covers lead 8.
- Strict historical timing/identity coverage, complete Bayesian scoring, strict
  TFT release and calibrated joint scenarios retain evidence gates.
- Genuine social extraction/ablation and qualified RL continuation remain open.
- Personal legal-policy studies require reconciled finances, committed transfers,
  hits and chips. The forecast competition does not require private finances.
- Schedules require the local worker and machine uptime; no OS service is installed.

The [master-plan checklist](MASTER_PLAN_STATUS.md) distinguishes delivered code,
executed research and remaining acceptance requirements.

## Verification record

**Latest backend/model stage:** 635 backend tests passed / 3 skipped; 22 operator
tests passed; Ruff lint/format and mypy passed. Actual full-universe fits, checkpoint
reloads, coverage guards, retry behavior and separate sensitivity freezes ran.

**Prior interface/integration stage:** 13 frontend unit tests, static checks and
production build passed; isolated smoke passed; desktop/mobile browser checks
12 passed / 10 optional skipped. These were not rerun for the backend-only stage.
See each dated report for exact scope. A preceding installed backend dependency
audit reported zero known vulnerabilities after patching; this is not a new audit.

**Repository cleanup:** documentation navigation and source layout were consolidated;
plans/runtime guidance moved with checksums, operational notes remain ignored,
and native artifacts are excluded from source exports. New checks: **28 operator
passed**, **5 focused backend passed**, isolated baseline **4 passed / 1 skipped**;
Ruff and documentation checks passed. These do not replace the earlier full suites.
See [release preparation](operations/RELEASE_PREPARATION.md) for scope and export guidance.

## Next action

After official GW10 finalization, score the frozen streams before reusing labels.
Compare all-player, likely-starter and position results, retain negative findings,
and freeze the declared weekly procedure for GW11. Keep original studies unchanged.
