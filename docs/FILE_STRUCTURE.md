# Repository structure

The layout separates application source, operator commands, maintained guidance,
measured evidence and private runtime state. Start with [documentation](README.md).

```text
fpl_build_kit/
├── README.md                   Product overview and quick start
├── AGENTS.md                   Shared agent instructions
├── CONTRIBUTING.md             Development and Git preparation
├── .github/workflows/          Offline CI and browser checks
├── apps/web/                   Next.js interface and frontend tests
├── backend/
│   ├── README.md               Backend module and dependency guide
│   ├── pyproject.toml          Python dependencies and checks
│   ├── uv.lock                 Resolved dependency versions
│   ├── src/fpl_app/             API, domain, models, worker and storage
│   └── tests/                  Backend unit/integration tests
├── scripts/
│   ├── README.md               Stable operator command reference
│   ├── research/               Forecast and evaluation entrypoints
│   └── …                       Launch, verification and export commands
├── tests/                      Operator and repository integration tests
├── docs/
│   ├── README.md               Documentation index
│   ├── START_HERE.md           Development/agent entrypoint
│   ├── BUILD_STATUS.md         Current behavior, checks and next action
│   ├── CHATGPT_PROGRESS_REPORT.md  Concise continuation handoff
│   ├── ROADMAP.md              Maintained priorities
│   ├── DECISIONS.md            Design decisions and resolved conflicts
│   ├── MASTER_PLAN_STATUS.md   Acceptance checklist
│   ├── specs/                  Product and technical contracts
│   ├── operations/             Worker, weekly research and release guides
│   ├── plans/                  Original supplied implementation plans
│   ├── experiments/            Immutable dated evidence and registry
│   ├── archive/                Superseded material and relocation checksums
│   └── local/                  Ignored private notes and operational records
├── data/                       Ignored databases, captures and native artifacts
└── dist/                       Ignored source exports and audit receipts
```

## Application boundaries

[The backend guide](../backend/README.md) maps Python package ownership. Interface
routes live in `apps/web/src/app/`, shared UI in `src/components/`, and client
bindings in `src/lib/api/`. Worker jobs handle long computations; API requests
submit or inspect jobs. Provider requests stay in the backend.

`backend/src/fpl_app/contracts.py` and API request/response models define runtime
contracts. `scripts/generate_api.py` generates `apps/web/openapi.json` and
`apps/web/src/lib/api/schema.d.ts`; do not edit generated bindings manually.

## Placement rules

- Add maintained requirements under `docs/specs/`; operations under `docs/operations/`.
- Add measured evidence in a new dated `docs/experiments/` directory and update its index.
- Keep original reports and supplied plans intact. Record relocations in
  `docs/archive/relocations.json`; update maintained links instead of rewriting history.
- Preserve CLI entrypoints under `scripts/`; import implementation from backend modules.
- Keep source captures, checkpoints, private state and generated datasets under
  ignored `DATA_DIR`. Private notes belong in ignored `docs/local/`.
- Keep installed dependencies, caches and active `.next*` builds on disk; they are
  operational files, not source-tree reorganization targets.

No application package or running-service path was changed by the documentation cleanup.
