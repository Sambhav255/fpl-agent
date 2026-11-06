# FPL model improvement and Codex execution plan

Prepared 3 November 2026. Repository: https://github.com/Sambhav255/fpl-agent

Reviewed revision: `0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59`.

## 1. How to use this file

Give this entire file to Codex in the existing project. Ask it to execute the implementation plan, starting with section 4, and use the master prompt in section 34. This is a working specification and implementation assignment, not a request for another planning document.

The next session should produce functioning model improvements, real experiment artifacts, meaningful tests, and a clear account of what improved. Documentation supports that work. Adding another dashboard is a low priority.

The objective is better Fantasy Premier League decisions across the remaining season: player selection, transfers, captaincy, bench order, chip timing, and the flexibility to respond to new information. Better rank is the desired outcome. It cannot be guaranteed, and rank itself is not a useful standalone training target.

Read the current checkout before editing. This review is pinned to the revision above. If the repository has advanced, retain completed work and adapt this plan to the changes. Do not reimplement features that now exist.

## 2. What the latest repository actually contains

The project has made substantial progress on modelling and evaluation. It is no longer fair to describe the latest changes as primarily interface work. The latest commit introduces rolling experiments, frozen selection diagnostics, and better preservation of measured evidence. The remaining gap is proving that forecast improvements translate into better legal FPL decisions.

| Area | Reviewed state | Implication |
| :--- | :--- | :--- |
| Application | Next.js, TypeScript, FastAPI, SQLite, Parquet, recoverable worker | Extend the existing architecture |
| Production forecasts | Approximate football baseline remains champion | Keep a reliable comparator available |
| Production strategy | Numerical planner remains champion | Improve inputs and planning evidence before replacing it |
| CatBoost | Real fitted models and chronological experiments | Improve the existing implementation |
| Points hurdle | Already implemented with a binary classifier and signed nonzero return regressor | Do not build a duplicate hurdle model |
| Rolling comparisons | Three fixed enriched configurations, GW5 through GW8 | Useful exploratory development evidence |
| Frozen forecast evaluation | Existing forecasts, source bindings, finalization gates, revisions | Preserve this system and extend it |
| Selection diagnostics | Origin eligibility, fixed comparisons, registration receipts, canonical event plans | Useful ranking evidence, not legal policy performance |
| Bayesian model | Team goal research exists; complete player scoring remains gated | Team goal accuracy is not player point accuracy |
| TFT | Real research implementation; strict historical provenance remains restricted | Additional neural complexity is not the immediate bottleneck |
| Reinforcement learning | Experimental policies and replay infrastructure | Continue as a challenger after strengthening the simulator |
| Long horizon planning | Existing bounded sequence search and chip paths | Search coverage and forecast support still need work |
| Weekly review | Recoverable local worker and optional schedules | Scheduling depends on a running process and correct data directory |
| Social signals | Live Reddit and X collection disabled; point adjustment zero | Add a measured evidence pipeline before changing forecasts |
| Personal transfer advice | Current private squad finances still need reconciliation | Public team import alone is insufficient for exact transfers |

The documentation now has a maintained specification area and an archive. Follow `AGENTS.md`, `docs/START_HERE.md`, `docs/BUILD_STATUS.md`, `docs/ROADMAP.md`, and the relevant `docs/specs/` files. Archived prompts do not override current contracts. Preserve immutable reports under `docs/experiments/` and private ignored state.

### Evidence from the latest reports

The repository reports 2,671 outer player fixture predictions per model across GW5 through GW8:

| Configuration | Pooled point RMSE |
| :--- | :--- |
| Multiscale opportunity | 2.0890 |
| Full context, second seed | 2.0983 |
| Points hurdle | 2.1016 |
| Reconstructed app baseline | 2.3660 |
| Rolling points baseline | 2.2749 |

These are four dependent weekly blocks, not 2,671 independent experiments. Historical timing, club membership, and schedule information include reconstruction assumptions. These weeks have already been inspected. Use them for development, not fresh prospective confirmation.

The provisional GW9 ranking report shows why overall RMSE is insufficient. In the same origin eligible likely starter pool, the baseline top five defenders returned 37 points, the original CatBoost list 23, and the selected full context news sensitivity list 12. Corresponding forward lists returned 24, 34, and 31. These are unconstrained lists, not legal squads, transfer policies, or captain decisions. One noisy week does not establish a winner.

The retained GW10 study contains 23 canonical frozen streams and 176 origin eligible players. Its primary comparison is already registered. Preserve it exactly. A later model belongs in a new prospective study with an honest creation time, not retroactively inside the old study.

### What was verified in this audit

Source and test files were retrieved at the pinned revision. All 143 retrieved Python files parsed successfully. Selected functions, training paths, artifact loading, rolling protocols, review orchestration, scoring, and frontend package commands were inspected.

A controlled probe of the actual `_predict` function, isolated from its module dependencies, confirmed that synthetic head outputs can produce `minutes_mean=90` alongside `appearance_probability=0.1`. This demonstrates missing output coherence enforcement. It does not establish that a retained real forecast currently contains that combination.

The repository reports 533 backend tests passed, 3 skipped, and 18 operator/documentation tests passed at this stage. Those suites were not rerun in this audit environment. The reviewed hosted Actions run, `41614248293`, had successful backend, frontend/build, and browser/persistence steps, but the overall run concluded cancelled. Do not describe the whole run as a completed green check.

No models were retrained here. Private retained data, model binaries, and current manager finances were not available through the repository review. Separate repository reported results from independently executed checks in all subsequent reports.

## 3. Product priorities

Use this order when choosing work:

1. Protect existing predictions, outcomes, user state, and deadline integrity.
2. Make appearance, minutes, and point forecasts coherent and measurable.
3. Add trustworthy historical data and stronger chronological evaluation.
4. Evaluate legal decisions from identical starting states.
5. Improve supported future forecasts and transfer flexibility.
6. Add complementary models that answer a specific unresolved question.
7. Make the weekly learning process durable and observable.
8. Add social evidence through controlled experiments.
9. Advance reinforcement learning once its environment earns trust.
10. Change the interface only where the improved backend needs clear controls or explanations.

Do not spend the session generating empty model cards, duplicate abstractions, or panels with simulated advanced outputs. Each major model task needs an actual run, retained predictions, and a comparator, or a precise documented blocker.

## 4. Immediate actions at session start

1. Inspect Git status and current instructions. Preserve unrelated local changes and ignored data.
2. Identify the current code revision, installed environment, data directory, running API, and running worker. Do not let two workers unknowingly use different state directories.
3. Read the maintained status and latest experiment reports. Record what has changed since the reviewed revision.
4. Check current official season, next deadline, event finality, and fixtures. Earlier messages mentioning GW6 are historical. The reviewed repository is discussing GW9 and GW10. Do not infer the current event from conversation history.
5. Inspect retained forecast bundles and their hashes before any training. Identify which completed events must be scored first.
6. If GW9 has finalized, score its original frozen forecasts and registered reviews before allowing those labels into a new fit. If it remains provisional, retain provisional diagnostics separately and exclude its targets from final training inputs.
7. Preserve the existing GW10 study and all original forecasts. Recheck the actual deadline rather than trusting a retained date.
8. Write a short execution checklist with task identifiers, dependencies, and ownership. Begin implementation immediately after this inventory.

The last retained status had GW9 `finished=false` and `data_checked=false`, even though ten fixtures were provisionally finished. That is a historical observation, not a claim about the live API now. Likewise, a retained GW10 deadline of 6 November 2026 at 18:30 UTC must be refreshed before use.

## 5. Concrete findings and fixes

| Priority | Finding | Source | Required response |
| :--- | :--- | :--- | :--- |
| P0 | New rolling and advancing experiments enforce scoring before target reuse, but the older collection trainer has no equivalent local guard | `models/deadline_experiments.py`, `models/rolling_experiments.py`, `models/football_catboost.py`, `learning/review.py` | Put the invariant at a shared boundary and cover every entry point |
| P0 | Binary opportunity heads use regression losses and clipped outputs | `models/football_catboost.py` | Compare proper classification heads with chronological calibration |
| P0 | Serving refit writes an empty calibration file | `models/football_catboost.py` | Preserve the honest status and implement a valid serving calibration design |
| P0 | Minutes output is clipped independently of appearance probabilities | `_predict` in `models/football_catboost.py` | Add coherent opportunity modelling and serialization tests |
| P0 | Loading assumes every `.cbm` is a regressor | `forecast_frozen` in `models/football_catboost.py` | Introduce typed head metadata and compatible loading before switching head types |
| P1 | Enriched research features and original serving heads are separate paths | `features/deadline.py` and the CatBoost experiment modules | Share feature contracts and head execution without creating another competing stack |
| P1 | Existing selection metrics do not evaluate legal policy trajectories | `evaluation/selection.py` | Add same state policy replay including hits, captaincy, substitutions, and future transfer inventory |
| P1 | The sequence planner has bounded coverage | `sequence.py` | Measure coverage and extend candidate generation, especially when more transfers are available |
| P1 | Historical collection features still use a current player universe and reconstructed information | Feature and collection code | Add explicit season identity, availability provenance, and missingness coverage |
| P1 | `rest_days` is elapsed time from the last player fixture to origin | `features/deadline.py` | Rename its meaning or add actual scheduled rest to the target fixture separately |
| P2 | Bayesian profile validation groups BPS with nonnegative counts | `models/bayesian_scoring.py` | Audit signed BPS support separately from event count validation |
| P2 | Local schedules require process uptime | Review and worker code | Add heartbeat, recovery instructions, and an optional supervised runtime configuration |
| P2 | Shared promotion conditions include policy seed requirements | `learning/promotion.py` | Separate forecast, deterministic planner, and stochastic policy evidence contracts |

The guard finding is a path coverage issue: the inspected `run_review` calls `train_collection_experiment`, which does not itself check retained benchmark scoring. It is not evidence that a live run has already leaked labels. Close the bypass and prove the shared invariant with tests.

Several earlier problems have already been addressed. Do not reopen the old forced one event horizon, old funding examples, or the repaired root starvation fixture as if they remain unfixed. Investigate current limitations with a fresh reproducer.

## 6. Define what good means before training

Maintain separate scorecards for forecasts, decisions, and execution.

### Forecast scorecard

Measure unconditional point MAE, RMSE, and bias; minutes MAE; appearance and 60 minute Brier score and log loss; calibration; interval coverage; and rank diagnostics. Report the whole captured universe and meaningful origin defined subsets separately.

### Decision scorecard

Measure realized points after hits from legal paper policies, relative to Keep, roll, and a fixed baseline policy. Include captain and vice captain, automatic substitutions, bench order, and subsequent state transitions. Track cumulative advantage, downside, transfer usage, budget feasibility, and the number of distinct event blocks.

### Execution scorecard

Distinguish the system recommendation from the action the user actually took. A missed deadline, inaccurate starting squad, and an inaccurate forecast are different errors. Do not train a model to compensate for an execution record that is unknown.

The primary prospective decision objective should be net FPL points over a declared evaluation window. Forecast loss remains important because it helps diagnose causes. It is not sufficient evidence that a transfer policy is better.

## 7. Historical data foundation

Add a reproducible season manifest and data quality report before indiscriminately expanding the model zoo.

Use official retained snapshots for current truth. Use a pinned historical archive, including the vaastav repository where suitable, for older seasons. Treat archives as source material with coverage limitations, not automatic proof that every field was available at a historical deadline.

Attempt the most recent three to six complete seasons first, depending on actual available columns and licensing. Then expand older data if it adds useful coverage. Do not hard code that every season contains all modern statistics.

Each season manifest should contain:

1. Provider, source URL, source commit or version, retrieval time, hashes, and allowed use.
2. Season identifier and scoring rules version.
3. Player, club, fixture, and event mapping versions.
4. Match completeness and field availability by season.
5. Which timestamps are observed and which are assumed.
6. Which fields are safe for a historical feature and which are labels only.
7. Duplicate, missing, corrected, postponed, and transferred player cases.
8. Explicit coverage of players who later left the league.

Use immutable raw files, normalized analytical tables, and versioned feature views. Build incrementally. An ingestion retry should reuse verified existing bytes, not create subtly different copies with the same identity.

### Canonical analytical tables

| Table | Minimum meaning |
| :--- | :--- |
| `season_rules` | Scoring and transfer rules applicable to a season |
| `player_identity` | Explicit mapping between source identities and canonical people |
| `club_identity` | Stable club mapping without assuming season numeric IDs persist |
| `player_club_interval` | Membership intervals with evidence and uncertainty |
| `fixture_revision` | Fixture schedule and status as observed at a timestamp |
| `player_fixture_outcome` | Final or provisional labels with revision and source binding |
| `source_snapshot` | Original bytes, capture time, source, and hash |
| `feature_row` | Features, origin, availability rules, and source lineage |
| `league_table_snapshot` | Table derived only from results known at that origin |
| `forecast_bundle` | Existing immutable forecast contract extended where necessary |

These are logical contracts. Reuse existing tables and envelopes if they already express the same information. Do not introduce a second state database solely to match these names.

## 8. Learn from past league tables correctly

Past tables can improve team strength estimates, but their timing matters.

Allowed examples include prior season final performance as a preseason prior for the next season; current table reconstructed from results available before the origin; recent goals and expected goals for and against; home and away strength; and promoted club priors with strong shrinkage and explicit uncertainty.

Disallowed examples include feeding a season's final position into predictions for early gameweeks of that same season, using later fixture results to reconstruct an earlier form table, or using a player's eventual club for all earlier matches.

Build rolling team strength as a chronological process. Before each fixture, update only from earlier available observations. Compare simple recency weighted strengths, a regularized team attack and defence model, and the existing Bayesian approach. Evaluate future team goals and player points separately.

Do not force a final league table to be the main target. FPL requires player minutes, role, scoring opportunities, and defensive events. A good team can rotate an expensive player out of the lineup. The model should understand that distinction without needing a motivational speech.

## 9. Player identity and scoring eras

Season element IDs are not globally stable. Preserve source season identifiers and use explicit cross season identity mappings. Names alone are inadequate. Where available, use stable provider codes and supporting metadata; retain unresolved mappings rather than silently joining similarly named players.

Track transfers using membership at the relevant time. Distinguish an unavailable player, a player outside the league, a missing archive row, and a genuine zero minute performance.

Current roster only reconstruction creates survivor bias. Include historical players who were sold, relegated, retired, or moved abroad. Record where the archive cannot support that coverage.

Scoring changes create different target distributions. Store the rule era, position at that time, and statistic availability. Older defensive contribution fields may be unmeasured rather than zero. If a historical match can be rescored under a later ruleset, mark it as reconstructed and retain the original result. If the required components do not exist, do not fabricate a modern points label.

Evaluate both a current rules comparable subset and a broader era aware model. Treat additional older data as an experiment because more rows can add systematic bias.

## 10. Improve appearance and minutes first

Extend `models/football_catboost.py` and its existing evaluation contracts. This is the first substantial implementation task.

### Binary heads

Compare the current regression based heads against `CatBoostClassifier` using a suitable binary objective for appearance, 60 minute status, and starts where reliable labels exist. Use positive class probabilities, with class order checked explicitly. A classifier's class prediction is not a probability.

Preserve support for missing start labels. The current fitting and serving paths handle missing start labels differently. Make that policy explicit and consistent. Do not infer starts from minutes without an identified approximation.

Handle one class training folds deliberately. Use an explicit, recorded prior or supported constant fallback, and report that the classifier could not be estimated. Do not crash a scheduled workflow or present a constant class as perfectly calibrated certainty.

### Typed artifacts

Add head metadata including model kind, objective, label definition, probability semantics, calibration type, feature version, and class mapping. Dispatch the loader by that metadata. Keep a compatibility reader for retained legacy artifacts or a deliberate refusal with a useful error if compatibility is impossible.

Changing only the training class is incomplete because `forecast_frozen` currently loads all `.cbm` files as regressors. Test save and load parity using actual small fitted models in the appropriate environment.

### Chronological calibration

Use earlier training data, a later but still historical calibration block, and a separate outer evaluation block. Compare uncalibrated probabilities with a conservative calibration method. Sigmoid calibration is a reasonable first candidate; isotonic needs enough data and should not be assumed superior on a few weeks.

Fit any calibrator without access to outer labels. Save its training interval, sample size, class balance, model identity, and feature contract. An empty calibration file means unavailable calibration, not successful calibration.

For a serving refit trained on additional data, do not silently reuse a calibrator fitted to a different score distribution. Choose a declared design: keep a calibration holdout, use chronological out of fold calibration with an explicit transfer assumption, or retain a labelled uncalibrated serving output until supported. Compare these designs before claiming calibrated live probabilities.

### Coherent minutes

For each fixture, enforce:

```text
0 <= P(appearance) <= 1
0 <= P(60 minutes or more) <= P(appearance)
0 <= P(start) <= P(appearance)
0 <= E(minutes) <= 90 * P(appearance)
```

Do not impose `P(60+) <= P(start)`: a substitute can play at least 60 minutes. Apply constraints per fixture, then aggregate a double gameweek. A valid two fixture event can exceed 90 expected minutes.

Consider a small mixture over no appearance, short appearance, and at least 60 minutes, with conditional duration models. Under whole minute labels and the current 90 minute convention, the corresponding expected duration bounds are:

```text
P(appearance) + 59 * P(60+) <= E(minutes)
E(minutes) <= 59 * P(appearance) + 31 * P(60+)
```

Use these bounds only when their label convention matches the data. A coherent mixture is preferable to arbitrary clipping. If a projection is used as an interim fix, retain raw values and report how often and by how much it intervenes.

### Required analysis

Break results down by substitute history, returning players, sparse history, club changes, position, known injury status, and origin likely starter groups. Retain both unweighted universe metrics and useful decision focused subsets. Compare the same official news treatment on both sides.

## 11. Improve point forecasts without losing valid negative outcomes

Retain direct signed point regression as a serious baseline. Improve its opportunity features, regularization, and temporal validation before increasing its depth.

The existing hurdle model predicts:

```text
P(points != 0) * E(points | points != 0)
```

That conditional target includes negative returns. Preserve that property. Do not replace it with `points > 0`, and do not confuse the nonzero probability with appearance probability. Disciplinary points can occur with zero recorded minutes.

For an appearance mixture, model the zero minute outcome branch honestly. A useful conceptual decomposition is:

```text
E(points) =
    P(appearance) * E(points | appearance)
    + P(no appearance) * E(points | no appearance)
```

The second term is often zero, but should not be forced to zero when the labels contain legitimate disciplinary outcomes.

Audit every downstream use of availability. Existing point means are intended to be unconditional. Multiplying them by an appearance probability again would double discount them. Store whether a mean is conditional or unconditional in the contract.

## 12. Add models in a controlled sequence

More models are useful when they supply different information or different errors. They are expensive when they repeat the same assumptions with a new logo.

| Candidate | Why it belongs | First experiment | Priority |
| :--- | :--- | :--- | :--- |
| Improved CatBoost opportunity and point bundle | Directly addresses the measured minutes problem | Current versus binary/calibrated/coherent heads on fixed folds | Immediate |
| Existing multiscale CatBoost | Strongest reported rolling point RMSE among the three tested configurations | Preserve as a fixed comparator | Immediate |
| Existing signed points hurdle | Different treatment of zero inflation | Compare its calibration and selection effects without changing old results | Immediate |
| Regularized linear model | Transparent shrinkage baseline with different variance | Ridge or Elastic Net on the same valid features | Next |
| LightGBM | Alternative tree learner with different fitting behavior | One modest signed point regression configuration on the same folds | Next |
| Hierarchical team attack and defence | Shares strength across teams and sparse observations | Future team goal comparison against a frozen simple goal baseline | Next |
| Player event component model | Football structure and coherent match simulation | Restrict initially to components actually observed | Later |
| Existing TFT | Direct multivariate future forecasting | Evaluate only once historical timing and multi lead contracts are credible | Later |
| Ranking model | May improve shortlist ordering | A separately labelled diagnostic within eligible event groups | Optional |
| Distributional or quantile tree model | Useful uncertainty and scenario inputs | Chronological interval calibration and decision sensitivity | Later |
| Reinforcement learning continuation model | Potentially values flexibility beyond a bounded search | Compare against the same numerical planner inside a validated environment | Research |

Do not make every row a required new production model in one session. The minimum useful expansion is a genuine regularized baseline and one LightGBM challenger after the shared probability fixes and evaluation harness are functioning.

Use an objective compatible with signed FPL points. Poisson and Tweedie assumptions do not apply directly to a target that can be negative. They can be suitable for specific nonnegative components if their assumptions and support fit.

Keep LightGBM, neural, Bayesian, and RL dependency changes deliberate. Existing base startup must not require every research extra. Lock exact resolved dependencies and record the runtime environment for reproducibility.

A ranker emits ordering scores, not calibrated expected points. Do not pass its arbitrary score into a numerical optimiser that expects points. Use it as a diagnostic or fit an independently validated mapping with clear semantics.

## 13. Better football features

Prioritize features with plausible future availability and an ablation question.

1. Minutes and starts over several windows, exponentially weighted opportunity, substitution patterns, and variance.
2. Expected goals and assists per exposure with strong shrinkage for sparse players.
3. Penalty and set piece roles with source, effective date, and uncertainty.
4. Position and role changes rather than a permanent season label where supported.
5. Opponent attack and defence strengths known at origin.
6. Home advantage, schedule congestion, and scheduled rest before each target fixture.
7. Club rotation, European and cup commitments where an accessible schedule supports them.
8. Returning player scenarios and competition for the same role.
9. Defensive contribution components under the applicable rules, with missingness indicators.
10. Injury or suspension evidence separated from market popularity.
11. Season stage and manager changes where timestamps and sample sizes support them.
12. Feature age and missingness, so a stale input is distinguishable from a current zero.

The current `rest_days` measures time from the last player fixture to the forecast origin. That is not the same as rest before the next match. Keep both concepts if useful, with accurate names. Future rest should use the schedule known at origin, not the fixture's eventual rearranged date.

Do not import undocumented proprietary expected points, postdeadline lineups, later injury news, or later price changes into a historical feature panel. Possessing a value today does not prove it was known then.

Evaluate ablations in feature families. Avoid a separate experiment for every arbitrary rolling window. Prefer a small fixed set of windows and shrinkage strengths with chronological validation.

## 14. Multi season and multi lead evaluation

Build a single reusable protocol shared by model families.

1. Use expanding or rolling historical origins with training strictly before evaluation.
2. Place inner model selection and calibration entirely before the outer period.
3. Group all rows from a fixture and relevant event together as required by the prediction question.
4. Purge labels whose target windows overlap a later evaluation origin.
5. Fit imputers, encoders, scaling, feature selection, early stopping, and ensemble weights only on allowed data.
6. Retain every outer prediction with its origin, source, target, configuration, and status.
7. Distinguish inspected development periods, historical audits, and untouched prospective monitoring.
8. Register primary comparisons and experiment budgets before fitting.

Player rows from the same week share weather, fixtures, team results, and news. Use event or time blocks for uncertainty and paired comparisons. Four weeks remain four weeks even if the row count looks impressive.

Do not repeatedly tune on GW9 because its misses are interesting, then report the same GW9 as independent validation. Error analysis can suggest the next experiment. Its confirmation must use other held out periods or future freezes.

Start with a small reproducible search budget. For example, at most three predefined variants per newly introduced family, with one fixed seed for deterministic configuration screening and a small stability check afterward. Record any expansion as a new experiment. Avoid hundreds of attempts selected by the best outer result.

## 15. Forecast future events honestly

Create forecasts for leads 1, 2, 3, 4, 6, and eventually 8 where the data supports them. Each lead must have an origin frozen before the target's information became available.

A multi lead experiment must not update player rolling features with real results from intervening future matches. Choose direct lead specific models, a model with lead features, or simulated recursive updates. Preserve the method in the manifest.

Retain fixture identity and the schedule version used at origin. A player event forecast is the sum over that event's known fixtures plus explicit assumptions about availability and schedule uncertainty. Blanks, doubles, postponements, and club changes need defined behavior.

Evaluate each lead separately for point accuracy, minutes, calibration, coverage, and planner decisions. Do not call an eight week baseline scenario an eight week calibrated model because its array has eight columns.

Longer horizons should reflect increasing uncertainty and weaker knowledge of future minutes. Support future return and rotation scenarios rather than assuming the next match probability stays constant for six weeks.

## 16. Ensembling

Add an ensemble only after retaining comparable chronological out of fold predictions.

Start with a small nonnegative blend or regularized stack. Compare it to a simple equal weight blend and the best development selected single model. Fit weights only on allowed development predictions, never the reported outer test targets.

Consider separate broad position or role blends only with adequate data and shrink them toward global weights. Do not fit a custom weight for every player using nine gameweeks.

Exclude a candidate if its coverage or semantics do not match. A team goals model, ranking score, conditional point mean, and unconditional point forecast are not interchangeable columns in a weighted average.

Retain component versions, feature versions, missing model policy, fitting interval, and uncertainty limitations. If a component is unavailable at runtime, fall back according to a registered rule and label the changed mixture. Do not silently renormalize into an untested policy.

Check residual diversity on allowed development periods. Two nearly identical CatBoost configurations can add less value than a modest regularized baseline. Compare decision stability as well as marginal RMSE.

## 17. Calibrated distributions and football simulation

Quantiles and scenarios are different products. Sorting three predicted quantiles prevents crossing but does not prove their coverage is correct. Independently sampling each player's quantiles does not create a calibrated joint match distribution.

For marginal forecast evaluation, add pinball loss and empirical interval coverage by lead, position, and opportunity group. Use sufficiently large time blocks and label small sample slices as uncertain. Any conformal method must respect chronology and its assumptions; it does not provide a free guarantee under football distribution shift.

For match scenarios, preserve shared team goals, clean sheets, opponent goals, minutes, assists, penalties, cards, and bonus allocation. Enforce physical consistency where components are simulated. A simulated team cannot allocate more player goals than its team total without an explicit own goal mechanism.

Bonus points require a valid ranking and tie mechanism. BPS itself should be audited as a signed score rather than automatically treated as a nonnegative event count. Verify actual provider support and current scoring rules before changing the validation contract.

The existing Bayesian player scoring gate requires components that may not all be available from free retained data. Build a clearly labelled partial component model when useful, with explicit residual point treatment, instead of fabricating complete observations. Keep the full scoring qualification gate intact until its actual requirements are met.

Before using scenarios for risk sensitive decisions, compare team goal means, score frequencies, clean sheets, player tail behavior, and scenario dependence against held out observations. A more complicated simulator can still be a worse simulator.

## 18. Evaluate legal decisions from the same starting state

Extend the existing ranking work into a paper policy evaluation system.

Freeze one canonical starting squad, purchase prices, selling prices, bank, free transfer inventory, chip state, committed hits, and deadline state for each comparison. Let every policy receive the same origin available inputs. Validate every resulting action independently of the solver.

Compare at least:

1. Keep the squad, optimizing only permitted lineup, captaincy, and bench choices under a fixed forecast policy.
2. Roll the transfer when legal.
3. The current baseline forecast with the current numerical planner.
4. The selected CatBoost forecast with that same planner.
5. A development selected ensemble, only if its inputs and weights are frozen.
6. The improved longer horizon planner under the same forecast inputs.

This separates model benefit from planner benefit. Do not improve both sides of a comparison and attribute all the gain to a new model.

Score points after incremental and already committed hits according to the declared state. Apply captain fallback, automatic substitution, bench order, formation, and chips under the season rules. A captain's expected contribution and vice fallback can depend on joint appearance outcomes. Do not estimate fallback by multiplying independent marginal probabilities without labelling that assumption.

Retain the entire state trajectory for multi event comparisons. A transfer this week changes next week's bank, inventory, and options. Comparing unrelated hindsight optimal squads each week is not a valid deployable transfer policy.

Report both a fixed starting state experiment and a sequential policy rollout where available. Historical prices and finances with uncertain timing need explicit limitations. Missing personal state should produce an unavailable personal comparison, not a synthetic bank value disguised as the user's account.

## 19. Improve long sighted transfer planning

Use a receding horizon approach: plan ahead, execute only the current manual decision, and recompute after new information. Future transfer sequences are contingent plans rather than promises.

The state must include squad membership, purchase basis, current sale value, bank in integer tenths, free transfer inventory, chips and windows, committed actions, and the temporary versus persistent squad distinction during Free Hit.

The existing search has improved root coverage, but ordinary transfer generation remains bounded and commonly limited to two replacements. Test states with three or more available free transfers, larger restructures, and useful funding moves. Do not describe bounded search as a globally optimal solution without an appropriate certificate.

Implement these improvements in stages:

1. Add search diagnostics: candidate counts, pruned branches, seeded roots, coverage bounds, runtime, and incumbent source.
2. Compare current results against exact small state oracles and a larger search budget on representative states.
3. Add candidate diversity by position, price band, minutes profile, fixture sequence, and funding role.
4. Retain Keep and roll as explicit candidates at every relevant state.
5. Extend feasible ordinary multi transfer generation using constrained optimisation or broader beam search where inventory supports it.
6. Distinguish search truncation from a genuine no beneficial move result.
7. Value future transfer flexibility through the continuation objective rather than a universal arbitrary bonus.
8. Show immediate gain, horizon gain, hit cost, and sensitivity to uncertain minutes separately.

Begin with expected points. Add a risk penalty or CVaR option only when scenario quality is adequate, using a registered risk preference. Avoid unsupported precision in statements such as a claimed probability of reaching a particular rank.

Price changes can affect future feasibility, but do not predict exact prices from crowd sentiment without evidence. Use explicit price scenarios if useful and report whether the recommendation is feasible under each one.

Chip comparisons need a terminal value or opportunity cost for consuming a scarce chip. Otherwise a short horizon can spend every valuable resource simply because the future is outside its field of view.

## 20. Reinforcement learning research

The user wants a system that improves over time. Weekly supervised refitting, calibrated model selection, and decision evaluation already provide useful learning. RL is a separate research candidate for valuing sequential choices.

Do not train an unconstrained policy on a few observed manager gameweeks and expect it to discover expert FPL strategy. There is too little independent real experience, and a policy can exploit simulator mistakes.

Use the existing environment and replay infrastructure. First verify transitions against the rules engine for buying, selling, profit rounding, hits, free transfer carry, wildcard, Free Hit, chip windows, and deadline changes. The policy should choose only legal actions or receive an exact legal action mask. The final recommendation still passes independent validation.

A useful initial RL target is continuation value: estimate the future value of squad structure, budget, and transfer flexibility, while the numerical planner selects concrete legal actions. Compare this with simple terminal value heuristics under the same simulator.

For every policy experiment:

1. Pin the environment, action generator, reward, training data, simulator parameters, and seed.
2. Reward net points with correct hit accounting and no accidental reward from popularity, transfer activity, or unrealized gains.
3. Train only on allowed historical periods and simulator draws.
4. Evaluate on separate seasons or event blocks and independently generated scenarios.
5. Compare with the current planner using paired common scenarios where appropriate.
6. Include several training seeds for stochastic stability without pretending they create new real seasons.
7. Stress test alternative scoring rates, rotation, injuries, and price scenarios to expose simulator exploitation.
8. Report action legality, runtime, downside, and disagreement with the planner.

The earlier short PPO comparison is not evidence of a useful live edge. A larger episode count is not sufficient if every episode comes from the same biased simulator. Keep policy training below the priority of real data, minutes, and legal decision evaluation.

## 21. Continuous weekly learning workflow

Create one coordinator around existing capabilities. Avoid parallel independent review systems with incompatible definitions of finality.

The intended sequence is:

```text
Capture source revision
Check official finalization
Score retained frozen forecasts and decisions
Publish outcome and evaluation revisions
Run data quality checks
Create eligible training snapshot
Refit registered candidate methods
Evaluate and produce challenger reports
Prepare current decisions using available qualified methods
Freeze forecasts and paper decisions before the next deadline
```

Each stage needs an idempotency key based on relevant source revisions, method versions, and event identity. Persist completion only after its outputs are durable. Use atomic publication, recoverable leases, and bounded retries. A crash during training must not produce a valid looking half artifact.

Centralize the rule that a newly completed event's frozen bundles are scored before its labels become eligible for refitting. Apply it to CLI jobs, scheduled reviews, rolling research, advancing experiments, and the older collection trainer. Registered selection reviews should remain recoverably publishable from scored outcomes.

Track `pending_finalization`, `ready_to_score`, `scored`, `quality_blocked`, `training`, `evaluated`, `shadow_ready`, and `failed` as meaningful states, reusing existing representations where possible. Show a useful failure reason and recovery instruction.

Do not force a retrain every time a worker polls the same unchanged data. The job identity should make duplicate work unnecessary. Outcome corrections should create a new revision and trigger the appropriate downstream invalidation without rewriting earlier forecasts.

## 22. Runtime durability

The current worker is local. If the laptop is off, the job does not run. Make that visible in the product and operator docs.

Add a heartbeat, last successful finality check, pending jobs, last scoring time, last successful model fit, and next expected action. Detect a stale heartbeat rather than displaying a schedule as if it implies guaranteed execution.

Provide an optional supervised local runtime configuration suitable for the user's operating system, plus restart and log instructions. Do not silently install background services. A documented configuration and verification command are useful implementation deliverables.

Keep external hosted scheduling or paid infrastructure outside the minimum scope. The user should be able to operate the learning loop locally with free data and a clearly stated uptime requirement.

## 23. Learning from misses and detecting drift

Create a weekly error report that answers why the system missed, not just which player scored the most.

Classify misses into appearance, duration, role, attacking opportunity, finishing variance, clean sheet, defensive contribution, bonus, data freshness, fixture change, or execution/state error. Allow multiple causes and retain uncertainty in the diagnosis.

Monitor:

1. Appearance and 60 minute calibration over completed time blocks.
2. Mean point bias and minutes bias by role and position.
3. Missing feature rates and input age.
4. New and transferred player performance.
5. Residuals for likely starters versus the many zero minute players.
6. Stability of shortlisted players and transfer recommendations across plausible model variants.
7. Performance by forecast lead and schedule density.
8. Data revision frequency and whether corrections alter conclusions.

Use development evidence to choose recency weighting, training window, and shrinkage. Compare an expanding historical model with a recency weighted model. Retain prior seasons as a stabilizer rather than erasing them after a difficult weekend.

Do not create a special rule to explain one missed haul. A high scoring defender can be an ordinary tail event. A repeated opportunity bias is a model issue. Preserve that distinction.

## 24. Reddit, X, experts, and crowd consensus

Treat social information as a separate evidence layer with measurable incremental value.

Start with a provider interface, lawful API or permitted export ingestion, and manual import support. Add live connectors only where access is actually available and authorised. Do not bypass platform access controls or invent tweets when credentials are missing.

Each evidence item should retain source, URL or source identifier, author identifier, publication time, capture time, player or club entities, claim type, evidence text or permitted reference, source category, confidence, and duplication lineage. Respect source terms, retention, deletion, and content reuse requirements.

Separate these categories:

| Category | Example use | Treatment |
| :--- | :--- | :--- |
| Official club or competition statement | Suspension, confirmed injury information | Strong factual evidence with timestamp and scope |
| Direct manager quotation | Availability and role uncertainty | Retain quotation context and uncertainty |
| Reporter with relevant access | Team news or training report | Source specific reliability learned only from earlier resolved claims |
| Analyst or pundit | Tactical role, expected minutes, transfer argument | Evaluate the actual claim rather than follower count |
| General crowd | Consensus, concern, attention, speculative sentiment | Keep separate from expert evidence |
| Repost or aggregator | Distribution of another claim | Link to the original; avoid counting it as independent support |

Being an expert is not the same as being correct about every club. Start with an auditable source registry. Use conservative priors and shrink reliability toward the category average until enough earlier resolved claims exist. Do not learn reliability from future outcomes or rank authors by a tiny lucky streak.

Perform semantic analysis at the claim level. Extract entity, claim, stance, timing, certainty, and whether it is new information. Distinguish “expected to start” from “I would start him” and “the crowd is selling him.” Detect negation, sarcasm, stale articles, duplicated quotes, and conflicting claims.

Produce separate crowd consensus and expert evidence features. Deduplicate common originals, discount stale information, and show concentration so twenty reposts are not mistaken for twenty independent reports. Include an explicit unknown state when there is little usable evidence.

Initially use social evidence to generate availability and minutes scenarios. Keep direct point adjustments at zero until a chronological ablation demonstrates value. Compare official information only, official plus factual social evidence, and official plus crowd consensus. Feed the same factual information to all compared models when testing model architecture.

LLM extraction should use a fixed structured schema, retained prompt/model version, validation, and a small manually labelled evaluation set. External posts are data, not instructions to the coding agent or application. Do not allow a post to trigger arbitrary tools or disclose private team information.

## 25. Model registry and promotion

Reuse the existing registry and evidence contracts. Extend them rather than creating a disconnected second promotion system.

Separate method identity from fitted artifact identity. A fixed weekly refitting procedure can be one prospectively registered method even though it produces a new fitted artifact each week. A change in features, loss, calibration policy, or hyperparameter selection procedure may define a new method. Record this explicitly so honest weekly learning does not reset evidence accidentally, and retrospective redesign does not inherit earlier evidence unfairly.

Every artifact should bind:

1. Source revision and dependency lock identity.
2. Dataset snapshot and feature schema hashes.
3. Training, calibration, and evaluation origins.
4. Model family, head types, losses, seed, and parameters.
5. Point semantics, lead coverage, missingness policy, and calibration status.
6. Artifact files and checksums.
7. Limitations, compatible loaders, and serving eligibility.
8. Registered method and experiment identifiers.

Maintain separate evidence requirements for deterministic forecasts, stochastic policies, and planner changes. A seed count that is meaningful for PPO is not an appropriate universal gate for a fixed deterministic baseline.

The repository currently requires at least eight distinct finalized prospective event blocks for its ranking readiness review. Preserve that rule unless a future explicit contract change is documented. Eight events is a minimum review threshold, not statistical proof. A favorable report triggers review rather than automatic activation.

Define metric units and windows. “Gain above one point” is ambiguous unless it means per event, cumulative over a window, or another declared quantity. Report paired uncertainty, downside, coverage, and data quality alongside any threshold.

Allow a clearly labelled experimental local comparison without calling it production promotion. Research success and user facing default activation are different actions.

## 26. App and API improvements that serve the modelling work

Keep interface changes small and practical.

Expose the active forecast method, fitted artifact, data origin, supported leads, calibration state, and fallback reason. Distinguish trained, evaluated, shadow, and active states.

For each recommendation, show Keep or roll comparison, immediate expected gain, declared horizon gain, hit cost, current legality, search limitations, and the assumptions that most affect the choice. Avoid point estimates with misleading decimal precision when model disagreement is large.

Make it possible to inspect forecast components and a few sensible alternatives. Show what new information would change the decision, such as a player being ruled out or a price scenario making a move infeasible.

Preserve unknown financial state. Public team import represents deadline data and can miss recent actions. Reconcile current players, purchase prices, selling prices, bank, free transfers, chips, and committed hits before personalized transfer advice. Continue useful nonfinancial analysis when that information is missing.

Keep model training and experiments in the recoverable worker. API requests should submit or inspect jobs rather than block on a long fit. Generate API bindings through the existing workflow when contracts change.

## 27. Reliability, security, and dependency work

Check the real environment and installed dependency graph. Do not copy an old vulnerability count into the new status as if it were current.

Run appropriate dependency audits and distinguish runtime exposure from development tooling. Fix relevant findings without replacing the application stack. Retain optional dependency isolation so a missing TFT or RL package does not break baseline startup.

Treat model artifacts as trusted local files with validated manifests. Do not introduce loading of arbitrary uploaded pickle files. Validate provider IDs, avoid arbitrary server URL fetches, and keep credentials and private account data out of logs and Git.

Research artifacts can be large. Keep raw data, binaries, private manager state, screenshots, and full generated datasets in ignored storage. Commit source, contracts, synthetic fixtures, and concise reproducible public evidence summaries where appropriate.

Distinguish UTC timestamps from user display time. Deadline logic must use timezone aware instants, not local string comparisons. Test daylight saving transitions where relevant.

## 28. Task backlog with acceptance criteria

Execute the core tasks in dependency order. Parallelize independent work only after agreeing shared contracts.

| ID | Task | Dependencies | Acceptance |
| :--- | :--- | :--- | :--- |
| M01 | Reconcile current checkout, official event status, and retained freezes | None | Current inventory and hashes recorded; no overwritten forecasts |
| M02 | Shared scoring before training eligibility guard | M01 | All training entry paths reject unscored newly final labels; corrected revisions handled explicitly |
| M03 | Typed CatBoost binary heads and compatible artifact loading | M01 | Small actual fit, save/load parity, class semantics, missing/one class behavior tested |
| M04 | Chronological calibration and coherent minutes | M03 | Separate calibration evidence, no impossible fixture outputs, clear serving status |
| M05 | Registered rolling comparison of old and new opportunity bundle | M02, M04 | Actual retained outer predictions and subgroup report; old freezes unchanged |
| M06 | Multi season source manifest and normalized ingestion | M01 | At least one prior season ingested end to end, quality report, reproducible rerun |
| M07 | Historical identities, membership, rule eras, and league table prefixes | M06 | Leakage and mapping tests; known versus assumed availability explicit |
| M08 | Regularized linear challenger | M05 or shared protocol | Actual same fold comparison and retained predictions |
| M09 | LightGBM challenger as an optional research dependency | M05 or shared protocol | Actual same fold comparison, startup isolation, locked dependencies |
| M10 | Legal paper policy replay | M01, existing rules | Same starting state, net points, captain/substitution/hit accounting, trajectories retained |
| M11 | Planner coverage and multi transfer extension | M10 | Exact small case comparisons, representative three or more transfer cases, search diagnostics |
| M12 | Direct multi lead forecasts | M05, M07 | Leads evaluated from fixed origins, no intermediate future observation leakage |
| M13 | Development fitted ensemble | M08, M09 | Out of fold weight fitting, fixed outer evaluation, clear fallback semantics |
| M14 | Weekly coordinator and worker health | M02 | Idempotent recovery tests, heartbeat, actual one event cycle exercised |
| M15 | Weekly error and drift report | M05, M10 | Opportunity, points, decisions, and execution separated |
| M16 | Bayesian component availability audit | M06 | Honest component coverage, signed BPS audit, simple goal comparator |
| M17 | Social claim ingestion and semantic schema | M01 | Manual or permitted input path, timestamps, deduplication, expert/crowd separation |
| M18 | Social extraction evaluation and forecast ablation | M17, M05 | Labelled extraction sample, prospective safe features, no automatic point uplift |
| M19 | RL continuation experiment | M10, M11, credible simulator | Legal transitions, held out evaluation, multiple seeds, planner comparator |
| M20 | API controls, generated bindings, and necessary interface explanations | Relevant completed tasks | Real backend outputs shown accurately; no invented advanced states |
| M21 | Consolidated verification and next status | All integrated tasks | Checks reflect actual runs; report gains, regressions, blockers, next action |

Do not block M03 through M05 on completing every historical archive. Do not block M06 through M07 on the new head implementation. Do not start M19 at the expense of the earlier tasks.

## 29. Parallel agent execution

The following is explicit authorisation for the next Codex session to use parallel agents where its runtime supports them. Use separate worktrees or isolated checkouts, with one integration owner. Do not have several agents edit the same checkout simultaneously.

Use up to four implementation agents initially:

1. Model agent: M03, M04, M05; owns the existing CatBoost head implementation and its focused tests.
2. Data agent: M06, M07; owns historical ingestion, identity, rule era, and availability contracts.
3. Decision agent: M10, then M11; owns legal policy comparison and search coverage tests.
4. Runtime agent: M02, M14; owns the shared training eligibility boundary and worker recovery.

The lead agent owns shared schemas, dependency locks, integration, broad checks, and final reports. Agree on boundaries before editing. Agents should return changed paths, actual checks, artifacts, unresolved issues, and integration notes. Read each diff before integrating it.

After the first wave integrates, assign M08 and M09 to the shared experiment runner, M12 to supported future forecasts, and M17 to the social schema. Avoid implementing competing versions of calibration or registry logic in separate branches.

If agent tools are unavailable, execute sequentially and state that limitation. Do not simulate agent activity in the report. Respect existing uncommitted user changes and do not use destructive resets to make a worktree convenient.

## 30. Tests that matter

Add tests for real invariants and failure modes. Avoid tests that merely repeat implementation constants.

### Data and timing

1. A later result cannot change an earlier feature row or league table snapshot.
2. Current club membership does not rewrite earlier seasons or earlier fixtures.
3. A delayed source publication remains unavailable before its actual known time.
4. Missing statistics differ from measured zero, and provisional outcomes stay outside final training inputs.
5. A player in a double has both fixture contributions; a blank is not a missing observation.
6. Final table position cannot enter earlier predictions for that same season.

### Models and calibration

1. Classifier save/load parity and positive class dispatch are correct.
2. Calibration cannot access outer targets and binds to the intended model method.
3. Missing and one class head labels follow the declared fallback policy.
4. Opportunity probabilities and per fixture expected minutes are coherent.
5. Negative point labels and zero minute disciplinary returns survive processing.
6. Unconditional point forecasts are not multiplied by availability again.
7. Multi lead features do not consume actual intervening outcomes.
8. Legacy artifacts load correctly or fail explicitly without changing old bytes.

### Decisions and runtime

1. Identical frozen inputs produce the same canonical decision under the declared deterministic policy.
2. Independent validation catches an infeasible budget, illegal formation, invalid club count, or incompatible chip.
3. Purchase, market, and selling prices remain distinct, with exact integer arithmetic.
4. Keep, roll, funding transfers, and three or more free transfer cases are represented correctly.
5. Automatic substitutions, captain fallback, Free Hit restoration, and committed hits are scored correctly.
6. A cancelled job resumes without publishing half an artifact or duplicating outcomes.
7. Every training entry point respects scoring before target reuse.
8. Worker downtime is visible; restarting with the correct data directory resumes pending work.
9. Later outcome revisions create a new score revision and do not alter the original forecast.
10. One canonical registered comparison per event prevents hindsight selection.

Use small synthetic fixtures for ordinary CI and actual retained artifacts for separate research runs. Heavy neural and RL extras should have explicit optional checks. A skipped optional check is not a passed training run.

## 31. Commands and verification

Use the repository's current scripts and read their help before passing research flags. Do not invent a command because a document would look more complete with one.

The reviewed repository supports these ordinary setup commands:

```sh
(cd backend && uv sync --locked)
(cd apps/web && npm ci)
bash scripts/dev.sh
```

Run relevant focused tests during development. After integration, use the maintained check scripts and the following commands as applicable:

```sh
cd backend
uv run pytest
uv run pytest ../tests
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

```sh
cd apps/web
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

```sh
python3 scripts/check_docs.py
python3 scripts/smoke.py
```

Browser and smoke checks need the expected API and worker. Use offline fixtures in normal CI. Use the optional live provider smoke only when appropriate and preserve private corrections. Confirm script options against `scripts/README.md` and current code.

If model APIs change, regenerate the existing API schema and TypeScript bindings with the maintained generation workflow. Verify the diff rather than editing generated bindings by hand.

Do not repeatedly rerun a full suite without a new change or unresolved issue. Do run actual model experiments after code checks: a passing test suite does not prove forecast improvement.

## 32. Required experiment and delivery artifacts

For every substantive experiment retain:

1. Registered protocol and hypothesis before fitting.
2. Code revision, dependency lock, source and dataset fingerprints.
3. Feature and target definitions with chronological partitions.
4. Actual trained artifact or precise unavailability reason.
5. Frozen outer predictions, including missing coverage rather than silently dropping it.
6. Forecast metrics, calibration, subgroup counts, and decision metrics where applicable.
7. Runtime, resource use, and reproducible operator command.
8. Development interpretation and limitations.

At session completion update the maintained status and concise progress report. Add a new experiment folder for new measured results; never rewrite an older immutable report to make the latest model look better.

The final report must state what changed, what actually ran, what improved, what regressed, what remains experimental, and the next concrete action. If no candidate improved the declared objective, say so and retain the comparator. A negative result is useful evidence.

## 33. Session completion targets

The minimum substantive session should complete M01 through M05, establish at least one prior season ingestion path with timing tests, and make progress on legal paper policy comparison. These tasks directly address the current bottleneck.

An ambitious session should also execute both new simple model families, produce a same state decision comparison, improve search coverage where a real gap is demonstrated, and exercise the coordinated scoring/refit workflow. Social ingestion and RL research can follow once those foundations are integrated.

Do not spend the final context window starting a large experiment that cannot publish a trustworthy result. Leave checkpoints, exact resume commands, current task IDs, and a runnable application. Use remaining capacity for independent verification, failure recovery, and resolving regressions.

The following are not completion evidence on their own: more models listed in a menu, a new model name in configuration, a training function never run, a chart populated with synthetic data, or an unexplained increase in backtest score after repeated tuning.

## 34. Master prompt to give Codex

```text
Continue implementing this existing FPL project using the attached plan. Read the
current AGENTS.md, START_HERE, BUILD_STATUS, ROADMAP, maintained specs, and latest
experiment reports first. Treat the reviewed revision in this file as an audit
baseline and adapt to newer changes. Preserve unrelated local work, private state,
retained forecasts, registered studies, and immutable experiment evidence.

My primary goal is stronger models and better legal transfer strategy across the
remaining season. Use most of the session for data, forecasting, evaluation,
planning, and weekly learning. Make only the interface changes needed to expose
real working functionality. Implement the work and run actual experiments rather
than returning another proposal.

I explicitly authorise parallel agent work where available. Use separate
worktrees with one integration owner. Start with model, historical data, decision
evaluation, and runtime agents as described in section 29. Agree shared contracts
before editing. The lead owns integration, lockfiles, shared schemas, final
verification, and the consolidated report. If parallel agents are unavailable,
work sequentially and say so.

Begin with M01: identify the current revision, environment, data directory,
worker, official event finality, next deadline, and retained forecast hashes.
Score newly finalized frozen bundles before their labels become training inputs.
Preserve the existing GW9/GW10 records if present. Never backdate a forecast or
change an old registered comparison to include a later candidate.

Implement M02 through M05 first. Centralize scoring before label reuse across
all training paths, including the older collection trainer and scheduled review.
Improve the existing CatBoost opportunity heads using proper binary losses,
explicit probability semantics, chronological calibration, and coherent minutes.
Implement typed head serialization and loading, legacy handling, one class and
missing label behavior. Do not build a competing probability stack. Retain
negative point outcomes and do not apply availability twice to an unconditional
point forecast. Execute the registered comparison and retain actual predictions.

In parallel, build the multi season data foundation using pinned source manifests,
explicit player and club identity mappings, membership intervals, rule eras,
missingness coverage, and origin availability. Ingest at least one prior season
end to end before expanding. Build historical team strength and league table
features only from information available at the origin. Final season tables can
be priors for the next season, never early features for the same season.

Extend ranking diagnostics into legal same state paper policy evaluation. Compare
Keep, roll, the baseline forecast/planner, and the new model using identical
starting finances, transfer inventory, chips, and origin available information.
Include hits, captain/vice, bench order, automatic substitutions, and subsequent
state transitions. Separate model benefit from planner benefit. Preserve unknown
personal financial state and complete useful independent work if it is missing.

After the shared evaluation path works, fit a regularized linear baseline and
one modest LightGBM challenger using the same folds and feature contracts. Keep
research dependencies optional. Expand only when a distinct hypothesis or error
pattern justifies it. Learn ensemble weights from allowed development predictions
and never select them on the outer results being reported.

Improve long horizon planning through supported direct multi lead forecasts,
search diagnostics, exact small case comparisons, and broader feasible transfer
generation when three or more free transfers are available. Preserve Keep and
roll. Report bounded search honestly. Treat future plans as contingent and value
transfer/chip flexibility explicitly. Do not pretend independent player quantiles
are a calibrated joint simulator.

Implement a recoverable weekly coordinator around existing finality, scoring,
training, evaluation, and freeze capabilities. Add heartbeat and useful recovery
status. Exercise a real eligible cycle where retained data permits it. Do not
retrain unchanged inputs on every poll or publish partial artifacts after a crash.

For social intelligence, implement a permitted ingestion or manual import path
with claim timestamps, entity extraction, deduplication, source categories,
expert versus crowd separation, and conservative source reliability. Initially
produce evidence and availability scenarios. Keep direct point adjustment at zero
until a chronological ablation demonstrates incremental value. Do not invent
posts or bypass platform access controls when credentials are absent.

Keep RL as a challenger. First validate legal transitions and the simulator,
then compare a continuation value approach or existing policy against the same
numerical planner using held out periods, multiple training seeds, and simulator
stress tests. Supervised weekly learning should work regardless of RL progress.

Run focused meaningful tests during development and the relevant consolidated
checks after integration. Run actual training and evaluation jobs where the
environment supports them. Distinguish code checks, repository reported results,
new local experiments, and unavailable optional checks. Do not claim a complete
green CI run when the run was cancelled.

Keep the app runnable and update the maintained status, progress report, operator
commands, and new experiment evidence. The final response must give changed
behavior, real results and counts, limitations, current champions, and the next
concrete step. Do not automatically promote models, submit transfers or chips,
push commits, deploy publicly, purchase data, or add account integrations.

Continue autonomously through the dependency ordered tasks while useful work
remains. Do not stop after planning or documentation. If a task is blocked, record
the specific missing input and continue independent tasks. Before context runs
out, leave exact checkpoints and resume instructions rather than starting an
unfinishable experiment.
```

## 35. Reusable weekly operating prompt

```text
Run the weekly FPL learning and decision cycle on the current code and retained
data. Verify official finality and source revisions. Score original frozen
forecasts and paper decisions before using newly finalized targets in training.
Preserve outcome revisions and original forecasts. Produce opportunity, points,
decision, and execution error diagnostics. Refit only registered eligible methods,
evaluate them chronologically, and retain actual artifacts without automatic
promotion. Reconcile current squad and financial state where available. Compare
Keep, roll, and legal transfers over supported horizons, with captain/vice, bench,
hit costs, flexibility, and uncertain minutes scenarios. Refresh the real deadline
and freeze forecasts and paper decisions before it. Report what actually ran,
what changed, what remains unknown, worker health, and the next action. Transfers
and chips remain manual.
```

## 36. Source references and boundaries

### Repository evidence

Use pinned files to reproduce this review, then inspect the current checkout for implementation:

1. [Reviewed commit](https://github.com/Sambhav255/fpl-agent/commit/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59)
2. [Build status](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/docs/BUILD_STATUS.md)
3. [Roadmap](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/docs/ROADMAP.md)
4. [Decision quality experiment](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/docs/experiments/2026-11-03-decision-quality/README.md)
5. [Post event experiment](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/docs/experiments/2026-11-03-gw9-post-event/README.md)
6. [CatBoost implementation](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/backend/src/fpl_app/models/football_catboost.py)
7. [Rolling experiments](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/backend/src/fpl_app/models/rolling_experiments.py)
8. [Enriched features](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/backend/src/fpl_app/features/deadline.py)
9. [Selection evaluation](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/backend/src/fpl_app/evaluation/selection.py)
10. [Scheduled review](https://github.com/Sambhav255/fpl-agent/blob/0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59/backend/src/fpl_app/learning/review.py)
11. [Reviewed Actions run](https://github.com/Sambhav255/fpl-agent/actions/runs/41614248293)

### Primary technical references

1. [Official FPL rules](https://fantasy.premierleague.com/help/rules): authoritative rules entry point. The page did not expose readable rule text to this review, so verify the actual current rule content before changing season logic.
2. [Official bootstrap endpoint](https://fantasy.premierleague.com/api/bootstrap-static/): current event and player metadata, subject to actual retrieval and retained snapshots.
3. [CatBoost binary objectives](https://catboost.ai/docs/en/concepts/loss-functions-classification): implementation reference for classification losses.
4. [CatBoost probability prediction](https://catboost.ai/docs/en/concepts/python-reference_catboostclassifier_predict_proba): reference for explicit class probability output.
5. [Scikit learn calibration](https://scikit-learn.org/stable/modules/calibration.html): reference for separating calibration from model fitting and evaluation.
6. [Scikit learn chronological splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html): useful building block, not a replacement for football specific grouping and target window purging.
7. [LightGBM parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html): objective and fitting reference. Use the installed locked version's supported behavior.
8. [Scikit learn linear models](https://scikit-learn.org/stable/modules/linear_model.html): regularized baseline reference.

### External FPL projects

The vaastav archive is a relevant historical source candidate. AIrsenal is a relevant reference for separating football prediction and FPL optimization. Verify current code, source versions, licenses, and compatibility before copying implementation or importing data.

1. [vaastav historical archive](https://github.com/vaastav/Fantasy-Premier-League)
2. [AIrsenal](https://github.com/alan-turing-institute/AIrsenal)

The following earlier user supplied projects remain optional discovery candidates. They have not received a complete current code audit as part of this handoff. Evaluate concrete components and licenses if they address an unresolved task; do not defer core model work to a broad repository tour.

1. [Prasann62 fpl analizer](https://github.com/Prasann62/fpl-analizer)
2. [niciac FantasyTool](https://github.com/niciac/FantasyTool)
3. [FPL Core Insights](https://github.com/olbauday/FPL-Core-Insights)
4. [Premier League insights](https://github.com/javaidb/premier-league-insights)
5. [Java topic listing](https://github.com/topics/fantasy-premier-league?l=java)

This plan's main conclusion is operational: improve the existing opportunity model, broaden trustworthy historical evidence, and test legal decisions from the same state. Additional model families should earn their place through that process.
