# FPL Assistant

A local Fantasy Premier League decision tool for squad review, legal transfer comparisons, lineups, captaincy, chip scenarios and saved plans. Built with Next.js, TypeScript, FastAPI, SQLite and a recoverable Python worker. Transfers and chips are executed manually on the official FPL site.

**[Start here](docs/START_HERE.md)** for users and coding agents. [Current build status](docs/BUILD_STATUS.md) records what works, what was actually checked and what remains gated.

## Run locally

Requires Node.js 22, Python 3.12, npm and [uv](https://docs.astral.sh/uv/).

```sh
(cd backend && uv sync --locked)
(cd apps/web && npm ci)
bash scripts/dev.sh
```

Open the interface at http://127.0.0.1:3000 and API documentation at http://127.0.0.1:8000/docs. The launcher starts the interface, API and worker; Ctrl-C stops all three. Default local use needs no credentials. See [.env.example](.env.example) for configuration. To choose a personal default, set `NEXT_PUBLIC_DEFAULT_TEAM_ID=YOUR_PUBLIC_TEAM_ID` in ignored `apps/web/.env.local`; Python services read exported environment variables.

Import a public team ID or load the labelled synthetic demo. Review the squad, prices, bank, free transfers and chips before analysis. A public import represents deadline data and may miss recent changes. Unknown or stale private financial state blocks affected transfer recommendations while lineup analysis remains available. Review private state again when the gameweek changes; refreshing official data preserves saved corrections.

## Models and research

The approximate baseline and numerical planner remain champions. Real CatBoost, Bayesian, TFT, ensemble and policy experiments are retained with source provenance, chronological evaluation and honest coverage limits. Research fitting does not automatically qualify a model for serving or promotion. Bayesian complete player scoring and strict TFT qualification remain gated. Social points adjustment is zero; live Reddit/X collection is disabled.

[The latest post-GW9 review](docs/experiments/2026-11-03-gw9-post-event/README.md) records provisional measurements and frozen GW10 challengers. [Operator commands](scripts/README.md) cover collection, research, immutable forecasts, finalized scoring and optional model dependencies. Score retained forecasts before refitting on their outcomes. Registered reviews and enabled schedules require a running worker using the matching `DATA_DIR`; this is not a hosted scheduler.

## Repository

| Location | Purpose |
| --- | --- |
| `apps/web/` | Next.js interface, generated API bindings and frontend tests |
| `backend/` | FastAPI, worker, rules, forecasts, optimiser and backend tests |
| `scripts/` | Stable operator commands and research entrypoints |
| `tests/` | Operator integration tests |
| `docs/` | Current guide/status, maintained specs, immutable experiments and archive |
| `data/` | Ignored private state, source snapshots and model artifacts |

Use the [file map](docs/FILE_STRUCTURE.md) for detailed locations, [specifications](docs/specs/README.md) for behavioral contracts and [CONTRIBUTING](CONTRIBUTING.md) for formatting, API generation, optional dependencies and source exports. Obsolete prompts, audits and handoffs are preserved in [docs/archive](docs/archive/README.md); private local records stay ignored.

## Verify changes

```sh
(cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src)
(cd apps/web && npm run format:check && npm run lint && npm run typecheck && npm run test && npm run build)
(cd apps/web && npx playwright install chromium && npm run test:e2e)
python3 scripts/smoke.py
backend/.venv/bin/python -m pytest tests
```

Browser and integration checks require the API and worker. Demo tests use synthetic team 0; normal CI uses offline fixtures. The optional live check is `python3 scripts/live_smoke.py --team-id YOUR_PUBLIC_TEAM_ID` and preserves private corrections. For production-build and browser-target commands, see [the operator index](scripts/README.md).

Keep credentials, databases, manager notes, screenshots and model artifacts out of Git. Existing history contains earlier personal notes; publication requires a fresh inspected source export. Nothing in this setup authorizes transfer submission, a Git push or public deployment.
