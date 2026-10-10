from fpl_app.contracts import ManagerState, Player, ProjectionRun, Recommendation, Settings

from .plans import validate_plan
from .rules import (
    RULES,
    MatchStats,
    advance_event,
    apply_transfers,
    bonus_points,
    readiness,
    score_lineup,
    score_match,
    select_lineup,
    selling_price,
    transfer_accounting,
    validate_chip,
    validate_formation,
    validate_lineup,
    validate_squad,
)

__all__ = [
    "RULES",
    "MatchStats",
    "advance_event",
    "apply_transfers",
    "bonus_points",
    "readiness",
    "score_lineup",
    "score_match",
    "select_lineup",
    "selling_price",
    "transfer_accounting",
    "validate_chip",
    "validate_formation",
    "validate_lineup",
    "validate_plan",
    "validate_squad",
]


def recommend(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    lineup_only: bool = False,
) -> Recommendation:
    """Contract entry point; lazy import prevents a domain/planner import cycle."""
    from fpl_app.optimisation import recommend as plan_recommendation

    return plan_recommendation(state, players, run, settings, lineup_only=lineup_only)


__all__.append("recommend")
