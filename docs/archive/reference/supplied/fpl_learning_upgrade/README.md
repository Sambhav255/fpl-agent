# FPL learning upgrade

Prepared for Sambhav on 12 October 2026. Reviewed repository commit `840c1185d005270717c7453fb278dc30a03c05f3`.

The app has improved substantially since the first audit. It now needs a reliable learning and evaluation loop, stronger season planning and an experimental reinforcement learning policy. A new dashboard is not the next milestone.

## Read and execute

1. Read [LATEST_REPOSITORY_AUDIT.md](LATEST_REPOSITORY_AUDIT.md) for what is fixed, what remains incomplete and what was verified.
2. Read [PRD_V3.md](PRD_V3.md) for product requirements and the gameweek workflow.
3. Read [RL_AND_LEARNING_SPEC.md](RL_AND_LEARNING_SPEC.md) for forecast updates, the simulator, the RL policy and the retained technology stack.
4. Read [EVALUATION_AND_BACKLOG.md](EVALUATION_AND_BACKLOG.md) for implementation order, tests and promotion gates.
5. Paste [CODEX_MASTER_PROMPT.md](CODEX_MASTER_PROMPT.md) into Codex in your existing repository. It directs implementation agents to work in separate worktrees with one integration owner.
6. After a gameweek, use [GAMEWEEK_REVIEW_PROMPT.md](GAMEWEEK_REVIEW_PROMPT.md). This runs the learning process; it does not automatically make the model better.
7. Use [SOCIAL_NEXT_STAGE.md](SOCIAL_NEXT_STAGE.md) for semantic extraction and source reliability improvements.

Copy this directory into `docs/learning_upgrade/`. Preserve the previous specifications and existing user changes. The master prompt treats this as an incremental upgrade and compares the checkout with the audited commit before editing.

## What this package changes

The previous upgrade connected an experimental model and improved candidate generation. This package adds a prospective decision journal, finalized outcome ingestion, dynamic chronological evaluation, a separately fitted current serving artifact, a genuine receding horizon replay, financial transitions, a Gymnasium environment and an RL challenger.

The recommended RL design selects among legal action candidates and learns future value. The rules engine and numerical optimiser still enforce squad legality and finances. Learning does not mean gambling away free transfers to gather training data.

Thirty remaining gameweeks would be a short learning history for one manager. Player forecasts can learn from many football observations, but strategy performance still has only a small number of shared gameweek outcomes. Historical and simulated episodes provide research data; genuinely prospective results provide a separate check.

The retained collection in the repository reports GW6 current, GW7 next, with the next deadline at 17 October 2026, 10:00 UTC. GW6 labels were preliminary at capture. There are 32 numbered events from GW7 to GW38 inclusive, assuming the normal 38 event season. The application must derive current status from the provider and finalization flags instead of hardcoding this document's dates.

## Verification limits

Hosted verification stages for the reviewed commit passed backend, frontend, browser and persistence checks when inspected. Workflow cleanup was still running at the last recorded check. The repository records 292 backend tests plus 13 root CLI tests and 16 browser tests; those recorded counts were not independently rerun here.

Local audit checks parsed 78 retrieved Python files and executed the synthetic probes in [verification/latest_probes.py](verification/latest_probes.py). The audit runtime lacks the full locked dependencies. The probe substituted only the storage checksum and clock functions; actual contracts, rules, solver and replay ran. This is not API, database, training or personal team verification. The result file records the exact scope.

No repository code, manager state, account transfer or chip action was changed by this audit.
