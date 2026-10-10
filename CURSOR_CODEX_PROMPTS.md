# Cursor and Codex prompts

Place AGENTS.md in the project root and the other files in `docs`. Start the interactive coding agent from that project root. Use one prompt at a time. These prompts request implementation, not another research report.

## First prompt: scaffold the project

```text
Build my personal Fantasy Premier League assistant from the specifications in this repository.

First read AGENTS.md and docs/README.md, docs/FPL_PRD.md, docs/TECH_STACK_AND_ARCHITECTURE.md, docs/DATA_AND_MODEL_SPEC.md, and docs/BUILD_PLAN_AND_TESTS.md.

Implement Milestone 0 completely. Use the specified Next.js and TypeScript interface, Python FastAPI backend, SQLite persistence, and a recoverable worker skeleton. Resolve compatible stable dependency versions and commit the lockfiles to the repository files. Keep Bayesian and TFT dependencies optional.

Create a runnable offline demo with clearly labelled synthetic players and a valid squad. Make sure demo data cannot be mistaken for a real team import or a trained model. Add a functional dashboard shell, typed API client, health route, initial migration, environment examples, test tooling, and startup instructions. Use a readable football pitch plus an accessible table, clean typography, and restrained colour.

Create docs/BUILD_STATUS.md and docs/DECISIONS.md. Record assumptions and any changes from the proposed contracts. Do the implementation and run the milestone checks. Do not stop after a plan. Do not claim advanced models are trained, add an OpenAI API integration, or attempt automatic FPL transfers.

Finish with exact local startup commands, checks actually run, and the next milestone. Scope this first task to Milestone 0.
```

## Continue with rules and manager state

```text
Read AGENTS.md and docs/BUILD_STATUS.md. Implement Milestone 1 from docs/BUILD_PLAN_AND_TESTS.md.

Prioritise integer money, acquisition prices, selling prices, squad and formation validation, current season rule configuration, ordinary free transfer transitions, already committed hits, explicit unknown values, and optimistic state versions. Add the manager state correction flow to the interface.

Use the documented contract and update it if implementation exposes an inconsistency. Add and run the money, squad, formation, and ordinary transfer tests. Leave incomplete chip support disabled and labelled. Update the build status with actual results and remaining work.
```

## Add live data and team import

```text
Implement Milestone 2. Read the provider and timing contracts before coding.

Probe the required public FPL endpoints, validate and archive responses, add conservative caching and retries, and build public team ID import with clear source Gameweek information. Parse official team URLs into IDs instead of fetching arbitrary URLs.

Show bank, free transfers, selling prices, and chips as unknown unless verified or confirmed. Let me correct recent changes. Retain the last good data on provider failure. Use mocks for normal tests and record one separate live read check if the provider is accessible.

Keep private account sync deferred. Update docs/BUILD_STATUS.md with what works and what still requires user confirmation in the app.
```

## Deliver the first useful recommendations

```text
Implement Milestone 3: dated features, a transparent baseline forecast, starting XI, captain and vice captain, bench order, and feasible single transfer recommendations.

Include Keep in every comparison. Check current selling prices, free transfers, already made moves, incremental hits, positions, and club limits. Independently validate solver outputs. Show model type, forecast timestamp, approximations, and missing information.

Persist saved plans with their exact input and forecast versions. Add an offline complete flow test from import and correction through recommendation and reload. Do not use fabricated CatBoost, Bayesian, or TFT predictions. Update the build status.
```

## Train CatBoost properly

```text
Implement Milestone 4. Audit the historical data and feature availability before training.

Keep training and validation chronological. Exclude same fixture outcomes and unverified historical xP. Represent zero minutes and missing records correctly. Train CatBoost and supporting appearance or minutes models using recorded dataset versions. Store seeds, cutoff, features, dependency versions, artifact hash, and evaluation metrics.

Compare against the existing baseline on unseen periods and by position and horizon. Activate CatBoost only with an honest documented justification. If data access is blocked, implement the pipeline and report the precise untrained status rather than fabricating results.
```

## Add six Gameweek planning

```text
Implement Milestone 5. Extend planning across six events with evolving ownership, bank, acquisition records, free transfers, transfer penalties, and a tested terminal value.

Support locks, exclusions, horizon selection, and a maximum additional hit budget. Include saving transfers. Return alternatives, weekly actions, incremental gains, and solver status. Do not count already committed penalties twice. Preserve the original state and projections for saved plans.

Run the transition and affordability tests plus an integration case involving several weeks. Update the build status.
```

## Add Bayesian events and simulation

```text
Implement Milestone 6 with the optional PyMC environment. Build the hierarchical football event model and a coherent scenario evaluator for shared match outcomes, minutes, clean sheets, attacking returns, defensive thresholds, automatic substitutions, and captain fallback.

Show convergence and predictive diagnostics. Label unavailable event details and approximate bonus scoring. Do not sum marginal quantiles to calculate squad quantiles. Validate the simulator on small controlled cases and compare forecasts against the baseline and CatBoost on unseen dates.

Keep the normal application usable without the Bayesian extra. Record true training and validation status.
```

## Add TFT and the ensemble

```text
Implement Milestone 7 with optional deep learning dependencies. Build a compact global TFT with historical observed variables and genuinely known future fixture variables. Handle blanks and multiple fixtures explicitly.

Do not use future realised minutes or injury information as future inputs. Keep mean forecasts distinct from quantile outputs. Train, evaluate, and register a genuine model artifact. Learn ensemble weights only on uncontaminated validation forecasts; allow zero weight for a weak model.

Compare the ensemble against the best individual model, record calibration and runtime, and update the model status screen. Do not replace honest unavailable outputs with synthetic predictions.
```

## Add chips and complete the personal app

```text
Implement Milestone 8. Verify current official chip windows and state transitions before enabling recommendations. Support the correct Wildcard, Free Hit, Bench Boost, and Triple Captain effects, including acquisition records, restored persistent squads, saved transfers, and consecutive Free Hit restrictions.

Finish saved plan history, readable exports, accessibility, backups, worker recovery, and an action list that I execute manually in FPL. Run the chip tests and complete offline flow. Clearly distinguish partial transfer replay from a complete historical strategy evaluation.

Update the documentation to match the implementation and report any remaining gaps against the complete product definition.
```

## Codex review prompt

```text
Review the current implementation against AGENTS.md and the specifications. First inspect docs/BUILD_STATUS.md.

Focus on financial and chip state transitions, public import limitations, future data leakage, appearance probability handling, Double Gameweeks, legal automatic substitutions, fabricated model status, job recovery, and frontend/backend contract drift.

Identify concrete issues with file references and reproducible examples. Fix clear correctness defects within the current scope and run meaningful checks. Keep unrelated user changes. Separate verified problems from hypotheses and state any checks that could not run.
```

## Resuming after a pause

```text
Read AGENTS.md, docs/BUILD_STATUS.md, and the relevant specifications. Inspect the repository state. Continue the next incomplete milestone without rebuilding completed work. Verify the existing app still runs before extending it. Update status with actual checks and remaining limitations.
```

## Practical usage

1. Begin in Cursor with the first prompt, or run `codex` in the project root and paste it there.
2. Use the same project documents in both tools.
3. Hand off after the current stage is checked and the build status is updated.
4. Keep each task scoped enough that you can review its output.
5. Once the baseline app works, add real models sequentially and insist on evaluation evidence.
