# Frozen journals as replay inputs

Implemented 2026-10-12. `backend/src/fpl_app/learning/replay.py` connects a deadline-frozen decision to the existing strict replay engine. It does not regenerate historical evidence or treat the recommended action as actual execution.

The baseline champion now has a reproducible producer. With an existing reviewed paper portfolio, the same ignored DATA_DIR for API/worker/command, and an isolated API port, run from the repository root:

```sh
DATA_DIR=/private/tmp/fpl-prospective-replay \
  /private/tmp/fpl-research-base/bin/python scripts/run_prospective_journal.py \
  --team-id 2000000001 --api-port 8163 --horizon 6 --policy all
```

That ID is a hypothetical research portfolio, not an imported account. The command checks API/store identity, captures source receipts and exact baseline/policy package bytes plus generated mappings, queues a fresh forecast, waits for the recoverable worker, requests analysis, freezes the decision and produces/seals each policy packet. Unknown private state or stale snapshots keep their existing gates. Actual execution is never inferred. Ordinary requests preserve existing queue fingerprints; an explicit replay capture creates a distinct forecast identity so older runs are not overwritten.

For separate stages use `scripts/prepare_journal_replay.py capture --team-id <id> --horizon 6 --policy all --enqueue`, then normal analysis/journal freeze, then `seal --decision-id <id> --capture-id <captured-id> --policy keep` (repeat for planner/proxy). Receipt availability is recorded only after capture completes. Source copies retain original actual provider receipt times; new code/mapping capture receives the actual current time. Old forecasts cannot qualify using a newly created capture. Packets publish atomically; incomplete staging directories remain separate and a retry preserves prior complete artifacts. Keep DATA_DIR's SQLite **and artifact directories** for full restoration; JSON backup exports capture/seal references.

Other providers retain the existing `ReplayManifest` contract; this baseline producer does not waive their release/input/timing gates. A manually retained packet must bind the exact frozen forecast, players, deadline and decision origin, complete schedule including blanks, policy implementation and all model payload bytes. Never relabel reconstructed historical assumptions as verified publication evidence.

Before the actual deadline, run:

```sh
backend/.venv/bin/python scripts/seal_journal_replay.py \
  --decision-id <frozen-decision-id> --packet-id <packet-id> \
  --manifest-sha256 <already-captured-manifest-sha256> --policy keep
```

Policies supported by the command are `keep`, `planner` and `proxy`. Each policy requires its own bound packet/seal. The seal records the actual current local time, immutable journal digest, manifest digest and policy identifier under a reserved SQLite write transaction. It accepts no caller-supplied seal timestamp. Unsafe paths/symlinks, changed files/code, mismatched journal inputs and late capture fail. Repeating an existing valid seal is idempotent, including after the deadline. An old unsealed journal stays ineligible for prospective evidence.

After the actual provider marks the event `finished` and `data_checked`, queue its normal outcome review. Select an **exact** persisted revision from that job; no command silently chooses “latest”:

```sh
DATA_DIR=/private/tmp/fpl-prospective-replay \
  /private/tmp/fpl-research-base/bin/python scripts/evaluate_journal_replay.py \
  --decision-id <sealed-decision-id> --outcome-revision <revision-sha> --policy all
```

`official_replay_inputs` independently rederives the selected official total-points/minutes revision from the retained bootstrap, fixture and live-result snapshots, checking their hashes, capture chronology, finalized status, exact frozen player coverage and schedule membership. Preliminary/pending, reassigned fixtures, previously blank clubs that acquire fixtures, missing results and ambiguous zero-minute cards/points fail the strategy gate. Unknown card statistics remain unknown, not absence. Old v1 scorecards are preserved and need a newly checked v2 revision for this adapter. Policies never receive outcomes.

The command compares the selected paper policies on the identical origin/state and writes immutable reports only under ignored DATA_DIR/replay_reports. Publication checks journal/revision/state fingerprints. It edits neither manager state nor execution records, fits no model and selects no winning policy for promotion. Reports include hypothetical financial transitions and must remain private. One event does not establish independent-season performance. The lower-level component-based `journal_replay_inputs` remains supported for callers with complete validated MatchStats.

The benchmark replays hypothetical policy actions from the frozen initial financial state. Later origins use their own frozen forecasts, with the engine's counterfactual financial transitions. Financial coverage is labelled `journal_known_prices_only`: known origin quotes are retained, but no realistic historical future price path is inferred. Actual selected/executed/paper actions remain separate journal records. The seal and replay calls do not edit live manager state. Team deletion removes its private SQLite seals; generic backup includes them.

Local timestamps and operator-authored manifests are retained consistency evidence, not external attestation. This bridge supplies prospective capture infrastructure, not a completed real prospective benchmark or policy advantage. Eleven authored tests cover positive strict replay, late sealing, missing/policy-specific evidence, changed journal/manifest/payload/seal, conflicting references, symlinks, team deletion and an actual API → worker → journal freeze → seal → replay flow.
