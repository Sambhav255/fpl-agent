"""Complete chip ownership candidates; certificates cover this MILP only.

The candidate optimises frozen ownership with a legal XI and captain at each
supported origin. It does not certify the subsequent financial sequence search.
The sequence engine independently replays every returned squad.
"""

from collections.abc import Iterator
from time import monotonic

from fpl_app.contracts import ManagerState, Player, ProjectionRun, Settings
from fpl_app.domain.rules import apply_transfers


def complete_chip_squads(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    deadline: float,
    offset: int,
    chip: str | None,
) -> Iterator[set[int]]:
    """Full replacement plus roll, respecting the user's explicit move cap.

    Wildcard values supported remaining events; Free Hit values its temporary
    event only. Retained players cost their selling value in the liquidation-budget
    constraint, so purchase basis and market prices are never conflated.
    """
    from fpl_app.optimisation.planner import _highs_candidate

    if chip not in {"wildcard", "free_hit"}:
        raise ValueError("Complete replacement candidates require Wildcard or Free Hit")
    maximum = 15
    if offset == 0 and settings.max_transfers_this_event is not None:
        maximum = min(maximum, settings.max_transfers_this_event)
    remaining = deadline - monotonic()
    owned = {pick.player_id for pick in state.picks}
    if remaining > 0 and maximum:
        candidate_settings = settings.model_copy(
            update={"horizon_events": settings.horizon_events - offset}
        )
        moves, _ = _highs_candidate(
            state, players, run, candidate_settings, remaining, chip, maximum
        )
        try:
            changed, _ = apply_transfers(state, players, moves, chip)
        except ValueError:
            pass
        else:
            selected = {pick.player_id for pick in changed.picks}
            if set(settings.locked_player_ids) <= selected and not selected & set(
                settings.excluded_player_ids
            ):
                yield selected
                if selected == owned:
                    return
    if set(settings.locked_player_ids) <= owned and not owned & set(settings.excluded_player_ids):
        yield owned
