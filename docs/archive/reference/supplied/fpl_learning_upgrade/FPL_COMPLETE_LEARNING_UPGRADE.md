# FPL complete learning upgrade

Prepared 12 October 2026. Audit, PRD, technical specification and execution prompts.


## FPL learning upgrade

Prepared for Sambhav on 12 October 2026. Reviewed repository commit `840c1185d005270717c7453fb278dc30a03c05f3`.

The app has improved substantially since the first audit. It now needs a reliable learning and evaluation loop, stronger season planning and an experimental reinforcement learning policy. A new dashboard is not the next milestone.

### Read and execute

1. Read [LATEST_REPOSITORY_AUDIT.md](LATEST_REPOSITORY_AUDIT.md) for what is fixed, what remains incomplete and what was verified.
2. Read [PRD_V3.md](PRD_V3.md) for product requirements and the gameweek workflow.
3. Read [RL_AND_LEARNING_SPEC.md](RL_AND_LEARNING_SPEC.md) for forecast updates, the simulator, the RL policy and the retained technology stack.
4. Read [EVALUATION_AND_BACKLOG.md](EVALUATION_AND_BACKLOG.md) for implementation order, tests and promotion gates.
5. Paste [CODEX_MASTER_PROMPT.md](CODEX_MASTER_PROMPT.md) into Codex in your existing repository. It directs implementation agents to work in separate worktrees with one integration owner.
6. After a gameweek, use [GAMEWEEK_REVIEW_PROMPT.md](GAMEWEEK_REVIEW_PROMPT.md). This runs the learning process; it does not automatically make the model better.
7. Use [SOCIAL_NEXT_STAGE.md](SOCIAL_NEXT_STAGE.md) for semantic extraction and source reliability improvements.

Copy this directory into `docs/learning_upgrade/`. Preserve the previous specifications and existing user changes. The master prompt treats this as an incremental upgrade and compares the checkout with the audited commit before editing.

### What this package changes

The previous upgrade connected an experimental model and improved candidate generation. This package adds a prospective decision journal, finalized outcome ingestion, dynamic chronological evaluation, a separately fitted current serving artifact, a genuine receding horizon replay, financial transitions, a Gymnasium environment and an RL challenger.

The recommended RL design selects among legal action candidates and learns future value. The rules engine and numerical optimiser still enforce squad legality and finances. Learning does not mean gambling away free transfers to gather training data.

Thirty remaining gameweeks would be a short learning history for one manager. Player forecasts can learn from many football observations, but strategy performance still has only a small number of shared gameweek outcomes. Historical and simulated episodes provide research data; genuinely prospective results provide a separate check.

The retained collection in the repository reports GW6 current, GW7 next, with the next deadline at 17 October 2026, 10:00 UTC. GW6 labels were preliminary at capture. There are 32 numbered events from GW7 to GW38 inclusive, assuming the normal 38 event season. The application must derive current status from the provider and finalization flags instead of hardcoding this document's dates.

### Verification limits

Hosted verification stages for the reviewed commit passed backend, frontend, browser and persistence checks when inspected. Workflow cleanup was still running at the last recorded check. The repository records 292 backend tests plus 13 root CLI tests and 16 browser tests; those recorded counts were not independently rerun here.

Local audit checks parsed 78 retrieved Python files and executed the synthetic probes in [verification/latest_probes.py](verification/latest_probes.py). The audit runtime lacks the full locked dependencies. The probe substituted only the storage checksum and clock functions; actual contracts, rules, solver and replay ran. This is not API, database, training or personal team verification. The result file records the exact scope.

No repository code, manager state, account transfer or chip action was changed by this audit.

## Latest repository audit

Repository: https://github.com/Sambhav255/fpl-agent

Reviewed commit: `840c1185d005270717c7453fb278dc30a03c05f3`, committed at 12 October 2026, 05:14 UTC. Previous audit: `e759bcfb299d3f818d2e80ebb017796874cf8019`. The comparison contains two new commits.

### Assessment

There is meaningful backend progress. The old finding that all prediction jobs directly call the baseline is no longer accurate. The funding counterexample is repaired. The social subsystem exists, although it remains an offline grammar baseline with disabled live adapters. Current state integrity checks are stronger.

The app is still an experimental strategy assistant. It has no implemented reinforcement learning policy, no automatic learning lifecycle, no audited season policy benchmark and no full financial or chip optimisation across future events. Forecast sophistication and measured strategy quality must be evaluated separately.

I retrieved 103 files at the pinned commit, covering backend source and tests, scripts, implementation documents, project instructions and CI. I parsed 78 Python files and ran focused synthetic behaviour probes. I did not access your ignored local database, trained binary artifacts, personal current squad or live services. Real training numbers below are repository reported experiments, not retraining performed during this audit.

### Improvements to retain

| Area | What is now implemented | Remaining boundary |
| --- | --- | --- |
| Forecast routing | Worker invokes `forecast_job`; Football CatBoost has a real adapter | Baseline remains default; Bayesian and TFT are not live routed adapters |
| Immutable serving | Manifest, model files, feature frames, mappings, source bytes and universe are checked | This proves provenance and compatibility, not predictive advantage |
| Funding transfers | Ownership, legal XI and captain are jointly valued in candidate MILP | Candidate generation is not a full sequence optimiser |
| Exact oracle | Small declared universes and at most two events | It cannot certify global performance of the eight event planner |
| Collection | CLI, immutable collections and recoverable jobs; pending/preliminary/final rows distinguished | Current selected universe has only 30 players; collector union limit is 100 |
| Football features | Position, club, opponent, venue and rule era are categorical inputs | Only eight numeric lag fields; substantial football context is still absent |
| Replay | Evolving transfer inventory, independent plan validation and exact supplied stats scoring | Policy horizon is forcibly one; no audited evolving price history |
| Injury horizon | Future unknown availability is no longer repeated as zero | Numeric future values are conditional available scenarios, not calibrated unconditional means |
| Social | Reviewed source roles, author/family bounded aggregation, deletable lineage | Grammar only; no live sources or source accuracy learning |
| Manager state | Explicit event review and stale state blocks | User must confirm new private state; collection cannot infer it |

### Material next findings

| ID | Priority | Finding and evidence | Required change |
| --- | --- | --- | --- |
| C01 | P0 | `evaluation/strategy.py:83` overwrites requested horizon with one | Pass supported horizon to policy, validate its full proposed path, execute only first event |
| C02 | P0 | `models/football_catboost.py:408` fixes development/test partitions to GW1 through GW5 | Generate folds from finalized available events; separate evaluated artifacts and latest serving refit |
| C03 | P0 | Replay checks `source_cutoff` and caller timestamps, but not `prediction_origin` or bound artifact evidence | Add explicit audited prospective and assumed retrospective modes with origin validation |
| C04 | P0 | `collection_frames` creates future features only for the next event; manifest support is one | Implement lead specific features and evaluated horizon support; never stretch the one event artifact by renaming it |
| C05 | P0 | No decision journal and outcome reconciliation pipeline in the source tree | Freeze predictions and actions before deadlines, join finalized results and record revisions |
| C06 | P1 | Full sequence search remains width six with accrued point pruning and frozen prices | Add dynamic financial MILP and continuation value; benchmark against exact small cases |
| C07 | P1 | Future chips forbidden both by planner generation and `validate_plan` expected chip logic | Extend preferences and validator to a legal chip schedule before solving dates |
| C08 | P1 | Future conditional availability points enter the mean point objective | Require explicit scenario mode or calibrated recovery mixture; compare endpoints for flagged players |
| C09 | P1 | Thirty selected players and a single 30 row current test are narrow and biased | Capture a broad prospectively defined universe, compare by relevant subgroups and event blocks |
| C10 | P1 | `MatchStats` defaults components to zero; replay requires caller supplied stats | Reconcile against official fixture point totals; do not manufacture absent statistics as zero |
| C11 | P1 | Auxiliary probabilities use clipped regressors plus additive calibration offsets | Fit and evaluate appropriate binary heads and minutes mixture with broader calibration data |
| C12 | P1 | `social/extraction.py` uses explicit action grammar; conditional claims excluded from consensus | Build a labelled semantic benchmark and conditional evidence views before any forecast feature use |
| C13 | P1 | Social source groups exist but historical topic accuracy weighting does not | Add resolved claim registry, shrinkage and chronological source reliability evaluation |
| C14 | P1 | No Gymnasium, PPO or learning journal implementation exists | Build the environment after replay and financial correctness; keep RL a separate challenger |

P0 means required for a trustworthy learning release. P1 means required for the broader season strategy and RL release. These are implementation priorities, not measured quality scores.

### Behaviour reproduced against actual source

#### Funding fix works

The same controlled 18 player case used in the earlier audit now produces:

| Strategy | Expected points |
| --- | ---: |
| Keep | 84 |
| Old squad proxy comparator | 94 |
| New planner | 101 |
| Exact small oracle | 101 |

The new candidate objective recognises that selling a costly reserve goalkeeper can fund a starting midfielder. This is a verified software improvement. It is not proof of an average seven point improvement on real teams.

#### Injury correction is a conditional scenario

For a player with current availability zero, GW8 has zero points. GW9 through GW15 have approximately 3.56 points, `appearance_probability=null`, and separate zero/available endpoints. This is more honest than treating a current flag as permanent. It also means an injured player can receive their fully available future value in the deterministic planner. The application must not describe this number as a calibrated expected recovery forecast.

#### Replay does not evaluate the requested horizon

A policy called through `replay_policy` with a requested six event horizon receives `horizon_events=1`. The planner being compared therefore has no opportunity to use its longer forecast path in replay. Executing one action each event is correct; forcing planning to one event is the limitation.

#### Future prediction origin is accepted by assumed replay

A synthetic run with `prediction_origin` on 11 October is accepted at a 10 October deadline if its `source_cutoff` and caller availability fields are earlier. The current replay explicitly disclaims audited provenance, so this is a missing strict replay gate rather than proof of leaked production forecasts. A new strict benchmark must reject this case. A reconstructed historical model can be fitted today for research, provided a separate simulated information origin is honestly declared; it must not claim the artifact existed at the past deadline.

Reproduction and raw output are in `verification/`. Storage checksum and clock functions were substituted to accommodate the audit runtime. Optimisation, contracts, domain scoring and replay were imported from the pinned source without substitution.

### What the current models demonstrate

The repository reports a current season artifact at actual origin 12 October 2026, 04:31 UTC. Fitting and lag history use 150 final GW1 to GW5 labels, with 30 preliminary GW6 rows excluded. The 30 row GW5 assumed timing test reports CatBoost RMSE 4.5017 versus population comparator 4.4634, and MAE 3.7520 versus 3.7444. There is no demonstrated current season advantage.

The older 2024/25 archive experiment reports CatBoost RMSE 2.1496 versus rolling points 2.1791, while MAE is worse, 1.1825 versus 1.1261. Empirical coverage of its nominal 80 percent interval is 31.4 percent. These are mixed diagnostic results under reconstructed timing and an older scoring regime. They do not justify current live promotion or precise confidence claims.

The fixed GW1 to GW5 partition has another consequence: even after later finalized events arrive, rerunning this function does not fit the points model on those new events. Future lag inputs may update, but the model fitting partition stays unchanged. There must be a separate latest data refit after honest evaluation. Adding the new test week to training before scoring its frozen forecast would invalidate the prospective comparison.

Do not delete strict provenance rules to manufacture a stronger model badge. Also do not wait indefinitely for perfect historical snapshots. Qualified reconstruction is useful for development, latest known outcomes are valid for future fitting, and new prospective capture builds the missing evidence over time.

### Verification evidence

Hosted workflow: https://github.com/Sambhav255/fpl-agent/actions/runs/38207057987

When inspected, locked installation, backend checks, frontend checks/build, and browser/persistence checks had completed successfully. The workflow job was still completing cache cleanup, so the overall run conclusion had not been reported. Prior two workflow runs were cancelled, not failed.

The latest build document records 292 backend tests, three skipped, 13 root CLI tests and 16 browser tests. Hosted step success corroborates the verification stages, but this audit did not independently rerun those counts. Offline dependency installation locally could not complete because the required packages were absent from cache. No permission or dependency restriction was bypassed.

The local audit parsed 78 Python files and reproduced four probes. It did not run the full locked suite, train model heads, serve an API, test SQLite concurrency or confirm the state of services on your Mac. Codex must perform those checks in your actual checkout and save reproducible evidence before declaring a milestone done.

### Immediate next move

Implement the decision journal, finalized outcome pipeline, dynamic evaluation/refitting and real receding horizon replay first. Then add a rules accurate simulator and train an RL challenger. Preserve baseline operation, opt in experimental forecasts, money unknowns, immutable artifacts and manual account execution throughout.

## FPL PRD v3: learning and season strategy

Owner: Sambhav. Date: 12 October 2026. Basis: commit `840c1185d005270717c7453fb278dc30a03c05f3` and the preceding intelligence upgrade.

### Product outcome

Before each deadline, provide a legal immediate decision, an eight event conditional strategy, captain/vice/bench choices, future chip options and an explained comparison with simpler approaches. After finalized results, assess forecast errors and decision outcomes, update suitable models, and retain or replace the current champion using recorded evidence.

The system should improve its estimates and decisions over time. Improvement is a measured result, not something guaranteed by retraining or adding a neural network.

### Architecture decision

Retain three football forecasting families: CatBoost, Bayesian events and TFT. Introduce a fourth, separate strategy component: a reinforcement learning policy or value function. Forecasts describe football outcomes; the policy chooses actions under finances, transfer inventory and future opportunities. The rules engine validates everything.

The baseline and numerical planner remain usable while advanced components mature. The active champion can be a simple model, an eligible individual advanced model or a validated ensemble. There is no requirement to blend a weak family into the deployed result.

### Scope

| Horizon | Decision | Product output |
| --- | --- | --- |
| Next deadline | Execute manually now | Roll/transfer/chip, spending, hits, XI, captain, vice and bench |
| Four, six and eight events | Receding horizon strategy | Alternative first actions, expected net value, finances, flexibility and triggers |
| Remaining season | Macro opportunities | Chip window calendar, fixture turns and contingency scenarios |
| Completed event | Learn and assess | Frozen prediction scorecard, realized net points, counterfactual immediate actions and update decision |

Only the immediate action is concrete. Later transfers are proposals to revisit. Unscheduled fixtures and unavailable future probabilities remain explicit uncertainty.

### Learning requirements

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

### Season planning requirements

P01. Replay lets a policy plan across its actual supported horizon, executes the first event only, advances prices and state, reveals newly available information, and replans. Never expose later snapshots or outcomes to the current policy.

P02. Finance is an explicit transition model: acquisition basis, market and selling values, bank, free transfers, committed and additional hits, temporary Free Hit ownership, permanent squad and chip inventory. Unknown inputs block the affected financial claim.

P03. Provide a candidate set with roll, legal singles, funding pairs, selected larger bundles, injury contingencies and chip alternatives. A learned policy cannot select an action missing from the candidate set. Candidate recall is a release metric.

P04. Add a genuine sequence optimiser with transfers and ownership changing by event. Incorporate allowed chip dates and legal windows. Extend the independent validator before enabling future chips.

P05. Value retained free transfers, bank and squad flexibility using a tested continuation function. Avoid rewarding them twice when the forecast horizon already captures the same benefit.

P06. Evaluate joint scenarios for availability, minutes, captain fallback, autosubs, clean sheets, attacking outcomes and fixture calendar changes. Compare all actions on shared football scenarios. If scenario probabilities are unavailable, report separate scenario results rather than inventing a weighted mean.

P07. Detailed plans default to the strongest supported horizon. Unsupported leads remain unavailable. A one event CatBoost artifact cannot be called an eight event forecast by repeating its numbers.

P08. Compare decisions over four, six and eight events and report sensitivity to terminal assumptions, injury scenarios and affordability changes. Wide action disagreement is a useful caution signal.

P09. Rank and mini league modes require an explicit rival model and objective. Default maximises points after hits. Ownership alone does not make a player a good differential.

### Reinforcement learning requirements

R01. Implement a Gymnasium FPL environment backed by the same domain transitions and scoring rules as replay. Exact mechanics must be validated before training.

R02. Start with a restricted action slate of legal current event plans and a finite season observation. The RL policy chooses a candidate; the optimiser provides legal transfers and lineup proposals. Include a legal roll action.

R03. Reward realized or simulated squad points after hits exactly once. Use no future actual points as current observation. Simulation estimates, historical research and live results have separate evidence labels.

R04. Train a real optional MaskablePPO challenger, save/reload it, and compare it with current planner, greedy, roll/keep and a simpler fitted value policy on the same episodes and football outcomes.

R05. Use at least five training seeds for a substantive research comparison, with fixed validation/tuning budgets and untouched tests. A tiny training smoke only proves integration, not strategy quality.

R06. Start RL in shadow mode. Promotion requires legal behavior, better held out strategy results, uncertainty assessment, acceptable downside and latency, and binding artifact evidence. Insufficient evidence means keep the existing champion.

R07. No live exploratory transfers are required. A personal team contributes observational feedback; historical replay and a validated simulator provide training episodes. Extra simulated trajectories are not extra independent football seasons.

R08. Reevaluate after material drift, feature changes, candidate generator changes or a scoring regime change. Retraining need not occur at every click or every new post.

### Social requirements retained and extended

S01. Keep facts, specialist football reports, FPL expert opinion, crowd opinion and unknown sources distinct. Reviewed roles and reliability vary by topic and time.

S02. Extract player/action/topic/horizon/condition/evidence/attribution, rather than general positivity. Show conditional opinions separately from unconditional consensus.

S03. Treat reposts and shared rumours as one evidence family. Report sampled coverage, independent families, distinct authors and disagreement separately for expert and crowd views.

S04. Benchmark semantic extraction on labelled held out source families and periods. Live adapters require permitted access and remain disabled when unconfigured. The app stays useful without them.

S05. Social features remain explanatory until a legal, chronological ablation shows incremental forecast or strategy value. Agreement with experts is not the RL reward.

### Essential views

Retain existing screens. Add only controls needed to review model selection, next event private state, journal entries, data coverage, experimental policy comparison and learning reports. Do not start a cosmetic redesign milestone.

The decision report includes immediate action, estimated net gain, hits, horizon comparison, assumptions, unknowns, scenario contingencies, next review trigger and artifact provenance. It should explain why a roll is better when applicable. The button should say best found plan unless exact optimality is proved for that scope.

### First usable release

A frozen forecast and decision journal can be scored after finalization; new finalized events enter dynamic evaluation and latest serving fitting; replay preserves policy horizon and financially advances state; a learning report identifies the current champion honestly. All this works with baseline forecasts even before RL is promoted.

The next release adds simulator mechanics and genuine RL training in shadow. Full season chip optimisation, complete Bayesian points and evaluated TFT horizons are subsequent measured upgrades, not requirements to delay the first learning release.

## RL and continual learning specification

This is a proposed implementation, not a description of a trained model currently in the repository. It extends the existing Python engine and preserves model evidence gates.

### Separate the learning problems

| Component | Learns | Feedback | First implementation |
| --- | --- | --- | --- |
| Football forecast | Minutes, appearances, point distributions and team strength | Finalized player fixture outcomes | CatBoost refits and calibration; Bayesian state updates |
| Strategy value | Future value of transfers, money, ownership and chips | Complete replay/simulation returns | Fitted state/action value and terminal continuation model |
| RL policy | Which legal action candidate to take | Sequential points after hits | Optional MaskablePPO challenger |
| Social evidence | Entity/action extraction and source reliability | Reviewed labels and resolved factual claims | Semantic benchmark and shrinkage estimates |

Refitting CatBoost after each event is continual supervised learning. A policy trained to maximise sequential rewards is reinforcement learning. Updating an explanation prompt is neither. Keep those names and artifacts distinct.

Six manager decisions provide little evidence about a strategy policy. They do not become hundreds of independent decisions by multiplying them by 15 players. Player outcomes provide many labels, but shared matches and events create dependence. Simulation expands the research state space while inheriting the simulator's mistakes.

### Retained and added technology

Keep Next.js, React, TypeScript, FastAPI, SQLite, Parquet, uv, NumPy/Pandas, SciPy/HiGHS and CatBoost. Bayesian and TFT remain optional. Reuse existing worker leases, cancellation, snapshots and compare and swap updates.

Add optional `rl` dependencies: Gymnasium, Stable Baselines3, SB3 Contrib and a compatible PyTorch build. Pin compatible stable releases in the lockfile after checking current official documentation. Do not copy floating master dependency versions or create a second incompatible Torch stack beside the TFT extra. Verify baseline installation without RL, RL only, and combined deep/RL extras.

Start on CPU with compact models. Store run configuration, code revision, dataset fingerprint, random seeds, library versions, training metrics and serialized artifacts locally. JSON/Parquet plus optional TensorBoard is enough initially; no Kubernetes, external vector service or mandatory experiment tracking subscription.

Suggested modules:

```text
backend/src/fpl_app/learning/journal.py
backend/src/fpl_app/learning/outcomes.py
backend/src/fpl_app/learning/folds.py
backend/src/fpl_app/learning/review.py
backend/src/fpl_app/learning/promotion.py
backend/src/fpl_app/simulation/environment.py
backend/src/fpl_app/simulation/scenarios.py
backend/src/fpl_app/simulation/finance.py
backend/src/fpl_app/policies/candidates.py
backend/src/fpl_app/policies/fitted_value.py
backend/src/fpl_app/policies/masked_ppo.py
scripts/review_gameweek.py
scripts/train_policy.py
scripts/evaluate_policies.py
```

Use existing modules where ownership and contracts make that simpler. These paths are recommendations, not an instruction to duplicate existing transitions.

### The prospective learning loop

1. Capture official sources and confirm the manager's private state separately.
2. Create current forecast artifacts using only finalized labels available at training time.
3. Freeze forecast origin, serving bundle, policy version, candidate menu and proposed action before the deadline. An origin is the actual information time; the deadline is the last legal decision time.
4. Record the user's confirmed actual action separately from the recommendation. Unconfirmed execution remains unknown.
5. Once provider event checking and fixture finalization pass, capture outcomes and attach a revision digest.
6. Score the already frozen predictions and policy portfolios before fitting on their new labels.
7. Generate chronological evaluation/refitting plans, run a challenger and compare on common origins and episodes.
8. Produce a promotion or retention report; generate a new immutable serving artifact when eligible.
9. At the next deadline, replan. Preserve older journals and revisions.

Local worker triggers should poll finalization modestly, support manual invocation and stop retrying after a bounded failure budget. Repeated invocation with identical input hashes is idempotent. Network capture never edits manager finances. No background job submits an FPL account action.

#### Proposed journal contract

```json
{
  "decision_id": "uuid",
  "season": "2026/27",
  "event": 7,
  "decision_origin": "actual timezone aware timestamp",
  "deadline": "provider timestamp",
  "state_version": 12,
  "snapshot_id": "immutable reference",
  "forecast_reference": "immutable reference",
  "policy_reference": "immutable reference",
  "candidate_set_reference": "immutable reference",
  "recommended_action_id": "candidate reference",
  "execution_status": "execution_unknown",
  "evidence_mode": "prospective_shadow",
  "input_sha256": "digest"
}
```

Store candidate details and private finances in local artifacts, not public Git. Store forecasts for covered nonowned players too, so evaluation is not limited to the chosen squad. Outcome attachments include actual label availability, capture, finalization status, source revisions, scoring era, and evaluation version.

### Fix fitting and validation

Replace the fixed partition literal in `train_collection_experiment` with a declared fold generator. Generate folds from available finalized events and actual or explicitly assumed label times. Stop if timing purges empty a partition. Do not move test events into development merely to make a fit succeed.

Use expanding development windows and later validation/calibration/test blocks where coverage allows. For the earliest season stages, record insufficient data for broad evaluation and use historical research plus current prospective shadows. Later predictions can use earlier test period results when those outcomes were actually available, but a fixed fitted model cannot learn the test targets during its frozen test run.

There are two artifact types:

1. Evaluation artifact: fit without its held out labels, used to estimate performance under recorded cutoffs.
2. Serving refit: after evaluation is finished, fit using all finalized labels available now, with its own actual completion time and future origin. It inherits method evidence, not the old artifact's identical fitted parameters or checksum.

The serving refit records the selected method, configuration, evaluation links and differences from evaluated models. Changing features, universe or heads invalidates automatic inheritance of evaluation support. A just completed GW5 evaluation cannot justify a latest refit whose configuration was selected by examining future outcomes.

Begin with a limited, registered feature ablation sequence: lag statistics, then fixture/strength covariates, then minutes/role/congestion, then permitted advanced event metrics. Current club and opponent IDs do not alone encode team strength. Fit team strength with shrinkage from earlier matches; preserve posterior uncertainty. Cross season identity and scoring era must be explicit.

Probability heads should use suitable binary losses where practical, coherent nesting, and separately fitted calibration. A probability of playing 60 minutes cannot exceed appearance probability. A minutes mixture distinguishes no appearance, substitute minutes and starts. Expected points are unconditional; never multiply a direct unconditional mean by availability again.

Calibrated distribution or conformal methods require chronological held out residuals and an explicit dependence/drift limitation. Until calibration works, leave uncertainty unavailable. A nominal interval with 31.4 percent empirical coverage is not an 80 percent confidence statement.

### Genuine receding horizon replay

At origin t, expose only observations available by t and the forecast path produced at t. Let the policy plan H events, capped by remaining events and actual provider support. Validate all H proposed weeks using the same settings and exact input fingerprint. Execute only week one. At t+1, reveal the newly available snapshot and outcomes, update the financial ledger, and plan again.

Do not take the second week's forecast from a later `ReplayOrigin` and pretend it existed in the earlier run. If the earlier run supports one event, the experiment is a one event experiment. Full horizons require frozen multilead forecasts built at that earlier origin.

Create distinct provenance modes:

1. Prospective strict: source, forecast and policy artifacts existed before the actual origin and deadline. Check hashes and actual timestamps.
2. Historical reconstructed: fitting may occur today, but simulated observation and fitting label cutoffs are honoured. Mark timing, memberships, prices and feature uncertainties.
3. Synthetic mechanics: authored outcomes for rules tests.
4. Generative simulation: outcomes sampled from a fitted world model with recorded assumptions.

Reject future prediction origins in strict mode. Do not falsely require an artifact trained today to have existed years ago for a clearly labelled retrospective research fit. A historical reconstruction cannot become a prospective performance claim.

Replay must represent current prices and purchase basis. If the initial purchase price is unknown, a recorded confirmed selling quote works only within its actual market anchor; a future price path requires an explicit assumption or known basis. Separate frozen price, reconstructed price and prospectively observed financial modes. A changed historical quote must not silently infer purchase cost.

### Environment definition

FPL strategy is partially observed: true player fitness, selection and future fixtures are not fully known. Start with a finite season belief/state representation rather than claiming perfect Markov information.

One environment step is one event. Observation contains normalized bank/transfer inventory, owned player and acquisition data, chip flags/windows, remaining events, as of fixture path, forecast means and supported uncertainty, availability evidence and missingness. It also contains a fixed size candidate feature matrix and validity mask.

The environment owns hidden realized or sampled football outcomes. Neither observations, policy accessible `info`, action masks nor candidate ranking may depend on those future outcomes. Reveal prior football results only after their recorded availability time. Player IDs are season scoped metadata, not a universal numerical ordering of talent.

`reset(seed, options)` chooses an admissible starting squad, season segment and a hidden replay/simulation path. `step(action)` independently validates the selected current action, applies transfers/chip, scores XI/autosubs/vice fallback, subtracts hits once, restores Free Hit when due and advances to the next origin.

Natural season end returns `terminated=true`. A research time or data budget boundary returns `truncated=true` with correct bootstrapping handling. Missing observations must not masquerade as a completed season. No hidden access to results through debug fields in training or serving.

#### Candidate action space

Start with `Discrete(K)`, K=32 as an initial implementation default. Each valid slot is a current event transfer/chip/lineup plan; unused slots are masked. Candidate provenance, ordering and hashes are frozen. Slot zero is a legal roll/keep option when normal decision readiness holds. Unknown live finances do not get replaced with a synthetic feasible transfer action.

Generate candidates from the optimiser and deterministic diverse templates: singles, funding pairs, roll, injury scenarios, limited hits and available chips. Independent validation comes before admission. Avoid 32 variations of the same single transfer. Log truncation and exact small universe recall.

A candidate represents only a first action, with future forecast summary features. Deduplicate identical first actions even if proposed future paths differ, and record the alternative continuations. Rank cannot refer to realized future points. Chip availability and affordability masks are computed only from the current state and declared scenario.

Because candidate slots change meaning between states, use a shared candidate encoder that scores state context plus each candidate's features, with invariant pooled context and masked logits. A plain fixed action index network can learn accidental slot meaning. Test that permuting candidates permutes policy probabilities and preserves the selected semantic action, apart from genuine ties. Preserve mask use in rollout collection, inference and evaluation.

SB3 Contrib documents that MaskablePPO requires its mask aware evaluation utilities and does not support recurrent policies. Do not combine its standard implementation with an LSTM policy and assume it works. Start with explicit current belief features and a compact shared scorer. Use custom policy methods compatible with the pinned masked distribution and value head.

### Reward and RL training

Base reward is squad event points after hits. Subtract total event hits once from realized points; committed hits are common to alternatives but still part of the portfolio total. Do not subtract the same hit again through an additional reward penalty. Free Hit restoration, free transfer retention and chip expiry affect future rewards through transitions.

Use finite season returns with gamma=1 as the primary objective, including events remaining in state. Evaluate gamma sensitivity only as a declared modelling variant. Reward scaling may help training, but reported performance is always raw points. Do not add arbitrary rewards for expert agreement, bank balance, follower popularity or using advanced models.

Potential based shaping can be a separate controlled experiment with an explicit terminal potential of zero. Rewarding each retained transfer while also learning its future value can double count flexibility. A horizon terminal continuation term is `V(state_after_H, remaining_events)` and must estimate only rewards after the scored H events.

Build a fitted value or fitted Q baseline first, then a genuine PPO fit. Teacher plans can initialize candidate/value models when produced from available forecasts. A hindsight best squad is a diagnostic upper bound, not a teacher that may access future actual points at live origins.

Historical player football outcomes are mostly exogenous to one fantasy manager's choices. With sufficient coverage, alternative legal actions can be scored immediately on the same event results. This does not reconstruct the entire alternative future without simulating its evolving squad, prices, inventory and later decisions. Replaying the same completed event thousands of times is not independent validation. Do not claim standard logged policy importance weighting when action propensities and support are absent.

For substantive PPO experiments, freeze data partitions and simulator versions, train at least five seeds, tune only on development/validation, and compare against the current policy on the same hidden paths and starting squads. Save checkpoints and optimizers for training reproducibility; live artifacts are immutable copies. Warm starts across events remain challengers and must pass the same tests.

### World model and simulator validity

Provide deterministic historical replay first. Add a generative world model with shared team goals/clean sheets, minutes, appearance, player scoring components and calendar/price scenarios. Current Bayesian samples are not yet a complete calibrated world model. Complete or explicitly qualify missing components before calling a simulation realistic.

Preserve correlations when scoring plans. Two defenders from the same club share clean sheet risk; double fixture outcomes are aggregated under event scoring and substitutions. Scenario identity is common across compared actions and policies.

Simulator stress tests include excessive hits, repeated chip use, profitable impossible price cycles, injured player optimism, missing fixtures, misleading uncertainty and artificial season cutoff effects. If RL exploits any of these, repair the world model and invalidate the affected experiment. Increasing episode count cannot fix an incorrect reward model.

The short term fallback is clearly labelled frozen price and conditional availability research, paired with a few robust scenario endpoints. It permits environment and policy mechanics work now. It cannot justify automatic live promotion until evaluation supports the relevant assumptions.

### Deployment and learning controls

Separate football champion and strategy champion registries. A policy promotion binds forecast family/version, candidate generator, observation schema, rules, simulator/evaluation evidence and policy checksum. Changing the candidate generator can invalidate an otherwise unchanged policy.

Modes: research, shadow, explicit experiment, active champion, disabled. Baseline/planner failure fallback is visible and separately labelled, never an RL result. Invalid actions are rejected before any state write. Stop experiment serving when required inputs, coverage or versions change.

Weekly review can create challengers automatically, but default replacement follows recorded predefined gates. No claim of monotonically increasing quality. Preserve a last valid champion for rollback. A failed model update should leave the app usable.

## Evaluation gates and implementation backlog

This plan prioritises learning infrastructure and decision quality. User interface changes are limited to essential review and evidence controls.

### Ordered milestones

| ID | Priority | Deliverable | Acceptance |
| --- | --- | --- | --- |
| D01 | P0 | Reproduce audit, run actual checkout checks and reconcile current event | Hosted/local checks recorded; manager state never inferred or overwritten |
| D02 | P0 | Decision journal and finalized outcome joins | Deadline freeze, execution distinction, idempotency and revision tests pass |
| D03 | P0 | Dynamic folds plus latest serving refit | New final event enters an eligible new fit; frozen test forecast scored first |
| D04 | P0 | Receding horizon replay and provenance modes | Policy receives requested supported horizon, only first action executes, future origins rejected in strict mode |
| D05 | P1 | Broad prospective universe and football feature ablations | Membership frozen at origin, coverage verified, no retrospective top scorer selection |
| D06 | P1 | Price and acquisition transitions; official points reconciliation | All legal financial paths replay; unknown components not filled with zeros |
| D07 | P1 | Full financial sequence/chip optimiser and validator | Future chips legal, balances and transfer inventory checked independently |
| D08 | P1 | Gymnasium environment and candidate contracts | Domain parity, deterministic seed behavior, masks, natural end/truncation tests |
| D09 | P1 | Fitted value and real MaskablePPO challenger | Fit/save/reload, masked evaluation, multiple seeds, same episode comparator report |
| D10 | P1 | Local recurring review jobs and promotion reports | Idempotent recoverable jobs; insufficient evidence retains champion |
| D11 | P1 | Semantic social benchmark and reliability registry | Author/family/time separation, condition extraction and resolution evaluation |
| D12 | P2 | Complete Bayesian scoring, multilead TFT and eligible ensembles | Real chronological evaluation and serving contracts; no mandatory weak blend |

D02 through D04 are the first learning release. D08/D09 make reinforcement learning real in shadow. D06/D07 can develop in parallel with journal work after shared contracts are agreed. Policy promotion depends on meaningful D05/D06 evidence, not merely finishing D09.

### Mechanics acceptance tests

1. Preserve the repaired funding regression: Keep84, proxy94, new101, exact101. Cover delayed funding, hits and locks/exclusions with independent enumeration.
2. A six event supported forecast gives replay policy six planning events, executes only one and replans at the next origin. Near GW38, horizon caps safely to remaining events.
3. Strict replay rejects a future `prediction_origin`, future source/model availability, mutated artifact, changed mappings and missing schedule. Reconstructed historical mode stays visibly distinct.
4. New finalized labels enter dynamic folds and subsequent serving refits. Preliminary/pending labels never do. Evaluation occurs before newly scored targets enter fitting.
5. Late label correction creates a new scorecard revision; old report remains traceable. Duplicate review jobs produce no duplicate journal/outcome attachment.
6. Actual execution unknown does not become the recommended squad. Paper portfolio and live execution are distinct.
7. Market rise/fall, rounded sale profit, reacquisition basis, confirmed quote anchors, committed hits and unknown values preserve the financial ledger. Test a Free Hit with prices moving during its temporary squad.
8. Future chip schedules pass inventory/window rules, prohibit multiple chips in an event, restore Free Hit and expire inventory correctly. Current validator must be extended deliberately.
9. Exact official fixture points reconcile with reconstructable component scoring. If unavailable components make reconstruction impossible, use a validated official total outcome adapter with explicit minutes/appearance coverage rather than zeros. Autosubs and captain fallback still follow domain rules.
10. Environment step agrees with domain replay for the same action and hidden outcomes. Test goalkeeper/outfield substitutions, one fixture played in a double, blank events and chip scoring.
11. Candidate padding is masked, roll remains legal, duplicate first actions collapse, illegal action raises and produces no persistent live write. Candidate permutation preserves semantic probabilities in the shared scoring architecture.
12. Same seed and versions reproduce trajectories. Mutating future outcomes cannot change a current observation, menu, mask or decision; it can change the subsequent reward.
13. True season end is terminated, artificial cutoff truncated. Value targets handle both correctly. Warm starting does not import test normalization statistics.
14. RL save/reload preserves deterministic chosen semantic actions on held out fixtures. Inference and evaluation both pass masks.
15. Optional RL/deep dependency absence leaves baseline startup and jobs working. Cancellation and worker retry do not replace frozen artifacts with latest versions.

### Forecast evaluation

Compare baseline, rolling points/minutes, position/club shrinkage and every challenger on the same covered origin/player/fixture universe. A selected player model is evaluated as selected coverage, not the whole league. Report fixture and event point RMSE, MAE and bias, appearance/start/60 minute Brier or log loss, minutes error, quantile loss and empirical coverage when available.

Report lead specific performance for every supported horizon; position, expected starter, rotation, new player, price band, blank/double and scoring era subgroups. Subgroups use information available at the forecast origin. A subgroup selected using realized future high scores is a retrospective diagnostic only.

Report mean versus median differences honestly. Do not add marginal quantiles to create event or squad quantiles. Evaluate distribution claims using valid joint simulations or explicit aggregate calibration.

Use event or season blocks for uncertainty, retaining match/player dependence. A 30 row player sample is not 30 independent weeks. Keep all tuning and ensemble weights out of final test data. Report effective covered events and limitations rather than hiding them behind a large row count.

### Strategy evaluation matrix

| Question | Hold fixed | Compare |
| --- | --- | --- |
| Does the planner improve? | Same forecast runs and football outcomes | Current proxy, repaired planner, full sequence planner |
| Do forecasts improve actions? | Same planner/candidate rules | Baseline versus football challengers |
| Does RL improve decisions? | Same forecast provider, candidate menu and episodes | Greedy, roll/keep, numerical planner, fitted value, PPO |
| Does future value help? | Same horizon and inputs | Unfitted tiebreak versus fitted continuation |
| Does social help? | Same legal source rights and origins | Football only versus permitted social features |

Compare cumulative net points, paired incremental points, per event gains, cumulative additional hits, chip use, remaining transfers, budget failures, legality, latency and sensitivity. Include conservative downside measures and worst event clusters. Raw FPL rank is secondary unless complete field data and a defined rival objective exist.

Common starting squads do not create independent seasons. Common random paths reduce comparison noise. Report both episode distribution and the number of distinct actual or simulated season paths. A hindsight exact oracle is an upper bound diagnostic, not a deployable baseline.

### Promotion rules

Before tuning, register a minimum meaningful strategy gain, an allowed downside tolerance, acceptable latency and legality requirements. Initial research default: five training seeds, zero invalid accepted actions, paired evaluation against the current planner, and a conservative confidence interval for incremental points. Five seeds is an engineering minimum, not a claim of statistical sufficiency.

Mechanics must all pass. Required evidence must bind the exact artifact and its observation/candidate/schema/rule versions. Mean improvement alone is insufficient if downside or coverage is materially worse. A lower confidence bound above the registered improvement threshold is a strong research gate, but sparse prospective gameweeks can remain inconclusive. Do not weaken gates just to activate RL.

A reconstructed historical win supports research selection; a simulator win supports simulation evidence. Neither alone proves a live edge. Shadow candidates may run immediately with honest labels and no account actions. Promotion stays unavailable when evidence is insufficient, while useful journal, calibration and planning upgrades still ship.

Prevent repeated test peeking: select hyperparameters on development/validation, freeze them, evaluate the test once, then begin a new forward monitoring period. Record every candidate attempted and retain failed experiments. A winning seed picked after inspecting test scores is not the policy result.

### Actual repository checks

Use the checkout's locked versions and current scripts. At audit time the hosted workflow runs:

```bash
uv sync --locked --project backend
npm ci --prefix apps/web
cd backend
uv run pytest
uv run pytest ../tests
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

From `apps/web`: `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, then the configured Playwright suite against an actual API and worker. Inspect the current `scripts/check.sh` and workflow instead of assuming an obsolete command list.

After shared contract edits regenerate API/types, build, start services in isolated ports and data paths, and perform actual journal/forecast/analysis/save/reload/outcome/review flow checks. Keep ordinary CI offline with authored fixtures. A permitted live smoke is separate and must preserve private state. Do not start duplicate services on ports already owned by the user's session.

### Ownership for implementation agents

The lead owns shared contracts, migrations, lockfiles, API/jobs, router, generated types and integration. One agent owns journal/outcomes/folds. Another owns strategy replay/finance/optimisation. Another owns the environment/policy models. Another owns football feature/evaluation or social scope, depending on the active milestone. An independent reviewer examines leakage, financial validity and evidence claims after integration.

Separate worktrees and nonoverlapping file ownership are required for concurrent editing. Use bounded native agent concurrency supported by the installed Codex runtime, with at most four implementation agents at once. If unavailable, execute the same scopes sequentially. An agent cannot edit a shared file without lead coordination.

## Social intelligence: next implementation stage

The current subsystem is a useful conservative starting point. It is not a trained semantic model and does not collect real Reddit/X content. Do not rebuild its capability, reviewed source or deletion infrastructure unnecessarily.

### Build semantics before consensus claims

Retain the grammar extractor as a precision comparator. Add entity linking and a structured semantic extractor with player ID, action, topic, horizon, condition, funding relation, attribution, fact/opinion/question status, evidence span and abstention. Preserve source text only where permitted. A claim must be supported by its span.

Examples for the benchmark are authored fixtures, not real posts:

| Text | Required interpretation |
| --- | --- |
| Palmer looks great but I would sell him to fund Salah | Palmer sell, Salah buy, funding relation; positive sentiment is not a hold vote |
| Captain Haaland only if the manager confirms he starts | Conditional captain; separate from unconditional captain consensus |
| Is Watkins worth a hit? | Question; no buy vote |
| Reporter says Saka trained, but no decision on Saturday | Attributed report and unresolved availability; not confirmed starting |
| Sold Jackson last week, now holding | Historical sell versus current hold |
| Nice cameo again, clearly captain material | Potential sarcasm; abstain if unsupported |

Build an initial 200 to 300 varied authored/permissioned examples, with a frozen test subset, source family and temporal separation. The number is an engineering target, not proof of accuracy. Independently double review a subset and record disagreements. Do not manufacture a human reviewed label by asking the same model to grade itself.

Compare grammar, compact embedding/entity models and a permitted structured language model extractor if available. Small pretrained sentence embeddings help entity resolution and rumour similarity; they do not directly solve stance or conditional recommendations. Benchmark entity accuracy, action/topic/horizon F1, conditional and attribution accuracy, report precision, abstention coverage and evidence span fidelity. Calibrate any confidence scores on held out labels.

### Expert and crowd separation

Use reviewed, versioned roles: official football source, specialist club reporter, FPL analyst, established manager, crowd and unknown. A reviewed expert label is not a guarantee of accuracy. Keep topic assignments explicit. A reporter may be credible about training without being strong at FPL transfer strategy.

Factual reliability can learn from timestamped claims with verifiable resolutions. Separate confirmed out/available, actual start and uncertain wording. Use shrinkage toward a topic prior and uncertainty intervals; sparse source histories stay close to the prior. Do not translate “might play” into an invented numerical probability or mark it wrong because the player did not play.

For FPL strategic opinion, evaluate comparable forecasted or recommended actions with explicit horizon, costs and uncertainty. Points gained by a single recommendation are noisy and depend on the starting squad. Avoid a leaderboard based on hindsight picking the one expert who happened to captain the week's highest scorer.

Freeze source inclusion and reliability as of each origin. Reviewing today's best performing pundit cannot retroactively make them part of last month's expert sample. Followers, verified badges and retweets are not the primary weighting signal.

### Aggregation and use

Show expert and crowd buy/sell/hold/captain distributions separately, by horizon and topic. Conditional views are separate rather than discarded permanently. Display disagreements, distinct authors, independent rumour families, coverage and recency.

Extend exact text deduplication to linked article and semantic evidence families with reviewed thresholds. Reposted reports are amplification, not independent confirmation. Cap author repetition and preserve conflicting claims. Missing live coverage stays unavailable.

Initially use reports to trigger review and opinions to explain agreement/disagreement. Structured availability evidence can create scenario branches when its provenance supports that use. No fixed expert bonus to player expected points. RL reward remains football points after hits.

Before any social derived training feature, verify permission for that derived use and run a football only versus social ablation on chronological origins. Also compare minutes improvement, strategy gain and false alarm costs. Engagement and hype often describe popular players rather than new football information.

### Access and retention

Current Reddit policy requires explicit approval for API access and places separate restrictions on training and commercial use. X developer guidance requires official permitted access and has explicit ML training restrictions. Reading, storing, semantic inference, exporting and training are separate capabilities; a token does not grant them all.

Use authored fixtures now and permitted data when available. No scrape fallback, identity matching of anonymous Reddit accounts to X accounts, or platform limit evasion. Provider deletion/edits must remove affected text, embeddings, claims, consensus caches and any permitted derived training artifacts under their retention rules. Keep numerical model results only when permitted and traceable.

Live collection remains an optional adapter. A missing Reddit or X configuration cannot stop football model and planner operation. Record sampling bias: a subreddit or curated X list is not the general FPL population.

## Codex master execution prompt

Paste the following into Codex in the existing repository. This authorises parallel implementation in isolated worktrees, with one integration owner. The earlier single checkout ownership rule still applies within each worktree.

```text
You are the implementation lead for my existing FPL assistant. Build the next learning and strategy release, then a real reinforcement learning challenger. Preserve the existing app and my local data. Prioritise forecast and decision quality over cosmetic interface work.

Start by reading AGENTS.md, relevant nested instructions, docs/BUILD_STATUS.md, docs/CURSOR_HANDOFF.md and docs/learning_upgrade/*.md. These documents were audited against 840c1185d005270717c7453fb278dc30a03c05f3. Inspect actual current code and compare with that commit. Newer implementation supersedes obsolete audit findings when verified. Do not overwrite unrelated user changes or ignored personal files.

I explicitly authorise multiple implementation agents. Use the installed runtime's native agent support, at most four implementation agents concurrently. Use separate worktrees and explicit file ownership. One lead owns contracts, migrations, dependencies/lockfiles, API/jobs, model router, generated types and integration. No concurrent shared file edits. If native agents are unavailable, perform the same tasks sequentially without inventing agent activity.

Initial workstreams:
1. Learning agent: decision journal, finalized outcome/revision joins, dynamic chronological folds, current serving refit and learning reports.
2. Strategy agent: true receding horizon replay, strict versus reconstructed provenance modes, financial transitions and future chip validator/optimiser work.
3. RL agent: Gymnasium environment, legal candidate contract, fitted value comparator, actual optional MaskablePPO fit/save/reload and masked evaluation.
4. Model evaluation agent: broad universe collection design, football covariate ablations, probability/minutes evaluation, prospective comparisons and independent benchmark data preparation.

Agree shared schemas before implementation. RL must not train against an unstable replay or candidate contract. The fourth agent may switch to social benchmark work after the first learning release is integrated. Assign an independent reviewer after integration to inspect leakage, finances, scoring and unsupported performance claims.

Stage 1: verify and build the actual learning loop.
Run current locked checks and record exact results, including root CLI tests. Reproduce funding84/94/101/101, injury conditional scenarios, replay forcing horizon1 and the missing strict prediction-origin check. Preserve existing improvements. Inspect the actual current gameweek from fresh provider state; do not trust a fixed document date. Collection must not modify manager state. Private bank, FT, hits, selling quotes and chips remain unconfirmed until reviewed by the user.

Implement D02 through D04 completely:
Freeze forecasts, candidate menu, policy/model checksums and recommendations before deadlines. Distinguish recommended action from confirmed execution and a paper portfolio. Attach finalized official outcomes with revision lineage. Score frozen predictions before fitting on their labels. Review jobs are idempotent and recoverable.

Replace the GW1/GW2 training, GW3 validation, GW4 calibration, GW5 test literal with dynamic chronological folds generated from finalized available labels. Keep held out evaluation separate from a latest data serving refit. A new completed event must enter an eligible new fit without rewriting past evidence. Tiny data is honestly qualified, not silently relabelled as broad validation.

Replay must let a policy plan across supported H events, validate that full plan, execute only its first event, advance the financial ledger and replan on the next origin. Do not import later forecast snapshots into the earlier horizon. Strict mode checks actual prediction and artifact timing; reconstructed historical mode permits present fitting with honest simulated cutoffs and assumptions. Do not require impossible backdated artifact creation for a clearly labelled historical research experiment.

Ship a working local gameweek review command with capture, finalization status, journal scoring, challenger evaluation/refit and promotion/retention report. Add only essential UI controls for reviewing this evidence. Preserve baseline operation, opt in advanced selection, source gates and manual account execution.

Stage 2: build the RL research release rather than only writing a skeleton.
Implement domain accurate Gymnasium reset/step, seed behavior, season termination versus research truncation, observations containing only as of information, and a legal fixed size candidate slate with padding masks. Apply transfers, hits, free transfer inventory, chips, Free Hit restoration, autosubs and captain fallback through validated domain transitions.

Use points after hits as reward, subtract hits once, and include remaining events in state. No reward for crowd approval or a dashboard score. No future outcomes in candidate construction, observation, mask or policy accessible debug info. No exploration through my actual FPL team.

Implement a compact fitted value baseline and a genuine optional MaskablePPO challenger with mask aware rollout/inference/evaluation. Candidate identities change across states: use a shared candidate scorer and test permutation behavior. Do not assume standard MaskablePPO supports recurrent policies. Fit a compact authored environment smoke, save/reload, and demonstrate real parameter training with all synthetic evidence labelled. This establishes mechanics only.

Then run a substantive bounded experiment on available qualified historical/replay/simulation data. Check existing local data first; free permitted sources may be collected through validated adapters. Separate reconstructed history, simulation and prospective evidence. Use at least five seeds for the substantive comparison, common football paths/starting squads, fixed validation budget and untouched tests. Start with small CPU runs, record time and resources, and do not launch unlimited tuning. More trajectories from one season are not independent seasons.

If realistic coverage is insufficient, implement and verify the complete data adapter and training/evaluation path, run the qualified experiment that is possible, and record the precise limitation. Do not invent realistic prices, absent scoring statistics, social content or a winning RL score. Missing perfect historical provenance does not justify stopping all qualified development.

RL remains shadow unless evidence meets recorded promotion gates. Keep forecast champion and policy champion distinct. Bind the policy to rules, observation schema, candidate generator, forecast support and artifact checksums. A low RMSE alone does not prove better transfers. Evaluate the repaired planner versus new planner on identical forecasts, and PPO versus numerical/fitted value policies on identical candidate sets and outcomes.

Stage 3: season and social improvements.
Complete dynamic financial sequence optimisation and future chip scheduling together with validator changes. Add continuation value only for rewards after the scored horizon. Compare four/six/eight event sensitivity. Treat unknown recovery as scenarios; conditional fully available points cannot masquerade as unconditional expectation. Do not expand CatBoost support beyond one event until frozen multilead features and evaluation exist.

Improve social semantics on a reviewed benchmark: entity, action, conditional buy/sell/hold/captain, horizon, attribution, reports versus opinions, sarcasm and abstention. Keep experts and crowd separate; source reliability is topic and time specific. Live Reddit/X adapters stay disabled until access and permitted processing are configured. Social derived signals enter training only with explicit rights and a chronological ablation. No flat expert points bonus and no consensus reward for RL.

Release discipline:
Run tests meaningful to domain, provenance, learning and finances. Run locked backend/root/frontend checks, regenerate changed contracts, build, and verify actual API/worker/browser/save/reload/review flow in isolated data and ports. Do not overwrite occupied services or current manager state. Optional RL/TFT/Bayesian extras must not break baseline startup.

Maintain BUILD_STATUS, DECISIONS and a handoff with implemented/verified/unavailable states. Keep personal data and artifacts ignored. Do not submit transfers, chips, external messages, purchase data or deploy publicly. Prepare reviewable commits or a draft PR if appropriate, without merging it automatically.

Continue through the requested stages while checks and dependencies permit. Do not finish after a plan, a new Models card or tests of mocked predictions. Final response must state concrete changes, actual checks, real versus synthetic training, measured comparisons, whether anything was promoted, and remaining blockers. If a complex model loses, retain the simpler champion and report that honestly.
```

## Prompt after a gameweek

Use this with Codex once the learning release is implemented. Before it exists, ask Codex to complete the master prompt's Stage 1 first.

```text
Run the implemented FPL gameweek learning review in this checkout. Read AGENTS.md, BUILD_STATUS and the learning upgrade specifications. Use actual provider event status and finalized flags, not a hardcoded GW6 assumption.

Preserve my private manager state and existing services. Inspect frozen journal entries and collect fresh official sources through validated adapters. A current recommendation does not prove I executed it; use confirmed execution or label a paper portfolio. Missing confirmation stays unknown.

If the event is not finalized, report pending status, capture revisions appropriately and do not train on preliminary targets. If finalized, join official fixture outcomes to the forecasts and journal, verify coverage and scoring, and score the predictions before new fitting. Do not create a backdated forecast for a missed deadline. Preserve prior report revisions.

Report points/MAE/RMSE/bias, minutes/appearance calibration, decision points after hits, immediate legal counterfactuals and coverage limitations. Explain whether errors came from minutes, football rates, unavailable inputs or the planning policy. Do not explain random football outcomes as proof of a bad decision without comparison.

Create dynamic chronological challenger evaluations and an immutable current serving refit where supported. Compare the same forecast universes and strategy episodes. Keep policy and forecast champions separate. Run substantive RL updates only with suitable data and an explicit bounded training budget. Retain the champion if gates are not met. Do not tune repeatedly on the same test events.

Generate a next deadline four/six/eight event comparison only where frozen horizon forecasts support it. Show roll, transfer/hit alternatives, finances, captain/vice/bench, chip windows and contingent triggers. Unknown private finances block transfer budget claims. New gameweek inputs require my review; do not infer them from old values.

Produce a concise learning report with actual artifact references, what changed, checks performed, whether any model was promoted, and next review triggers. Save private reports under ignored docs/local and data as appropriate. Update build/handoff notes. No account actions, paid sources or external messages.
```

## Sources and evidence

Reviewed 12 October 2026. Repository findings are derived from pinned source and local synthetic probes. External implementation guidance uses primary sources. Proposed architecture and gates are recommendations, not claims that the repository already implements them.

### Repository

1. [Pinned repository](https://github.com/Sambhav255/fpl-agent/tree/840c1185d005270717c7453fb278dc30a03c05f3).
2. [Changes since previous audit](https://github.com/Sambhav255/fpl-agent/compare/e759bcfb299d3f818d2e80ebb017796874cf8019...840c1185d005270717c7453fb278dc30a03c05f3).
3. [Current build status](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/docs/BUILD_STATUS.md).
4. [Football CatBoost experiments](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/docs/experiments/CATBOOST_FOOTBALL.md). Reported metrics; ignored binary artifacts were not retrieved.
5. [Strategy replay](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/evaluation/strategy.py).
6. [Planner](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/optimisation/planner.py).
7. [Forecast router](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/models/router.py).
8. [Hosted verification](https://github.com/Sambhav255/fpl-agent/actions/runs/38207057987). Relevant checks succeeded; overall cleanup remained in progress at the recorded audit observation.

### Reinforcement learning

1. [Gymnasium environment tutorial](https://gymnasium.farama.org/introduction/create_custom_env/). Custom environment interfaces and explicit episode endings.
2. [Stable Baselines3 guidance](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html). Practical training and evaluation guidance; verify stable package versions when installing.
3. [MaskablePPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html). Mask aware evaluation utilities required; standard implementation does not support recurrent policies. This supports the proposed masked candidate policy mechanics, not an FPL performance claim.
4. [Competing with Humans at Fantasy Football](https://ojs.aaai.org/index.php/AAAI/article/view/8259). Research precedent for sequential team selection under partial observability. It is not a current 2026/27 FPL benchmark for this app.

### Forecasting research

1. [OpenFPL paper](https://arxiv.org/abs/2508.09992), [full text](https://arxiv.org/html/2508.09992v1). A useful public data forecasting benchmark candidate, with position specific ensembles and prospectively tested short horizons. Published author results are not independently reproduced here. Scoring era, source access, code licensing and data timestamp differences must be checked before implementation or comparison.
2. [Temporal Fusion Transformer paper](https://arxiv.org/abs/1912.09363). Supports the model family concept; the app still requires an implemented and evaluated multilead decoder.
3. [Sentence BERT paper](https://arxiv.org/abs/1908.10084). Supports semantic embedding comparison, not automatic FPL recommendation understanding.

### Official FPL and platform sources

1. [FPL API bootstrap](https://fantasy.premierleague.com/api/bootstrap-static/). Current event metadata and universe; future implementation must retain source bytes and observed timestamps.
2. [2026/27 FPL changes](https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627).
3. [2026/27 chip windows](https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627). Two chip sets and one chip per event; verify actual deadline timestamps from current official data.
4. [Official rules](https://fantasy.premierleague.com/en/help/rules). Retain verified rules evidence before changing domain transitions.
5. [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy). API approval and processing/training restrictions.
6. [X Developer Guidelines](https://docs.x.com/developer-guidelines), [X Developer Policy](https://docs.x.com/developer-terms/policy). Permitted access, ML restrictions and retained content requirements must be checked before enabling adapters.

No paper, vendor claim or social popularity measure proves that a complex model will improve this specific team's decisions. The new journal and policy evaluation are how that question becomes testable.
