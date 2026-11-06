# Operations

Run commands from the repository root unless a command states otherwise.

| Task                                                 | Guide                                              |
| ---------------------------------------------------- | -------------------------------------------------- |
| Install and launch locally                           | [Project quick start](../../README.md#quick-start) |
| Collect, train, freeze and score                     | [Operator reference](../../scripts/README.md)      |
| Understand the weekly model competition              | [Weekly research workflow](WEEKLY_RESEARCH.md)     |
| Inspect worker health and optional macOS supervision | [Worker runtime](WORKER_RUNTIME.md)                |
| Verify and prepare a Git change                      | [Contributing](../../CONTRIBUTING.md)              |
| Create a clean source snapshot                       | [Release preparation](RELEASE_PREPARATION.md)      |

Use the same absolute `DATA_DIR` for collection, jobs, scoring and the worker. Local
processes require machine uptime. Private manager state, source captures, model
artifacts and operational logs stay in ignored storage.
