# Start here: coding-agent handoff

Read [the ChatGPT progress report](CHATGPT_PROGRESS_REPORT.md), [build status](BUILD_STATUS.md), [root agent instructions](../AGENTS.md), [upgrade backlog](intelligence_upgrade/IMPLEMENTATION_BACKLOG.md), then the relevant specifications indexed in [docs/README.md](README.md). Preserve ignored data/ and docs/local/; they contain real source/model artifacts and private manager corrections. Existing work is preserved; no account transfer/chip submission, cloud deployment or Git push was performed.

Learning upgrade D02–D10 now has working local infrastructure: immutable journals, finalized outcome revisions, chronological CatBoost folds/refit, full-bootstrap universe capture, supported-horizon replay, official points scoring, future chip/price-path validation, financial sequence search, Gymnasium candidates, actual fitted-Q and five-seed MaskablePPO research, and disabled-by-default recurring reviews. Read [implementation status](learning_upgrade/IMPLEMENTATION_STATUS.md) and the current section of BUILD_STATUS before editing.

Baseline remains the football default and the numerical planner remains the strategy champion. Sequence search is exact only when its declared small-universe state space is exhausted. Large catalogues use two-replacement ordinary paths and complete Wildcard/Free Hit ownership candidates; they stay explicitly bounded without a global certificate. Journals connect to strict replay through [pre-deadline seals](learning_upgrade/JOURNAL_REPLAY.md). Research policies are inactive. D11 has authored benchmark/reliability and structured extractor contracts, but no independent human labels or configured semantic model. D12 has complete-component Bayesian research scoring and real multilead TFT fit/reload/evaluation, with inactive validated artifact adapters and a genuine validation-fit/test-evaluated mean ensemble. Inactive multilead TFT and mean-ensemble artifacts now appear in the research registry with verified report bindings. Audited local shadow registration, worker serving, immutable qualification copies and Models controls are implemented; see [the serving contract](learning_upgrade/ADVANCED_SERVING.md). Reproducible real baseline/CatBoost/ensemble release packets and frozen input producers now work through actual API/worker/browser inference. Real Bayesian/TFT calibration and release qualification remain gated. Read the [finalized real experiment report](experiments/2026-10-13-real-football-finalized/README.md). Never turn these limits into invented outputs.

## Historical context

Preceding football integration and learning-stage details are retained in [build history](history/BUILD_STATUS_2026-10-12.md) and [learning history](history/LEARNING_IMPLEMENTATION_2026-10-12.md). Current verified behavior and limits are in BUILD_STATUS and the ChatGPT report.

## Run and resume

Install with `(cd backend && uv sync --locked)` and `(cd apps/web && npm ci)`. Start all services with `bash scripts/dev.sh`. Prior personal services used dev3000, production3001 and API8000. The latest verified real preview uses production3163/API8163 and an isolated temporary database; its worker is separate. Latest retained copy is ignored data/research/prospective-replay-2026-10-14/; previous real-football copies are preserved. The latest preview was built with NEXT_BUILD_DIR=.next-prospective-replay; the older personal build uses .next-upgrade-final; do not depend on old process IDs.

Research CLI help: `backend/.venv/bin/python scripts/collect_football.py --help` and `backend/.venv/bin/python scripts/prepare_football_forecast.py --help`. Experiment reports are under docs/experiments/. Source and runtime data remain separated; regenerate a clean source snapshot using scripts/export_source.py if publishing without earlier private Git history.

Current verification and exact scope are in BUILD_STATUS and [the verification report](learning_upgrade/VERIFICATION_REPORT.md). Next engineering: score the new sealed baseline GW7 journal with an exact finalized v2 outcome revision, then score the existing CatBoost shadows separately, advance folds and reassess champions. [Automated capture/evaluation evidence and commands](experiments/2026-10-14-prospective-replay/README.md) replace manual baseline replay assembly. Independent social review/semantic extraction and real Bayesian/TFT calibration remain gated. Six finalized current-era events are below TFT’s eight-event chronological minimum. Do not claim synthetic checks, historical assumptions or untrained pipelines are live model accuracy.

Read [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for the complete layout, generated API contract workflow and preserved original package location.

## Repository boundaries

- `apps/web/`: interface and browser/unit tests; read its AGENTS.md before edits.
- `backend/`: API, worker, domain rules, model code, migrations and backend tests.
- `scripts/` and `tests/`: operator commands and their integration/CLI tests.
- `docs/`: canonical specifications, contracts, decisions, experiment reports and this handoff.
- `data/`, `docs/local/`, `.env.local`: ignored persistent/private local state; preserve them.
- Dependencies, `.next*`, caches and test output are local generated files, not source. Existing build folders may be referenced by a live process or generated Next.js types.

Use current BUILD_STATUS rather than original execution prompts or historical audit claims to decide what remains. As meaningful progress changes, update CHATGPT_PROGRESS_REPORT. After each stage update BUILD_STATUS and this handoff if the startup procedure or next actions change. Do not commit private data or describe previous checks as newly run.
