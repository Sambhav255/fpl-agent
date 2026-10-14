# Prospective replay producer evidence

Actual continuation verified 14 October 2026 UTC. This extends the [retained real-football experiment](../2026-10-13-real-football-finalized/README.md); it performs no new real football refit or champion promotion. Authored tests verify mechanics, while the retained official data and actual API/worker/browser run verify future capture and serving. None is a completed prospective performance test.

The final-code command captured source receipts, exact baseline/policy package bytes and generated mappings before prediction **2026-10-14T03:55:56.105461Z**. It queued a baseline forecast, analysed it, froze the hypothetical portfolio's GW7 journal at **03:56:05.936939Z**, and sealed keep/planner/proxy packets before the official **17 October 10:00 UTC** deadline. Coverage is **667 players / 4,002 fixture means / six events**. Five plans passed independent validation. Financial starts are hypothetical; no actual team, bank, purchase prices, transfers or chips were inferred. Actual execution remains unknown.

A fresh official status snapshot observed provider current GW6/next GW7. The `finished=false` and `data_checked=false` fields in integration.json refer to **GW7**. The completed GW6 training collection remains the earlier immutable revision. Zero outcome revisions exist for the new journal. Historical assumptions in existing CatBoost research are preserved. Earlier unsealed shadows are not retroactively made strict, and captures rejected after a code change remain retained without qualification.

The baseline producer verifies catalogue reconstruction from original official bytes, horizon/schedule/player identity, package and file digests, completed capture availability, and identical recomputed baseline projections. Queued jobs recheck evidence, normal requests retain prior baseline fingerprints, and explicit captures produce separate run IDs. Packet publication is atomic and interrupted staging copies do not prevent retry. SQLite backup exports capture/seal references; full restoration also requires the ignored artifact directories.

Official outcome schema v2 reconciles totals/minutes, duplicate/type checks, schedule membership and source receipts. Unknown fixture statistics/card participation stay unknown. Changed schedules, missing universe rows and ambiguous zero-minute cards/points block strict strategy replay. Old v1 revisions remain intact and need a new checked v2 review. The scoring command takes an exact revision, independently rebuilds it from retained official bytes, verifies the policy seal and fences report publication. Policies never receive outcomes, and private replay reports include hypothetical financial transitions only under ignored DATA_DIR.

| Fresh check | Result |
| --- | --- |
| Locked base backend | 464 passed / 11 skips |
| Locked RL backend | 480 passed / 7 skips |
| Root CLI | 14 passed |
| Ruff lint/format; mypy | Passed; 126 backend files formatted; 81 source files in both environments |
| Frontend format/lint/types/unit/production build | Passed; 13 unit tests |
| Actual production browser/API/worker | 16 passed / 6 explicit personal-state skips |

Fifty-one new authored cases cover official revisions (29), capture packets (15) and paper CLI flows (7). The unchanged base/RL skip difference enables 16 optional cases; shared Bayesian/TFT/opt-in skips remain. Gymnasium, Torch, PyMC and TFT libraries are absent from the actual base worker. Existing 115 locked-stack deprecation warnings are unsuppressed. Earlier attempts recorded a loaded solver timeout, a CLI/API default-payload mismatch, a forecast-response synchronization failure and ENOSPC during a model write/browser trace close. The payload/response issues were fixed without weakening assertions. Owned uv download cache was cleared while installed environments, sources, datasets, artifacts and personal state were preserved. Final affected full suites passed, with native fitting and browser verification run sequentially after the space incident.

## Reproduce

Start a separate API and worker against the same reviewed isolated DATA_DIR; use the standard backend `fpl_app.api.main:app` and `python -m fpl_app.jobs.worker` entry points. No account import is required. Existing verified preview is production **3163**, API **8163**, build `.next-prospective-replay`. Recheck processes instead of relying on saved PIDs.

```sh
export DATA_DIR=/private/tmp/fpl-prospective-replay
export UV_PROJECT_ENVIRONMENT=/private/tmp/fpl-research-base
uv sync --locked --project backend
uv run --locked --project backend python scripts/run_prospective_journal.py \
  --team-id 2000000001 --api-port 8163 --horizon 6 --policy all
```

In separate terminals start the same store and the already built production interface:

```sh
DATA_DIR=/private/tmp/fpl-prospective-replay UV_PROJECT_ENVIRONMENT=/private/tmp/fpl-research-base \
  uv run --locked --project backend uvicorn fpl_app.api.main:app --host 127.0.0.1 --port 8163
DATA_DIR=/private/tmp/fpl-prospective-replay UV_PROJECT_ENVIRONMENT=/private/tmp/fpl-research-base \
  uv run --locked --project backend python -m fpl_app.jobs.worker
(cd apps/web && BACKEND_URL=http://127.0.0.1:8163 NEXT_BUILD_DIR=.next-prospective-replay \
  npm run start -- --port 3163)
```

The example ID is a hypothetical portfolio already present in the isolated research copy. A normal reviewed state retains its existing staleness/financial gates. Separate steps are available through `prepare_journal_replay.py capture --enqueue` and `seal`; see [the complete contract](../../learning_upgrade/JOURNAL_REPLAY.md).

After actual official finalization, request `/api/v1/learning/decisions/<decision-id>/outcomes`, wait for its recoverable worker and retain the exact returned revision. Then:

```sh
uv run --locked --project backend python scripts/evaluate_journal_replay.py \
  --decision-id <sealed-id> --outcome-revision <exact-revision-sha> --policy all
```

That command produces an immutable private report, changes no manager/action/model record and does not choose a promotion. Code changes deliberately fail an old seal; use its retained exact package in an isolated checkout for that comparison rather than revising its timestamps or manifest.

Checks from backend use the selected locked environment: `uv run --locked pytest`, `uv run --locked pytest ../tests`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, and `uv run --locked mypy src`. Sync `/private/tmp/fpl-research-rl` with `--extra rl` and use `uv run --locked --extra rl` for **every** backend command in that environment; omitting the extra would prune optional RL packages during synchronization. Frontend uses `npm run format:check`, `lint`, `typecheck`, `test -- --maxWorkers=1`, and `BACKEND_URL=http://127.0.0.1:8163 NEXT_BUILD_DIR=.next-prospective-replay npm run build`.

```sh
cd apps/web
E2E_BASE_URL=http://127.0.0.1:3163 \
REAL_SHADOW_TEAM_ID=2000000001 \
PROSPECTIVE_REPLAY_TEAM_ID=2000000001 \
PROSPECTIVE_REPLAY_DECISION_ID=ff89f35c18e1d52b9c272b3325132393bcb4de6af9cc2d0ff62023ad43f8c51c \
npm run test:e2e
```

`manifest.json` binds integration.json and verification.json plus command source checksums. Report receipts contain no actual private manager state. Durable ignored backup: `data/research/prospective-replay-2026-10-14/`, including consistent SQLite backup, model/input artifacts, captures, complete replay packets and actual verification logs. The active temporary copy remains available. Private financial replay outputs must never be copied into public reports.

Remaining prerequisites are future finalized outcomes, additional chronological data for multilead/TFT evaluation, real Bayesian/TFT calibration and release evidence, independent social review/configuration, and actual user-confirmed private state. Baseline/numerical champions remain unchanged. No transfer/chip submission, paid data, deployment, Git push or actual-team exploration occurred.
