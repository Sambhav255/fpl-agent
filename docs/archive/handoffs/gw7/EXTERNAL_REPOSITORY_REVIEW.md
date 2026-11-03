# External repository review

Reviewed 17 October 2026 UTC. Six repositories and the supplied Java topic page were inspected. Source snapshots are pinned below. Code and data were read, not installed or executed. No external project's performance claims were independently reproduced.

## Recommendation at a glance

| Source | Best use | Deadline priority | Adoption decision |
| --- | --- | --- | --- |
| AIrsenal | Football point components, minutes/availability, transfer plan search and baseline comparison | Highest code reference | Selectively adapt after tests; do not install its full stack tonight |
| FPL Core Insights | xG/xA, defensive actions, minutes/roles, competition workload and team strength context | Useful optional evidence | Add a source adapter after identity/timing/rights checks; keep official data authoritative |
| Vaastav | Historical labels, fixture/player histories, reproducible archive experiments | Already partly used | Keep historical use; not a live weekly source |
| Prasann62 fpl analizer | Comparison/report presentation and sampled manager ownership | Low | Do not adopt its prediction/confidence/price algorithms |
| niciac FantasyTool | Simple endpoint inventory and raw collection examples | Low | Existing application collection is already stronger |
| javaidb premier league insights | Understat/FPL joins, player exploration and sampled manager comparisons | Later research | Reimplement useful concepts with explicit IDs; do not copy unlicensed files |
| Java topic page | API wrapper discovery | None for deadline | No Java migration or ML component identified |

## 1. AIrsenal

Repository: https://github.com/alan-turing-institute/AIrsenal

Reviewed commit: `f39ca752efc469f5301952f1c8de430d1b31317d`, 16 October 2026. Root `LICENSE` is MIT. Preserve copyright/licence notices for copied or adapted substantial code and record exact upstream commit/file in an attribution register. Source data access is a separate question.

The current tree is AIrsenal v2. Old online paths under `framework` are not the correct references for this snapshot. Its current files separate models, point components, minutes, squad scoring and transfer strategies.

### Useful model references

1. `src/airsenal/prediction/team_models/xg.py`: opponent adjusted attack/defence estimation from earlier team xG. This is a useful challenger to arbitrary FDR multipliers, particularly for defensive value. Fit and validate on the same local chronological folds; do not copy upstream default parameters as proof of calibration.
2. `src/airsenal/prediction/player_models/xg.py`: shrunk player goal/assist involvement shares. Useful for the eventual complete Bayesian/component model; preserve source xG definition and minutes exposure.
3. `src/airsenal/prediction/minutes_models/recent.py` and `minutes.py`: explicit minutes distributions, availability known at the root event, expected return event and history fallback. The root/fixture event distinction is useful for preventing future injury leakage.
4. `src/airsenal/prediction/point_components/empirical_bayes.py` and `def_con.py`: position priors and threshold based defensive contribution points, separated by appearance length. Evaluate expected threshold crossing rather than adding a raw count to points.
5. `docs/xg-models.md`: an example of documenting tests, rejected ideas and minutes limitations. The report identifies new signings with no usable history as a weakness. Do not copy a zero minutes fallback for every new player.

These changes belong in a tested challenger. Direct total points CatBoost and PPG already incorporate components through their targets. Adding a new defensive contribution or saves bonus to them without reconciling the existing target can double count.

### Useful planning references

`src/airsenal/optimization/transfer_optimizers/tree_search.py`, `moves.py` and `plan.py` separate move counts/chips, free transfer inventory, hits and a complete plan's value. `plan.py` constructs a Keep comparator with the same scoring assumptions as the alternatives. `strategies/single.py` and `double.py` provide targeted move proposal references.

Adapt the distinction between a strategy schedule and the candidate squad search; it makes comparing Roll, one move, a funding pair and future moves clearer. It does not remove the need for fair current action budget coverage in our engine.

### Do not copy blindly

1. `next_gameweek_transfers` can omit zero moves at the FT cap unless `allow_unused_transfers` is enabled. Upstream separately restores a baseline. Keep/Roll must remain available in our tool even when retaining five FT yields no new transfer.
2. `squad_score.py` defaults to geometric discount 14/15 and can weight substitutes. Our objective defaults to undiscounted net points; discounting is a sensitivity experiment. Bench weights are a proxy, not exact expected automatic substitutions.
3. The double transfer proposer contains an early `break` in the inner incoming loop. It proposes useful pairs but must not be described as a full exact enumeration of all pair outcomes under every nonlinear squad objective.
4. Recent minutes are an empirical sample, not a calibrated start classifier. Its docs describe rotation and new signing limitations.
5. The component documentation leaves own goals, saved penalties and missed penalties unpredicted. It is not a complete stochastic FPL scoring simulator merely because it has many components.
6. The project has account apply commands and clean database commands. They are outside this task. Do not run them or share a database/environment with the personal app.

Best action tonight: use the modelling and search decomposition as review references. Repair and compare our own existing planner first. Do not spend the deadline installing JAX, its database and a parallel account workflow.

## 2. FPL Core Insights

Repository: https://github.com/olbauday/FPL-Core-Insights

Reviewed commit: `174d22b32badeac7c6d329fdc1d20e0276919b9a`, 17 October 2026. README explicitly invites data use and requests attribution, but no standalone licence file was found in the retrieved tree. Preserve source attribution and check upstream data terms and permitted use before redistribution or training. Public CSV access is not a substitute for checking field provenance.

This is the most useful additional data candidate. It links FPL IDs with player match xG/xA, shots, defensive actions, minutes, fixtures and club Elo. Nonleague matches can provide workload and role context. It is not a transfer optimiser or a pretrained point forecast service.

### Evidence actually inspected

1. The 2026/27 GW6 `playermatchstats.csv` sample has FPL player IDs, match keys, authoritative `minutes_played`, xG/xA, tackles, clearances, interceptions, recoveries and defensive contributions among its fields. Some sampled nonappearance rows have null statistics; null remains unknown/inapplicable rather than a zero event.
2. The 2026/27 GW7 `playermatchstats.csv` is header only at the pin. A GW7 directory does not imply completed GW7 outcomes. Do not train on or invent rows from it.
3. `scripts/clean_playermatchstats.py` implements explicit handling for phantom appearances, player club mismatches and timelines that contradict minutes. Those are useful validation ideas.
4. `DATA_INTEGRATION_REVIEW.md` describes extensive quality work for 2025/26 Premier League data. Its counts are the maintainer's report, not a full independent audit here. They do not certify 2026/27 or every nonleague competition.
5. The workflow schedules exports at 07:30, 15:30 and 23:30 UTC. README says two daily refreshes with different hours. Use actual commit and capture times, not the README schedule, for freshness.

### Integration design

Pin the commit, save bytes/hash and actual observed time, then map by season and FPL ID. Use tournament plus match key and provider/player identity to avoid cross competition joins. Validate club, opponent, kickoff, duplicates, numeric ranges and availability. A match ID is not automatically an official FPL fixture ID.

Keep source columns distinct: official FPL xG, external summary xG, shot model xG, xGOT and ClubElo are different measures. Never silently add them together. The review explicitly documents differences between summary and shot xG. Match finishing time and missingness control lag eligibility.

Prefer canonical Premier League tournament rows for league targets. Do not concatenate the same rows again from `By Gameweek`; they are alternate projections. Cup/friendly data may inform fatigue, not league target points, and coverage is partial.

`playerstats` is cumulative. `player_gameweek_stats` differences may include source corrections/resets. Do not repeatedly sum cumulative values or assume every negative difference is impossible. Verify actual semantics from exporter code. End of gameweek snapshots are not demonstrated predeadline snapshots; historical availability must remain assumed unless proved by retained evidence.

The reviewed integration deliberately excludes raw API provenance/capture columns and leaves parts of collection private. Its exporter uses the maintainer's Supabase credentials. Consume allowed published files; do not assume the repository is a complete self hosted collector or request their secrets.

Best action tonight: optionally inspect lagged GW6 and earlier context for the owned players and short list after identity checks. Use it as a sourced comparison/watchlist. A new feature based model requires testing after the deadline.

## 3. Vaastav historical dataset

Repository: https://github.com/vaastav/Fantasy-Premier-League

Reviewed commit: `9779cdbc0c07f6c900c2d0c181ddf6bb9c800f88`, 28 August 2026. The licence text is MIT for software and separately notes that data belongs to FPL/Understat. The GitHub licence metadata reports NOASSERTION; reading the actual text matters.

Keep using its historical season/player/fixture labels and data dictionary. The user's app already uses a pinned2024/25 archive, so this is not a new modelling breakthrough.

README says weekly updates ended after 2024/25 and describes three later seasonal updates. It is unsuitable as the live GW7 injury, price or form source. It also warns that unshifted `xP` may be collected after results and leak information. Prefer exclusion for the strict model unless exact field availability is proved; shifting alone is not a complete timestamp audit. Cross season player IDs and current memberships require mapping.

Best action tonight: retain already validated archive data. Do not replace live official capture with this repository or start rebuilding the archive.

## 4. Prasann62 fpl analizer

Repository: https://github.com/Prasann62/fpl-analizer

Reviewed commit: `a62747796367fc1fbe60f8b5dddb7c2ddb8cba53`, 2 February 2026. Root licence is MIT. Source is a PHP/JavaScript toolkit; the app's Python/TypeScript stack need not change.

There are useful presentation concepts: separate comparison choices, fixture tickers and sampled manager ownership. They are lower priority than the working decision engine.

The named AI outputs are not evidence of advanced learned forecasts:

1. `ai-team-point-predictor.php` multiplies form by an FDR factor and then randomises it with `Math.random()` in roughly0.8 to1.2. It also gives an absent fixture a neutral difficulty instead of establishing a blank. Do not copy.
2. `ai-team-improver.php` mixes form/PPG and fixture factors. Its confidence is a weighted form/fixture/ownership score, not a calibrated probability.
3. `price-predictor.php` assigns rise/fall percentages using hand chosen transfer count thresholds. It is not a validated market probability forecast.

Do not turn that confidence meter into our plan success probability or its popularity score into player expected points. Research interfaces can be polished while the numbers underneath remain heuristics.

## 5. niciac FantasyTool

Repository: https://github.com/niciac/FantasyTool

Reviewed commit: `287f5fb594c29a29f38d8bcdc33304520a7feeec`, 25 September 2026. No licence file was found in the retrieved tree. Read concepts; do not transplant source without permission/licence clarity.

README inventories bootstrap, fixtures, player summary and live event endpoints. `src/api_data_fetcher.py` illustrates raw fetching/storage; `processing.py` is a very small JSON loader with an old example path. The user's app already provides stronger snapshot, validation, pacing, revision and worker features. No useful trained transfer model was identified in the inspected files. Its price site reader is not a reason to add an unapproved scrape dependency tonight.

## 6. javaidb premier league insights

Repository: https://github.com/javaidb/premier-league-insights

Reviewed commit: `5f4bab0c3176fa74be405b67be880161077b5d47`, 31 January 2025. No licence file was found in the retrieved tree. The README's certificate badge is not a software licence.

Useful ideas are FPL/Understat joins, fixture/form exploration and a selected manager group for comparative ownership. `src/functions/data_builder.py` contains the cross source assembly; `data_analysis.py` contains prospect ranking and beacon ownership analysis. A selected manager group is descriptive evidence, not unbiased expert consensus or calibrated xP.

Reimplement cross source concepts with explicit IDs, season mappings, reviewed ambiguous names and source timestamps. Do not silently accept best fuzzy name matches. No deadline ready superior learned transfer policy was established by these scripts. No stack migration or notebook dependency is needed for the personal app.

## 7. Java topic directory

The supplied URL is a filtered discovery page, not another dataset or optimiser. At retrieval it showed `kelanyll/FPLWrapper` and `jamoamo/jfpl`, described as Java FPL API wrappers. These listings add no demonstrated forecasting or transfer search advantage. Python/TypeScript ingestion already exists. No adoption needed.

## Follow up backlog after the decision

1. Review an AIrsenal inspired opponent adjusted xG/component challenger and calibrated minutes model against the same folds and policy replay.
2. Add a Core Insights source adapter with pinned bytes, duplicate projections, source namespacing and missingness tests.
3. Test position shrinkage for saves/cards/defensive contribution without double counting direct total points targets.
4. Evaluate opponent adjusted role/minutes and cross competition workload features prospectively.
5. Maintain an attribution register for any MIT code adapted. Reuse no unlicensed source by default.

The best reusable asset is a tested modelling or data idea. Copying a repository wholesale is unnecessary and can weaken the user's stronger provenance and financial safeguards.
