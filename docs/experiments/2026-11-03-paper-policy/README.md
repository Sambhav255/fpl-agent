# Same-state paper comparison and search mechanics — 3 November 2026

This stage extends the existing legal replay engine to compare different frozen
forecast methods with the same planner. It is implementation and synthetic
mechanics evidence, **not measured forecast improvement or prospective policy
performance**. No champion changed and no account action was performed.

The new `compare_forecast_policies` boundary requires identical initial finances,
origin information, player catalogue and prices, fixture schedules, and realized
outcomes. Each declared candidate supplies its own forecasts and policy; outcomes
remain outside the policy interface. The ordinary independent plan validator,
financial transitions, chip handling, captain fallback and automatic substitutions
remain authoritative. Reports now retain lineup, captain/vice/bench, committed and
incremental hits, pre/post-action states, next-origin financial state and forecast
fingerprints. Keep and roll coincide under the same lineup forecast.

A predeclared synthetic two-event CLI run compared Keep, roll, the existing planner
and that same planner with deliberately altered synthetic goalkeeper forecasts.
All four completed legal sequential trajectories. The returns were 48, 48, 62 and
104 synthetic points respectively. These values were designed to exercise behavior
and say nothing about real model quality. The input, protocol and full private-shaped
trajectories are retained under ignored `data/research/paper-policy-2026-11-03/`.
The report cannot overwrite an earlier result; complete bytes publish atomically.

The bounded ordinary sequence menu previously stopped at two replacements even
when three or more free transfers remained. A new exact small-universe regression
exhibits three independent no-hit upgrades: the old two-move menu misses the
third improvement, while the widened bounded search matches exhaustive enumeration
of 72 declared squads with a 40-edge budget. A small deterministic beam seeds
larger free-transfer restructures before deeper continuations consume the budget.
The lazy menu allows up to the remaining free inventory (at most five), or two
replacements for lower inventory. It respects locks, exclusions, positions, event
limits and subsequent independent legal/financial validation. Recursive purchase
combination generation avoids materializing large Cartesian pools. This remains
bounded search and carries no full-catalogue global optimality claim.

A real comparison of the new opportunity model against the original forecast from
the same prospective financial state is still unavailable: it needs a newly frozen
candidate, its own valid origin evidence and finalized outcomes. Existing studies
and private financial uncertainty were preserved. Next: freeze that comparison
before an eligible future deadline and score it after official finalization.

Reproduce the mechanics command with the retained ignored input:

```sh
backend/.venv/bin/python scripts/research/compare_paper_policies.py \
  --input data/research/paper-policy-2026-11-03/input.json \
  --output data/research/paper-policy-2026-11-03/NEW-report.json
```

The CLI accepts existing runtime manager/player/forecast schemas, complete outcome
records and the existing replay provenance contract. It neither fetches labels nor
fits, selects or promotes a model. See [operator commands](../../../scripts/README.md).

New checks: **83 replay, policy, sequence, chip and CLI tests passed**, with one
dependency deprecation warning. Changed-file Ruff lint/format and mypy for both
changed source modules passed. The CLI was exercised with actual retained
synthetic input; its overwrite guard was checked through subprocess integration.
[Verification and artifact hashes](verification.json).
