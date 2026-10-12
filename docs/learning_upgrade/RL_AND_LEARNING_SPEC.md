# RL and continual learning specification

This is a proposed implementation, not a description of a trained model currently in the repository. It extends the existing Python engine and preserves model evidence gates.

## Separate the learning problems

| Component | Learns | Feedback | First implementation |
| --- | --- | --- | --- |
| Football forecast | Minutes, appearances, point distributions and team strength | Finalized player fixture outcomes | CatBoost refits and calibration; Bayesian state updates |
| Strategy value | Future value of transfers, money, ownership and chips | Complete replay/simulation returns | Fitted state/action value and terminal continuation model |
| RL policy | Which legal action candidate to take | Sequential points after hits | Optional MaskablePPO challenger |
| Social evidence | Entity/action extraction and source reliability | Reviewed labels and resolved factual claims | Semantic benchmark and shrinkage estimates |

Refitting CatBoost after each event is continual supervised learning. A policy trained to maximise sequential rewards is reinforcement learning. Updating an explanation prompt is neither. Keep those names and artifacts distinct.

Six manager decisions provide little evidence about a strategy policy. They do not become hundreds of independent decisions by multiplying them by 15 players. Player outcomes provide many labels, but shared matches and events create dependence. Simulation expands the research state space while inheriting the simulator's mistakes.

## Retained and added technology

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

## The prospective learning loop

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

### Proposed journal contract

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

## Fix fitting and validation

Replace the fixed partition literal in `train_collection_experiment` with a declared fold generator. Generate folds from available finalized events and actual or explicitly assumed label times. Stop if timing purges empty a partition. Do not move test events into development merely to make a fit succeed.

Use expanding development windows and later validation/calibration/test blocks where coverage allows. For the earliest season stages, record insufficient data for broad evaluation and use historical research plus current prospective shadows. Later predictions can use earlier test period results when those outcomes were actually available, but a fixed fitted model cannot learn the test targets during its frozen test run.

There are two artifact types:

1. Evaluation artifact: fit without its held out labels, used to estimate performance under recorded cutoffs.
2. Serving refit: after evaluation is finished, fit using all finalized labels available now, with its own actual completion time and future origin. It inherits method evidence, not the old artifact's identical fitted parameters or checksum.

The serving refit records the selected method, configuration, evaluation links and differences from evaluated models. Changing features, universe or heads invalidates automatic inheritance of evaluation support. A just completed GW5 evaluation cannot justify a latest refit whose configuration was selected by examining future outcomes.

Begin with a limited, registered feature ablation sequence: lag statistics, then fixture/strength covariates, then minutes/role/congestion, then permitted advanced event metrics. Current club and opponent IDs do not alone encode team strength. Fit team strength with shrinkage from earlier matches; preserve posterior uncertainty. Cross season identity and scoring era must be explicit.

Probability heads should use suitable binary losses where practical, coherent nesting, and separately fitted calibration. A probability of playing 60 minutes cannot exceed appearance probability. A minutes mixture distinguishes no appearance, substitute minutes and starts. Expected points are unconditional; never multiply a direct unconditional mean by availability again.

Calibrated distribution or conformal methods require chronological held out residuals and an explicit dependence/drift limitation. Until calibration works, leave uncertainty unavailable. A nominal interval with 31.4 percent empirical coverage is not an 80 percent confidence statement.

## Genuine receding horizon replay

At origin t, expose only observations available by t and the forecast path produced at t. Let the policy plan H events, capped by remaining events and actual provider support. Validate all H proposed weeks using the same settings and exact input fingerprint. Execute only week one. At t+1, reveal the newly available snapshot and outcomes, update the financial ledger, and plan again.

Do not take the second week's forecast from a later `ReplayOrigin` and pretend it existed in the earlier run. If the earlier run supports one event, the experiment is a one event experiment. Full horizons require frozen multilead forecasts built at that earlier origin.

Create distinct provenance modes:

1. Prospective strict: source, forecast and policy artifacts existed before the actual origin and deadline. Check hashes and actual timestamps.
2. Historical reconstructed: fitting may occur today, but simulated observation and fitting label cutoffs are honoured. Mark timing, memberships, prices and feature uncertainties.
3. Synthetic mechanics: authored outcomes for rules tests.
4. Generative simulation: outcomes sampled from a fitted world model with recorded assumptions.

Reject future prediction origins in strict mode. Do not falsely require an artifact trained today to have existed years ago for a clearly labelled retrospective research fit. A historical reconstruction cannot become a prospective performance claim.

Replay must represent current prices and purchase basis. If the initial purchase price is unknown, a recorded confirmed selling quote works only within its actual market anchor; a future price path requires an explicit assumption or known basis. Separate frozen price, reconstructed price and prospectively observed financial modes. A changed historical quote must not silently infer purchase cost.

## Environment definition

FPL strategy is partially observed: true player fitness, selection and future fixtures are not fully known. Start with a finite season belief/state representation rather than claiming perfect Markov information.

One environment step is one event. Observation contains normalized bank/transfer inventory, owned player and acquisition data, chip flags/windows, remaining events, as of fixture path, forecast means and supported uncertainty, availability evidence and missingness. It also contains a fixed size candidate feature matrix and validity mask.

The environment owns hidden realized or sampled football outcomes. Neither observations, policy accessible `info`, action masks nor candidate ranking may depend on those future outcomes. Reveal prior football results only after their recorded availability time. Player IDs are season scoped metadata, not a universal numerical ordering of talent.

`reset(seed, options)` chooses an admissible starting squad, season segment and a hidden replay/simulation path. `step(action)` independently validates the selected current action, applies transfers/chip, scores XI/autosubs/vice fallback, subtracts hits once, restores Free Hit when due and advances to the next origin.

Natural season end returns `terminated=true`. A research time or data budget boundary returns `truncated=true` with correct bootstrapping handling. Missing observations must not masquerade as a completed season. No hidden access to results through debug fields in training or serving.

### Candidate action space

Start with `Discrete(K)`, K=32 as an initial implementation default. Each valid slot is a current event transfer/chip/lineup plan; unused slots are masked. Candidate provenance, ordering and hashes are frozen. Slot zero is a legal roll/keep option when normal decision readiness holds. Unknown live finances do not get replaced with a synthetic feasible transfer action.

Generate candidates from the optimiser and deterministic diverse templates: singles, funding pairs, roll, injury scenarios, limited hits and available chips. Independent validation comes before admission. Avoid 32 variations of the same single transfer. Log truncation and exact small universe recall.

A candidate represents only a first action, with future forecast summary features. Deduplicate identical first actions even if proposed future paths differ, and record the alternative continuations. Rank cannot refer to realized future points. Chip availability and affordability masks are computed only from the current state and declared scenario.

Because candidate slots change meaning between states, use a shared candidate encoder that scores state context plus each candidate's features, with invariant pooled context and masked logits. A plain fixed action index network can learn accidental slot meaning. Test that permuting candidates permutes policy probabilities and preserves the selected semantic action, apart from genuine ties. Preserve mask use in rollout collection, inference and evaluation.

SB3 Contrib documents that MaskablePPO requires its mask aware evaluation utilities and does not support recurrent policies. Do not combine its standard implementation with an LSTM policy and assume it works. Start with explicit current belief features and a compact shared scorer. Use custom policy methods compatible with the pinned masked distribution and value head.

## Reward and RL training

Base reward is squad event points after hits. Subtract total event hits once from realized points; committed hits are common to alternatives but still part of the portfolio total. Do not subtract the same hit again through an additional reward penalty. Free Hit restoration, free transfer retention and chip expiry affect future rewards through transitions.

Use finite season returns with gamma=1 as the primary objective, including events remaining in state. Evaluate gamma sensitivity only as a declared modelling variant. Reward scaling may help training, but reported performance is always raw points. Do not add arbitrary rewards for expert agreement, bank balance, follower popularity or using advanced models.

Potential based shaping can be a separate controlled experiment with an explicit terminal potential of zero. Rewarding each retained transfer while also learning its future value can double count flexibility. A horizon terminal continuation term is `V(state_after_H, remaining_events)` and must estimate only rewards after the scored H events.

Build a fitted value or fitted Q baseline first, then a genuine PPO fit. Teacher plans can initialize candidate/value models when produced from available forecasts. A hindsight best squad is a diagnostic upper bound, not a teacher that may access future actual points at live origins.

Historical player football outcomes are mostly exogenous to one fantasy manager's choices. With sufficient coverage, alternative legal actions can be scored immediately on the same event results. This does not reconstruct the entire alternative future without simulating its evolving squad, prices, inventory and later decisions. Replaying the same completed event thousands of times is not independent validation. Do not claim standard logged policy importance weighting when action propensities and support are absent.

For substantive PPO experiments, freeze data partitions and simulator versions, train at least five seeds, tune only on development/validation, and compare against the current policy on the same hidden paths and starting squads. Save checkpoints and optimizers for training reproducibility; live artifacts are immutable copies. Warm starts across events remain challengers and must pass the same tests.

## World model and simulator validity

Provide deterministic historical replay first. Add a generative world model with shared team goals/clean sheets, minutes, appearance, player scoring components and calendar/price scenarios. Current Bayesian samples are not yet a complete calibrated world model. Complete or explicitly qualify missing components before calling a simulation realistic.

Preserve correlations when scoring plans. Two defenders from the same club share clean sheet risk; double fixture outcomes are aggregated under event scoring and substitutions. Scenario identity is common across compared actions and policies.

Simulator stress tests include excessive hits, repeated chip use, profitable impossible price cycles, injured player optimism, missing fixtures, misleading uncertainty and artificial season cutoff effects. If RL exploits any of these, repair the world model and invalidate the affected experiment. Increasing episode count cannot fix an incorrect reward model.

The short term fallback is clearly labelled frozen price and conditional availability research, paired with a few robust scenario endpoints. It permits environment and policy mechanics work now. It cannot justify automatic live promotion until evaluation supports the relevant assumptions.

## Deployment and learning controls

Separate football champion and strategy champion registries. A policy promotion binds forecast family/version, candidate generator, observation schema, rules, simulator/evaluation evidence and policy checksum. Changing the candidate generator can invalidate an otherwise unchanged policy.

Modes: research, shadow, explicit experiment, active champion, disabled. Baseline/planner failure fallback is visible and separately labelled, never an RL result. Invalid actions are rejected before any state write. Stop experiment serving when required inputs, coverage or versions change.

Weekly review can create challengers automatically, but default replacement follows recorded predefined gates. No claim of monotonically increasing quality. Preserve a last valid champion for rollback. A failed model update should leave the app usable.
