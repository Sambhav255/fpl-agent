# Documentation archive

This archive preserves historical context. Start with [the current guide](../START_HERE.md), root [AGENTS.md](../../AGENTS.md) and [current status](../BUILD_STATUS.md). Archived prompts, ownership assignments, module paths, audit findings, backlogs and test counts are not instructions for the current checkout.

| Directory | Preserved material |
| --- | --- |
| [history](history/README.md) | Earlier implementation, build status and verification narratives |
| [upgrades/intelligence](upgrades/intelligence/README.md) | October strategy audit, original execution prompt, backlog, source notes and probes |
| [upgrades/learning](upgrades/learning/README.md) | October learning audit, prompts, implementation status, backlog, verification and probes |
| [handoffs/gw7](handoffs/gw7/README.md) | Original GW7 handoff and external review |
| [November handoff](handoffs/HANDOFF_2026-11-03.md) | Superseded continuation and publication preparation notes |
| [reference](reference/README.md) | Supplied original learning package, original milestone prompts and API design snapshot |
| `contracts/` | Superseded initial and upgrade integration notes |

Current product and operational contracts were moved into [specs](../specs/README.md), including the essential advanced-serving and journal-replay contracts. Runtime state, private records and model artifacts remain ignored outside this archive. `docs/experiments/` remains unchanged as immutable measured evidence.

## Relocation verification

[relocations.json](relocations.json) records all 67 moved files, original and relocated SHA256 hashes, byte sizes and exact Markdown link substitutions. Reversing those substitutions reconstructs every original byte; archive prose and recorded results were not discarded. Supplied originals remain byte-identical and retain [their original package manifest](reference/supplied/fpl_learning_upgrade.sha256.json). Their old wording and paths are intentionally historical.

Markdown links in browsable historical records were rebased. Paths written as code, old repository URLs and historical commands retain their original meaning. Immutable experiment reports and supplied originals may still link to former locations; use `previous_path` → `path` in the relocation manifest instead of treating those references as current commands. Running archived probe scripts is optional historical investigation, not part of normal CI.
