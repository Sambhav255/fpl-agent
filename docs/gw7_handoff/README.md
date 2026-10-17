# GW7 deadline package

Priority is a fresh legal transfer decision before Saturday 17 October 2026, 05:00 Chicago time. Reverify the official deadline. If it has passed, plan the next legal event.

1. Give [CURRENT_AGENT_PROMPT.md](CURRENT_AGENT_PROMPT.md) to the current agent.
2. Provide [GW7_AGENT_HANDOFF.md](GW7_AGENT_HANDOFF.md) for the app review, reproduced defect and deadline workflow.
3. Provide [EXTERNAL_REPOSITORY_REVIEW.md](EXTERNAL_REPOSITORY_REVIEW.md) for the six repos, Java directory, reuse choices and licence notes.
4. See [SOURCES_AND_SCOPE.md](SOURCES_AND_SCOPE.md) for pins and verification limits.

Copy this folder to docs/gw7_handoff/ in the project. Preserve newer changes and private data. This audit cannot name personal transfers because current confirmed squad and finances are only available to your local agent.

## Reproduce the defect

From project root, using its installed environment:

~~~bash
backend/.venv/bin/python docs/gw7_handoff/verification/sequence_budget_probe.py .
~~~

After repair:

~~~bash
backend/.venv/bin/python docs/gw7_handoff/verification/sequence_budget_probe.py . --expect-fixed
~~~

The probe runs actual supplied contracts, transitions and sequence solver with a synthetic 80 player universe and 100 edge budget. No functions are mocked, no provider is called, and no database is used. The audit returned 234 points by buying in the last event, compared with legal immediate buy/hold 360 and Keep 192.

This exposes traversal order at a deliberately small budget, not a real team loss or global optimum. Add repository regression tests rather than relying only on the audit script. No application code or private state was changed by this audit.
