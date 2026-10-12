# FPL Assistant agent instructions

Read this file before editing the project. Start or resume with `docs/START_HERE.md` and `docs/BUILD_STATUS.md`. Read the relevant specifications in `docs` before implementing a milestone. Use `docs/FILE_STRUCTURE.md` for file locations; historical records and supplied originals do not override current status.

## Product

Build a personal standard Fantasy Premier League decision tool. Default to free data, local development, and manual execution of transfers by the user. The complete product includes CatBoost, Bayesian events, TFT, and a separate rules aware optimiser. A labelled baseline is the first usable milestone.

## Specification order

1. Explicit user instructions.
2. Current verified official FPL rules.
3. `docs/FPL_PRD.md` for product scope.
4. `docs/DATA_AND_MODEL_SPEC.md` for data, manager state, and models.
5. `docs/TECH_STACK_AND_ARCHITECTURE.md` for interfaces and structure.
6. `docs/BUILD_PLAN_AND_TESTS.md` for delivery order and checks.

If documents conflict, resolve the smallest reversible choice and record it in `docs/DECISIONS.md`. A material unresolved rules conflict must disable the affected recommendation rather than invent behaviour.

## Implementation

Use Next.js, React, TypeScript, and a Python FastAPI backend. Use SQLite for app state, Parquet for analytical artifacts, uv for Python dependencies, and npm for the interface. Make Bayesian and TFT dependencies optional.

Build the requested milestone completely before moving on. Do not create a dashboard full of invented advanced model outputs. Keep `docs/BUILD_STATUS.md` current and inspect it when resuming. Update `docs/CHATGPT_PROGRESS_REPORT.md` as meaningful progress, actual checks, blockers or next actions change. Keep its file map and current summary concise; distinguish prior checks from newly run checks and omit private state.

## Domain correctness

1. Store money as integer tenths of a million. Keep points a separate type.
2. Distinguish market, purchase, and selling prices.
3. Track already made transfers and committed hits, not only proposed moves.
4. Distinguish persistent and temporary Free Hit squads.
5. Treat unknown financial or chip state as unknown.
6. Public team ID import represents a deadline squad and may miss recent changes.
7. Validate every recommendation independently after solving.
8. Save transfer inventory and chip windows as explicit season rules.
9. Preserve formation, bench priority, and captain fallback rules.
10. Keep unavailable and approximate features visible to the user.

## Data and forecasting

1. Save immutable source bytes and timestamps.
2. Build features as of the FPL deadline, including both fixtures of a double.
3. Exclude same fixture outcomes and unverified historical xP.
4. Fit preprocessing and ensemble weights on training or validation partitions only.
5. Distinguish absent players, blank events, missing rows, and missing statistics.
6. Keep cross season player mappings explicit.
7. Means, medians, quantiles, and confidence statements have different meanings.
8. Expected points are unconditional on appearance; never apply availability twice.
9. Use genuine training and evaluation artifacts before calling a model trained.
10. Never guarantee rank or assume a complex model beats a baseline.

## Application integrity

Fetch provider data through the backend. Construct provider URLs from validated IDs. Do not request arbitrary pasted URLs. Keep source credentials and private manager data out of Git and logs. Use version checks for edits and input fingerprints for jobs and plans.

Long computations run in a recoverable worker. The interface shows job progress and errors. Demo data is clearly synthetic and separate from real data. Optional dependency failures must not break the baseline app.

Do not submit transfers or chips, publish the app, buy data, or add an account integration unless the user asks for that scope. Those actions are not required to implement the local tool.

## Verification

Run checks appropriate to the changes. Critical rules, financial transitions, feature timing, and optimiser validity require meaningful tests. Use offline fixtures for normal CI and a separate optional live provider check.

The planned backend commands are `uv run pytest`, `uv run ruff check .`, and `uv run mypy src` from `backend`. Planned interface commands are `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run test:e2e` from `apps/web`. Create the scripts during scaffolding and keep the documentation consistent with actual commands.

At the end of each requested stage, state what changed, what was actually checked, what remains unavailable, and the next concrete step. Record limitations honestly. Do not rewrite unrelated files or discard existing user changes.

## Collaboration

Use one editing agent per checkout unless the user explicitly requests parallel work. Cursor and Codex can take turns. Before switching tools, update the build status and leave the project runnable.
