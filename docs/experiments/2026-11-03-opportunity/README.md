# Opportunity heads — 3 November 2026

A fixed comparison registered before fitting evaluated legacy regression heads with additive probability offsets against binary Logloss heads with earlier sigmoid calibration and per-fixture opportunity projection. Four expanding outer folds cover GW5–8, **2,671 player-fixture rows per method**. Only finalized GW1–8 labels from the verified collection were used. The shared scoring-before-training guard passed on a consistent SQLite backup. Existing forecasts, registered studies and source database were not rewritten.

| Metric | Legacy regression + offset | Binary + sigmoid + coherent minutes |
| --- | ---: | ---: |
| Appearance Brier | 0.129059 | 0.129910 |
| 60-minute Brier | 0.103395 | 0.104127 |
| Appearance log loss | 0.413805 | 0.410889 |
| 60-minute log loss | 0.337739 | 0.336117 |
| Minutes MAE | 16.882671 | 16.845961 |
| Point RMSE | 2.140505 | 2.140505 |

The binary bundle **did not improve either primary Brier objective**. Log losses and minutes errors improve slightly. Point predictions are identical because the unconditional point head is unchanged; appearance is never applied again to its output. These inspected dependent historical blocks do not establish prospective benefit. Baseline football and the numerical optimiser remain champions.

Calibration alone improved binary appearance Brier from 0.130738 to 0.129910, but the full calibrated/projected 60-minute Brier worsened from raw binary 0.103312 to 0.104127. The report preserves raw versus final metrics, reliability bins, event/position results, sparse histories, likely starters and observed substitute-history subsets. Both methods use the same historical features and no historical injury news. Injury/return/club-change subgroup evidence is unavailable. Current-universe membership and historical publication times remain reconstructed assumptions. No tuning on these outer results or automatic promotion occurred.

The binary method projected 176 fixture minute means (mean absolute change 0.099874 minutes across all rows) and 53 threshold probabilities. Raw values and projection deltas remain in predictions. Whole-minute, 90-minute mixture bounds constrain each fixture independently; a double may exceed 90 event expected minutes. Starts use only observed labels; missing labels are omitted consistently, all-missing starts remain unavailable, and one-class folds retain an explicit Beta(1,1) prior fallback.

[Protocol](protocol.json) was retained before fitting, binding feature columns, folds, source collection, implementation hashes and dependency lock. [Full report](report.json) binds frozen prediction hashes. The exact executed source bytes, eight fitted artifacts, calibration metadata, SQLite backup and outer predictions remain in ignored `data/research/opportunity-2026-11-03/`. Runtime was **21.50 seconds**. The saved implementation predates later metadata-only clarifications; its original bytes and hashes are retained. No old artifact was modified.

Typed artifacts dispatch classifiers with explicit positive class probabilities and verify reload parity. The reader retains legacy regressors/additive offsets and legacy minute values. Held-out calibrators bind model identity, features, interval, count and class balance. Latest-data serving refits remain explicitly **uncalibrated** and never reuse another fit's calibrator. The evaluated calibrated auxiliary method and uncalibrated serving auxiliary method are identified separately.

Reproduce with a fresh output directory (the runner refuses overwrite):

```sh
backend/.venv/bin/python scripts/research/opportunity_comparison.py \
  --database data/research/gw9-models-2026-10-31/app.sqlite \
  --collection-id 7ad5d2a7c28d4f1497e1f84ad4db4354 \
  --output data/research/opportunity-new-run
```

New focused verification: **35 tests passed** across opportunity, CatBoost and forecast routing; backend mypy passed (91 source files including the temporarily copied shared guard), and changed Python files passed Ruff. Broader integrated checks belong in the maintained build status. This result supports retaining the comparator and testing a declared minutes mixture or supported calibration holdout on future registered evidence, rather than assuming classification automatically wins.
