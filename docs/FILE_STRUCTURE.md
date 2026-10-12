# Repository file map

Start with [START_HERE](START_HERE.md), [current status](BUILD_STATUS.md) and [the ChatGPT report](CHATGPT_PROGRESS_REPORT.md). Specifications describe intended scope; status documents describe implemented and checked behavior.

```text
fpl_build_kit/
├── AGENTS.md                 Coding and domain instructions
├── README.md                 Setup, commands and capabilities
├── CONTRIBUTING.md           Contribution and contract workflows
├── apps/web/                 Next.js app, frontend tests and generated API types
├── backend/                  Python API, worker, models, domain and backend tests
├── scripts/                  Stable operator entrypoints and repository checks
├── tests/                    Operator CLI integration tests
├── docs/
│   ├── START_HERE.md          Resume guide
│   ├── BUILD_STATUS.md        Current state and next work
│   ├── CHATGPT_PROGRESS_REPORT.md
│   ├── FILE_STRUCTURE.md      This map
│   ├── learning_upgrade/     Maintained learning specs, contracts and verification
│   ├── intelligence_upgrade/ Maintained earlier strategy specs and audit context
│   ├── experiments/          Experiment reports and evidence limits
│   ├── history/              Superseded build/implementation/verification narratives
│   ├── reference/            Original prompts, supplied packages and design contracts
│   └── local/                Ignored private working notes
├── data/                     Ignored SQLite state, sources, features and model artifacts
└── dist/                     Ignored generated exports
```

The product/data/architecture/build specifications stay directly under `docs/` at the paths used by AGENTS.md. Active backend modules stay under `backend/src/fpl_app/`: `api`, `jobs`, `providers`, `storage`, `domain`, `features`, `models`, `optimisation`, `evaluation`, `learning`, `strategy` and `social`. Frontend routes live under `apps/web/src/app/`, UI components under `src/components/`, and API bindings under `src/lib/api/`.

## Contracts and commands

`backend/src/fpl_app/contracts.py` and the API's Pydantic request/response models define the runtime contract. `apps/web/openapi.json` and `apps/web/src/lib/api/schema.d.ts` are generated from the current app. Run `npm run generate:api` from `apps/web` after installing the locked backend dependencies; it generates offline using an in-memory store. The original design-only JSON is preserved at `docs/reference/contracts/openapi-design.json`.

Keep operator scripts at their existing paths so README/CI commands remain stable. `scripts/generate_api.py` generates the runtime OpenAPI snapshot; `scripts/dev.sh` launches local services; `scripts/check.sh` runs project checks; `scripts/export_source.py` creates a source-only archive. Football collection/forecast and learning/review commands remain named entrypoints in the same directory.

## Preserved originals and history

The supplied root `fpl_learning_upgrade/` package moved to [reference/supplied/fpl_learning_upgrade/](reference/supplied/fpl_learning_upgrade/). The duplicate combined specification was removed from the maintained directory after verifying the complete original remains in this archive. Every original file retained identical bytes, verified against [its checksum manifest](reference/supplied/fpl_learning_upgrade.sha256.json). Use the maintained `docs/learning_upgrade/` copy for current instructions; the original contains obsolete paths and audit assumptions.

[History](history/README.md) retains all preceding status narratives, with Markdown links rebased to their new location. Earlier test counts remain historical evidence and are not newly run checks. A separately described Codex progress tracker is absent from this checkout; its historical description does not imply an implemented package here.

Dependencies, `.next*` builds, caches, test output, private notes, environment files and runtime data are deliberately outside the source organisation. They may be used by running services and were not moved or deleted. Git's existing unrelated edits/deletions remain intact.
