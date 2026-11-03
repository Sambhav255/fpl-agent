# Documentation index

Begin with [START_HERE](START_HERE.md). [BUILD_STATUS](BUILD_STATUS.md) is the authoritative record of current implementation, checks and remaining limits; [CHATGPT_PROGRESS_REPORT](CHATGPT_PROGRESS_REPORT.md) is its concise continuation summary.

| Reference | Purpose |
| --- | --- |
| [Improvement roadmap](ROADMAP.md) | Season strategy, ordered model work and acceptance criteria |
| [Specifications](specs/README.md) | Product, data, architecture, rules sources, learning and serving contracts |
| [File map](FILE_STRUCTURE.md) | Source locations, runtime data and generated artifacts |
| [Decisions](DECISIONS.md) | Recorded design choices and resolved specification conflicts |
| [Operator commands](../scripts/README.md) | Startup, research, scoring and worker operation |
| [Contributing](../CONTRIBUTING.md) | Formatting, verification, contract generation and source exports |
| [Archive](archive/README.md) | Superseded prompts, status, audits, original packages and relocation checksums |

## Measured evidence

Reports under `experiments/` are retained evidence with their original dates, source assumptions and limitations. They do not imply promotion or newly executed checks.

- [3 November: GW9 post-event review and GW10 freeze](experiments/2026-11-03-gw9-post-event/README.md)
- [3 November: rolling model evaluation and frozen selection diagnostics](experiments/2026-11-03-decision-quality/README.md)
- [31 October: deadline model review](experiments/2026-10-31-gw9-model-review/README.md)
- [14 October: prospective replay producers](experiments/2026-10-14-prospective-replay/README.md)
- [13 October: finalized real-football experiments](experiments/2026-10-13-real-football-finalized/README.md)
- Earlier capability reports: [collection](experiments/COLLECTION.md), [CatBoost](experiments/CATBOOST_FOOTBALL.md), [social](experiments/SOCIAL.md), [initial real-football run](experiments/2026-10-13-real-football/README.md).

Immutable reports may mention old documentation locations. Resolve those through the [archive relocation manifest](archive/relocations.json); their bytes were preserved. Private working notes and personal state remain in ignored `docs/local/` and `data/`.
