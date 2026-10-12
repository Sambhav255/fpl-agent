# Contributing

Read [AGENTS.md](AGENTS.md) and the relevant [specifications](docs/README.md) before changing behavior. Keep money in integer tenths of a million, preserve unknown manager state, and validate every recommendation independently.

## Setup and formatting

Use the locked installation commands in the README. Format Python with `uv run ruff format .` from `backend`; format the interface with `npm run format` from `apps/web`. Generated API types and OpenAPI snapshots are excluded from frontend formatting and retain generator formatting.

Run the README checks before proposing changes. Root `bash scripts/check.sh` runs the combined checks; API and worker must already be available for browser tests. CI uses offline fixtures and synthetic demo state. Live provider checks are opt-in.

## API contracts

Change the Pydantic contracts/request models, then run `npm run generate:api` from `apps/web` after installing locked backend dependencies. This generates `apps/web/openapi.json` and `apps/web/src/lib/api/schema.d.ts` offline from the actual API with an in-memory store; a running server is unnecessary. The original design-only snapshot is preserved at `docs/reference/contracts/openapi-design.json`. Read [the file map](docs/FILE_STRUCTURE.md) before moving source or generated artifacts.

## Model work

Install optional dependencies with `uv sync --locked --all-extras` from `backend`. `FPL_OPTIONAL_SMOKE=1 uv run --all-extras pytest tests/test_models.py tests/test_features.py tests/test_evaluation.py tests/test_strategy_adapters.py tests/test_publication_timing.py` exercises optional libraries with synthetic data. Passing those tests does not establish trained-model performance. Follow [ML integration](docs/ML_INTEGRATION.md) for release eligibility.

## Preparing a Git change

Review `git status --short` and `git diff --check`. Keep databases, source snapshots, models, local manager notes, credentials, and build output out of Git. Local session notes belong under ignored `docs/local/`. Commit lockfiles with dependency changes and regenerate contracts when necessary. Update build status with checks actually run and any remaining limitations.

The current dependency audit reports an unresolved development-only `braces` advisory through Next.js ESLint tooling. The installed upstream version has no patched release available in the registry checked during cleanup; avoid forced framework downgrades. Recheck `npm audit` when updating dependencies.

Existing Git history contains earlier personal manager notes. Sanitizing the current files does not erase that history. To publish a clean initial snapshot without rewriting the existing repository, run `python3 scripts/export_source.py` from the root, extract the ignored `dist/fpl-assistant-source.zip`, and initialize a new repository there. The archive includes the current Git-visible source and excludes ignored local state and the `.git` directory. Inspect its contents before publishing.
