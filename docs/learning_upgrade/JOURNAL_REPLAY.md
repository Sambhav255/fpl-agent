# Frozen journals as replay inputs

Implemented 2026-10-12. `backend/src/fpl_app/learning/replay.py` connects a deadline-frozen decision to the existing strict replay engine. It does not regenerate historical evidence or treat the recommended action as actual execution.

Prepare the existing `ReplayManifest` contract and source/model/policy/mapping bytes under ignored `DATA_DIR/replay_inputs/<packet-id>/manifest.json`. Its forecast, players, deadline and information time must exactly match the frozen journal; information time is `decision_origin`. Include complete schedule declarations through the supported horizon, including blanks. Bind the policy's exact identifier/source and the package implementation digest. All evidence availability and model timing gates still apply. See the replay contract in [implementation status](IMPLEMENTATION_STATUS.md).

Before the actual deadline, run:

```sh
backend/.venv/bin/python scripts/seal_journal_replay.py \
  --decision-id <frozen-decision-id> --packet-id <packet-id> \
  --manifest-sha256 <already-captured-manifest-sha256> --policy keep
```

Policies supported by the command are `keep`, `planner` and `proxy`. Each policy requires its own bound packet/seal. The seal records the actual current local time, immutable journal digest, manifest digest and policy identifier under a reserved SQLite write transaction. It accepts no caller-supplied seal timestamp. Unsafe paths/symlinks, changed files/code, mismatched journal inputs and late capture fail. Repeating an existing valid seal is idempotent, including after the deadline. An old unsealed journal stays ineligible for prospective evidence.

For a finalized paper comparison, call `journal_replay_inputs(store, decision_id, policy, outcomes)` and pass its returned initial manager state and `ReplayOrigin` to `replay_policy`. The bridge loads the saved checksum from the seal and rechecks the packet and journal. The report retains journal/seal digests alongside strict provenance. Outcome components are caller-supplied, must be finalized and complete, and are never given to the policy. The bridge does not itself ingest or attest those labels; use the existing finalized outcome review before assembling a benchmark.

The benchmark replays hypothetical policy actions from the frozen initial financial state. Later origins use their own frozen forecasts, with the engine's counterfactual financial transitions. Financial coverage is labelled `journal_known_prices_only`: known origin quotes are retained, but no realistic historical future price path is inferred. Actual selected/executed/paper actions remain separate journal records. The seal and replay calls do not edit live manager state. Team deletion removes its private SQLite seals; generic backup includes them.

Local timestamps and operator-authored manifests are retained consistency evidence, not external attestation. This bridge supplies prospective capture infrastructure, not a completed real prospective benchmark or policy advantage. Eleven authored tests cover positive strict replay, late sealing, missing/policy-specific evidence, changed journal/manifest/payload/seal, conflicting references, symlinks, team deletion and an actual API → worker → journal freeze → seal → replay flow.
