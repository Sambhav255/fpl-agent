# Git and source release preparation

This guide prepares a reviewable source change. It does not push, publish, initialize
a replacement repository or rewrite existing Git history.

## Review the working tree

```sh
git status --short
git diff --stat
git diff --check
python3 scripts/check_docs.py
```

Review both changed and untracked files. Existing user changes must remain intact.
Include relevant source, tests, lockfiles and generated API contracts. Keep local
configuration, manager records, screenshots, captures, checkpoints, caches and build
output out of Git. `.gitignore` also excludes native model/array formats if generated
outside `data/`; the source exporter independently rejects unexpected native files.

Run checks appropriate to the changed code; see [contributing](../../CONTRIBUTING.md).
CI uses baseline dependencies and offline fixtures. Native optional-model tests
require the matching extras and report skips honestly when unavailable.

## Existing history and a clean source snapshot

Earlier commits contain personal manager notes. Clean current files do not remove
those commits. For a public repository with clean initial history, use the audited
source export in a separate, fresh destination rather than publishing the existing
history or rewriting it during routine maintenance.

```sh
python3 scripts/export_source.py
```

The ignored outputs are:

- `dist/fpl-assistant-source.zip`: current Git-visible source, including untracked
  source files, without `.git/`, ignored local state or dependencies.
- `dist/fpl-assistant-source.audit.json`: included paths, sizes, SHA256 hashes,
  archive identity and known credential-pattern scan results.

Inspect the audit and extracted contents before creating or publishing a repository.
The scanner detects known patterns and forbidden paths; it is not a guarantee that
all sensitive text is recognized. A clean export is an additional artifact, not a
replacement for the current working checkout or a commit.

## Cleanup verification record

New checks executed for the 6 November repository cleanup:

- **28 operator/repository tests passed**, including source-export and package-guide checks.
- **5 focused backend tests passed** with installed research dependencies.
- A separate locked baseline environment: **4 passed / 1 optional fit skipped**.
- Backend Ruff lint/format passed; maintained-document formatting and local links checked.
- **69 relocations, 52 archived originals and 67 experiment files** verified by checksum.
- `git diff --check` passed. No ignored local files are tracked in the current index.
- A fresh source export was created and inspected with its file hashes and known
  credential-pattern audit. The archive excludes repository history.

The prior complete backend/model suite (635 passed / 3 skipped) and frontend
verification remain in their dated reports; neither was rerun as a full suite for
this documentation cleanup. CI now checks actual documentation and source export;
a new remote CI run is not claimed.

Application entrypoints, source artifacts and private state were preserved. No
commit, push, remote operation or history rewrite was performed.
