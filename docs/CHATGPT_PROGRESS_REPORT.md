# ChatGPT progress report

Updated: 2026-10-12. This is the compact current handoff, not a claim that the full upgrade is complete. Read it before historical audits or execution prompts. Local paths are a file map; a separate ChatGPT conversation needs the relevant files attached or accessible through a connected workspace.

## Current outcome

The local baseline FPL application is usable. The numerical planner remains the strategy champion; research forecasts and policies are inactive. Transfers and chips are executed manually by the user. No account integration, paid data, deployment or model promotion was performed.

The supplied package is preserved byte-for-byte under [reference/supplied/fpl_learning_upgrade/](reference/supplied/fpl_learning_upgrade/README.md). Canonical specifications and implementation records are in [learning_upgrade/](learning_upgrade/README.md). Existing private state, ignored data and unrelated user changes must be preserved.

## Upgrade progress

| Stage | Implemented | Remaining or evidence limit |
| --- | --- | --- |
| D01 | Checkout audit and isolated browser/provider checks | Current private financial/chip state requires actual user inputs; never infer it |
| D02 | Immutable pre-deadline journal, execution distinction, finalized outcome revisions | Real future event finalization and prospective use |
| D03 | Expanding chronological CatBoost folds and separately identified latest serving refit | Small current-era sample; no demonstrated model advantage |
| D04 | Supported-horizon replay, first-action execution, strict provenance checks | Pre-deadline journal seals and strict replay bridge implemented; real finalized prospective policy benchmark unavailable |
| D05 | Frozen full-bootstrap universe option and common-holdout feature ablations | Broad live capture and ongoing finalized labels |
| D06 | Financial transition regressions and official-total-points scoring adapter | More real finalized reconciliation evidence |
| D07 | Future chips/prices, independent validation, exact small-universe and bounded full-catalogue financial dynamic program | 700-player contract verified; large paths cap replacements at two per event/chip week; global full-league optimiser incomplete |
| D08–D09 | Optional Gymnasium environment, fitted-Q, actual five-seed MaskablePPO, durable training jobs | Retained runs test synthetic mechanics; meaningful real policy evidence unavailable |
| D10 | Disabled local review schedules, durable ticks, challenger and promotion gates | No personal schedule enabled or challenger promoted |
| D11 | Authored social benchmark, structured extraction contract, factual reliability | Zero independent human reviews; no semantic model or live Reddit/X collection |
| D12 | Complete-component Bayesian research scoring, real multilead TFT fitting/evaluation, inactive adapters, validation-fit mean ensemble | Inactive registry, audited shadow registration/worker/UI and immutable qualification copies implemented; real calibration, complete producer release packets and baseline/CatBoost ensemble members remain |

## Latest verification

File organisation checks passed: 13 byte-identical archived originals, 130 maintained local links, offline runtime API generation, safe source export, 14 CLI tests, generator lint/format, frontend lint/types/format and 13 unit tests. The full application evidence below is from the preceding implementation stage.

Latest continuation: full backend **414 passed, 3 optional skips**, root CLI **14 passed**, Ruff lint/format and mypy **74 source files** passed. Frontend lint/typecheck, **13 unit tests** and final isolated production build passed. Final production browser suite passed **12 checks, 6 explicit personal-state skips**, covering sequence analysis, visible search limits, saving/reload, journal freezing/actions and shadow gates on desktop/mobile. Optional-library absence passed API/demo/baseline worker/strategy status checks. Eleven journal bridge tests include actual API/worker freeze → seal → strict replay; a 700-player authored sequence passed independent validation. These are mechanics checks, not real prospective policy/model accuracy. Exact evidence: [verification report](learning_upgrade/VERIFICATION_REPORT.md).

See [the repository file map](FILE_STRUCTURE.md) for source, current docs, historical records, generated contracts and ignored runtime data.

## Files to read for a specific question

| Question | Read |
| --- | --- |
| Resume safely; what changed? | [START_HERE](START_HERE.md), [BUILD_STATUS](BUILD_STATUS.md), [root instructions](../AGENTS.md) |
| Full upgrade acceptance and progress | [implementation status](learning_upgrade/IMPLEMENTATION_STATUS.md), [backlog/tests](learning_upgrade/EVALUATION_AND_BACKLOG.md), [PRD](learning_upgrade/PRD_V3.md) |
| Journal, outcomes and recurring reviews | `backend/src/fpl_app/learning/`, `backend/tests/test_learning_journal.py`, `backend/tests/test_learning_review.py` |
| Financial planning and legality | `backend/src/fpl_app/domain/`, `backend/src/fpl_app/optimisation/sequence.py`, `backend/tests/test_sequence_planning.py` |
| Replay evidence | `backend/src/fpl_app/evaluation/strategy.py`, `provenance.py`, `backend/src/fpl_app/learning/replay.py`, `backend/tests/test_journal_replay.py` |
| Research policies and training jobs | `backend/src/fpl_app/strategy/`, `backend/tests/test_strategy_learning.py`, `test_strategy_jobs.py` |
| Forecast fitting, adapters and serving | `backend/src/fpl_app/models/`, `backend/tests/test_strategy_adapters.py`, `test_tft_multilead.py`, `test_forecast_router.py` |
| Social research limits | `backend/src/fpl_app/social/`, `backend/tests/test_social_learning.py`, [social specification](learning_upgrade/SOCIAL_NEXT_STAGE.md) |
| Interface and complete user flows | `apps/web/src/components/`, `apps/web/e2e/`, `apps/web/AGENTS.md` |
| Design choices and conflicts | [DECISIONS](DECISIONS.md) |

Start locally with `bash scripts/dev.sh` after locked dependency installation described in START_HERE. Last verified isolated production preview: port 3148, API 8128, temporary data directory; recheck processes rather than assuming they remain running. Private artifacts are intentionally excluded from this public handoff.

## Work in progress and next actions

D12 audited shadow registration, worker routing, Models controls and immutable qualification copies are implemented. Journal-to-replay seals and bounded full-catalogue sequence scaling are also implemented. Next: audited producer release packets and genuine prospective benchmark assembly. Independent social review, configured semantic extraction, complete producer release packets and real-data calibration remain. Advanced recommendations and promotion stay gated. Private state confirmation remains a separate prerequisite.

The `codex-progress-tracker/` package is a separate documentation-only planning project, not implemented FPL functionality.

## Maintenance and ChatGPT reading prompt

Update this report during meaningful milestones, verification results, blockers or changes to the next action. Keep BUILD_STATUS and implementation status consistent. Record actual checks and distinguish inherited results; do not invent completion percentages, timing estimates, performance or private inputs. Keep the current summary concise and retain detailed history in BUILD_STATUS.

Suggested prompt: “Read CHATGPT_PROGRESS_REPORT.md first, then the linked current status and relevant source/tests provided. Distinguish implemented behavior, checked behavior, research evidence and remaining work. Historical audits and specifications describe earlier state or desired scope. Identify missing files explicitly instead of assuming access from a local path.”

Progress log:

- 2026-10-12: Created this compact handoff and linked ongoing maintenance into the agent workflow. Completed inactive D12 registry discovery and integrity checks, with fresh full backend and focused desktop/mobile verification recorded above.

- 2026-10-12: Implemented audited D12 shadow registration/qualification/worker/UI, pre-deadline journal replay seals and lazy bounded sequence paths over a full catalogue. Fresh full backend: 414 passed / 3 optional skips. Final browser suite: 12 passed / 6 explicit personal-state skips after fixing the locator, exposing returned warnings and awaiting save responses. No real-data promotion or account action.

- 2026-10-12: Organised current guidance, history and unchanged supplied references; moved the design-only schema into reference/contracts, corrected stale handoff paths and made runtime API generation offline and reproducible. Organisation checks passed and are recorded in BUILD_STATUS; full numerical/model/browser evidence remains from the prior build.
