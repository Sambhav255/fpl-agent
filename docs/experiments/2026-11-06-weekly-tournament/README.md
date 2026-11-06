# Weekly backend model competition — 6 November 2026

This stage focuses on model experiments and prospective scoring, independently of
private manager finances. It does not claim that forecast losses establish legal
transfer-policy benefit. Baseline football and the numerical planner remain champions.

## What actually ran and froze

A separate SQLite backup used verified full-universe collection
`646ba36453a047ceb671993b8342f04f`, captured **04:05:58 UTC** on 6 November.
All **670 official players** were retained. The scoring-before-training guard passed.
Cloned personal review schedules were disabled in the isolated research store.

Six fixed mean methods ran: Ridge, **Extra Trees**, **histogram gradient boosting**,
CatBoost, fixed recency-weighted CatBoost and LightGBM. The two bold families are new
challengers. A fixed equal-weight blend and the actual football baseline complete
eight prospective streams. Hist-gradient uses squared-error means; its separately
fitted quantile heads do not substitute a median for expected points. Signed point
labels survive; no point mean is multiplied by appearance again.

Five expanding GW5–9 folds used train-only preprocessing/vocabularies, a separate
later validation block for auxiliary calibration, and a later outer event. No
hyperparameter selection used the outer results. Latest-data serving refits use
finalized GW1–9 labels; their auxiliary probabilities remain **uncalibrated** and
never inherit another fit's sigmoid. Actual worker job elapsed time was **70.40 s**.
Seventy-two native head/checkpoint files, preprocessing, split indices, exact executed
implementation, dependency identities, source bytes, predictions and evaluations
remain under ignored `data/research/weekly-tournament-2026-11-06/`.

Eight additional official-zero sensitivity streams were frozen separately: official
0%/unavailable/suspended players receive one deterministic zero override; doubtful
flags remain unchanged. This affected 176 players, including inactive roster entries.
These are explicitly availability scenarios, not eight additional trained models.
The original raw benchmark was not rewritten.

There are **16 new streams × 670 players = 10,720 event-point forecasts**. The same
local scorer also watches exact copies of the two original canonical GW10 bundles
(23 streams), giving **39 streams × 670 players = 26,130 forecasts**. Existing
registered study definitions and original files are unchanged. Streams can share
architectures, forecasts and auxiliary heads; they are not independent experiments.
[Freeze identities and aggregate metrics](metrics.json) retain publication/deadline bindings.
All prospective GW10 outcomes remain pending official finalization. The original
streams froze earlier than this competition; cross-bundle differences include input
freshness/news, not only model architecture. The six new mean methods share the
same new source and folds for the controlled within-competition comparison.

## Actual historical measurements

Matched **3,341 player-event rows over five dependent events**:

| Method | RMSE | MAE |
| --- | ---: | ---: |
| Reconstructed football baseline | 2.32524 | 1.82905 |
| CatBoost | **2.03905** | 1.16665 |
| Recency CatBoost | 2.04146 | 1.16304 |
| Equal-weight means | 2.04265 | 1.15629 |
| LightGBM | 2.05149 | 1.16451 |
| Extra Trees | 2.06248 | **1.14806** |
| Ridge | 2.12527 | 1.29213 |
| Histogram gradient boosting | 2.14261 | 1.22075 |

CatBoost wins the declared historical RMSE metric; Extra Trees has the best overall
MAE. In the **888 origin-defined likely-starter fixture rows**, LightGBM has the
lowest MAE (2.4086); CatBoost retains lower RMSE (3.1261). A population-wide winner
does not necessarily win the decision-relevant subset. These already-inspected
historical blocks retain current-universe, schedule/membership and publication-time
reconstruction limitations. They are development evidence, not a new prospective win.

One shared auxiliary bundle combines Extra Trees appearance/60-minute classifiers
and minutes regression, validation-only sigmoid calibration in historical folds,
and histogram quantile regressors. Fixture-level coherence bounds are applied;
raw probabilities/minutes and projection changes remain in retained rows.

| Matched auxiliary metric | Rolling comparator | New shared heads |
| --- | ---: | ---: |
| Minutes MAE | 13.87894 | 13.76099 |
| Appearance Brier | 0.12990 | 0.11156 |
| 60-minute Brier | 0.10989 | 0.09040 |

The nominal 10–90% interval covered **88.60%**, with mean width 2.8499 points.
Sorting removed crossing in 55 raw rows; it does not establish calibration. Marginal
quantiles and probabilities are unavailable as joint event distributions for doubles;
fixture means/minutes are summed, while double-event quantiles/appearance are omitted.
No independence assumption is used to fabricate them.

## Scoring and subsequent weeks

The standard recoverable worker scores only after official `finished` and
`data_checked` gates and complete outcome coverage. The extended scorecard retains
point MAE/RMSE/bias, matched coverage, Spearman, position diagnostics, top-five and
single-top-pick diagnostics, minutes MAE/bias, appearance and 60-minute Brier/log
loss/reliability, quantile pinball/coverage/width. Shortlists are unconstrained
ranking diagnostics, not legal portfolios. Old streams without auxiliary forecasts
keep those metrics unavailable. Missing outcomes never become zero.

An opted-in tournament hooks the existing six-hour full-universe learning review.
It waits for the previous event to finalize, scores retained bundles before label
reuse, registers one canonical study per event, then queues fitting in the existing
worker. Repeated review captures do not expand an already frozen event. Completed
unit and publication retries reuse checksummed artifacts rather than altering
publication timestamps. Failures remain recoverable jobs, never silent promotion.

The default worker was refreshed with this code and both new and original benchmark
registrations. A real scheduled review completed at 04:36:31 UTC and recorded
`already_frozen` for this event, rather than rerunning the competition. After code
changes, old review ticks are preserved and generation resumes at the next configured
slot; stale ticks are not rewritten or retried every minute. No OS service was installed: collection/scoring require the Mac awake
and the worker alive. No private squad, account, chip or transfer action is changed.

## Verification

Final backend suite: **635 passed, 3 skipped**. Operator suite: **22 passed**.
Ruff lint/format and mypy passed (105 source files). Actual small native fits tested
all six methods, reload/checkpoint parity, empty serving calibration partitions,
probability/minute/quantile semantics and recovery. Offline tests verify incomplete
outcomes, separate official-zero scenarios, parent preservation, opt-in scheduling
and one registration per event. Full bootstrap membership and exact future fixture
coverage are checked before publication, so partial collection cannot fabricate zero
forecasts for uncollected players. The actual full-universe job succeeded; a repeated
operator command returned `already_frozen` without refitting.

An earlier full run overlapped a schedule-fixture edit and failed that test; the
final clean run above passed. No frontend code or frontend tests were changed/run
in this backend stage. The prior frontend checks remain recorded in the preceding
report, not relabelled as new verification.
