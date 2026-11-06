# FPL Assistant

A local Fantasy Premier League research and decision tool. Review a squad, compare
legal transfers, choose a lineup and captain, explore chip scenarios, and retain
plans alongside immutable forecast evidence. Transfers and chips are executed
manually on the official FPL site.

**[Documentation](docs/README.md)** · **[Build status](docs/BUILD_STATUS.md)** ·
**[Model experiments](docs/experiments/README.md)** · **[Contributing](CONTRIBUTING.md)**

## Quick start

Requires Node.js 22, Python 3.12, npm and [uv](https://docs.astral.sh/uv/).

```sh
(cd backend && uv sync --locked)
(cd apps/web && npm ci)
bash scripts/dev.sh
```

- Interface: http://127.0.0.1:3000
- API documentation: http://127.0.0.1:8000/docs

The launcher starts the interface, API and recoverable worker. Ctrl-C stops the
launcher-owned processes. Default use requires no credentials; configuration is
listed in [.env.example](.env.example). Python services read exported environment
variables. Put optional interface settings in ignored `apps/web/.env.local`.

Load the labelled synthetic demo or import a public team ID. Public imports show
deadline state and can miss recent actions. Confirm current prices, bank, transfer
inventory and chips before personal transfer analysis. Unknown finances remain
unknown; eligible lineup analysis can continue independently.

## Capabilities and model status

| Area              | Available behavior                                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Decision engine   | Rules-aware numerical planner, independent validation, saved plans and stale-input checks                                         |
| Default forecasts | Labelled approximate football baseline                                                                                            |
| Forecast research | Actual CatBoost, Ridge, LightGBM, Extra Trees and histogram-boosting experiments; separate mean, probability and quantile outputs |
| Weekly evaluation | Full-universe forecast freezes, finalized scoring, chronological comparisons and recoverable opt-in jobs                          |
| Advanced research | Bayesian, TFT and policy experiments with explicit data and qualification gates                                                   |

Research results do not automatically replace the baseline or planner. Historical
backtests, prospective forecasts and realized policy benefit are separate evidence.
The [latest weekly competition](docs/experiments/2026-11-06-weekly-tournament/README.md)
records actual measurements and pending GW10 outcomes.

The application uses Next.js, React and TypeScript, a Python FastAPI backend,
SQLite state, Parquet analytical artifacts and a local worker. Provider requests
run through the backend. Bayesian, deep-learning, RL and extra research dependencies
are optional; see the [backend guide](backend/README.md).

## Project layout

```text
apps/web/       Interface, API bindings and browser/unit tests
backend/        API, worker, forecasting, rules and optimisation
scripts/        Stable operator commands and research entrypoints
tests/          Operator and repository checks
docs/           Guides, specifications, plans and measured evidence
data/           Ignored local state, source captures and model artifacts
```

Use the [file map](docs/FILE_STRUCTURE.md) for module ownership and the
[documentation index](docs/README.md) for navigation. Measured reports remain
immutable; superseded material is retained in `docs/archive/`.

## Development and verification

```sh
(cd backend && uv run pytest && uv run pytest ../tests)
(cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm run format:check && npm run lint && npm run typecheck && npm run test && npm run build)
python3 scripts/check_docs.py
```

Browser checks (`npm run test:e2e` from `apps/web`) and `python3 scripts/smoke.py`
require an API and worker against isolated synthetic state. Normal CI uses offline
fixtures; live provider checks are separate. [Contributing](CONTRIBUTING.md) explains
optional tests, contract generation and the combined check script.

Weekly collection and scoring require the matching local worker and machine uptime;
configuration is not hosted scheduling. Follow the [operations guide](docs/operations/README.md)
for the learning loop and recovery.

Keep credentials, manager records, model artifacts and generated output out of Git.
For a clean history-free source snapshot, follow [release preparation](docs/operations/RELEASE_PREPARATION.md).
