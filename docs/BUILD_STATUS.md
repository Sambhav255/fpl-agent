# Current build status

Updated 31 October 2026 UTC. Read [START_HERE](START_HERE.md), [HANDOFF](HANDOFF.md), and the [experiment report](experiments/2026-10-31-gw9-model-review/README.md). Earlier technical evidence is retained in [history](history/BUILD_STATUS_2026-10-30.md); personal decision notes and their originals are ignored local records.

## Model and learning work

- Fresh official capture: 669 players, 671 retained snapshots, 5,220 finalized GW1–8 player-fixture labels.
- Executed: six-event baseline; four-fold CatBoost evaluation and separate current refit; genuine TFT mean/quantile research fit and current refit; Bayesian team-goal held-out evaluation and extended converged refit; validation-fitted ensembles; fitted-Q and five-seed MaskablePPO research.
- Four genuine pre-GW7 journals were scored against exact finalized official revisions. The saved ensemble had lower error than saved baseline captures on that event; origins differ and no promotion follows.
- Eight additional fixed variants tested opportunity, xG/xA, defensive actions, rest/team context, regularization and a second seed. Settings were registered before fitting; historical GW7–8 results are explicitly exploratory because those blocks were inspected earlier. The validation-selected configuration and ensemble were frozen for genuine GW9 evaluation.
- Current frozen evidence: three benchmark bundles, 28 player-mean streams and one Bayesian team-goal stream. First automatic finalized-data check is 3 November at 12:00 UTC, with six-hour retries while the matching local worker runs.

## Runtime behavior

The normal worker polls enabled weekly reviews and due benchmark scorecards once per minute. Review jobs use leases, heartbeats, input fingerprints and immutable output publication. The first locally enabled weekly capture/evaluate/CatBoost-refit job succeeded and preserved the manager-state fingerprint. Separate research data requires a worker with that same `DATA_DIR`; see [operator commands](../scripts/README.md).

Scoring waits for official `finished` and `data_checked`, retains fresh source bytes, reports missing outcomes and schedule changes, compares shared player coverage and preserves original predictions. It does not silently promote a model or submit an account action.

## Limits

The baseline and numerical optimiser remain champions. Current CatBoost supports one lead; longer baseline forecasts are conditional scenarios. Bayesian full player scoring remains blocked by incomplete component evidence. TFT research uses explicit historical timing/schedule assumptions; strict production qualification remains blocked. Tiny model differences do not establish better forward choices or rank gains. Actual private account state remains a separate confirmation requirement.

## Verification

| Actual final check                                         | Result                                                      |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| Backend full installed suite                               | **498 passed / 3 skipped**; 132 dependency warnings         |
| Backend Ruff / format / mypy                               | Passed; mypy 84 source files                                |
| Root operator and source-export tests                      | **16 passed**                                               |
| Frontend formatting / lint / typecheck                     | Passed                                                      |
| Frontend unit tests / production build                     | **13 passed**; Next.js 16.4.3 build passed                  |
| Isolated production desktop/mobile browser suite           | **12 passed / 10 configuration-dependent skips**            |
| Actual isolated API + worker smoke                         | Passed                                                      |
| Runtime npm audit                                          | **0 vulnerabilities**                                       |
| Full npm audit                                             | **18 moderate development-tool findings**; no high/critical |
| Python dependencies / documentation links / Git whitespace | Passed                                                      |

Browser skips require explicit private-team or reviewed real-shadow fixtures, which were absent from the isolated demo run. No live personal browser claim is made. Earlier verification counts remain historical. [Machine-readable verification](experiments/2026-10-31-gw9-model-review/verification.json).

## Repository preparation

Current documentation is consolidated around this status page, START_HERE, HANDOFF and FILE_STRUCTURE. Private originals were backed up under ignored local records. Duplicate root handoff material was moved intact into that local backup; canonical supplied material remains available. Build artifacts and dependencies are hidden in the editor through workspace settings. Existing Git history retains older personal notes, so source-only packaging is the publication boundary.

The audited source export also has a separate publication checkout with a clean local initial commit and no remote. Next: follow HANDOFF from that checkout for destination and push review, then score frozen GW9 predictions in the original research workspace after official finalization before further model selection or refitting. No push was performed.
