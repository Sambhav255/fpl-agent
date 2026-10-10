"""Synthetic audit counterexample: these values are not real projections."""

import pytest

from fpl_app.contracts import ManagerState, Pick, Player, Projection, ProjectionRun, Settings
from fpl_app.domain.plans import validate_plan
from fpl_app.domain.rules import apply_transfers, select_lineup
from fpl_app.optimisation.oracle import exact_oracle
from fpl_app.optimisation.planner import recommend, squad_proxy_candidate


def funding_fixture(horizon=1):
    positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
    players = [
        Player(
            player_id=i + 1, name=f"P{i + 1}", club=i // 3 + 1, position=pos, market_price_units=50
        )
        for i, pos in enumerate(positions)
    ]
    players += [
        Player(player_id=16, name="Cheap GK", club=7, position=1, market_price_units=45),
        Player(player_id=17, name="Premium MID", club=8, position=3, market_price_units=55),
        Player(player_id=18, name="Upgrade GK", club=9, position=1, market_price_units=50),
    ]
    picks = [
        Pick(player_id=p.player_id, purchase_price_units=50, position=i + 1)
        for i, p in enumerate(players[:15])
    ]
    state = ManagerState(
        team_id=1,
        current_chip_confirmed=True,
        snapshot_id="audit",
        bank_units=0,
        free_transfers_at_event_start=2,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        picks=picks,
        event_start_picks=[p.model_copy(deep=True) for p in picks],
        event_start_bank_units=0,
    )
    values = [10, 9, 7, 6, 5, 4, 3, 9, 8, 7, 6, 5, 6, 5, 4, 0, 16, 15]
    projections = [
        Projection(
            player_id=p.player_id,
            fixture_id=e * 100 + p.club,
            event=e,
            expected_points=float(v),
            expected_minutes=90,
            appearance_probability=1,
        )
        for e in range(8, 8 + horizon)
        for p, v in zip(players, values, strict=True)
    ]
    run = ProjectionRun(
        projection_run_id="audit",
        snapshot_id="audit",
        source_cutoff="2026-10-09T00:00:00Z",
        data_mode="demo",
        horizon_events=horizon,
        projections=projections,
    )
    return state, players, run


def test_funding_pair_84_94_101_exact_and_independent_validation():
    state, players, run = funding_fixture()
    settings = Settings(horizon_events=1, max_additional_hit_points=0, max_transfers_this_event=2)
    original = state.model_dump()
    proxy, _ = squad_proxy_candidate(state, players, run, settings, 10, None, 2)
    proxy_state, _ = apply_transfers(state, players, proxy)
    assert select_lineup(state, players, run.projections, 8)["expected_points"] == 84
    assert select_lineup(proxy_state, players, run.projections, 8)["expected_points"] == 94
    proxy_result = recommend(state, players, run, settings, candidate_mode="squad_proxy")
    assert (
        max(
            [proxy_result.baseline_plan.net_points]
            + [p.net_points for p in proxy_result.alternatives]
        )
        == 94
    )
    oracle = exact_oracle(state, players, run, settings)
    assert oracle.net_points == 101
    result = recommend(state, players, run, settings)
    best = max(result.alternatives, key=lambda p: p.net_points)
    assert best.net_points == 101
    assert best.bank_units == 0 and best.incremental_hits == 0
    assert len(best.actions) == 2
    assert not validate_plan(best, state, players, run, settings, result.baseline_plan)
    assert best.solver["optimality_gap"] is None
    assert "candidate only" in best.solver["candidate_gap_scope"]
    assert state.model_dump() == original


def test_two_event_delayed_funding_benefit_matches_oracle():
    state, players, run = funding_fixture(2)
    players = players[:17]
    run.projections = [p for p in run.projections if p.player_id != 18]
    for p in run.projections:
        if p.player_id == 17:
            p.expected_points = 0 if p.event == 8 else 40
    state.free_transfers_at_event_start = 1
    settings = Settings(horizon_events=2, max_additional_hit_points=0, max_transfers_this_event=1)
    oracle = exact_oracle(state, players, run, settings)
    result = recommend(state, players, run, settings)
    best = max([result.baseline_plan] + result.alternatives, key=lambda p: p.net_points)
    assert best.net_points == oracle.net_points
    assert best.weeks[0]["actions"] == []
    assert {a["in"] for a in best.weeks[1]["actions"]} == {16, 17}
    assert best.total_hits == 0
    assert not validate_plan(best, state, players, run, settings, result.baseline_plan)


def test_oracle_refuses_inexact_budget_or_unknown_finances():
    state, players, run = funding_fixture()
    with pytest.raises(ValueError, match="budget"):
        exact_oracle(state, players, run, Settings(horizon_events=1), max_nodes=1)
    state.bank_units = None
    with pytest.raises(ValueError, match="finances"):
        exact_oracle(state, players, run, Settings(horizon_events=1))
