# FPL Assistant

Personal local Fantasy Premier League recommendation tool. Next.js interface, FastAPI API, SQLite state, separate recoverable worker, immutable source snapshots, and Parquet modelling artifacts. Transfers and chips are performed manually on the official FPL site.

## Install

Requires Node 22 (tested 22.13.1), npm, Python 3.12, and uv.

```sh
cd backend
uv sync --locked
cd ../apps/web
npm ci
npx playwright install chromium
cd ../..
```

## Run locally

```sh
bash scripts/dev.sh
```

Open http://127.0.0.1:3000. API documentation: http://127.0.0.1:8000/docs. Ctrl-C stops the interface, API, and worker.

Processes can also be run in separate terminals:

```sh
cd backend
uv run uvicorn fpl_app.api.main:app --host 127.0.0.1 --port 8000
```

```sh
cd backend
uv run python -m fpl_app.jobs.worker
```

```sh
cd apps/web
npm run dev
```

## Workflow

Load the clearly labelled synthetic demo or import a public team ID. Public picks describe a deadline squad and can miss recent changes. Review and correct ownership, bank, purchase/selling prices, free transfers, transfers already made, committed hits, and chip inventory. Unknown financial fields stay unknown; lineup analysis is useful, transfer recommendations require confirmation. Generate projections, compare Keep with valid moves, inspect weekly lineup/captain/bench, and save a plan. No account credentials are needed.

Baseline forecasts are approximate and have no calibrated confidence intervals. Advanced model status must be backed by genuine artifacts and chronological evaluation. Plans retain source/forecast/state versions; changed inputs mark them stale.

## Checks

```sh
cd backend
uv run pytest
uv run ruff check .
uv run mypy src
cd ../apps/web
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

With the actual API and worker running, `python3 scripts/smoke.py` from the root checks the offline demo through persisted plans. Final verification results and exact remaining work are recorded in [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md).

## Specifications

The original root Markdown specifications are preserved; individual working copies are in docs. See [docs/DECISIONS.md](docs/DECISIONS.md) for implementation choices and [docs/CONTRACTS.md](docs/CONTRACTS.md) for shared integration contracts.

The local baseline application is running and verified; the complete advanced-model release remains incomplete. Review fixes for missing statistics, availability labels, TFT deadline encoders, audit binding, and immutable model publication are in the code. Strict activation is still blocked: it needs a deadline-verified source bundle, held-out comparison, and explicit promotion. Continue from [docs/CURSOR_HANDOFF.md](docs/CURSOR_HANDOFF.md) and [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md). Do not treat implemented training pipelines as trained or activated models.
