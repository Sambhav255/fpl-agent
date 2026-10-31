# Agent start guide

Read this page, [BUILD_STATUS](BUILD_STATUS.md), [HANDOFF](HANDOFF.md), and the root [AGENTS.md](../AGENTS.md) before editing. Use the [file map](FILE_STRUCTURE.md) and [specification index](README.md) to locate the relevant contract.

## Current work

The 31 October review ran real baseline, CatBoost, Bayesian team-goal, TFT mean/quantile, ensemble and policy experiments. Additional registered ablations now include xG/xA, defensive actions, opportunity, rest and team context. Frozen GW9 forecasts have automatic finalized-event scoring. Read the [experiment report](experiments/2026-10-31-gw9-model-review/README.md) for actual results and limitations.

The baseline remains the default football model and the numerical optimiser remains the strategy champion. Bayesian complete player scoring lacks required components; strict TFT release qualification lacks verified historical availability. Research fits do not remove those gates. Means and quantiles have distinct meanings.

## Run locally

```sh
(cd backend && uv sync --locked)
(cd apps/web && npm ci)
bash scripts/dev.sh
```

The interface uses port 3000 and API port 8000. The launcher also starts the recoverable worker. Enabled review schedules and registered benchmark checks are polled by the normal worker. An isolated research worker must use the same exported `DATA_DIR` as its retained forecasts.

## Preserve local evidence

`data/`, `docs/local/`, environment files, installed dependencies and `.next*` folders are local artifacts. Preserve them. Personal selections and screenshot evidence are recorded only in ignored local notes; current account execution and private finances must not be inferred. The personal app state may be older than the research origin and requires reconciliation before serving a new recommendation.

Current research is under ignored `data/research/gw9-models-2026-10-31/`. Source bytes, model checkpoints, registered settings, frozen predictions and evaluations are retained there. Post-event scoring must use the original forecasts before any subsequent refit. Never backdate a prediction or fill missing outcomes with zero.

## Verification and publishing

Use the [current status](BUILD_STATUS.md) for checks actually run and the [handoff](HANDOFF.md) for release preparation. Existing Git history contains earlier personal notes; a clean source export is required for a fresh public initial snapshot. Root duplicate handoff material was preserved under ignored local backups; canonical historical supplied material remains in `docs/gw7_handoff/` and `docs/reference/`.

Previous technical evidence is retained in [history](history/README.md). It does not override current status. No Git push or public deployment is authorized by this handoff.
