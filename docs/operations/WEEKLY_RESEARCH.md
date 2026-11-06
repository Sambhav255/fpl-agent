# Weekly research workflow

Use the [operator reference](../../scripts/README.md#weekly-all-player-model-competition)
for exact commands and the [experiment registry](../experiments/README.md) for results.
The current competition operates independently of private manager finances.

## Evidence lifecycle

1. Capture immutable official bytes, observation times and the full player universe.
2. Check official finalization. Score frozen forecasts before their labels enter training.
3. Validate coverage, source identity, feature timing and missingness.
4. Register fixed methods and chronological partitions before fitting.
5. Fit training-only preprocessing and preserve native checkpoints and predictions.
6. Publish a new forecast before its actual deadline; preserve the original study.
7. Score actual outcomes after official finalization, including incomplete coverage.
8. Compare fixed methods across weeks. Promotion remains a separate evidence review.

The default local store opts into the existing full-universe review schedule. One
canonical tournament is registered per event after the previous event finalizes.
Repeated captures do not expand an already frozen study. New hypotheses use a new,
honestly timestamped study; they do not inherit untouched evidence from earlier work.

## What the comparison measures

| Output                      | Diagnostics                                                                       |
| --------------------------- | --------------------------------------------------------------------------------- |
| Unconditional signed points | MAE, RMSE, bias, matched coverage and event rank correlation                      |
| Opportunity                 | Appearance/60-minute Brier scores, log loss and reliability bins                  |
| Minutes                     | MAE, bias and coherent fixture-level duration bounds                              |
| Marginal quantiles          | Pinball loss, interval coverage, width and raw crossing records                   |
| Selection                   | Position and origin-defined likely-starter subsets, top-five/top-pick diagnostics |
| Robustness                  | Sparse histories, model disagreement, source revisions and missing coverage       |

Shortlists are unconstrained diagnostics, not legal portfolios. Mean forecasts,
medians, quantiles and probabilities have different meanings. Shared auxiliary heads
are not independent evidence for each point model. Marginal quantiles cannot be
summed into a calibrated double-gameweek or joint squad distribution.

## Operating controls

Use the same absolute `DATA_DIR` for collection, jobs and the worker. See
[worker runtime](WORKER_RUNTIME.md) for heartbeat, recovery and optional supervision.
The worker must remain alive and the machine awake. No hosted scheduler is implied.

`configure_tournament.py --disable` stops future competition registration; frozen
benchmarks still score. Native checkpoints and completed publications are reused
through checksums. Partial collection cannot create synthetic zero forecasts.
Optional library failures remain visible jobs and do not replace the baseline.

Keep current live championship status in [build status](../BUILD_STATUS.md), not in
this workflow guide. Retain both improvements and regressions in dated reports.
