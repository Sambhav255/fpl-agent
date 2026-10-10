"""Transfer cap, this-week optimum, and chip advice."""

import pytest
from pydantic import ValidationError
from test_optimisation import run_for
from test_rules import sample

from fpl_app.contracts import Settings
from fpl_app.domain import apply_transfers, recommend, select_lineup
from fpl_app.optimisation import validate_plan


def test_transfer_cap_settings_reject_out_of_range():
    assert Settings().max_transfers_this_event is None
    assert Settings(max_transfers_this_event=0).max_transfers_this_event == 0
    assert Settings(max_transfers_this_event=20).max_transfers_this_event == 20
    with pytest.raises(ValidationError):
        Settings(max_transfers_this_event=-1)
    with pytest.raises(ValidationError):
        Settings(max_transfers_this_event=21)


def test_cap_one_cannot_return_two_moves_this_week():
    state, players = sample()
    state.free_transfers_at_event_start = 2
    run = run_for(state, players, 1)
    for projection in run.projections:
        if projection.player_id > 15:
            projection.expected_points = 30
    shared = {"horizon_events": 1, "max_additional_hit_points": 0, "solver_time_limit_seconds": 2}
    uncapped = recommend(state, players, run, Settings(**shared))
    assert any(len(plan.weeks[0]["actions"]) >= 2 for plan in uncapped.alternatives)
    settings = Settings(**shared, max_transfers_this_event=1)
    capped = recommend(state, players, run, settings)
    assert capped.gameweek_optimum is not None
    plans = [capped.baseline_plan, capped.gameweek_optimum, *capped.alternatives]
    assert all(len(plan.weeks[0]["actions"]) <= 1 for plan in plans)
    assert capped.gameweek_optimum.this_week_net == pytest.approx(
        capped.gameweek_optimum.weeks[0]["net_points"]
    )
    delta = (
        capped.gameweek_optimum.weeks[0]["net_points"] - capped.baseline_plan.weeks[0]["net_points"]
    )
    assert capped.gameweek_optimum.this_week_delta == pytest.approx(delta)
    assert not validate_plan(
        capped.gameweek_optimum, state, players, run, settings, capped.baseline_plan
    )


def test_cap_zero_matches_keep():
    state, players = sample()
    run = run_for(state, players, 2)
    for projection in run.projections:
        if projection.player_id > 15:
            projection.expected_points = 25
    settings = Settings(
        horizon_events=2,
        max_transfers_this_event=0,
        max_additional_hit_points=4,
        solver_time_limit_seconds=1,
    )
    result = recommend(state, players, run, settings)
    assert result.gameweek_optimum is not None
    assert result.gameweek_optimum.actions == []
    assert result.gameweek_optimum.net_points == pytest.approx(result.baseline_plan.net_points)
    week_net = result.baseline_plan.weeks[0]["net_points"]
    assert result.gameweek_optimum.weeks[0]["net_points"] == pytest.approx(week_net)
    assert result.gameweek_optimum.this_week_delta == pytest.approx(0)
    assert all(not plan.weeks[0]["actions"] for plan in result.alternatives)


def test_gameweek_optimum_is_best_this_week_single_inside_cap():
    state, players = sample()
    players = [
        *players,
        players[0].model_copy(
            update={
                "player_id": 30,
                "name": "Punt",
                "club": 8,
                "position": 3,
                "market_price_units": 50,
            }
        ),
    ]
    run = run_for(state, players, 2)
    for projection in run.projections:
        if projection.player_id == 1:
            projection.expected_points = 40
        elif projection.player_id <= 15:
            projection.expected_points = 1
        elif projection.player_id == 19:
            projection.expected_points = 6
        elif projection.player_id == 30:
            projection.expected_points = 30 if projection.event == state.next_event else 0
    settings = Settings(
        horizon_events=2,
        max_transfers_this_event=1,
        max_additional_hit_points=0,
        solver_time_limit_seconds=2,
    )
    result = recommend(state, players, run, settings)
    optimum = result.gameweek_optimum
    assert optimum is not None
    assert len(optimum.weeks[0]["actions"]) == 1
    assert optimum.weeks[0]["actions"][0]["in"] == 30
    owned = {pick.player_id for pick in state.picks}
    by_position = {player.player_id: player.position for player in players}
    singles = [[]]
    for pick in state.picks:
        for player in players:
            if player.player_id in owned or player.position != by_position[pick.player_id]:
                continue
            singles.append([{"out": pick.player_id, "in": player.player_id}])

    def single_net(moves):
        moved, _ledger = apply_transfers(state, players, moves, None)
        lineup = select_lineup(moved, players, run.projections, state.next_event, None)
        return lineup["expected_points"] - (moved.confirmed_hit_points or 0)

    best = max(single_net(moves) for moves in singles)
    assert optimum.weeks[0]["net_points"] == pytest.approx(best)
    assert optimum.this_week_net == pytest.approx(best)
    assert all(len(plan.weeks[0]["actions"]) <= 1 for plan in result.alternatives)
    assert not validate_plan(optimum, state, players, run, settings, result.baseline_plan)


def test_used_bench_boost_is_not_advised():
    state, players = sample()
    state.chips["bench_boost_1"] = False
    run = run_for(state, players, 3)
    for projection in run.projections:
        if projection.event == state.next_event and projection.player_id > 10:
            projection.expected_points = 40
    result = recommend(
        state,
        players,
        run,
        Settings(horizon_events=3, max_transfers_this_event=0, solver_time_limit_seconds=0.4),
    )
    advice = {item.chip: item for item in result.chip_advice}
    assert advice["bench_boost"].status == "used"
    assert advice["bench_boost"].this_week_points is None
    assert advice["triple_captain"].status in {"save", "play_this_week"}


def test_triple_captain_and_bench_boost_match_lineup_points():
    state, players = sample()
    run = run_for(state, players, 3)
    for projection in run.projections:
        if projection.player_id == 1 and projection.event == state.next_event:
            projection.expected_points = 25
        elif projection.player_id == 1:
            projection.expected_points = 2
    result = recommend(
        state,
        players,
        run,
        Settings(horizon_events=3, max_transfers_this_event=0, solver_time_limit_seconds=0.4),
    )
    advice = {item.chip: item for item in result.chip_advice}
    tc = select_lineup(state, players, run.projections, state.next_event, "triple_captain")
    bb = select_lineup(state, players, run.projections, state.next_event, "bench_boost")
    assert advice["triple_captain"].this_week_points == pytest.approx(
        tc["expected_points"]
        - select_lineup(state, players, run.projections, state.next_event, None)["expected_points"]
    )
    assert advice["bench_boost"].this_week_points == pytest.approx(
        bb["expected_points"]
        - select_lineup(state, players, run.projections, state.next_event, None)["expected_points"]
    )
    assert advice["triple_captain"].status == "play_this_week"
    assert advice["triple_captain"].comparison_points is not None
    assert advice["triple_captain"].this_week_points > advice["triple_captain"].comparison_points
    assert "season" in advice["triple_captain"].reason.casefold()
    assert advice["bench_boost"].status in {"save", "play_this_week"}
    assert advice["wildcard"].status == "not_evaluated"
    assert advice["free_hit"].status == "not_evaluated"


def test_wildcard_and_free_hit_stay_off_unless_requested():
    state, players = sample()
    run = run_for(state, players, 2)
    for projection in run.projections:
        if projection.player_id > 15:
            projection.expected_points = 0
    idle = recommend(state, players, run, Settings(horizon_events=2, solver_time_limit_seconds=0.4))
    idle_advice = {item.chip: item for item in idle.chip_advice}
    assert idle_advice["wildcard"].status == "not_evaluated"
    assert idle_advice["free_hit"].status == "not_evaluated"
    requested = recommend(
        state,
        players,
        run,
        Settings(horizon_events=2, chip_policy="free_hit", solver_time_limit_seconds=1.5),
    )
    advice = {item.chip: item for item in requested.chip_advice}
    assert advice["free_hit"].status == "save"
    assert advice["wildcard"].status == "not_evaluated"
    assert advice["free_hit"].this_week_points is not None
    assert advice["free_hit"].comparison_points is not None
    assert advice["free_hit"].this_week_points <= advice["free_hit"].comparison_points
    assert requested.baseline_plan.chip is None
