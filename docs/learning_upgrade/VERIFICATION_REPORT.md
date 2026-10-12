# Current verification evidence

Updated 2026-10-12. Earlier stage narratives, commands and counts are preserved in [verification history](../history/VERIFICATION_2026-10-12.md). Current feature scope is in [implementation status](IMPLEMENTATION_STATUS.md) and [BUILD_STATUS](../BUILD_STATUS.md).

## Last application implementation checks

| Check | Result |
| --- | --- |
| Complete backend suite | 414 passed; 3 optional skips |
| Root operator CLI tests | 14 passed |
| Backend lint/format/types | Ruff passed; mypy 74 source files |
| Frontend lint/format/types/build | Passed |
| Frontend unit suite | 13 passed |
| Production browser suite | 12 passed; 6 explicit personal-live-state skips |
| Optional-library absence | API health, demo, baseline worker and strategy status passed with Gym/SB3/Torch/PyMC/ArviZ/Lightning blocked |

These checks preceded file organisation. The isolated browser flow on production3148/API8128 covered corrections → sequence analysis → visible limitations → save/reload → deadline freeze → journal selection/manual execution reporting, plus registry and shadow gates on desktop/mobile. The final run passed after correcting a test locator, displaying omitted backend warnings and awaiting successful save responses before UI assertions.

## Evidence boundaries

- Seventeen advanced-serving contract tests cover API/worker/source/coverage/timing/publication fences, immutable qualification copies, actual authored NetCDF Bayesian sampling and genuinely validation-fitted authored ensemble blending. TFT serving prediction is mocked; separate real-library fit/save/reload tests use authored data.
- Eleven journal bridge tests cover pre-deadline capture, late/mutated evidence, policy-specific seals, deletion and actual API → worker → freeze → seal → strict paper replay. Finalized outcome components remain caller-supplied; no real prospective benchmark is claimed.
- A 700-player authored catalogue produced an independently validated two-event financial path. Two-replacement restrictions apply to large catalogues, including chip weeks; no global full-league optimum is certified.
- Research policy/forecast checks and authored social labels test mechanics and installation, not live accuracy. Independent human review count remains zero.
- Positive advanced real-data browser inference, personal live-state reconciliation and actual finalized prospective policy evaluation remain unavailable. Six browser tests explicitly require opted-in personal state.

Local source/review/journal timestamps are consistency evidence, not external attestations. No account action, promotion, live ingestion, paid data or deployment occurred in the final implementation continuation.

## File organisation checks

New organisation checks passed: 13 unchanged original file checksums, 130 maintained local documentation links, offline OpenAPI/TypeScript generation, exact OpenAPI equality to the runtime app, a 266-file source export with private/runtime folders excluded, 14 root CLI tests, generator Ruff lint/format, frontend lint/types/format and 13 frontend unit tests. `git diff --check` passed. The first generation attempt hit the sandboxed uv cache; using a temporary cache allowed the same command to run without environment changes. Domain behavior and runtime source paths did not change; the full numerical/model/browser suites were not rerun solely for these moves.
