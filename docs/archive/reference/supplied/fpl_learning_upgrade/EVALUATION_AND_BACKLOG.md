# Evaluation gates and implementation backlog

This plan prioritises learning infrastructure and decision quality. User interface changes are limited to essential review and evidence controls.

## Ordered milestones

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

## Mechanics acceptance tests

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

## Forecast evaluation

Compare baseline, rolling points/minutes, position/club shrinkage and every challenger on the same covered origin/player/fixture universe. A selected player model is evaluated as selected coverage, not the whole league. Report fixture and event point RMSE, MAE and bias, appearance/start/60 minute Brier or log loss, minutes error, quantile loss and empirical coverage when available.

Report lead specific performance for every supported horizon; position, expected starter, rotation, new player, price band, blank/double and scoring era subgroups. Subgroups use information available at the forecast origin. A subgroup selected using realized future high scores is a retrospective diagnostic only.

Report mean versus median differences honestly. Do not add marginal quantiles to create event or squad quantiles. Evaluate distribution claims using valid joint simulations or explicit aggregate calibration.

Use event or season blocks for uncertainty, retaining match/player dependence. A 30 row player sample is not 30 independent weeks. Keep all tuning and ensemble weights out of final test data. Report effective covered events and limitations rather than hiding them behind a large row count.

## Strategy evaluation matrix

| Question | Hold fixed | Compare |
| --- | --- | --- |
| Does the planner improve? | Same forecast runs and football outcomes | Current proxy, repaired planner, full sequence planner |
| Do forecasts improve actions? | Same planner/candidate rules | Baseline versus football challengers |
| Does RL improve decisions? | Same forecast provider, candidate menu and episodes | Greedy, roll/keep, numerical planner, fitted value, PPO |
| Does future value help? | Same horizon and inputs | Unfitted tiebreak versus fitted continuation |
| Does social help? | Same legal source rights and origins | Football only versus permitted social features |

Compare cumulative net points, paired incremental points, per event gains, cumulative additional hits, chip use, remaining transfers, budget failures, legality, latency and sensitivity. Include conservative downside measures and worst event clusters. Raw FPL rank is secondary unless complete field data and a defined rival objective exist.

Common starting squads do not create independent seasons. Common random paths reduce comparison noise. Report both episode distribution and the number of distinct actual or simulated season paths. A hindsight exact oracle is an upper bound diagnostic, not a deployable baseline.

## Promotion rules

Before tuning, register a minimum meaningful strategy gain, an allowed downside tolerance, acceptable latency and legality requirements. Initial research default: five training seeds, zero invalid accepted actions, paired evaluation against the current planner, and a conservative confidence interval for incremental points. Five seeds is an engineering minimum, not a claim of statistical sufficiency.

Mechanics must all pass. Required evidence must bind the exact artifact and its observation/candidate/schema/rule versions. Mean improvement alone is insufficient if downside or coverage is materially worse. A lower confidence bound above the registered improvement threshold is a strong research gate, but sparse prospective gameweeks can remain inconclusive. Do not weaken gates just to activate RL.

A reconstructed historical win supports research selection; a simulator win supports simulation evidence. Neither alone proves a live edge. Shadow candidates may run immediately with honest labels and no account actions. Promotion stays unavailable when evidence is insufficient, while useful journal, calibration and planning upgrades still ship.

Prevent repeated test peeking: select hyperparameters on development/validation, freeze them, evaluate the test once, then begin a new forward monitoring period. Record every candidate attempted and retain failed experiments. A winning seed picked after inspecting test scores is not the policy result.

## Actual repository checks

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

## Ownership for implementation agents

The lead owns shared contracts, migrations, lockfiles, API/jobs, router, generated types and integration. One agent owns journal/outcomes/folds. Another owns strategy replay/finance/optimisation. Another owns the environment/policy models. Another owns football feature/evaluation or social scope, depending on the active milestone. An independent reviewer examines leakage, financial validity and evidence claims after integration.

Separate worktrees and nonoverlapping file ownership are required for concurrent editing. Use bounded native agent concurrency supported by the installed Codex runtime, with at most four implementation agents at once. If unavailable, execute the same scopes sequentially. An agent cannot edit a shared file without lead coordination.
