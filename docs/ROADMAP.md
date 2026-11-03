# Improvement roadmap

Goal: support a top-10,000 season finish through better weekly decisions. Rank is the user's outcome target, not a model guarantee or a training label. The current points gap to 10,000 is unverified. Optimize expected points after hits with legal state transitions; evaluate forecast, decision and execution errors separately.

## Priorities and acceptance

| Priority | Work | Acceptance | Current state |
| --- | --- | --- | --- |
| 1 | Decision quality and honest evaluation | Frozen origin-based shortlists; no outcome-driven eligibility/backfilling; separate ranking and legal policy replay; distinct finalized weekly evidence | Implemented this stage; GW10 prospective selection registered |
| 2 | Robust model comparison | Earlier inner validation, expanding outer tests, source/checkpoint identity, no outer-target tuning | Executed three fixed enriched challengers over GW5–8; historical results remain exploratory |
| 3 | Minutes and availability | Improve existing CatBoost appearance/60-minute heads using binary objectives; coherent probabilities, chronological calibration, Brier scores and minutes error; same deadline news for comparisons | **Next implementation task** |
| 4 | Better personal decisions | Reconcile current squad/finances; legal same-state Keep/roll/transfer/lineup/captain/bench comparisons; stress-test plausible minutes assumptions | Engine exists; current private state needs reconciliation before transfer advice |
| 5 | Supported future forecasts | Evaluate direct multi-lead forecasts and future availability assumptions; preserve blanks/doubles and freeze each horizon at origin | One-lead trained support; longer baseline numbers remain conditional scenarios |
| 6 | Broader model families | Complete Bayesian components and historical provenance; TFT only if it improves the relevant measured objective | Research only; do not add complexity to compensate for weak evidence |

## What this stage established

A genuine durable rolling experiment produced 2,671 outer player-fixture predictions per model across GW5–8. Pooled RMSE: multiscale opportunity **2.0890**, prior full-context **2.0983**, points hurdle **2.1016**, reconstructed app baseline **2.3660**, rolling points **2.2749**. The hurdle's earlier tiny single-split advantage does not hold consistently. These are inspected, reconstructed historical weeks, not fresh prospective proof.

Retrospective ranking diagnostics of the original frozen GW9 forecasts expose different strengths. Among 171 players with predeadline five-fixture mean minutes at least 60, baseline's top-five defender shortlist returned 37 points; original CatBoost's returned 23 and selected full-context/news sensitivity returned 12. Forward shortlist returns were 24, 34 and 31 respectively. These unconstrained lists are not legal squads, transfers or captaincy policies, and a single week's outcomes are noisy. The result prevents treating lower league-wide RMSE as sufficient evidence of better FPL choices.

A new GW10 selection plan is registered before deadline using the existing 23 canonical forecast streams and 176 origin-eligible players. It fixes the comparator, primary challenger, attacking top-one diagnostic, position top-five lists, deterministic ties, source collection and method identity. Missing selected outcomes remain missing; hindsight never backfills a shortlist. The GW9 analysis is explicitly retrospective and provisional. Neither can silently become a promotion test.

## Next implementation task: opportunity probabilities

Extend the existing `models/football_catboost.py` evaluation path rather than creating a competing probability stack. Compare binary-loss appearance and 60-minute heads with the current heads on expanding chronological folds. Fit calibration on a separate earlier calibration block; enforce `P(60+) <= P(appearance)`, valid expected minutes and distinct probabilities versus point means. Audit substitutes, returning players, short histories and missing statistics. Preserve zero-minute disciplinary outcomes in total points. Never apply availability twice to unconditional mean forecasts.

Keep the experiment small and register configurations before fitting. Report Brier/calibration, minutes errors, likely-starter/position point errors and ranking diagnostics together. Preserve all existing GW9/GW10 forecasts. Score any newly finalized event before consuming it in a new fit. Select on development evidence; retain untouched future monitoring. Do not retune GW10 predictions after observing GW10.

## Weekly operating routine

1. After official finalization: archive outcome revisions, score frozen forecasts and saved legal paper decisions, classify misses, then refit separately.
2. Early week: reconcile squad and transfer inventory, review minutes/roles and the supported fixture horizon, compare Keep/roll with feasible moves.
3. Before deadline: refresh official sources/news, confirm finances/selling prices/chips, inspect captain/vice and bench, and stress-test uncertain availability. Avoid hits justified only by tiny uncertain gains; retain the calculated cost/flexibility tradeoff.
4. Freeze the actual forecast/decision versions before deadline; record user execution separately. Late captures remain late.
5. Review process quality across weeks. Do not chase a differential merely to move rank or react to one haul. No rank probability or fixed points target is fabricated.

## Evidence and release policy

Production remains baseline football plus the numerical optimiser. Ranking-readiness reports require at least eight distinct finalized prospective event blocks with the same registered method/comparison; repeated captures and training seeds do not create extra weeks. Eight weeks remains a small sample. Any interval is descriptive; a favorable report means review, not automatic activation. Calibration, coverage, legal policy replay, downside and operational checks remain separate release evidence.

Full Bayesian player scoring, strict TFT provenance, future calibrated joint distributions and the current private manager-state reconciliation remain unavailable. See [BUILD_STATUS](BUILD_STATUS.md) for the exact checks and [START_HERE](START_HERE.md) to resume. Retained evidence is linked from [the documentation index](README.md).
