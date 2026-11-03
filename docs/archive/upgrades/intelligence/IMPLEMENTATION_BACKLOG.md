# Implementation backlog

Date: 10 October 2026. Implement against the current checkout after comparing it with audited commit `e759bcfb299d3f818d2e80ebb017796874cf8019`. Do not rebuild the application or overwrite ongoing work.

## Delivery policy

Prioritise data, forecasting and decision quality. Freeze cosmetic improvements except small changes needed to expose real model provenance, decisions and evidence. Each milestone must produce executable behaviour and a report. Documentation or a training function alone is not completion.

Advance independent work when another track is blocked. If a model fails to improve measured results, keep it as a challenger, record the result, and continue improving the planner and other models. Do not manufacture a winning benchmark.

## First release: useful intelligence

### B01. Lock in the reproduced search regression

Priority P0. Owner: optimisation.

Port `verification/audit_probes.py` into the existing pytest suite. The funding pair test should initially demonstrate the current miss. Keep the 84, 94 and 101 fixture values explicitly synthetic. Add an exact enumerator for small squad universes with transfer caps and legal formations.

Acceptance: the new planner finds the legal 101 point plan in this fixture, with two free transfers, correct money, zero extra hits and independent replay. The benchmark distinguishes proxy optimality from plan optimality.

### B02. Correct the optimisation objective

Priority P0. Owner: optimisation.

Replace or supplement the 15 player proxy with ownership, starting lineup and captain variables. Include exact funding bundles and multi event financial transitions. Keep the existing planner available as a named comparator.

Acceptance: small one and two event universes match exact enumeration. Tests cover a funding move, delayed benefit, roll, free transfer cap, future chip date and Free Hit restoration. Larger runs retain legal incumbents and report true bounds or an explicit unavailable gap.

### B03. Start prospective collection and historical audit

Priority P0. Owner: data.

Implement a command and worker job that captures current football versions and deadline forecasts. Normalise element histories and fixtures. Build a source coverage report, canonical mappings and a versioned label panel. Pin historical source versions rather than fetching a floating branch in a supposedly reproducible experiment.

Acceptance: a real retained sample includes checksum references, event deadlines, player mappings, scheduled exposures and revision state. The audit reports unknown timing honestly. Collection produces actual before deadline snapshots when run at those times. No made up verified bundle is accepted.

### B04. Train and evaluate the first football aware CatBoost model

Priority P0. Owner: modelling.

Add fixture, club, role, minutes and rule era features. Use chronological folds and a broader final evaluation. Support a labelled historical experiment on incomplete archive timing and prospective shadow forecasts. Preserve a separate default promotion decision.

Acceptance: a real data artifact reloads, generates current origin forecasts and produces reproducible comparisons against declared baselines. Report lead time, appearance and positional results and uncertainty. If performance is worse, the result stays visible and the baseline stays champion.

### B05. Wire model selection into the worker

Priority P0. Owner: integration.

Add a provider router, common artifact eligibility checks and immutable job references. Separate experimental opt in use from default champion promotion. A real trained challenger may serve future forecasts only under its honest evaluation label and with data actually available at the live origin. It must not claim retrospective deadline deployment.

Acceptance: two suitable test providers produce different projection jobs; an advanced live data artifact can be selected when its declared mode permits it; missing or incompatible artifacts fail clearly; retries resolve the same artifact; inactive Models badges cannot contradict the worker.

### B06. Build strategy replay

Priority P0. Owner: evaluation.

Implement policies for frozen Keep, refreshed greedy transfers, current planner and new planner. Evolve manager state and score actual outcomes. Compare planners on identical forecasts before comparing forecast families.

Acceptance: a reproducible report contains realised points after hits, coverage assumptions, multiple starting squads, paired differences and legality. Future snapshots and target outcomes cannot enter actions. Unknown historical financial inputs downgrade the replay claim instead of being silently filled.

## Second release: long horizon football strategy

### B07. Calibrate minutes and availability

Priority P1. Owner: modelling.

Fit appearance, starts and minute distributions, including recovery scenarios. Validate the 60 minute threshold and unusual zero minute scoring cases where the source defines them. Apply current probabilities only to the scope they describe.

Acceptance: next event absence does not mechanically imply eight events of absence. Recovery assumptions remain uncertain and sourced. Minutes metrics and reliability curves are stored on held out and prospective forecasts.

### B08. Preserve joint scenarios and full scoring

Priority P1. Owner: Bayesian modelling and integration.

Complete Bayesian scoring or add calibrated residual components. Persist common outcome draws and score legal substitutions, captain fallback and bench boost through the existing rules engine.

Acceptance: calibrated distributions are checked against full point labels. Partial scoring is never relabelled complete. Scenario IDs remain aligned across players and plans. Saved reports can reproduce simulation results and disclose Monte Carlo error.

### B09. Value future choices and chips

Priority P1. Owner: optimisation.

Add continuation rollouts, horizon sensitivity, future chip dates, diverse alternative plans and scenario reranking. Separate the next eight event detailed policy from the remaining window chip roadmap.

Acceptance: reported current actions are consistent across unrevealed scenarios. Tests include horizon reversals, preserving an upgrade route, chip expiration and price affordability. Show conditional future actions rather than an unqualified fixed schedule.

## Parallel social track

### B10. Build source capabilities and offline extraction

Priority P1. Owner: social intelligence.

Implement disabled official adapters, capability records, manual source registry, permitted retention, synthetic fixtures, semantic player and stance extraction, evidence family clustering and separate expert/crowd aggregation.

Acceptance: no credentials or no approval means unavailable, not fake consensus. Extraction tests include quotes, negation, funding pairs, jokes, multiple players and conditions. Entity precision target is measured on adjudicated held out fixtures. Deletions invalidate derived content.

### B11. Activate permitted analytics and validate influence

Priority P1 for descriptive analytics, P2 for model influence. Owner: social intelligence and evaluation.

Enable only sources whose access covers the exact use case. Keep cost caps, source sampling metadata and role reviews. Fit no weights or football features from restricted content without permission covering that training.

Acceptance: source links, role evidence, distinct author counts and coverage are inspectable. Descriptive opinion is separate from football probabilities. Any forecast influence has a separately measured permitted ablation and no double counting of official news.

## Third release: all three forecast families compared

### B12. Complete TFT and eligible ensemble

Priority P2. Owner: modelling.

Implement a genuine decoder across the supported event horizon, categorical football covariates, stored best checkpoints and proper missingness. Compare against the already working CatBoost and Bayesian models. Fit ensemble weights on development forecasts only.

Acceptance: all three families have genuine training and evaluation reports or a concrete external blocker. The app can serve the strongest eligible family or ensemble. Final evaluation is separate from weight fitting. A weak TFT is not included in the default merely because it is advanced.

## Parallel ownership plan for Cursor and Codex

| Role | Owns | Dependencies |
| --- | --- | --- |
| Lead | Shared schemas, migrations, lockfiles, API contracts, router integration, release reports | Establish contracts before worker edits |
| Data agent | Provider extensions, panels, collection, source audit and mappings | Existing storage contracts |
| Model agent | Features agreed with data agent, minutes, model training and forecast evaluation | Audited panel interfaces |
| Optimisation agent | Exact small oracle, MILP, continuation and policy evaluation | Forecast and manager state contracts |
| Social agent | Source registry, disabled adapters, extraction, evidence and consensus | Approved capability schema; live access not required for offline implementation |
| Reviewer, after integration | Independent review and acceptance evidence | Completed integrated changes |

Use at most four implementation subagents concurrently plus the lead, subject to client limits. Assign precise file ownership or isolated worktrees. Shared files are changed by the lead. The model and data agents must agree on feature ownership before parallel editing. Do not solve coordination conflicts by deleting another agent's work.

## Required handoff evidence

Each completed milestone includes changed files, actually executed checks, real versus synthetic data status, reproducible artifact or report references, measured limitations and the exact next action. Store current state in `docs/BUILD_STATUS.md` and experiments in a separate results index.

Run the project's normal checks and focused domain, serving, leakage and strategy tests. Optional training installation tests do not substitute for the real evaluation report. Preserve the user’s local database and private corrections.

## First command to give Codex

Use `CODEX_EXECUTION_PROMPT.md`. The lead should inspect the actual current branch, reproduce B01, establish contracts, and delegate B02, B03, B04 and B10 where their dependencies allow it. Complete B05 and B06 before treating the first intelligence release as done.
