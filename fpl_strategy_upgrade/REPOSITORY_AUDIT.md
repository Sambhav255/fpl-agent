# FPL repository audit

Reviewed 10 October 2026. Repository: [Sambhav255/fpl-agent](https://github.com/Sambhav255/fpl-agent). Pinned commit: `e759bcfb299d3f818d2e80ebb017796874cf8019`.

## Assessment

The project is a useful baseline application with real domain logic and substantial unfinished modelling work. It is not yet an evaluated machine learning strategy engine. Your concern about priorities is justified: the next release should prove forecasting and decision quality before adding further visual polish.

The existing model files are more than decorative placeholders. CatBoost has genuine training code, Bayesian fitting calls PyMC, and TFT fitting calls PyTorch Forecasting. However, the application prediction worker only calls the approximate baseline. There is no implemented promotion and routing path that would make a successful model training run power the planner.

Do not discard the application. Preserve its manager state corrections, unknown financial state handling, rules, immutable snapshots, recoverable jobs, version checks and independent plan validation. Improve the intelligence behind those interfaces.

## Scope and evidence

I retrieved 80 files at the pinned commit, including all 34 Python source files, 13 backend test files, selected frontend components and tests, CI configuration and current implementation notes. I traced data collection, feature construction, training, inference adapters, model registry, projection jobs, transfer search and chip advice. I ran two controlled synthetic behavioural probes against the actual checked out source and parsed all 47 Python files for syntax.

I did not execute the full project test suite, train the three model families, inspect your ignored local data, or run your personal team. This environment lacks several project dependencies. The repository reports 194 backend tests passing, three skipped tests, and 14 browser tests passing; those counts are developer recorded results rather than results independently reproduced here. A GitHub Checks run for this commit was in progress when inspected. Passing application tests would not establish forecasting or transfer performance.

All findings below describe the pinned code. Later local changes or commits need a fresh comparison.

## Findings

| ID | Priority | Finding | Evidence | Consequence |
| --- | --- | --- | --- | --- |
| A01 | P0 | Projection jobs always use the baseline | `backend/src/fpl_app/jobs/__init__.py`, `Worker.compute`, lines 318 to 330 | Training an advanced artifact alone cannot improve the live app |
| A02 | P0 | The only active forecast is heuristic | `models/baseline.py`, `baseline_run` | Forecast quality and uncertainty are not established |
| A03 | P0 | CatBoost uses ten lagged numeric inputs | `features/pipeline.py`, `NUMERIC_FEATURES`, lines 41 to 52; `models/training.py`, `train_catboost` | Opponent, venue, position and fixture context are absent from its actual training matrix |
| A04 | P0 | Search can miss valuable funding combinations | `optimisation/planner.py`, `_highs_candidate` and `recommend`; reproduced below | A solved proxy is not the best legal transfer plan |
| A05 | P0 | No integrated strategy replay exists | `evaluation/metrics.py` contains forecast metrics and ensemble fitting, but no evolving manager policy evaluator | There is no evidence that recommendations beat simpler policies after hits |
| A06 | P1 | Beam pruning uses accrued points | `optimisation/planner.py`, lines 389 to 403 | Paths with an immediate sacrifice can disappear before their future benefit is assessed |
| A07 | P1 | Current availability persists throughout the horizon | `models/baseline.py`, probability set outside fixture loop | An injury flag for the next match can suppress a player for eight events |
| A08 | P1 | Future chip use is not jointly optimised | `optimisation/planner.py`, `event_chip = chip if offset == 0 else None`; `optimisation/advice.py` | Present advice cannot support an integrated season game plan |
| A09 | P1 | Scenario information is lost before planning | Bayesian sampler produces joint outcomes, adapter returns marginal projections, planner uses scalar means | Correlated outcomes, automatic substitutions, captain fallback and downside cannot guide decisions |
| A10 | P1 | Bayesian scoring and minutes are incomplete | `models/bayesian.py`, `shared_scenarios` | Team goal forecasts are not a complete calibrated FPL points model |
| A11 | P1 | TFT is restricted to one event | `models/tft.py`, `max_prediction_length=1`; strict adapter rejects longer horizons | Its name does not imply implemented forecasting across multiple future events |
| A12 | P1 | Historical provenance is a bottleneck without a practical collection plan | `features/archive.py`, `features/pipeline.py`, `docs/ML_INTEGRATION.md` | The project can remain indefinitely blocked while waiting for an ideal historical bundle |
| A13 | P1 | Evaluation is too narrow | `models/training.py`, `split_panel`; `evaluation/metrics.py` | The final two event cutoffs provide a small test window; broad performance is unknown |
| A14 | P1 | Promotion eligibility is always false | `models/registry.py` and `models/training.py`, `evaluate_run` | A trained or evaluated badge cannot become an operational champion |
| A15 | P1 | No social intelligence implementation | No Reddit, X, claim extraction or consensus modules in the complete tree | The requested expert and crowd evidence layer requires a new subsystem |
| A16 | P2 | Product emphasis favours the current event | `apps/web/src/components/planner/optimum-card.tsx`, heading “Optimum move” | The principal interface can draw attention away from the stronger horizon policy |

P0 means required for the next trustworthy intelligence release. P1 means required for the broader strategy release. These are review priorities, not measured performance scores.

## Reproduced transfer search failure

A synthetic one event case has 18 players, a legal 15 player owned squad, two free transfers, zero bank, and no permitted additional hits. It uses plausible purchase prices of £4.5m, £5.0m and £5.5m.

| Plan | Expected points | Action |
| --- | --- | --- |
| Keep | 84 | Keep the owned squad |
| Best returned by current planner | 94 | Replace one goalkeeper with a goalkeeper upgrade |
| Best exhaustive legal plan | 101 | Sell reserve goalkeeper for £5.0m, buy £4.5m reserve, use released £0.5m to upgrade a midfielder |

The seven point gap is a controlled software counterexample, not an estimate of real world losses. The existing solver had time remaining and reported an optimal candidate proxy with zero proxy gap. That gap describes its own linear squad objective, not the complete recommendation problem.

The proxy maximises the sum of points from all 15 owned players. Downgrading a bench goalkeeper looks costly under that objective, although the retained first goalkeeper can still start. The candidate menu contains all single transfers and only a small number of proxy generated transfer bundles. It therefore misses the beneficial pair. This is a direct reason to solve squad ownership, starting lineup and captaincy together.

Reproduction is provided in `verification/audit_probes.py`, with output in `verification/audit_probe_results.json`. The portable probe takes the actual project root as its argument and imports that project's `backend/src` code. Run it through the project environment as documented in the verification README. Do not treat this script as a replacement for the project regression suite.

## Reproduced availability limitation

For a synthetic player with current availability equal to zero, the baseline emits zero expected points and zero expected minutes in every event from GW8 through GW15. The code intentionally freezes snapshot availability, and discloses this assumption. It has no recovery trajectory.

Build event specific availability from public return information and calibrated recovery scenarios. Do not assume recovery merely because several weeks pass. Distinguish a probability for the next match from a permanent removal or suspension duration.

## What the model code actually does

### Baseline

It blends a shrunk points per appearance reference with approximate appearance, goals, assists, clean sheet and constant bonus components. Fixture difficulty and home advantage are hand chosen adjustments. Defensive contributions, cards, saves and concessions are missing from the component forecast. This may be a useful comparator, but it is not a trained or calibrated forecast.

### CatBoost

There is a real mean regressor and auxiliary classifiers for appearance, 60 minute exposure and starts when labels exist. The mean target is unconditional, which is appropriate. However, the feature list omits much of the football context already present elsewhere in the panel. The inference adapter derives minutes from a lagged average, does not supply calibrated point distributions, and is not connected to prediction jobs.

### Bayesian events

The team goal model is genuinely hierarchical and samples a shared match score. This is a useful foundation for correlated clean sheet and attacking outcomes. Player minutes use a heuristic 20 or 80 minute mixture, and goalkeeper selection is simplified. Full BPS, defensive contribution, saves and disciplinary outcomes are missing. Full match concessions are used even where a player's on pitch interval should matter. Preserve the joint scenario idea and complete it before treating these points as comparable with a full FPL target.

### TFT

The implementation genuinely fits separate mean and quantile heads and makes an effort to preserve deadline information and fixture slots. It is a compact CPU model with a one step decoder. Opponent IDs are currently treated as numeric inputs. It needs categorical football context, a genuine decoder across the supported horizon, proper target masking, held out evaluation and an operational serving path.

### Ensemble

Convex weight fitting exists as a utility. It is not an active ensemble service. An ensemble fitted on validation data is not automatically better outside that data. Weight fitting and champion selection need separate tests and uncertainty reporting.

## Historical data correction

The Vaastav repository currently says weekly updates stopped after 2024/25, with three larger updates per subsequent season. It is an archive source, not a dependable weekly collection service. It also explicitly warns that its `xP` field may reflect information collected after matches. The current exclusion of unverified historical xP is sensible. See [dataset notice](https://github.com/vaastav/Fantasy-Premier-League).

Do not remove the honesty gates to manufacture eligibility. Instead add distinct modes for historical reconstruction, research experiments, prospective shadow forecasts and deployed forecasts. Historical fitting performed today can be a valid retrospective experiment if its input cutoffs are respected. It must not claim that the artifact existed at the historical deadline. Conversely, final historical observations already known today can legitimately be used to train a model for a future deadline, even when their exact original publication timing is uncertain. Such a model still needs honestly qualified evaluation before becoming the default.

## What to retain

1. Financial fields stay unknown until confirmed.
2. Money remains integer tenths with separate acquisition and selling values.
3. Plan validity is checked independently after solving.
4. Source and manager state versions invalidate stale plans.
5. Synthetic demo data is separated from real training and performance claims.
6. Long jobs remain recoverable and optional model dependencies remain optional.

## Recommended next release

Freeze cosmetic work. Ship an evaluated football forecast, a lineup aware planning objective, a real prediction router, and a reproducible strategy replay report. Start collecting future deadline snapshots immediately. Build social extraction and expert/crowd summaries independently, with no automatic forecast adjustment until permissions and usefulness are established.

Success means the application can answer: “Which action is best now, why does it help over the coming events, when would that recommendation change, and what evidence supports the forecast?” It does not mean that all three model names appear on a page.
