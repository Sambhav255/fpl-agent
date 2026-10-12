# FPL Assistant

A local Fantasy Premier League strategy workspace for squad review, projections, legal transfer comparisons, chip planning, and saved plans. Built with Next.js, TypeScript, FastAPI, SQLite, and a recoverable Python worker.

## Capabilities

- Import published public team picks or explore a clearly labelled synthetic demo.
- Correct manager state, distinguish purchase/current/selling prices, and preserve unknown finances.
- Compare keeping the squad with legal transfers across up to eight gameweeks.
- Select a lineup, captain, vice captain, and bench; inspect chip timing and save versioned plans.
- Track immutable source snapshots, background jobs, and prediction provenance.

The approximate baseline is the default. Football CatBoost can run as an explicit, one-gameweek experiment with immutable source/artifact checks and a declared player universe. Preparation now evaluates expanding chronological event folds, then creates a separate latest-data serving refit; early seasons report insufficient evaluation instead of forcing a split. Earlier small tests did not beat the simple comparison forecast, so no challenger is promoted. Bayesian complete-component research scoring, real multilead TFT fitting/evaluation and eligible mean ensembles are implemented with audited opt-in shadow worker/UI contracts. Real-data qualification and calibration remain gated. The Models page shows actual evaluation status and an experimental comparison flow. See [model integration](docs/ML_INTEGRATION.md) and [build status](docs/BUILD_STATUS.md). Transfers and chips are executed manually on the official FPL site.

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

After a gameweek changes, review the squad and private state in Settings. Changing the gameweek clears draft financial and selling-price confirmations; populated new-event values require an explicit review checkbox before saving. Refreshing official data preserves saved private state and blocks analysis when that state is stale.

## Football research workflow

From the repository root, after installing backend dependencies:

```sh
backend/.venv/bin/python scripts/collect_football.py --help
backend/.venv/bin/python scripts/prepare_football_forecast.py --help
```

Capture with `--include-owned` and optional `--from-collection COLLECTION_ID`; use `--include-all` for a deadline-frozen full bootstrap player universe (bounded at 1,000 players). The collector prints a new immutable collection ID without changing manager state. Prepare a qualified experiment with `prepare_football_forecast.py --collection-id COLLECTION_ID --team-id YOUR_PUBLIC_TEAM_ID`. Add `--register` only after reviewing the current manager state and matching retained catalogue sources. The Models page can then validate a serving bundle and request an experimental forecast through the worker. Preliminary event outcomes are excluded from the current experiment's fitting and lag features.

Collection jobs are also available through `POST /api/v1/data/collections`; progress and failures use the existing jobs API. Reddit/X live collection is disabled; `/api/v1/social/status` reports capabilities honestly and social points adjustment is zero. Future baseline availability is an explicit conditional planning scenario, not a calibrated recovery forecast or a repeated current injury flag.

## Repository

```text
apps/web/       Next.js interface, generated API types, unit and browser tests
backend/        FastAPI, providers, rules, optimiser, models, worker and tests
docs/           Specifications, contracts, decisions and current build status
scripts/        Local service launcher and integration checks
data/           Local database, snapshots and model artifacts (Git ignored)
```

Start a coding session with [docs/START_HERE.md](docs/START_HERE.md). Canonical specifications and engineering references are indexed in [docs/README.md](docs/README.md). See [the file map](docs/FILE_STRUCTURE.md) for the layout; unchanged supplied material is archived under `docs/reference/supplied/` and older status narratives under `docs/history/`.

## Development checks

```sh
(cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm run format:check && npm run lint && npm run typecheck && npm run test && npm run build)
(cd apps/web && npx playwright install chromium && npm run test:e2e)
python3 scripts/smoke.py
backend/.venv/bin/python -m pytest tests
```

Browser and integration tests require the API and worker to be running. Demo tests use synthetic team 0. The optional live check preserves existing local corrections:

```sh
python3 scripts/live_smoke.py --team-id YOUR_PUBLIC_TEAM_ID
```

For a separate production build, use `NEXT_BUILD_DIR=.next-production npm run build`, then `NEXT_BUILD_DIR=.next-production npm run start -- --port 3001` from `apps/web`. Browser tests can target it with `E2E_BASE_URL=http://127.0.0.1:3001 npm run test:e2e`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for formatting, API generation, optional model dependencies, and Git preparation. Latest checks and remaining work are recorded in [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md).

## Learning research and reviews

Saved Plans supports immutable deadline decisions, manual execution reporting and finalized outcome reviews. Future-chip and financial sequence controls are in Planner. Small-universe exhaustive search is distinguished from bounded full-catalogue paths, which cap replacements at two per event including chip weeks. Frozen journals can seal pre-deadline replay evidence; see [journal replay](docs/learning_upgrade/JOURNAL_REPLAY.md). Baseline and numerical planning remain the default champions.

Optional local strategy research:

```sh
(cd backend && uv sync --locked --extra rl)
backend/.venv/bin/python scripts/train_strategy.py --synthetic-smoke --timesteps 128
# Run the normal worker to process the returned durable job ID:
(cd backend && uv run --extra rl python -m fpl_app.jobs.worker)
backend/.venv/bin/python scripts/benchmark_social.py
```

Use `--episodes path/to/frozen-episodes.json` for explicitly labelled local train/test research episodes. The JSON bytes and implementation are fingerprinted when queued; no arbitrary file path is requested through the API. Optional Bayesian/TFT development requires `uv sync --locked --extra bayes --extra deep --extra rl`. Synthetic PPO fitting checks mechanics and installation; it does not establish a live advantage. Models lists inactive policy evidence separately from football forecasts.

Recurring reviews are disabled until saved in the live team's Saved Plans controls. With API/worker running, launch `backend/.venv/bin/python scripts/review_learning.py --watch` to enqueue due intervals. Enable collection/refitting deliberately in those controls. Closing the scheduler stops new ticks; disabling the schedule fences queued reviews. No private inputs, transfers, chips or champion pointers are changed by a review.

The detailed implemented scope, remaining release/data prerequisites and actual verification are recorded in [learning implementation status](docs/learning_upgrade/IMPLEMENTATION_STATUS.md).
