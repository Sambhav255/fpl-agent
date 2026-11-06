# Documentation

Start with the guide for your task. Current implementation and verification live in
[build status](BUILD_STATUS.md); specifications describe requirements, while dated
experiment reports preserve evidence.

| I want to…                                  | Read                                                                                           |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Install and use the application             | [Project quick start](../README.md#quick-start)                                                |
| Resume development or agent work            | [Start here](START_HERE.md)                                                                    |
| See what works and what remains unavailable | [Build status](BUILD_STATUS.md)                                                                |
| Understand the source layout                | [File map](FILE_STRUCTURE.md), [backend guide](../backend/README.md)                           |
| Change product or technical behavior        | [Specifications](specs/README.md), [decisions](DECISIONS.md)                                   |
| Operate jobs, data and model experiments    | [Operations](operations/README.md)                                                             |
| Review actual model measurements            | [Experiment registry](experiments/README.md)                                                   |
| Understand planned work and remaining gates | [Roadmap](ROADMAP.md), [acceptance checklist](MASTER_PLAN_STATUS.md), [plans](plans/README.md) |
| Prepare a source change or clean export     | [Contributing](../CONTRIBUTING.md), [release preparation](operations/RELEASE_PREPARATION.md)   |
| Find superseded documents                   | [Archive](archive/README.md)                                                                   |

## Documentation boundaries

- **Maintained:** guides, status, specifications, roadmap and operator reference.
- **Preserved:** original supplied plans, dated experiments and archival records.
- **Local only:** private manager notes, screenshots and operational logs in ignored
  `docs/local/`; runtime data, source captures and native artifacts in ignored `data/`.

Old links in immutable reports resolve through the [relocation manifest](archive/relocations.json).
The [continuation summary](CHATGPT_PROGRESS_REPORT.md) is a compact handoff, not a
second source of requirements or a replacement for measured evidence.
