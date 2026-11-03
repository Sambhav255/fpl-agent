# Runtime and integration contracts

The authoritative runtime types are `backend/src/fpl_app/contracts.py` and the Pydantic request/response models in `backend/src/fpl_app/api/`. Generate the frontend OpenAPI snapshot and TypeScript bindings from the actual app; see [CONTRIBUTING](../../CONTRIBUTING.md). The [archived initial contracts](../archive/contracts/CONTRACTS_2026-11-03.md) and [upgrade contract](../archive/contracts/UPGRADE_CONTRACTS_2026-11-03.md) preserve implementation history, including obsolete agent ownership assignments.

## Integrity requirements

- Store money in integer tenths of a million and points separately. Preserve unknown financial and chip state. Public imports are deadline evidence, not proof of current private state.
- State edits require the expected version; queued jobs and plans bind input fingerprints. Keep immutable source bytes, actual observation times, source hashes and explicit player coverage.
- Distinguish requested and resolved forecast providers. Baseline is the default. Advanced selection requires a specific immutable artifact and explicit experimental, shadow or recorded promotion mode.
- Queue references bind artifact, source, mapping, implementation, origin and horizon. Retries reject mutated inputs rather than resolving a new latest artifact. Missing uncertainty remains unavailable.
- Collection may create retained observations and labels; it must not silently alter manager state. Preliminary outcomes cannot become finalized fitting or scoring targets.
- Expected points are unconditional on appearance. Preserve complete double fixtures, blanks and missing data separately. Apply availability once.
- Lineup analysis may use unknown finances; affected transfer recommendations remain blocked. Independent rules and financial validation runs after solving.
- Planner claims match declared search coverage. An exact small-universe oracle does not prove a large-catalogue plan globally optimal.
- Social collection requires permitted access and deletable lineage. Offline authored examples are synthetic; disabled Reddit/X adapters and zero social points adjustments remain visible.

Read the [data specification](DATA_AND_MODEL_SPEC.md), [forecasting/planning extension](strategy/ML_DATA_AND_PLANNING_SPEC.md), [advanced serving](learning/ADVANCED_SERVING.md) and [journal replay](learning/JOURNAL_REPLAY.md) for detailed evidence and publication requirements. Current availability and actual verification belong in [BUILD_STATUS](../BUILD_STATUS.md).
