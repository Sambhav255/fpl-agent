# Backend

FastAPI services, a recoverable SQLite-backed worker, rules-aware planning and
source-bound forecasting experiments. Run commands in this directory unless noted.

## Install and run

```sh
uv sync --locked
uv run uvicorn fpl_app.api.main:app --host 127.0.0.1 --port 8000
```

Run the worker in another terminal with the same environment:

```sh
uv run python -m fpl_app.jobs.worker
```

The root `scripts/dev.sh` launcher starts both services and the interface. Set an
absolute `DATA_DIR` when operating a research store. Do not run two workers against
the same store unintentionally. See [worker operations](../docs/operations/WORKER_RUNTIME.md).

## Source map

| Package                  | Responsibility                                                           |
| ------------------------ | ------------------------------------------------------------------------ |
| `api/`, `contracts.py`   | HTTP routes and validated runtime contracts                              |
| `domain/`                | Money, squad rules, transfers, chips and scoring                         |
| `optimisation/`          | Candidate generation, numerical planning and validation                  |
| `providers/`, `storage/` | Fixed-provider collection, immutable source bytes and SQLite records     |
| `features/`              | Deadline-safe feature construction and historical normalization          |
| `models/`                | Training, serialization, research methods and qualified serving adapters |
| `evaluation/`            | Chronological forecast metrics, selection and policy comparisons         |
| `learning/`              | Journals, finalized scoring, review orchestration and evidence gates     |
| `jobs/`                  | Durable queues, leases, cancellation, dispatch and health                |
| `strategy/`, `social/`   | Optional policy research and reviewed social evidence                    |

Tests live in `tests/`. Root-level `../tests/` exercises operator commands,
documentation and source export. Keep analytical datasets and checkpoints under
ignored `DATA_DIR`, not alongside Python modules.

## Optional models

The `research`, `bayes`, `deep` and `rl` extras are explicit. To preserve all installed
research libraries while updating the locked environment:

```sh
uv sync --locked --all-extras
uv run --no-sync pytest
```

Normal baseline CI does not require every extra; corresponding native-model checks
may skip. Installing a package does not establish a trained or qualified model.
The [experiment registry](../docs/experiments/README.md) distinguishes actual fits,
negative results, prospective freezes and outstanding evidence gates.

## Checks and contracts

```sh
uv run pytest
uv run pytest ../tests
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Use `uv run --no-sync` when verifying an already installed all-extras environment.
After changing request/response models, regenerate API bindings using
`npm run generate:api` from `../apps/web`. Generated artifacts are checked in;
private state and native model binaries are not.

See [weekly research](../docs/operations/WEEKLY_RESEARCH.md), the
[operator reference](../scripts/README.md) and [specifications](../docs/specs/README.md)
for experiment registration, scoring-before-training and release requirements.
