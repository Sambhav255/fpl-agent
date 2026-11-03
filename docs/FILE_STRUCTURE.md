# Repository file map

Begin with [START_HERE](START_HERE.md). [BUILD_STATUS](BUILD_STATUS.md) describes current implementation and checks; [specifications](specs/README.md) describe requirements.

```text
fpl_build_kit/
├── AGENTS.md                 Shared coding and domain instructions
├── README.md                 Local setup and project overview
├── CONTRIBUTING.md           Verification, contracts and source exports
├── .vscode/settings.json     Shared Explorer/search exclusions
├── apps/web/                 Next.js interface and frontend tests
├── backend/                  FastAPI, worker, models, rules and backend tests
├── scripts/                  Stable operator commands; README.md is the index
│   └── research/             Deadline experiments, frozen scoring and reviews
├── tests/                    Operator CLI integration tests
├── docs/
│   ├── START_HERE.md         Single entry point for users and agents
│   ├── BUILD_STATUS.md       Current state, checks and next work
│   ├── CHATGPT_PROGRESS_REPORT.md
│   ├── DECISIONS.md          Design choices and resolved conflicts
│   ├── ROADMAP.md            Ordered model and decision improvements
│   ├── specs/                Maintained requirements and contracts
│   │   ├── strategy/         Forecasting, planning and social extensions
│   │   └── learning/         Learning, shadow serving and replay contracts
│   ├── experiments/          Immutable dated experiment evidence
│   ├── archive/              Historical instructions, audits and supplied originals
│   └── local/                Ignored private working notes
├── data/                     Ignored runtime and research evidence
└── dist/                     Ignored generated source exports
```

## Application and generated contracts

Backend code is under `backend/src/fpl_app/`: `api`, `jobs`, `providers`, `storage`, `domain`, `features`, `models`, `optimisation`, `evaluation`, `learning`, `strategy` and `social`. Frontend routes are in `apps/web/src/app/`, components in `src/components/` and API bindings in `src/lib/api/`.

`backend/src/fpl_app/contracts.py` and API Pydantic models define the runtime contract. `scripts/generate_api.py` generates `apps/web/openapi.json` and `apps/web/src/lib/api/schema.d.ts` offline from the actual app. Run `npm run generate:api` from `apps/web` after installing locked backend dependencies. The original design snapshot is [archived](archive/reference/contracts/openapi-design.json).

`scripts/dev.sh` launches the local services, `scripts/check.sh` runs project checks and `scripts/export_source.py` produces a source-only archive. Keep operator entrypoint paths stable; [scripts/README](../scripts/README.md) documents available commands.

## Research and immutable evidence

Deadline research uses `scripts/research/deadline_experiments.py`, `freeze_review.py`, `score_forecasts.py` and `post_event_review.py`. Backend modules include `features/deadline.py`, `models/deadline_experiments.py`, `models/points_hurdle.py`, `learning/forecast_benchmark.py` and `learning/post_event.py`. The worker performs durable fitting, finalized scoring and registered final reviews in its matching `DATA_DIR`.

`research/rolling_experiments.py` queues expanding evaluation through `models/rolling_experiments.py`. `research/selection_review.py` registers source-bound shortlists through `evaluation/selection.py` and `learning/selection_review.py`; the worker attaches final selection reviews. `scripts/check_docs.py` verifies archive checksums and local documentation links.

Real-data producers and policy/planning benchmarks remain named entrypoints under `scripts/`; the operator index describes their scopes and evidence modes. Prospective replay uses `run_prospective_journal.py`, `prepare_journal_replay.py`, `evaluate_journal_replay.py` and `learning/{packets,official_replay,paper}.py`.

Preserve ignored `DATA_DIR/{replay_captures,replay_inputs,replay_reports}`, SQLite state and `data/research/` together. They contain source bytes, checkpoints, frozen forecasts, journals and private financial replay reports. Personal screenshots and execution reconciliation remain only in ignored local records. Dependencies, caches and `.next*` builds may be used by running services and are not archival source.

## Documentation boundaries

Active product/data/architecture/build contracts are under `docs/specs/`; essential advanced serving and replay contracts are in `docs/specs/learning/`. Historical status, prompts, audits, old backlogs and handoffs are under `docs/archive/`. [The archive index](archive/README.md) explains authority, supplied-original checksums and the reversible relocation manifest. Experiment reports retain their original bytes and dated assumptions. Neither archived instructions nor earlier test counts override BUILD_STATUS.
