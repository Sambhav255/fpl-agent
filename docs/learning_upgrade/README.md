# Learning upgrade

This is the maintained learning-specification and operational-contract directory. Start with [current implementation](IMPLEMENTATION_STATUS.md), [project status](../BUILD_STATUS.md) and [the ChatGPT report](../CHATGPT_PROGRESS_REPORT.md). Specifications describe intended scope; implementation/evidence documents describe actual behavior.

## Product specifications

- [PRD V3](PRD_V3.md): learning workflow and product requirements.
- [RL and learning specification](RL_AND_LEARNING_SPEC.md): evaluation, simulator and policy architecture.
- [Ordered backlog and tests](EVALUATION_AND_BACKLOG.md): delivery and promotion gates.
- [Social next stage](SOCIAL_NEXT_STAGE.md): semantic extraction and reliability requirements.
- [Sources](SOURCES.md): specification references.

## Current operations and evidence

- [Advanced shadow serving](ADVANCED_SERVING.md): reviewed artifacts, immutable input packets and worker/UI operation.
- [Journal replay seals](JOURNAL_REPLAY.md): pre-deadline capture and strict paper replay.
- [Verification report](VERIFICATION_REPORT.md): actual checks and evidence limits.
- [Gameweek review prompt](GAMEWEEK_REVIEW_PROMPT.md): review guidance; never automatic model improvement.
- [Verification probes](verification/README.md): offline authored mechanics and historical results.

## Historical planning material

[The repository audit](LATEST_REPOSITORY_AUDIT.md) and [original master execution prompt](CODEX_MASTER_PROMPT.md) describe the audited earlier checkout and proposed work. Current verified implementation supersedes their obsolete findings. Follow root AGENTS.md for editing/collaboration; the historical prompt does not request extra agents for an ordinary continuation.

The unchanged supplied package, including the combined complete specification, is archived under [docs/reference/supplied/fpl_learning_upgrade](../reference/supplied/fpl_learning_upgrade/README.md). Its combined specification duplicates these individual specs and is kept only in that reference location. Earlier detailed stage narratives are retained in [history](../history/README.md). Private source/model artifacts and manager notes stay ignored, as described in [the file map](../FILE_STRUCTURE.md).

Baseline and the numerical planner remain champions. Independent social review, real calibration/prospective evidence, complete producer release packets and global league optimisation remain unfinished. Authored checks, local reviews and historical assumptions never establish live accuracy or promotion eligibility.
