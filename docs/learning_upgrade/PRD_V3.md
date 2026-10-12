# FPL PRD v3: learning and season strategy

Owner: Sambhav. Date: 12 October 2026. Basis: commit `840c1185d005270717c7453fb278dc30a03c05f3` and the preceding intelligence upgrade.

## Product outcome

Before each deadline, provide a legal immediate decision, an eight event conditional strategy, captain/vice/bench choices, future chip options and an explained comparison with simpler approaches. After finalized results, assess forecast errors and decision outcomes, update suitable models, and retain or replace the current champion using recorded evidence.

The system should improve its estimates and decisions over time. Improvement is a measured result, not something guaranteed by retraining or adding a neural network.

## Architecture decision

Retain three football forecasting families: CatBoost, Bayesian events and TFT. Introduce a fourth, separate strategy component: a reinforcement learning policy or value function. Forecasts describe football outcomes; the policy chooses actions under finances, transfer inventory and future opportunities. The rules engine validates everything.

The baseline and numerical planner remain usable while advanced components mature. The active champion can be a simple model, an eligible individual advanced model or a validated ensemble. There is no requirement to blend a weak family into the deployed result.

## Scope

| Horizon | Decision | Product output |
| --- | --- | --- |
| Next deadline | Execute manually now | Roll/transfer/chip, spending, hits, XI, captain, vice and bench |
| Four, six and eight events | Receding horizon strategy | Alternative first actions, expected net value, finances, flexibility and triggers |
| Remaining season | Macro opportunities | Chip window calendar, fixture turns and contingency scenarios |
| Completed event | Learn and assess | Frozen prediction scorecard, realized net points, counterfactual immediate actions and update decision |

Only the immediate action is concrete. Later transfers are proposals to revisit. Unscheduled fixtures and unavailable future probabilities remain explicit uncertainty.

## Learning requirements

L01. Freeze a decision journal before each forecast origin and deadline. Record source collection, model artifact and policy artifact checksums, team state version, declared player universe, supported horizon, forecast components, feasible candidate set, chosen/rejected actions, finances and timestamps.

L02. Maintain separate `recommended`, `user_selected`, `confirmed_executed` and `execution_unknown` actions. A recommendation is not proof that the user submitted it. Outcome learning uses the actual confirmed squad or a clearly labelled paper portfolio.

L03. Ingest finalized player fixture results and event metadata, retain revisions, and join them to the frozen journal. Pending and preliminary rows cannot become finalized training targets. Later corrections create a new evaluation revision, not silently changed past reports.

L04. Score all covered player forecasts, including zeros actually reported by the provider. Distinguish a blank fixture schedule, actual nonappearance, missing history and incomplete capture.

L05. Recompute dynamic chronological folds after each finalized event. Perform evaluation first, then a separately identified current serving refit using all finalized data available at its actual origin. Advance folds as the season advances.

L06. Update calibration or football strength estimates only with labels actually available at the update time. Preserve old artifacts. No mutable model can change a queued or published prediction.

L07. Publish a concise learning report: errors, bias, minutes/appearance calibration, current model comparison, strategy result after hits, data coverage, drift, and reasons to retain or change the champion.

L08. Automate local collection, scoring and challenger training through idempotent worker jobs. A missed capture is a missing prospective observation; never backdate it. This application schedule is separate from a ChatGPT reminder or automation.

L09. Use the whole covered football universe for supervised learning where practical. Avoid building the training universe by selecting the best scorers at the end of the season.

L10. Training rights for social derived signals must be explicit. Social text or embeddings do not automatically become permissible training inputs.

## Season planning requirements

P01. Replay lets a policy plan across its actual supported horizon, executes the first event only, advances prices and state, reveals newly available information, and replans. Never expose later snapshots or outcomes to the current policy.

P02. Finance is an explicit transition model: acquisition basis, market and selling values, bank, free transfers, committed and additional hits, temporary Free Hit ownership, permanent squad and chip inventory. Unknown inputs block the affected financial claim.

P03. Provide a candidate set with roll, legal singles, funding pairs, selected larger bundles, injury contingencies and chip alternatives. A learned policy cannot select an action missing from the candidate set. Candidate recall is a release metric.

P04. Add a genuine sequence optimiser with transfers and ownership changing by event. Incorporate allowed chip dates and legal windows. Extend the independent validator before enabling future chips.

P05. Value retained free transfers, bank and squad flexibility using a tested continuation function. Avoid rewarding them twice when the forecast horizon already captures the same benefit.

P06. Evaluate joint scenarios for availability, minutes, captain fallback, autosubs, clean sheets, attacking outcomes and fixture calendar changes. Compare all actions on shared football scenarios. If scenario probabilities are unavailable, report separate scenario results rather than inventing a weighted mean.

P07. Detailed plans default to the strongest supported horizon. Unsupported leads remain unavailable. A one event CatBoost artifact cannot be called an eight event forecast by repeating its numbers.

P08. Compare decisions over four, six and eight events and report sensitivity to terminal assumptions, injury scenarios and affordability changes. Wide action disagreement is a useful caution signal.

P09. Rank and mini league modes require an explicit rival model and objective. Default maximises points after hits. Ownership alone does not make a player a good differential.

## Reinforcement learning requirements

R01. Implement a Gymnasium FPL environment backed by the same domain transitions and scoring rules as replay. Exact mechanics must be validated before training.

R02. Start with a restricted action slate of legal current event plans and a finite season observation. The RL policy chooses a candidate; the optimiser provides legal transfers and lineup proposals. Include a legal roll action.

R03. Reward realized or simulated squad points after hits exactly once. Use no future actual points as current observation. Simulation estimates, historical research and live results have separate evidence labels.

R04. Train a real optional MaskablePPO challenger, save/reload it, and compare it with current planner, greedy, roll/keep and a simpler fitted value policy on the same episodes and football outcomes.

R05. Use at least five training seeds for a substantive research comparison, with fixed validation/tuning budgets and untouched tests. A tiny training smoke only proves integration, not strategy quality.

R06. Start RL in shadow mode. Promotion requires legal behavior, better held out strategy results, uncertainty assessment, acceptable downside and latency, and binding artifact evidence. Insufficient evidence means keep the existing champion.

R07. No live exploratory transfers are required. A personal team contributes observational feedback; historical replay and a validated simulator provide training episodes. Extra simulated trajectories are not extra independent football seasons.

R08. Reevaluate after material drift, feature changes, candidate generator changes or a scoring regime change. Retraining need not occur at every click or every new post.

## Social requirements retained and extended

S01. Keep facts, specialist football reports, FPL expert opinion, crowd opinion and unknown sources distinct. Reviewed roles and reliability vary by topic and time.

S02. Extract player/action/topic/horizon/condition/evidence/attribution, rather than general positivity. Show conditional opinions separately from unconditional consensus.

S03. Treat reposts and shared rumours as one evidence family. Report sampled coverage, independent families, distinct authors and disagreement separately for expert and crowd views.

S04. Benchmark semantic extraction on labelled held out source families and periods. Live adapters require permitted access and remain disabled when unconfigured. The app stays useful without them.

S05. Social features remain explanatory until a legal, chronological ablation shows incremental forecast or strategy value. Agreement with experts is not the RL reward.

## Essential views

Retain existing screens. Add only controls needed to review model selection, next event private state, journal entries, data coverage, experimental policy comparison and learning reports. Do not start a cosmetic redesign milestone.

The decision report includes immediate action, estimated net gain, hits, horizon comparison, assumptions, unknowns, scenario contingencies, next review trigger and artifact provenance. It should explain why a roll is better when applicable. The button should say best found plan unless exact optimality is proved for that scope.

## First usable release

A frozen forecast and decision journal can be scored after finalization; new finalized events enter dynamic evaluation and latest serving fitting; replay preserves policy horizon and financially advances state; a learning report identifies the current champion honestly. All this works with baseline forecasts even before RL is promoted.

The next release adds simulator mechanics and genuine RL training in shadow. Full season chip optimisation, complete Bayesian points and evaluated TFT horizons are subsequent measured upgrades, not requirements to delay the first learning release.
