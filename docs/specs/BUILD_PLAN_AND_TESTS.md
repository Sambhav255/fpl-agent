# Build plan and acceptance tests

Build sequentially. Keep `docs/BUILD_STATUS.md` current. Every milestone records changed files, commands actually run, results, remaining limitations, and the next task. Do not report a command as passed if it was only suggested.

## Milestone 0: scaffold and reproducible demo

Create the web app, Python package, database migrations, configuration examples, job skeleton, and test tooling. Generate the frontend API types from OpenAPI. Resolve stable compatible versions and commit lockfiles.

Create a deterministic demo with enough players across clubs and positions to form several legal squads. Label it synthetic. Keep synthetic data physically and logically separate from live data. Use no network calls in the demo tests.

Acceptance: web and API start; health check passes; migration runs on an empty database; demo dashboard renders; root startup and shutdown instructions work; baseline tests and static checks pass.

## Milestone 1: rules and manager state

Implement integer money, legal squad checks, starting formations, selling prices, acquisition tracking, transfer transitions, and corrections with optimistic version checks. Implement current season rule configuration with verification metadata.

Acceptance: all money, squad, formation, and ordinary transfer tests below pass. Missing financial fields block transfer solving but permit valid lineup analysis. Demo state persists across restart.

## Milestone 2: source collection and public team import

Implement official FPL bootstrap, fixtures, player history, manager, picks, and history adapters. Fetch selected player histories without overwhelming the provider. Archive source payloads and fixture versions. Add URL parsing, readiness reports, correction UI, stale state handling, and manual refresh.

Acceptance: import one real public team; show source Gameweek; correct a recent transfer and financial state; survive an API failure using the last good snapshot; prevent arbitrary URL fetching; confirm that demo and live states never mix.

## Milestone 3: baseline projections and current week decisions

Build a dated feature pipeline, transparent baseline, projection store, lineup optimisation, captain and vice selection, bench ordering, and feasible single transfer comparison. Keep the six event display available where fixtures exist, but label the initial solver as limited to current week decisions.

Acceptance: Keep appears in every comparison; recommended actions are affordable and legal; displayed differences reconcile with calculations; projection provenance is visible; stale state is rejected; a saved recommendation reloads with the same forecast version.

This is the first useful personal release. Do not postpone it while waiting for three complex models.

## Milestone 4: historical audit and CatBoost

Audit source coverage, IDs, same fixture data leakage, potentially revised xP, zero minutes records, and feature availability. Implement chronological folds and baseline metrics. Train CatBoost and supporting availability models on real audited data.

Acceptance: no feature is available after its cutoff; a training run produces a reproducible artifact; held out metrics are recorded; activation is justified against the baseline; interface distinguishes trained, evaluated, and active status.

## Milestone 5: horizon planning

Extend the optimiser to a six event horizon with bank, purchase prices, transfer inventory, hits, and terminal value. Allow locks, exclusions, horizon changes, and a maximum additional hit budget. Show alternative transfer sequences.

Acceptance: saved transfer rollover, sell and rebuy, multiple moves, and already committed hits are correct; no artificial final week spending occurs in a controlled test; solver timeout returns a validated incumbent or an explicit no result.

## Milestone 6: Bayesian model and fuller simulation

Build the Bayesian event model, calibrated minutes states, shared match scenarios, automatic substitutions, and vice captain fallback. Add posterior diagnostics and partial component warnings.

Acceptance: scenario frequencies match expected probabilities within simulation error; players from one team share match conditions; bench legality holds in every sampled scenario; approximate bonus components are identified; uncertainty metrics are calibrated or unavailable.

## Milestone 7: TFT and ensemble

Implement the compact TFT pipeline, future covariate rules, masking, double fixtures, evaluation, and validated ensemble weights. Keep the deep dependency optional.

Acceptance: TFT trains on a small real panel; no future observed covariate leaks; means and quantiles retain their correct meaning; held out comparison is recorded; the ensemble can exclude a weak or missing model; inference works with reproducible artifacts.

## Milestone 8: chips and complete personal release

Implement chip windows, inventory, transition rules, and scenario evaluation. A chip requiring unavailable start of event state must be disabled with a useful explanation. Finish saved plans, history, exports, accessibility, backups, and recovery.

Acceptance: current official chip behaviour is verified; all chip tests pass; one complete demo and one real imported state reach a saved plan; the app gives a clear manual action list and submits no FPL changes.

## 1. Money tests

| Case | Expected result |
|---|---|
| Buy 75, market 78 | Sell 76 |
| Buy 75, market 76 | Sell 75 |
| Buy 75, market 79 | Sell 77 |
| Buy 75, market 74 | Sell 74 |
| Bank 5, sell 76, buy 81 | Bank 0 |
| Bank 5, sell 76, buy 82 | Reject as unaffordable |
| Sell and later rebuy | New acquisition price is used |
| Unknown acquisition and no confirmed sell price | Transfer solving blocked |
| Confirmed sell price from an old market snapshot | Recompute or require confirmation |

## 2. Squad and lineup tests

1. Exactly 15 unique eligible players and required positional counts.
2. Three players from a club allowed; four rejected for an ordinary resulting squad.
3. One goalkeeper, 3 DEF, 5 MID, 2 FWD is a legal XI.
4. One goalkeeper, 5 DEF, 4 MID, 1 FWD is a legal XI.
5. Two defenders or no forward is illegal.
6. Captain and vice are distinct starting players.
7. The goalkeeper substitute does not occupy an outfield bench slot.
8. A real world club transfer exception is explicitly reconciled.

## 3. Scoring tests

Use the verified season rule configuration. Test 0, 1, 59, 60, and 90 minutes; position dependent goal points; saves at 2, 3, 5, and 6; clean sheet eligibility; conceded goals at 1, 2, 3, and 4; penalty misses and saves; own goals; card combinations; and bonus ties.

For defensive contribution, a defender at 9 actions earns zero and at 10 earns two; at 20 earns two, not four. A midfielder or forward at 11 relevant actions earns zero and at 12 earns two. Recoveries contribute only under the correct position rule.

Check a player substituted after 60 minutes before a later concession, a player leaving before 60, and red card concession handling. Test the official rule for cards received without an appearance when evaluating automatic substitution eligibility; do not infer this rule from minutes alone.

Total points may be negative. Make sure scoring and forecast display can represent them.

## 4. Transfer tests

| Ordinary event start | Total moves | Total hit | Next event allowance |
|---|---:|---:|---:|
| 1 free transfer | 0 | 0 | 2 |
| 1 free transfer | 1 | 0 | 1 |
| 1 free transfer | 2 | 4 | 1 |
| 2 free transfers | 1 | 0 | 2 |
| 2 free transfers | 3 | 4 | 1 |
| 5 free transfers | 0 | 0 | 5 |
| 5 free transfers | 4 | 0 | 2 |

Test one move already made with an event start allowance of two: one further move has no hit and two further moves create a four point total hit. In a recommendation delta, already committed penalties appear in both comparable plans rather than being counted twice.

If a Wildcard is activated after ordinary transfers, verify that the appropriate penalties are cancelled. Track total event moves, not just the difference between the final and starting squads; a sell and rebuy may involve moves despite identical final ownership.

## 5. Chip tests

1. Chip availability matches the verified season windows.
2. Unused first window chips expire at the correct deadline.
3. One chip per event.
4. Consecutive Free Hits rejected, including across the window boundary.
5. Free Hit temporarily changes active ownership and restores persistent ownership next event.
6. Original acquisition records survive Free Hit.
7. Wildcard permanently changes ownership and acquisition records.
8. Saved free transfers follow the verified chip rule.
9. Bench Boost scores eligible bench players without duplicate counting through substitution logic.
10. Triple Captain applies the correct multiplier and eligible fallback.
11. A chip plan cannot run with unknown required inventory or restore state.

## 6. Automatic substitution tests

1. Missing goalkeeper uses only the reserve goalkeeper if eligible.
2. In a XI with three defenders, a missing defender cannot be replaced by a midfielder while leaving only two defenders.
3. If the first bench player would violate formation, a later legal player may enter.
4. Multiple missing players produce a legal XI with the official priority order.
5. A one minute cameo prevents the ordinary no appearance substitution.
6. A captain missing both fixtures of a double allows eligible vice fallback; appearing in either fixture prevents that fallback.
7. Neither captain nor vice eligible means no captain multiplier.
8. Same club competing goalkeepers have linked appearances in the scenario model.

## 7. Data and leakage tests

1. Every feature record has a decision cutoff and source reference.
2. A future dated source cannot enter an earlier feature join.
3. Same fixture minutes and points cannot be features for its forecast.
4. A double's second fixture cannot use the first fixture's outcome at the original deadline.
5. End of season roles and injury flags are excluded from earlier decisions.
6. Historic xP is excluded by default.
7. Fixture reassignment uses the version known at the deadline.
8. Overlapping future targets do not cross validation partitions.
9. Scalers and imputers are fitted on training data only.
10. Missing statistics are distinguishable from genuine zeros.
11. No duplicate player fixture rows.
12. A new provider schema fails clearly and preserves the prior good data.

## 8. Job, state, and interface tests

Test duplicate requests, worker crash and expired lease recovery, cancellation, conflicting state edits, source outage, partial import, invalid team URL, stale projection, absent optional model, and reload after saving.

Use a small offline integration dataset to verify the full path: import response, correction, feature build, projection, recommendation, validation, persistence, and reload. Add a separate optional live provider check; normal CI should not depend on FPL uptime.

The interface must show the source Gameweek, unknown finances, data timestamps, active model, approximation labels, and errors. Cover keyboard use, table accessibility, mobile width, and long player names. Never show demo data as the user's imported squad.

## 9. Evaluation and activation

Record MAE, RMSE, ranking quality, appearance calibration, threshold calibration, and interval coverage where relevant. Measure recommendations using realised net points, captaincy, hit usage, and legal state transitions. Use consistent starting states and Gameweek blocked uncertainty estimates.

Promote a model only after it improves a defined validation objective without unexplained calibration failures. Compare once on the untouched test period. If no advanced model beats the baseline, report that honestly and keep the baseline active while investigating.

## 10. Definition of done

1. Relevant domain tests and integration flow pass.
2. Static checks and interface build pass.
3. Every reported test was actually run.
4. Database migrations and restart persistence work.
5. No secrets or personal state in Git.
6. Data and model limitations are visible.
7. Documentation matches the commands and schemas actually implemented.
8. The milestone has a short reviewable change summary and an updated build status.

The complete product additionally requires the three genuine model implementations, their evaluation records, the advanced planning engine, and verified chip handling. Completing the baseline milestone alone is not completing the whole project.
