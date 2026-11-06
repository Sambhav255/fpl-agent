# Contributing

Read [build status](docs/BUILD_STATUS.md), the relevant [specifications](docs/specs/README.md)
and applicable `AGENTS.md` instructions before changing behavior. Keep changes scoped;
preserve existing user edits, private runtime state and immutable experiment evidence.

## Setup and code boundaries

Follow the [quick start](README.md#quick-start). The [backend guide](backend/README.md)
and [file map](docs/FILE_STRUCTURE.md) describe module responsibilities. Keep CLI
entrypoints stable under `scripts/`; place implementation in backend modules.

Money uses integer tenths of a million. Unknown finances remain unknown. Independently
validate recommendations after solving. Long computations use recoverable worker jobs;
provider data is fetched through validated backend paths.

## Verification

From `backend`:

```sh
uv run pytest
uv run pytest ../tests
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

From `apps/web`:

```sh
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

From the repository root:

```sh
python3 scripts/check_docs.py
git diff --check
```

`bash scripts/check.sh` combines the project checks. Browser and smoke tests require
an API and worker using isolated synthetic state; production services with personal
state are not a disposable test store. Normal CI is offline. Live provider checks
are explicitly separate.

Format Python with `uv run ruff format .` from `backend`; format interface files
with `npm run format` from `apps/web`. Do not manually reformat generated bindings.
Run checks appropriate to the actual change and report exactly which checks ran.

## Models and optional dependencies

Install research libraries deliberately using `uv sync --locked --all-extras` from
`backend`. Use `uv run --no-sync` to verify that installed environment without
removing extras. Baseline CI must remain usable without optional libraries;
optional native-fit tests should skip explicitly when their dependencies are absent.

Register experiments before fitting. Fit preprocessing, calibration and ensemble
weights only on allowed earlier partitions. Preserve signed outcomes, missingness,
source hashes and artifact identities. Score frozen forecasts before reusing their
labels. Report improvements and regressions, coverage and evidence limits; a passing
suite or model fit alone does not establish better decisions.

Release qualification follows [ML integration](docs/specs/ML_INTEGRATION.md), not a
model name or installation flag. [Weekly operations](docs/operations/WEEKLY_RESEARCH.md)
explains the fixed competition and its separate evidence levels.

## API contracts

Change Pydantic contracts/request models, then run `npm run generate:api` from
`apps/web` with locked backend dependencies installed. The generator uses an
in-memory store; it does not require a running API. Commit the generated
`apps/web/openapi.json` and `apps/web/src/lib/api/schema.d.ts` with contract changes.
The historical design-only schema remains under `docs/archive/reference/contracts/`.

## Documentation and publication

Update [build status](docs/BUILD_STATUS.md) and its concise continuation summary
when implemented behavior, checks or next actions change. Update indexes when adding
guides or reports. Keep original plans/reports intact and record moves in the
checksum-verified relocation manifest. Run `python3 scripts/check_docs.py` afterward.

Commit lockfiles with dependency changes. Audit dependencies when changing them,
distinguishing runtime from development findings and optional libraries. Never
relabel an old audit or test count as newly executed.

Before committing, inspect changed and untracked files. Follow
[release preparation](docs/operations/RELEASE_PREPARATION.md) for private/generated
exclusions, the existing-history limitation and an audited clean source export.
Repository maintenance does not authorize a push, deployment or FPL account action.
