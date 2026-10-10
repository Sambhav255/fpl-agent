# FPL intelligence upgrade kit

Prepared 10 October 2026 for Sambhav's existing FPL application. Audit baseline: `e759bcfb299d3f818d2e80ebb017796874cf8019`.

## Main conclusion

The existing app uses an approximate forecast and has useful infrastructure, but its advanced model code does not power prediction jobs. The transfer search also has a reproduced objective mismatch. Prioritise real data, evaluation, routing and planning before more visual work.

## Files

| File | Purpose |
| --- | --- |
| REPOSITORY_AUDIT.md | Evidence, limitations and 16 specific findings |
| FPL_PRD_V2.md | Updated product scope and release gates |
| ML_DATA_AND_PLANNING_SPEC.md | Data, three model families, serving, evaluation and long horizon planning |
| SOCIAL_INTELLIGENCE_SPEC.md | Semantic claims, expert versus crowd consensus, access and evidence controls |
| IMPLEMENTATION_BACKLOG.md | Twelve implementation tasks and acceptance criteria |
| CODEX_EXECUTION_PROMPT.md | Copyable execution instructions with multiple agents |
| SOURCES.md | Pinned code evidence and primary external references |
| verification/ | Portable review probes and recorded synthetic results |
| FPL_INTELLIGENCE_UPGRADE_COMPLETE.md | Combined Markdown copy for convenient reading |

## Use in Cursor

Copy this folder into the project as `docs/intelligence_upgrade/`. Do not overwrite the working source, original specifications, manager state or local data. Give Codex `CODEX_EXECUTION_PROMPT.md`.

This kit revises the forecasting, strategy and social scope of the original specifications. Current official rules and existing integrity requirements remain controlling. Compare the current branch with the audited commit before treating a finding as still present. Use the individual files for implementation; do not read the combined file again unless needed.

The first intelligence release consists of B01 through B06: reproduce and fix the funding pair miss, collect real data, evaluate CatBoost, wire the serving router and run strategy replay. Social extraction can proceed independently with synthetic examples while live access is pending.

## Verification limits

The audit parsed all 47 Python files and ran two synthetic behavioural probes against actual repository source. It did not rerun the entire application suite, train real models, or evaluate the private team. The seven point synthetic search gap is a software counterexample, not a real world performance estimate.

No model improvement, expert reliability or rank gain is claimed without future measurement.
