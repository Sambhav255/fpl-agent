# Build status

Updated 2026-10-10. The baseline application is implemented and locally verified. Advanced ML-backed strategy is the remaining product priority. No advanced model is active. Git preparation does not publish the application or submit FPL actions.

## Ownership

The lead owns integration, contracts, configuration, generated types, dependencies, and release checks. Earlier implementation agents completed their scoped backend, rules, frontend, and model work; independent review findings were addressed. Repository cleanup is performed in the existing checkout, preserving user changes and local data.

## Milestones

| Area | Current state |
| --- | --- |
| Local application | Next.js interface, FastAPI, SQLite and recoverable worker implemented |
| Rules and state | Season configuration, money, formations, transfers, chip inventory, captain fallback and substitutions tested |
| Import and providers | Validated public import, caching, immutable snapshots, manual corrections and unknown-state handling implemented |
| Baseline decisions | Labelled projections, legal lineup, transfer comparisons, weekly plans, persistence and stale-input checks implemented |
| Horizon planning | Up to eight events using bounded beam/HiGHS candidates; frozen prices and approximate terminal policy disclosed |
| Historical/CatBoost | Audit/features/training/evaluation pipeline and retrospective diagnostic artifact; strict activation blocked |
| Bayesian | Real optional sampling pipeline and strict adapter; calibrated minutes/full scoring and real evaluation incomplete |
| TFT/ensemble | Real optional one-event fit/inference pipeline, deadline encoders and adapters; multiweek decoder, real evaluation and ensemble activation incomplete |
| Git preparation | Source formatting, grouped ignores, documentation index, contributor guide and offline CI workflow added |

## Verification

Cleanup backend checks: **194 passed, 3 skipped**; Ruff lint and format checks passed; mypy passed for **34 source files**. Frontend lint, generated route types, typecheck, **11 unit tests**, and the production build passed. Typechecking the clean snapshot also passed without pre-existing Next.js output. Final production Playwright verification passed **14/14 tests** on desktop and mobile, including independent Models display, configured default profile without import, demo corrections, caps, saves, stale state and the real financial gate. Earlier runs exposed an over-specific selector, initial loading races, and a concurrent demo smoke collision; those were corrected, and the final suite ran serially without weakening assertions.

Previous milestone checks: frontend lint/typecheck, **9 unit tests**, production build and **10 production browser tests** passed. Optional real-library checks passed **41 tests** using synthetic fixtures. Public import and live unknown-price gate were verified without submitting transfers or changing unconfirmed private values. Synthetic optional training is not model-performance evidence.

CI is configured but has not yet run on a hosted Git provider. The frontend dependency audit reports five high-severity entries in the development-only Next.js ESLint dependency chain, rooted in the unpatched `braces` advisory. Production-only dependency audit passed with **zero vulnerabilities**. Actual API/worker integration smoke passed again after the API restart. Optional live public-team smoke also passed, including legal lineup persistence and preservation of manager finances.

## Personal-profile and Models fixes

Personal default configuration is read from ignored frontend environment settings; loading it never submits an import or overwrites state. Models now load independently of manager state, with refresh/error handling and clear inactive/diagnostic labels. Repeated identical public imports preserve private corrections and unknowns with CAS protection; changed season, event or ownership returns a review conflict. These behaviors have unit/API tests and independent review.

A private, timestamped baseline strategy report and conditional transfer watchlist are saved locally under ignored `docs/local/`, with live projection/analysis artifacts under `data/`. A legal lineup-only Keep plan is persisted; no transfer or chip was submitted. Budget-valid real transfer search remains blocked by unconfirmed selling values.

## Running services

Final production interface: http://127.0.0.1:3001 (built with `NEXT_BUILD_DIR=.next-release-v2`, served with `NEXT_BUILD_DIR=.next-release-v2 npm run start -- --port 3001` from `apps/web`). Development interface remains at http://127.0.0.1:3000. API was restarted with the tested import fix at http://127.0.0.1:8000; worker remains running. Temporary superseded production servers were stopped.

## Runtime and data

Use `bash scripts/dev.sh` from the repository root. Interface: http://127.0.0.1:3000; API: http://127.0.0.1:8000/docs. The local database is `data/app.sqlite`; source snapshots and analytical/model artifacts also live under ignored `data/`. Existing state and artifacts are preserved. Private historical session notes are retained under ignored `docs/local/`.

## Blockers and exact next steps

1. Obtain deadline-verified historical source bundles, fixtures, deadlines, and explicit cross-season player/club mappings; audit their immutable timestamps.
2. Complete calibrated Bayesian minutes/scoring and TFT multiweek decoding; run genuine chronological training, validation, and untouched-test evaluation.
3. Bind evaluated artifacts, mappings, source versions and input fingerprints into recoverable prediction jobs and registry eligibility; activate only after passing those checks.
4. Fit ensemble weights on eligible validation forecasts and report held-out strategy/model results honestly.
5. Confirm required private financial state in the interface before real transfer recommendations. Unknown values remain blocked.
6. Review the diff and dependency advisory. Existing history contains earlier personal notes; use the clean source snapshot for a new public repository unless publishing that history is intentional. No Git push is performed by this cleanup task.
