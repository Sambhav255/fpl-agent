# FPL strategy assistant PRD v2

Owner: Sambhav. Date: 10 October 2026. Basis: repository audit at commit `e759bcfb299d3f818d2e80ebb017796874cf8019`.

## Product decision

Build a personal FPL decision system that improves forecasting, transfers and the overall game plan. Preserve the existing application and prioritise intelligence and measurable decision quality. This document updates the modelling, planning, evaluation and social scope of the original PRD. Existing rules, state integrity and manual execution requirements remain applicable.

The three forecast families remain CatBoost, Bayesian football events and TFT. Implement and compare all three. Deploy the best eligible individual model or subset ensemble. Do not require a weak model to be included merely to reach a count of three.

## Primary outcome

Before a deadline, the user receives a legal immediate action, an explained plan across upcoming events, conditional future actions, captain and bench decisions, chip opportunities, and separate summaries of expert opinion and crowd consensus. Every forecast and plan carries its source, timing, evidence quality and limitations.

The main objective is expected FPL points after hits. Optional modes assess downside or a specific mini league objective. Popularity, account follower counts and general positive sentiment do not directly become expected points.

## Scope by horizon

| Horizon | Purpose | Required output |
| --- | --- | --- |
| Current deadline | Concrete decision | Roll or transfer, exact costs, lineup, captain, vice captain, bench and timing |
| Next eight events | Detailed planning | Transfers by event, bank and free transfer paths, net value and contingencies |
| Next eight to twelve events | Strategic watchlist | Fixture turns, potential restructuring and uncertainty; twelve event solving is an extension requiring contract and forecast support |
| Remaining chip windows | Macro strategy | Candidate Wildcard, Free Hit, Bench Boost and Triple Captain windows with calendar scenarios |

A future transfer is a contingent proposal. Recompute after new information. Do not present a fixed path as a promise that the same player will remain best in six weeks.

## Users and core questions

The first user is Sambhav managing one standard FPL team. Support an imported deadline squad plus manually confirmed current state. The product should answer:

1. Should I roll, use one transfer, use a funding pair, or take a hit?
2. Is the current event favourite still best over the whole horizon?
3. Which transfer preserves an upgrade route to a future captain?
4. What changes if an injury, rotation risk, price move or fixture postponement occurs?
5. Where should my chips fit into the current window?
6. What do credible football sources, FPL analysts and the sampled crowd agree or disagree about?
7. Does the social evidence add useful information beyond football statistics?

## Functional requirements

### Forecasting

F01. Produce a frozen forecast for each eligible player and scheduled fixture, plus event totals. Include unconditional expected points, expected minutes, appearance probability, start probability, 60 minute probability and uncertainty when calibrated.

F02. Model opponent and club strengths, venue, recent and longer performance, role and set pieces, minutes trends, congestion, season scoring regime, and event specific availability. Add xG and xA only through a source with suitable access and timestamp evidence.

F03. Make model lifecycle explicit: implemented, trained, retrospectively evaluated, shadow, eligible, active, disabled. The active model must be the one actually used by the worker. Identify model artifact, feature version and mappings in every result.

F04. Support an approximate baseline and independent simple comparators. Optional model failures must not fabricate a successful advanced forecast.

F05. Provide calibrated joint scenarios for risk calculations and nonlinear squad scoring. Marginal point quantiles alone do not justify a probability that one plan beats another.

### Transfer and strategy engine

P01. Optimise ownership, starting lineup, captaincy, transfers and finances across events. Correct the reproduced funding pair failure.

P02. Compare Keep, Roll, best immediate action, best horizon policy, and meaningful alternatives. Separate additional hits from already committed hits.

P03. Value free transfer inventory and future flexibility beyond a final tie break. Compare longer horizons and terminal policies to expose horizon artefacts.

P04. Search multiple transfer bundles and chip dates. Include future chip actions rather than restricting chips to the first event. Independently replay every returned plan.

P05. Compare scenario distributions using the same simulated football outcomes for all plans. Include legal automatic substitutions and vice captain fallback.

P06. Return triggers such as “buy only if start probability exceeds the validated threshold” or “this route requires the price to stay below £X”. Derive thresholds from the planner, not invented text.

P07. Compare waiting for information with making an early transfer under price and availability uncertainty. If a reliable price forecast is absent, show affordability scenarios rather than an asserted rise probability.

P08. Keep strong current financial gates. If money is unknown, provide lineup advice and clearly conditional affordability information, without labelling a transfer budget valid.

### Social intelligence

S01. Add approved Reddit and official X ingestion adapters. Access and spending remain disabled until configured. The baseline and football models work without either provider.

S02. Resolve posts to player IDs, action, topic, event horizon, certainty and evidence. Distinguish factual reports from opinions, questions, jokes, team reveals and copied claims.

S03. Separate official football information, specialist club reporters, FPL analysts, established FPL managers and the ordinary crowd. Membership of a source category is reviewed and versioned, never inferred solely from popularity.

S04. Rank sources within their expertise using past verifiable claims and uncertainty. A football injury reporter and a good FPL manager have different areas of expertise.

S05. Show independent expert and crowd summaries for buy, sell, hold, captain and avoid stances. Include coverage, distinct authors, effective sample size, disagreement and source recency. These describe sampled sources, not all FPL managers.

S06. Collapse copied articles and repeated rumours into one evidence family. Cross platform amplification does not create independent confirmation.

S07. Initially use social information as an explanatory layer and a watchlist trigger. Enable quantified forecast changes only after source permissions, calibration and prospective evaluation support them.

S08. Missing or stale social coverage remains unavailable. It does not become neutral sentiment.

### Evaluation and explanations

E01. Freeze all features by the forecast origin and separate fitting, model selection, ensemble fitting and final evaluation periods.

E02. Compare both forecast accuracy and realised strategy points after hits. Evaluate multiple starting squads and seasons or scoring regimes with explicit coverage limitations.

E03. Explain the numerical decision using football components, minutes, hits, opportunity cost and uncertainty. A language model may summarise structured outputs but must not select players or invent probabilities.

E04. Keep a prospective deadline journal that records predictions and recommendations before results. Reproduce each report from immutable input references.

## Decision report contract

| Section | Content |
| --- | --- |
| Immediate action | Exact transfers or roll, costs, hits and current squad legality |
| Horizon comparison | Expected incremental points against each named comparator |
| Conditional plan | Future route, alternative branch and invalidation triggers |
| Team selection | Legal formation, captain, vice captain, bench priority |
| Chip strategy | Marginal value of spending versus preserving each available chip |
| Football evidence | Minutes and scoring drivers, fixture effects, data coverage |
| Expert view | Reviewed source category, stance, evidence and disagreement |
| Crowd view | Sample scope, stance, breadth, recency and uncertainty |
| Model confidence | Eligible model, validation status, horizon support and distribution status |
| Timing | Forecast origin, source cutoffs, stale conditions and refresh instructions |

Use an explicit unavailable state for any section whose evidence is insufficient. Example figures in fixtures or demo reports must be labelled synthetic.

## Release gates

| Gate | Requirement |
| --- | --- |
| Correctness | All returned plans pass independent financial, squad, formation and chip replay |
| Forecast integrity | No future features, target revisions or model selection leakage at a claimed origin |
| Serving | Selected eligible artifact demonstrably changes projection job outputs |
| Search quality | Small deterministic test universes match an exhaustive oracle; full problems report actual solver limitations |
| Research evidence | Reproducible chronological comparison against declared baselines, with uncertainty and subgroup results |
| Default promotion | Evaluation supports usefulness; prospective forecasts support deployment readiness; no claimed superiority without evidence |
| Social launch | Access is authorised for the intended processing, missing providers degrade cleanly, extraction quality is measured |
| Social forecast influence | Additional predictive or decision value demonstrated separately from the football only model |

Do not promise a percentage gain or a rank target before measurement. Predeclare practical tolerances and statistical tests before looking at the final test period. A model that fails to improve the default can remain an honest research challenger.

## Priorities and boundaries

P0: fix objective mismatch, add real model routing, collect deadline data and produce a baseline versus CatBoost evaluation and strategy replay.

P1: complete minutes and scoring, add robust planning and future chip dates, implement expert and crowd summaries, and evaluate Bayesian scenarios.

P2: implement TFT across the supported horizon, eligible ensemble weights, social signal ablations and optional mini league objectives.

Defer new navigation, decorative charts, visual redesigns, generic chat, automatic transfer submission, paid football data purchases and social posting. Small interface changes needed to expose real model selection, evidence or conditional plans are within scope.

## Product metrics

Measure forecast error and calibration by event, position, price tier and appearance class; strategy points after hits versus Keep, greedy transfers and the existing planner; transfer regret against a small universe oracle; probability that a recommendation changes under plausible input perturbations; runtime and valid incumbent rate; minutes forecast error; extraction and source classification quality; and provider cost.

Also measure paired strategy comparisons with a common transfer flexibility policy. A frozen Keep comparator alone overstates the value of a strategy that keeps receiving new information and making transfers.

## Acceptance scenario

Given a confirmed squad and frozen sources, the system can recommend rolling now to enable a future funding pair, show why the horizon policy differs from the immediate favourite, identify a chip opportunity, and explain whether expert disagreement changes its assumptions. The same recommendation can be reconstructed later. If no evaluated advanced model is eligible, the report explicitly says it uses the baseline.
