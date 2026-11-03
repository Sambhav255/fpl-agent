# Maintained specifications

Read [START_HERE](../START_HERE.md) and [BUILD_STATUS](../BUILD_STATUS.md) first. Specifications define requirements and interfaces; they do not establish that a feature is implemented, evaluated or promoted. Current runtime schemas are generated from the backend, and operator commands live in [scripts/README](../../scripts/README.md).

## Base product and engineering contracts

Apply explicit user instructions, verified current official rules, then the product/data/architecture/build order in root [AGENTS.md](../../AGENTS.md). Later scope extensions below add requirements without relaxing integrity or evidence gates. Record unresolved conflicts in [DECISIONS](../DECISIONS.md); disable materially uncertain rule recommendations.

1. [Product requirements](FPL_PRD.md)
2. [Data and model specification](DATA_AND_MODEL_SPEC.md)
3. [Stack and architecture](TECH_STACK_AND_ARCHITECTURE.md)
4. [Build plan and acceptance tests](BUILD_PLAN_AND_TESTS.md)
5. [Rule and data sources](SOURCES.md): dated research leads; verify live rules before changing behavior.

- [Runtime and integration contracts](CONTRACTS.md)
- [Advanced-model adapter requirements](ML_INTEGRATION.md)
- [Planner transfer controls](PLANNER_TRANSFER_CONTROLS_STATUS.md)

## Forecasting, strategy and social scope

- [Strategy product extension](strategy/FPL_PRD_V2.md)
- [Forecasting, data and planning](strategy/ML_DATA_AND_PLANNING_SPEC.md)
- [Social evidence and access](strategy/SOCIAL_INTELLIGENCE_SPEC.md)

## Learning and operational contracts

- [Learning product extension](learning/PRD_V3.md)
- [Learning, simulator and policy requirements](learning/RL_AND_LEARNING_SPEC.md)
- [Social evaluation extension](learning/SOCIAL_NEXT_STAGE.md)
- [Advanced shadow serving](learning/ADVANCED_SERVING.md)
- [Journal capture, seals and strict paper replay](learning/JOURNAL_REPLAY.md)

These retained specifications contain dated proposals and historical verification passages. Read present implementation and release eligibility from BUILD_STATUS and immutable experiment reports. Proposed module names or commands do not supersede actual runtime schemas or the operator index. Historical execution prompts, audits, backlogs, old status and supplied originals are indexed in [the archive](../archive/README.md) and are not current agent instructions.
