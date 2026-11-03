# GW7 transfer and strategy handoff

Prepared 17 October 2026 UTC, late 16 October in Chicago. Owner: Sambhav. Reviewed public application commit `a3754b39f1a81b05a59b668bfdd363bb89d48d6d`.

## Priority

Produce a fresh, financially valid GW7 transfer recommendation for the actual confirmed team, with XI, captain, vice captain, bench, chip decision and a conditional longer plan. The Premier League currently states a deadline of Saturday 17 October at 11:00 BST: 10:00 UTC, 05:00 America/Chicago. Recheck the official provider on execution. If it has passed, do not manufacture a GW7 decision; move to the next legal event.

This is a deadline task. Do not spend tonight rebuilding models, enabling social ingestion, redesigning screens or installing AIrsenal. Use the existing working engine and repair the specific decision defect below. Research and richer source integration follow the decision.

## Latest application state

The previous prompt was substantially implemented. Read current `docs/CHATGPT_PROGRESS_REPORT.md`, `docs/BUILD_STATUS.md` and `docs/START_HERE.md` before older audits. Local changes after the pinned public commit may supersede this review.

1. Full 667 player collection and real current CatBoost/ensemble serving exist. The latest documented finalized collection is from 13 October, with 3,883 final fixture labels across GW1 through GW6. It is not fresh deadline day team news.
2. The documented two origin historical test reports CatBoost RMSE 2.1914 against reconstructed baseline 2.3841. Rolling comparators have lower MAE. This is narrow, assumed timing evidence, not a confirmed prospective advantage.
3. Current CatBoost supports one event. Longer current forecasts use the labelled conditional availability baseline. The historical eight lead CatBoost experiment has an older scoring regime and cannot silently become current live forecasts.
4. Complete Wildcard and Free Hit candidates, selling basis, financial sequence transitions and independent validation exist. Ordinary large catalogue sequence paths remain limited to two replacements per event.
5. Actual historical PPO research exists. Its retained short comparison reports 98 mean points against numerical/menu planner 101. Keep RL inactive for the deadline.
6. Prospective baseline capture, queued forecasts, journal freezing, seals and finalized outcome evaluation are automated. Existing journals are paper evidence; actual execution remains unknown unless separately confirmed.
7. Current private squad, selling quotes, bank, FT, committed hits and chips still require actual user review. Public research portfolios cannot supply those values.

Reported latest local verification is 464 base tests/11 skips, 480 RL tests/7 skips, 14 CLI tests and production browser 16/6 personal state skips. Those are repository recorded checks. The latest hosted run 38658276130 has successful backend, frontend/build and browser/persistence steps, but its final run conclusion is cancelled. Do not report a green completed workflow. This audit did not rerun the full application or inspect the Mac's services/private database.

## New decision defect: root action starvation

`backend/src/fpl_app/optimisation/sequence.py` performs recursive depth first search. `bounded_squads` yields keep first. `visit` recursively explores that branch's future moves before trying another current event squad. A finite node or time budget can therefore leave excellent current transfers unexamined.

This is not a hypothetical concern. A controlled test against the pinned actual source uses 80 players, four events, one free current transfer, no hits and a 100 edge budget. All inputs are synthetic. An incoming midfielder scores 25 each event versus owned players 4, costs the same and has no injury or club conflict.

| Plan | Four event points |
| --- | ---: |
| Keep | 192 |
| Sequence result | 234 |
| Legal buy now and hold | 360 |

The returned sequence keeps for three events and buys only in the fourth. Independent legal transitions confirm the immediate buy and hold path. The probe uses actual contracts, rules and sequence code; no functions are mocked and no provider/database is used. The 126 point gap is a software fixture, not a real FPL performance estimate. The deliberately small edge budget exposes traversal order, not the typical loss under production settings.

Repair before trusting a roll recommendation from a budget exhausted sequence search:

1. Seed the incumbent with Keep plus promising legal current transfers, funding pairs and supported chip candidates, each extended to a complete legal horizon.
2. Allocate coverage across distinct current actions before spending the whole budget inside one future subtree. Consider a budgeted frontier, best first search or root round robin with valid complete continuations.
3. Share one total compute deadline. Candidate generation, incumbent seeding and deeper search all count toward it. Preserve cancellation and a complete valid incumbent.
4. Record distinct current actions considered, root coverage limits, incumbent source, explored edges, elapsed time and optimality scope.
5. Preserve existing exact exhaustion behavior on small universes. A stronger heuristic does not create a global certificate.

Turn the included probe into a regression expecting the immediate buy and hold value to be found within its declared budget. Also test funding pairs, exclusion of injured candidates, delayed benefits, deadline exhaustion and independence from candidate ordering.

Until repaired and verified, compare both current bounded planner and sequence engine, plus explicitly scored immediate candidate continuations. A sequence roll from an unexplored root menu is not evidence that rolling is best.

## Deadline execution order

### 1. Locate the actual workspace

Check working tree, current instructions, processes, ports and DATA_DIR. Research previews3162/8162 and3163/8163 use isolated paper data. They are not automatically the user's personal environment. Preserve ignored data, notes, installed environments and running services. Use a reversible separate checkout for code changes where needed.

Read the current personal state through validated local interfaces. Identify whether it is still GW6, whether public picks are from the last deadline, and whether transfers have already been made for GW7. Do not overwrite current ownership with a fresh public import.

### 2. Reconcile only missing private facts

Required: all 15 current owned players, current selling values, bank, free transfers, transfers already made, committed hits, chip inventory and active chip. Use existing confirmed state only when it still applies. If any are missing, ask the user in one concise checklist or request their current transfer page screenshot. Continue independent data/news/lineup work while waiting.

Do not infer purchase prices from selling quotes or infer FT from public history. A plan with unconfirmed finances is conditional, not budget valid. Keep the event rollover review and version checks.

### 3. Refresh football evidence

Capture fresh official bootstrap/fixtures and owned player plus candidate histories. Reuse retained finalized GW1 through GW6 outcomes when hashes and schema are valid. Do not make the decision wait for an unnecessary complete archive download. A full new collection is fine when the existing paced collector and remaining time permit it.

Check current injuries, suspensions, recent starts/minutes, penalties and role changes using official FPL and current club/press conference reports. Record observed time, source and exact claim. Availability is not the same as a guaranteed start. Quote attribution matters. Do not use postdeadline lineups or rumours as if they were known earlier.

Use the fresh baseline and, when the immutable release path supports the current collection, the current one event CatBoost and mean ensemble as distinct comparisons. Do not bypass snapshot/manifest gates to reuse stale bundles. Do not pretend a simple average of different horizon providers is an evaluated ensemble.

### 4. Build the transfer matrix

Always include Keep/Roll, useful singles, legal funding pairs and relevant two move combinations. If several FTs are available, the ordinary sequence cap of two is a restriction: include feasible three or more move bundles through an appropriate candidate generator or disclose the omission. Do not silently waste available transfer options.

Compare zero new hits, then a four point hit only where justified; larger hits require an explicit case and user preference. Count committed hits separately, and subtract new hits once. A backup goalkeeper downgrade can fund a starting upgrade; do not rank all 15 equally outside Bench Boost.

For each first action compute:

1. GW7 net points and change versus Keep on the same forecast/provider.
2. Four, six and eight event net values where supported, with finances and FT paths.
3. Next event bank/FT, key upgrade routes and downside if the targeted player does not start.
4. Injury return and affordability scenarios, using no invented probability weights.
5. Horizon stability: does the first action win only because of one optimistic terminal or recovery assumption?

When comparing CatBoost and baseline, use the common one event scope/universe. For longer planning, show the conditional baseline separately. A hybrid with CatBoost first event and baseline later events is a new explicitly labelled experimental policy, not the validated ensemble. Only add it if time and evaluation support it.

### 5. Make the game plan concrete

Choose the recommended first action using net horizon value, confirmed affordability, role/minutes evidence and robustness. A roll is valid when it survives adequate current action search. If close, show two options and the fact that would change the choice.

Return exact sells/buys, remaining bank, FT next event, incremental hits, formation, XI, captain/vice and ordered bench. Explain why the vice is reliable enough to cover the captain and why bench order works under legal formations. Do not automatically suggest a low ownership differential without a rival objective.

Consider chip use as an opportunity cost decision. Triple Captain adds one extra captain score over normal captaincy, not three extra scores. Bench Boost adds reserve scores. Compare current opportunities with plausible remaining window options; do not play a chip merely because a full replacement candidate has high points.

Future actions are triggers rather than promises: e.g. preserve enough bank for a future captain route, sell only if minutes fall, or revisit a flagged player after confirmed return news. Derive affordability thresholds from actual integer finances.

### 6. Verify and freeze

Run targeted search/rules/financial tests after the repair. Independently validate every shortlisted plan and compare incumbent quality with the prechange engine on identical inputs. Broad checks can follow the first usable decision; do not make a valuable baseline report wait for optional Torch or a new data platform.

Before deadline recheck current prices, status, ownership and state version. Save the final report privately under `docs/local/GW7_DECISION_<timestamp>.md` and immutable input/plan references under ignored data. Freeze a new prospective journal after the final information changes and before the deadline. Preserve earlier journal versions and execution unknown status.

The existing `scripts/run_prospective_journal.py` queues a baseline forecast, caps current moves at two and uses default analysis settings. It does not by itself produce the whole decision matrix or prove the sequence repair was exercised. Inspect and choose the required settings explicitly. Confirm policy seals bind the exact algorithm/settings actually evaluated.

No account transfer, chip submission or claim of execution. Provide a manual action checklist for the user. After actual official finalization, score the chosen explicit revision before new fitting. Do not score GW7 outcomes in advance or delay a deadline decision until future results exist.

## Borrowing priority

Read `EXTERNAL_REPOSITORY_REVIEW.md`. For this deadline, borrow ideas rather than adopting a second stack. AIrsenal provides useful component/minutes/search references; Core Insights supplies optional player context after source and identity checks. Vaastav remains historical research data. The PHP tool's randomised form forecasts, its heuristic confidence/price probabilities and unrelated Java wrappers should not enter the decision engine.

## Completion standard

The work is complete when the actual user has a fresh legal recommendation with a reasoned game plan, the root search defect is fixed or clearly bypassed with independently scored alternatives, and the final predeadline inputs are frozen. Another benchmark dashboard or research portfolio alone does not complete this task.
