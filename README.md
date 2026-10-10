# FPL Assistant

A local Fantasy Premier League strategy workspace for squad review, projections, legal transfer comparisons, chip planning, and saved plans. Built with Next.js, TypeScript, FastAPI, SQLite, and a recoverable Python worker.

## Capabilities

- Import published public team picks or explore a clearly labelled synthetic demo.
- Correct manager state, distinguish purchase/current/selling prices, and preserve unknown finances.
- Compare keeping the squad with legal transfers across up to eight gameweeks.
- Select a lineup, captain, vice captain, and bench; inspect chip timing and save versioned plans.
- Track immutable source snapshots, background jobs, and prediction provenance.

The approximate baseline is active. CatBoost, Bayesian events, TFT, and ensemble pipelines are implemented to varying degrees; advanced model activation still requires verified historical data and chronological evaluation. See [model integration](docs/ML_INTEGRATION.md) and [build status](docs/BUILD_STATUS.md). Transfers and chips are executed manually on the official FPL site.

## Quick start

Requires Node.js 22, Python 3.12, npm, and [uv](https://docs.astral.sh/uv/).

```sh
(cd backend && uv sync --locked)
(cd apps/web && npm ci)
bash scripts/dev.sh
```

- Interface: http://127.0.0.1:3000
- API documentation: http://127.0.0.1:8000/docs

The launcher starts the interface, API, and worker. Ctrl-C stops all three. For a personal default, set `NEXT_PUBLIC_DEFAULT_TEAM_ID=YOUR_PUBLIC_TEAM_ID` in ignored `apps/web/.env.local`. The app loads saved state rather than reimporting it, and a deliberate demo selection remains available. Local defaults work without an environment file; [.env.example](.env.example) documents configuration. Store runtime environment values in the service's `.env.local` or export them in the shell as appropriate; the Python services use exported environment variables.

Import a public team ID or load the demo, review the state, generate projections, compare alternatives, and save a plan. Public picks may reflect the last deadline rather than a manager's current private squad. Unconfirmed selling prices, bank, free transfers, or chip state block affected transfer recommendations while lineup analysis remains available.

## Repository

```text
apps/web/       Next.js interface, generated API types, unit and browser tests
backend/        FastAPI, providers, rules, optimiser, models, worker and tests
docs/           Specifications, contracts, decisions and current build status
scripts/        Local service launcher and integration checks
data/           Local database, snapshots and model artifacts (Git ignored)
```

Original build-kit specifications remain at the root; working specifications are indexed in [docs/README.md](docs/README.md).

## Development checks

```sh
(cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm run format:check && npm run lint && npm run typecheck && npm run test && npm run build)
(cd apps/web && npx playwright install chromium && npm run test:e2e)
python3 scripts/smoke.py
```

Browser and integration tests require the API and worker to be running. Demo tests use synthetic team 0. The optional live check preserves existing local corrections:

```sh
python3 scripts/live_smoke.py --team-id YOUR_PUBLIC_TEAM_ID
```

For a separate production build, use `NEXT_BUILD_DIR=.next-production npm run build`, then `NEXT_BUILD_DIR=.next-production npm run start -- --port 3001` from `apps/web`. Browser tests can target it with `E2E_BASE_URL=http://127.0.0.1:3001 npm run test:e2e`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for formatting, API generation, optional model dependencies, and Git preparation. Latest checks and remaining work are recorded in [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md).
