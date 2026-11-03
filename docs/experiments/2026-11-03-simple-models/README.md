# Fixed simple-model comparison — 3 November 2026

Two real unconditional point models were registered and fitted on the **same existing enriched panel and expanding GW5–8 folds** as the retained rolling comparison. Each produced **2,671 outer player-fixture predictions**, with matched row identities and source/comparator checksums verified. [Report](report.json), [registered configuration summary](protocol-summary.json) and [verification](verification.json) retain measured results and fingerprints. All four historical blocks have already been inspected: these are exploratory development measurements, not fresh prospective evidence.

| Method | Pooled RMSE | Pooled MAE |
| --- | ---: | ---: |
| Fixed ridge linear, alpha 10 | 2.202751 | 1.342174 |
| Fixed modest LightGBM 4.7.0 | 2.094006 | 1.199822 |
| Existing full context second seed | 2.098273 | 1.209798 |
| Existing multiscale opportunity | 2.089037 | 1.212077 |
| Existing points hurdle | 2.101591 | 1.208248 |
| Reconstructed app baseline | 2.365965 | 1.849133 |
| Rolling five-match points | 2.274912 | 1.241795 |

LightGBM's RMSE is slightly lower than the original full-context CatBoost and higher than the multiscale CatBoost. Ridge improves over the reconstructed app/rolling comparators but is worse than every retained CatBoost configuration. These four dependent weekly blocks do not establish a decision-policy benefit or a promotion. Baseline football and the numerical optimiser remain champions. No outer result was used to tune these configurations or fit ensemble weights.

Both methods use the full existing categorical/numeric feature contract. Training-only vocabulary, median imputation, scaling and missingness flags are serialized. Unknown categories receive an explicit all-zero encoding. Ridge uses signed labels and an unpenalized intercept; no availability multiplier or nonnegative clipping is applied. LightGBM uses at most 250 trees, 15 leaves/depth 4, seed 43 and validation-only stopping. Each native model is retained, and LightGBM serialization parity is checked during fitting. Optional LightGBM imports do not affect app startup or the linear implementation.

The actual final durable worker job `8d18537f829d4feabc16507d424da85b` succeeded in about **4.6 seconds** of queued computation after registration at 13:10:09 UTC. A subsequent retry verified and reused all eight completed fold/method checkpoints; report and prediction hashes were unchanged. The prior run before adding dependency-lock binding is retained separately and gave identical metrics. This was a durability refinement, not a new configuration search.

Artifacts remain ignored under `data/research/simple-models-2026-11-03/models/simple_experiments/5a03cad65fe2f6bb69bf1936`. The research store is a SQLite backup of retained source/evidence, with only its copied pending jobs removed before the experiment; original source stores, frozen forecasts, and personal app state were untouched. Training invokes the shared score-before-label-reuse guard. Only finalized GW1–8 targets were consumed.

To queue a fresh registered comparison after installing the optional `research` extra:

```sh
DATA_DIR="$PWD/data/research/simple-models-2026-11-03" \
  backend/.venv/bin/python scripts/research/simple_experiments.py \
  --reference-directory data/research/gw9-models-2026-10-31/models/rolling_experiments/102edc1f41beeaec690aaa78 \
  --work-once
```

Use the same absolute `DATA_DIR` as the intended store, as explained in the operator guide; a fresh registration gets its actual creation time. Research dependencies were installed in a temporary isolated target for the actual run; the maintained optional lock now records LightGBM 4.7.0.

Four focused tests passed: train-only preprocessing and unknown-category handling; signed linear labels/save-load parity; optional dependency import isolation; outer-target independence and checkpoint corruption rejection. Ruff lint/format and module mypy passed. No frontend changes were made. Historical timing/membership/schedule reconstruction limitations of the original panel remain. Next: test complementary development predictions through a separately registered ensemble or same-state legal policy comparison, retaining untouched prospective weeks.
