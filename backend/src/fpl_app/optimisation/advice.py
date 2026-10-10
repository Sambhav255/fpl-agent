"""This-week chip notes from lineup points. No second transfer search."""

from __future__ import annotations

from fpl_app.contracts import ChipAdvice, ManagerState, Plan, Player, ProjectionRun, Settings
from fpl_app.domain.rules import (
    advance_event,
    player_map,
    select_lineup,
    validate_chip,
)

LABELS = {
    "triple_captain": "Triple Captain",
    "bench_boost": "Bench Boost",
    "wildcard": "Wildcard",
    "free_hit": "Free Hit",
}


def rolled_states(state: ManagerState, horizon: int) -> list[ManagerState]:
    current = state.model_copy(deep=True)
    current.current_chip = None
    states: list[ManagerState] = []
    for _ in range(horizon):
        states.append(current)
        if len(states) < horizon:
            current = advance_event(current)
    return states


def chip_inventory(state: ManagerState, chip: str) -> bool | None:
    window = 1 if state.next_event <= 19 else 2
    value = (
        state.chips[f"{chip}_{window}"]
        if f"{chip}_{window}" in state.chips
        else state.chips.get(chip)
    )
    if value is True:
        return True
    if value is False:
        return False
    return None


def full_slate(state: ManagerState, players: list[Player], run: ProjectionRun) -> bool:
    if not run.fixtures:
        return False
    by_id = player_map(players)
    clubs = {by_id[pick.player_id].club for pick in state.picks}
    playing = {
        club
        for fixture in run.fixtures
        if fixture.event == state.next_event
        for club in (fixture.home_club, fixture.away_club)
    }
    return clubs <= playing


def lineup_points(
    state: ManagerState, players: list[Player], run: ProjectionRun, chip: str | None
) -> float:
    return float(
        select_lineup(state, players, run.projections, state.next_event, chip)["expected_points"]
    )


def _item(
    chip: str,
    status: str,
    reason: str,
    this_week: float | None = None,
    comparison: float | None = None,
) -> ChipAdvice:
    return ChipAdvice(
        chip=chip,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        this_week_points=this_week,
        comparison_points=comparison,
        reason=reason,
    )


def chip_advice(
    state: ManagerState,
    chosen: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    baseline: Plan,
    scenario_net: float | None,
) -> list[ChipAdvice]:
    items: list[ChipAdvice] = []
    keep_states = rolled_states(state, settings.horizon_events)
    chosen_states = rolled_states(chosen, settings.horizon_events)
    keep_net = float(baseline.weeks[0]["net_points"])
    for chip in ("triple_captain", "bench_boost", "wildcard", "free_hit"):
        label = LABELS[chip]
        if chip_inventory(state, chip) is False:
            items.append(_item(chip, "used", f"{label} already used in this chip window."))
            continue
        if chip in {"wildcard", "free_hit"} and settings.chip_policy != chip:
            items.append(
                _item(
                    chip,
                    "not_evaluated",
                    f"{label} is not solved unless you ask for it. This is not a season-long timing call.",
                )
            )
            continue
        errors = validate_chip(state, chip)
        if chip_inventory(state, chip) is not True or errors:
            reason = errors[0] if errors else f"{label} inventory is unknown for this window."
            items.append(_item(chip, "unavailable", reason))
            continue
        if chip in {"wildcard", "free_hit"}:
            items.append(_limited_chip(chip, label, state, players, run, scenario_net, keep_net))
            continue
        items.append(_scored_chip(chip, label, players, run, keep_states, chosen_states))
    return items


def _limited_chip(chip, label, state, players, run, scenario_net, keep_net):
    if scenario_net is None:
        return _item(
            chip,
            "unavailable",
            f"{label} was requested but this run did not solve a this-week scenario.",
        )
    difference = scenario_net - keep_net
    status = "play_this_week" if difference > 0 else "save"
    slate = (
        "This week has a full fixture slate. "
        if chip == "free_hit" and full_slate(state, players, run)
        else ""
    )
    reason = (
        f"{slate}{label} this week scores {scenario_net:.1f} versus Keep {keep_net:.1f} "
        f"({difference:+.1f}) after the chip is spent. Not a season-long optimum, "
        "and the chip is not played automatically."
    )
    return _item(chip, status, reason, scenario_net, keep_net)


def _scored_chip(chip, label, players, run, keep_states, chosen_states):
    def uplift(week_state):
        plain = lineup_points(week_state, players, run, None)
        return lineup_points(week_state, players, run, chip) - plain

    this_week = uplift(chosen_states[0])
    source = keep_states if chip == "triple_captain" else chosen_states
    # Compare chip marginal value, not team totals (a strong XI is not a strong bench).
    eligible = [week for week in source[1:] if not validate_chip(week, chip)]
    future = [uplift(week) for week in eligible]
    if not future:
        return _item(
            chip,
            "save",
            f"No later eligible {label} week is available in this horizon. Timing comparison unavailable; not a season-long optimum.",
            this_week,
            None,
        )
    comparison = max(future)
    difference = this_week - comparison
    status = "play_this_week" if difference > 0 else "save"
    detail = "captain extra" if chip == "triple_captain" else "bench extra"
    reason = (
        f"{label} {detail} is {this_week:.1f} this week versus {comparison:.1f} in the best other "
        f"eligible week of this horizon ({difference:+.1f}). Not a season-long optimum; "
        "these are approximate forecast means, and the chip is not played automatically."
    )
    return _item(chip, status, reason, this_week, comparison)
