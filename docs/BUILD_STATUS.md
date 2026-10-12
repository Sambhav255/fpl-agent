# Current build status

Updated 2026-10-12. Start with [START_HERE](START_HERE.md), [the ChatGPT report](CHATGPT_PROGRESS_REPORT.md) and [the repository file map](FILE_STRUCTURE.md). Earlier stage narratives are preserved in [history](history/README.md); their old blockers/counts do not override this summary.

## Implemented application

The local baseline tool supports public deadline-squad import, explicit private financial/chip corrections, unconditional projections, independently validated planning, manual transfers/chips and versioned saved plans. Baseline forecasts and the numerical planner remain champions.

Learning infrastructure includes immutable deadline journals, action/execution separation, finalized outcome revisions, chronological CatBoost folds/refit, frozen full-universe collection, strict receding-horizon replay with pre-deadline journal seals, official-points scoring, financial/chip/Free Hit transitions, exact small-universe and bounded full-catalogue sequence planning. Large sequences cap replacements at two per event, including chip weeks; global optimality is not claimed. Optional Gymnasium, fitted-Q and five-seed MaskablePPO research, recoverable training jobs and disabled recurring reviews are implemented.

Social research has authored benchmarks, structured extraction contracts and factual reliability. Bayesian complete-component scoring, actual multilead TFT fitting/evaluation, validation-fitted mean ensembles and inactive registry entries are implemented. Reviewed immutable artifact copies, audited shadow bundles, worker routing and Models controls are implemented; registration/queue/publication reject changed, future or incomplete evidence. Planner shows returned limitations and plan assumptions.

## Remaining work

- Complete audited training-to-release packets and baseline/CatBoost ensemble member integration.
- Global full-league optimisation; current full-catalogue paths are bounded.
- Independently reviewed social labels and a configured semantic extractor.
- Genuine chronological calibration and finalized prospective policy benchmarks.
- Current private financial/chip reconciliation from actual user inputs; unknown state is never inferred.

Current-era final labels remain below TFT's eight-event minimum. Research checks do not establish live model accuracy or a strategy advantage. No champion promotion, account actions, paid data or deployment occurred.

## File organisation

Current guidance, specifications, operational contracts, history and original reference material now have separate locations. The supplied upgrade package is byte-preserved under `docs/reference/supplied/fpl_learning_upgrade/`; a checksum manifest verifies all 13 files. Older status/verification narratives are retained under `docs/history/` with rebased Markdown links. The original design-only schema moved to `docs/reference/contracts/openapi-design.json`; runtime OpenAPI and TypeScript bindings are generated together offline using an in-memory store. Stale handoff paths were corrected. Operator entrypoints, app modules, ignored data/private notes, dependencies, caches and running builds remain in place.

Organisation checks passed: all 13 archived files have identical bytes; 130 maintained local Markdown links resolve; offline API generation matches the actual app; the 266-file source export excludes private/runtime folders; 14 root CLI tests, generator Ruff lint/format, frontend lint/types/format and 13 frontend unit tests passed. `git diff --check` passed. No domain behavior changed in this organisation stage.

## Verification and preview

The preceding implementation passed **414 backend tests / 3 optional skips**, **14 root CLI tests**, Ruff lint/format, mypy **74 source files**, **13 frontend unit tests**, lint/format/types/build and **12 production browser tests / 6 explicit personal-state skips**. Optional-library absence was checked in a fresh process. These are prior application checks, not newly rerun during file organisation; [verification](learning_upgrade/VERIFICATION_REPORT.md) records their exact limits.

Last verified isolated preview: http://127.0.0.1:3148, API8128 and a separate worker, `.next-learning-final-verified`, temporary data only. Recheck processes before reuse. Normal startup remains `bash scripts/dev.sh` after locked dependency installation. Next engineering step: audited producer training-to-release pipeline without weakening evidence gates.
