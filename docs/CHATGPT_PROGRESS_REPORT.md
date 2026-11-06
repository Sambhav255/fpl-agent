# Continuation summary

Start with [build status](BUILD_STATUS.md), the [documentation index](README.md)
and [weekly backend competition](experiments/2026-11-06-weekly-tournament/README.md).

## Latest repository maintenance

Documentation now separates current guidance, operations, original plans and dated
evidence. Root README/status/file map were consolidated; backend has a module guide.
The supplied master plan moved byte-for-byte to `docs/plans/`; worker guidance moved
to `docs/operations/`. Operational notes/logs remain ignored under `docs/local/`.
All application modules, CLI entrypoints, private state and measured reports remain
in place. Relocation checks now preserve 69 moves, 52 originals and 67 evidence files.

Native model/array artifacts are ignored and independently rejected by source export.
CI checks documentation and source export. The research-native fit test now skips
explicitly without optional libraries. New checks: 28 operator passed; 5 focused
backend passed with extras; fresh baseline 4 passed/1 skipped; Ruff and docs checks
passed. Full backend/frontend suites were not rerun for this cleanup.

Fresh audited source is in ignored `dist/fpl-assistant-source.zip` with its audit JSON.
Existing history still contains older personal notes; public release should use a
reviewed clean export rather than imply current-file cleanup erased history. No
commit, push, replacement repository or history rewrite was performed.

## Retained modelling state

GW10: 39 watched streams / 670 players, including 16 new raw/official-zero streams;
actual outcomes remain pending official finalization. Prior stage checks: 635 backend
passed/3 skipped, 22 operator passed. CatBoost won historical RMSE; Extra Trees won
overall MAE; LightGBM won likely-starter MAE. Shared historical auxiliary heads improved
matched Briers; current refits remain uncalibrated. No champion promoted.

The default local worker handles opted-in reviews, scoring before label reuse and
one canonical tournament after prior-event finalization. A review recorded
`already_frozen` instead of refitting GW10. Machine/worker uptime is required; no
OS service was installed. Model artifacts and sources stay under ignored
`data/research/weekly-tournament-2026-11-06/` and earlier stores.

Next: review the Git diff/export, then score finalized GW10 and freeze the same
registered weekly procedure for GW11. Personal legal-policy comparison and advanced
Bayesian/TFT/social/RL qualification retain the [acceptance gates](MASTER_PLAN_STATUS.md).
