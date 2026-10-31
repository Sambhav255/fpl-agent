# Commit and publishing handoff

Start with [START_HERE](START_HERE.md), [BUILD_STATUS](BUILD_STATUS.md), and [FILE_STRUCTURE](FILE_STRUCTURE.md). The current experiment results and limits are in the [31 October report](experiments/2026-10-31-gw9-model-review/README.md).

## Changes to review

- Real model review and eight registered deadline ablations, including lagged xG/xA, defensive actions, rest and team context.
- Durable frozen forecast scoring: official finalization gates, source retention, matched coverage, missing/schedule-change handling and six-hour retries.
- Worker polling for enabled learning schedules and due forecast checks.
- Research commands grouped under `scripts/research/`, with a [command index](../scripts/README.md).
- Current documentation shortened; historical engineering records separated from ignored personal notes. Duplicate root handoff material preserved in ignored backups.
- Shared editor exclusions hide dependencies, model data and generated output without deleting them.
- Next.js and matching ESLint configuration patched to 16.4.3, with compatible transitive audit fixes.

## Verification

The final verification table is maintained in BUILD_STATUS. Do not substitute older test counts. Review `git diff --check`, locked dependencies, generated contracts when relevant, and the export audit before committing.

## Publishing boundary

Existing Git history includes earlier personal notes. The current source tree has been cleaned, and ignored databases, model artifacts, screenshots, credentials and personal notes stay local. A source-only export excludes `.git` history; it does not erase history already present in this repository or on a remote.

Use the prepared `dist/fpl-assistant-source.zip` or extracted `dist/publish/fpl-assistant/` for a fresh initial publication after inspecting the archive audit. `dist/` is ignored. The existing checkout remains available with its original history. No history rewrite, remote change or push is part of this preparation.

The extracted publication checkout has a clean local initial commit on `main` and no remote. The next agent should work from that directory, inspect `git status`, the export audit and the selected GitHub destination, then add the intended remote and push when instructed. The ZIP contains the same source without Git metadata. Do not force-push this fresh history over an existing repository.

Keep using the original workspace for its retained private data and active learning workers. Its working changes are preserved, and its older history has not been rewritten. Publishing from the original workspace requires a separate review of that historical privacy boundary.

## Runtime and post-gameweek evaluation

The normal app starts with `bash scripts/dev.sh`. Enabled reviews run while its worker runs. The current research benchmark uses a separate ignored `DATA_DIR`, and its dedicated worker uses that directory. It first checks for finalized GW9 results on 3 November at 12:00 UTC and retries every six hours if necessary.

To resume that research worker or manually check results, use the `DATA_DIR` and commands in the local operator note under `docs/local/`; generic commands are documented in `scripts/README.md`. Score frozen predictions before refitting. The current forecast bundles must not be rewritten when outcomes become available.

The personal app state was preserved and may be older than the research origin. User-selected transfers and screenshot evidence are in ignored local notes. Submission, private balances and current chip activation still require their own evidence before app-state reconciliation.

## Remaining limits

Baseline football and numerical planning remain champions. Bayesian complete player scoring and strict TFT release evidence remain gated. New historical ablation results are exploratory; GW9 is their first untouched prospective event. Local recurring review is not an always-on hosted service. See the current dependency audit in BUILD_STATUS for any remaining development-tool advisories.
