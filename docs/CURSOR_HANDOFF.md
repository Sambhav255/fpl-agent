# Continuation handoff

Read BUILD_STATUS.md first, then root AGENTS.md, docs/intelligence_upgrade/IMPLEMENTATION_BACKLOG.md and the relevant specifications. Preserve ignored data/ and docs/local/; they contain real source/model artifacts and private manager corrections. Existing work is preserved; no account transfer/chip submission, cloud deployment or Git push was performed.

## Latest verified stage

Football collection CLI and recoverable jobs, an actual trained/reloaded Football CatBoost experimental adapter, immutable serving bundles, scoped candidate coverage, Models-page comparison UI, disabled social status, and explicit future availability scenarios are integrated. Baseline stays default. Full multi-event/chip optimisation and all-family promotion remain incomplete.

The prepared GW7 artifact is football_catboost/20261012T043103-339bf843. It uses final GW1–5 labels only; incomplete GW6 is excluded. Its tiny assumed-timing test did not beat the population comparator, so do not promote it. Actual source catalogue bytes match retained training observations. The private manager state remains the prior GW6 state and is intentionally stale after the live dataset refresh. Reconcile current squad, event and private inputs before registering/serving or recommending transfers; never infer bank, selling values, chips or free transfers.

Independent review found and accepted fixes for rollover reconfirmation and untouched selling-price market anchors. Unstarted-match placeholder zeros now become pending observations with null normalised outcomes. Baseline future injury endpoints are separate scenarios, not calibrated probabilities or point quantiles.

Checks actually run: backend292passed3skipped, Ruff/format/mypy47source files; rootCLI13tests; frontend13unit tests, lint/typecheck/format and production build;16desktop/mobile production browser tests. Actual API/worker collection succeeded without changing personal state. Latest results and exact next actions are in BUILD_STATUS.md.

## Run and resume

Install with `(cd backend && uv sync --locked)` and `(cd apps/web && npm ci)`. Start all services with `bash scripts/dev.sh`. Current dev3000, production3001, API8000/docs and separate worker are running. The current production build uses NEXT_BUILD_DIR=.next-upgrade-final; do not depend on old process IDs.

Research CLI help: `backend/.venv/bin/python scripts/collect_football.py --help` and `backend/.venv/bin/python scripts/prepare_football_forecast.py --help`. Experiment reports are under docs/experiments/. Source and runtime data remain separated; regenerate a clean source snapshot using scripts/export_source.py if publishing without earlier private Git history.

Next engineering: broader prospective football evaluation; full multi-event financial/chip continuation; audited policy replay; full Bayesian player scoring/minutes; multiweek TFT and eligible ensemble. Five completed current-era events are below TFT’s eight-event chronological minimum. Do not claim synthetic checks, historical assumptions or untrained pipelines are live model accuracy.
