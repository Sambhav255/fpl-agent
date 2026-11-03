# Earlier-OOF-only convex ensemble — 3 November 2026

The registered hypothesis was that a convex blend of **ridge, LightGBM and multiscale CatBoost**, fitted only to earlier out-of-fold development predictions, would improve unconditional point RMSE against matched individual models. The run used the previously inspected historical panel. It did **not** improve over the best individual: ensemble RMSE **2.078964**, compared with multiscale CatBoost **2.071538** and LightGBM **2.077180** on the same **2,004 GW6–8 outer rows**. No model was promoted. This negative result is retained without retuning the model set or weights.

The first OOF week, GW5, is development warmup and excluded from the reported ensemble window. For GW6, weights use only GW5 OOF predictions; GW7 uses available GW5–6 OOF labels; GW8 uses available GW5–7 OOF labels. Each base model was trained before its own prediction origin. Weight fitting also checks that all development labels precede the current prediction origin. A week's outcome can inform subsequent weeks after availability, but cannot fit that week's own forecast. These are three dependent historical event blocks, not prospective confirmation.

| Matched method | GW6–8 RMSE |
| --- | ---: |
| Earlier-OOF convex ensemble | 2.078964 |
| Multiscale CatBoost | 2.071538 |
| LightGBM | 2.077180 |
| Ridge | 2.205577 |
| Full-context CatBoost | 2.082353 |
| Points hurdle | 2.088113 |
| Reconstructed app baseline | 2.338818 |

The [report](report.json) retains exact per-origin weights, development windows, counts, availability cutoffs and artifact hashes. The [protocol summary](protocol-summary.json) retains the fixed model set and weight rule registered at **13:14:29 UTC**, before fitting ensemble weights. Earlier development-fit MSE improved slightly at each origin, which did not translate to a same-window advantage over the best individual. There is no outer-driven fallback or retrospective selection of an ensemble champion.

The short local computation reused already fitted models; it did not run base model training. All source and prediction hashes were checked, the shared scoring-before-label-reuse guard ran, and a repeated exact-protocol execution produced an unchanged report and artifact hashes. Full predictions, original protocol and implementation bytes remain ignored under `data/research/simple-models-2026-11-03/models/oof_ensemble/cad76fb4930b242979cf9b81`.

Reproduce a fresh actual registration with:

```sh
DATA_DIR="$PWD/data/research/simple-models-2026-11-03" \
  backend/.venv/bin/python scripts/research/oof_ensemble.py \
  --simple-directory data/research/simple-models-2026-11-03/models/simple_experiments/5a03cad65fe2f6bb69bf1936
```

Three focused tests passed: perturbing current/future outer targets cannot change the weights or predictions at their own/earlier origins; delayed development labels are excluded and contaminated base training is rejected; missing/duplicate prediction coverage fails. Ruff lint/format and module mypy passed. Original historical timing, membership, schedule and current-universe reconstruction limits remain. No old GW9/GW10 freeze or registered comparison was changed. Next: retain the stronger single-model comparator and collect prospective evidence or test same-state legal policy outcomes; do not tune this blend on these reported weeks.
