# FPL product requirements

Version: 1.0. Date: 9 October 2026. Working name: FPL Assistant.

## 1. Product outcome

Help Sambhav make better Fantasy Premier League decisions by combining player forecasts with the exact constraints of his squad. Recommend transfers, starting XI, captain, vice captain, bench order, and chip scenarios. Explain expected benefits, uncertainty, and the assumptions behind each recommendation.

The default objective is maximum expected FPL points over the next six Gameweeks after transfer penalties. A separate competitive mode may later target the probability of beating a particular mini league rival.

This product covers the standard FPL game. It does not cover FPL Draft, FPL Challenge, American football, or daily fantasy contests.

## 2. User and product defaults

1. One personal user in the first release.
2. Free data in the initial build.
3. Local application with persisted data.
4. Recommendations are advisory. The user makes changes on the official FPL website.
5. Team ID import with corrections for information unavailable publicly.
6. Six Gameweeks as the default horizon, adjustable from one to eight.
7. Current points maximisation as the default mode.
8. Desktop first, with a readable mobile layout.
9. No paid subscriptions, commercial deployment, or account integration required to deliver the first useful release.

## 3. Problems to solve

| Problem | Required outcome |
|---|---|
| A points ranking ignores my squad | Recommendations account for bank, selling prices, positions, and club limits |
| A transfer looks good for one week | Compare its effect across the planning horizon |
| A player may not start | Display appearance and minutes probabilities |
| I have already changed my squad | Let me correct the imported public squad before solving |
| The model suggests too many moves | Account for hits, saved transfers, and the value of flexibility |
| The recommendation is a mystery | Explain the relevant fixtures, minutes, and scoring components |
| A beautiful backtest may use future data | Show the information cutoff and record forecasts before deadlines |

## 4. Functional scope

### P0: first useful release

1. Fetch and archive official player, fixture, and event data.
2. Import a squad using a numeric team ID or a valid official Points page URL.
3. Show the import Gameweek and distinguish it from the upcoming Gameweek.
4. Correct players, bank, free transfers, selling prices, captaincy, bench, and chip availability.
5. Validate a 15 player squad and persist it locally.
6. Generate a labelled baseline forecast for the available fixtures.
7. Recommend starting XI, captain, vice captain, and bench order.
8. Compare keeping the team with feasible single transfers.
9. Show projected points before and after a hit, where applicable.
10. Save alternative plans without submitting anything to FPL.
11. Provide an offline demo and meaningful empty, error, loading, and stale states.

### P1: complete personal decision tool

1. Train and evaluate CatBoost, Bayesian, and TFT model families.
2. Publish comparable forecasts through one common projection contract.
3. Use validated ensemble weights when they improve performance.
4. Solve sequences of transfers across several Gameweeks.
5. Simulate automatic substitutions, vice captain fallback, and shared match outcomes.
6. Evaluate Wildcard, Free Hit, Bench Boost, and Triple Captain scenarios.
7. Allow player locks, exclusions, minutes overrides, and a maximum number of hits.
8. Show model disagreement and sensitivity to assumptions.
9. Maintain a log of forecasts, recommendations, outcomes, and evaluation runs.

### P2: optional extensions

1. Exact current squad sync through a verified session based method or browser extension.
2. Timestamped news extraction and reviewed availability updates.
3. Mini league tracking and explicit chasing or defending objectives.
4. Price movement scenarios using available official information.
5. Hosted access with authentication and backups.
6. Licensed event or expected lineup data if free data proves insufficient.

## 5. Explicit exclusions

The initial product does not place transfers, scrape commercial projections behind a paywall, require an LLM API key, promise a rank improvement, or claim three models are trained when they are placeholders. Live whole game rank reconstruction, detailed Opta heatmaps, payments, and a mobile app are outside the first release.

## 6. Main user flow

1. Open the app and see the next FPL deadline with a data timestamp.
2. Enter a team ID or load the demo.
3. Review the imported public squad and its source Gameweek.
4. Confirm current players, financial information, transfers already made, and chips.
5. Resolve any missing selling prices or unknown free transfers.
6. Run analysis for the selected horizon.
7. Compare Keep, Best single move, Best combination, and chip scenarios where supported.
8. Inspect projected benefit, downside, assumptions, and alternative plans.
9. Save a plan and receive a plain list of actions to perform manually in FPL.

Lineup analysis can run with unknown financial information. Transfer recommendations must remain blocked until bank, free transfers, and relevant selling prices are confirmed.

## 7. Screen requirements

| Route | Content |
|---|---|
| `/` | Imported squad, next deadline, readiness, suggested lineup, recommendation summary |
| `/players` | Searchable projections table, position and price filters, fixture details |
| `/planner` | Squad by Gameweek, transfer actions, bank, free transfers, captain, chips |
| `/models` | Active forecast, model availability, validation metrics, disagreement |
| `/history` | Saved plans, published forecasts, realised results |
| `/settings` | Team import, manager state corrections, refresh, overrides, export, delete local state |

Use a football pitch view for the lineup and an accessible table showing the same information. Position meaning must remain clear without relying on colour. Use keyboard accessible controls and visible loading indicators. Show money in millions but store integer tenths internally.

A player card should show name, club, FPL position, price, projected points, upcoming fixtures, minutes assumption, and availability warning. Do not imply decimal projections are precise outcomes.

## 8. Recommendation contract

Every recommendation must identify:

1. Current manager state and its version.
2. Data snapshot and forecast version.
3. Deadline and forecast horizon.
4. Players entering and leaving.
5. Bank and free transfers after the actions.
6. This week and horizon points relative to the Keep plan.
7. Gross improvement, total transfer penalty, and incremental penalty relative to Keep.
8. Formation, captain, vice captain, and bench order.
9. Chip and its effect, if any.
10. Major assumptions, data gaps, and model disagreement.
11. Scenario statistics when a calibrated simulator exists.
12. Solver status, time limit, and optimality gap where available.

Explain differences using stored calculations. If a transfer is mainly valuable because it enables another move, say so. If several plans are effectively tied relative to model uncertainty, present them as alternatives.

Do not manufacture a confidence percentage by mapping a score to a percentage. Before probabilistic calibration is available, display uncertainty as unavailable and show concrete sensitivity cases.

## 9. Season rules

Facts below are based on the official 2026/27 material cited in SOURCES.md. Verify the current live rules and configuration when implementing. Store the rule version and verification timestamp.

| Constraint | Rule |
|---|---|
| Initial budget | 1000 units, where one unit is £0.1m |
| Squad | 2 GK, 5 DEF, 5 MID, 3 FWD |
| Starting XI | 11; 1 GK; at least 3 DEF, 2 MID, 1 FWD |
| Club limit | At most 3 players from one club, subject to official handling of real club transfers |
| Captain | Starting player; double points; eligible vice captain fallback |
| Free transfers | One ordinary allowance per Gameweek, up to five stored |
| Extra transfers | Four points per transfer above the available allowance |
| Ordinary limit | Up to 20 transfers in one Gameweek; chip exceptions |
| Chips | Two sets of Wildcard, Free Hit, Bench Boost, Triple Captain |
| First chip window | Through the Gameweek 19 deadline in this season |
| Free Hit | Temporary squad; cannot be played in consecutive Gameweeks |
| Wildcard and Free Hit | Preserve saved transfers under the current rules |

An imported squad with more than three players at a club due to a real world transfer must be identified as a special state. Verify the official transfer restriction and require a compliant resulting squad before recommending moves. Do not silently remove a player.

### Fantasy scoring matrix

| Event | Points |
|---|---:|
| Appearance below 60 minutes | 1 |
| Appearance at least 60 minutes | 2 |
| Goal by GK / DEF / MID / FWD | 10 / 6 / 5 / 4 |
| FPL assist | 3 |
| Clean sheet by GK or DEF / MID | 4 / 1 |
| Every three goalkeeper saves | 1 |
| Penalty save | 5 |
| Penalty miss | Minus 2 |
| Every two conceded goals by GK or DEF | Minus 1 |
| Yellow / red card | Minus 1 / minus 3 |
| Own goal | Minus 2 |
| Match bonus | 1, 2, or 3, with official tie handling |
| Defensive contribution threshold | 2 per fixture, without stacking |

Defenders need 10 combined clearances, blocks, interceptions, and tackles. Midfielders and forwards need 12, including recoveries. Clean sheets require the applicable 60 minute eligibility and concession conditions. Verify assist and card edge cases against the full official rules rather than treating this matrix as an exhaustive scorer.

Defensive contribution points, revised bonus scoring, assist definitions, clean sheet eligibility, red card handling, and finalisation timing must be modelled or explicitly marked approximate. Automatic substitutions must preserve legal formation.

## 10. Correctness and reliability requirements

1. No illegal recommendation passes final validation.
2. No unknown bank or selling price is treated as zero or current market value.
3. No stale plan is silently recalculated against a different manager state.
4. No forecast uses an observation first available after its stated cutoff.
5. A public import is labelled as public deadline data.
6. Provider outages do not delete the last good snapshot.
7. Importing a different team does not mix its financial state with the previous team.
8. Pending jobs survive an API restart and can recover from a worker failure.
9. All model outputs show their availability: baseline, trained, evaluated, disabled, or unavailable.
10. Real observations and synthetic demo data are clearly separated.

## 11. Product success and release gates

Correctness is a release requirement. Better predictive performance is an empirical goal.

For the first release, a recorded demo and one real public import must complete the flow from import to saved valid recommendation. The demo must work without network access after setup. The user must be able to inspect and correct every input that affects affordability.

For the modelling release, require chronological held out evaluation and publication of errors by position, appearance status, and horizon. A new model must justify activation against baseline forecasts. The ensemble may give a model zero weight if it adds no value.

For the advanced planning release, require replay tests for prices, hits, free transfer rollover, chip boundaries, temporary Free Hit state, and automatic substitutions. Compare net outcomes against consistent baseline policies using the same starting state.

## 12. Outstanding product choices

Keep the defaults unless the user changes them. Later decisions include a paid data budget, public hosting, exact account sync, and a mini league target. None blocks the initial local build.
