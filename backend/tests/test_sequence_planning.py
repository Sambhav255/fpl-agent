"""Synthetic mechanics, never evidence of a live strategy advantage."""

import pytest
from pydantic import ValidationError
from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import Settings
from fpl_app.domain.plans import input_fingerprint, validate_plan
from fpl_app.domain.rules import advance_event, apply_transfers, sale_value
from fpl_app.optimisation.oracle import exact_oracle
from fpl_app.optimisation.planner import recommend
from fpl_app.optimisation.sequence import bounded_squads, solve_sequence


def best_plan(result):
    return max([result.baseline_plan, *result.alternatives], key=lambda p: p.net_points)


def test_future_triple_captain_sequence_matches_independent_enumeration():
    state, players, run = funding_fixture(2)
    state.chips = {"triple_captain_1": True}
    for p in run.projections:
        if p.player_id == 1 and p.event == 9:
            p.expected_points = 30
    settings = Settings(
        horizon_events=2,
        max_additional_hit_points=0,
        locked_player_ids=[p.player_id for p in state.picks],
        future_chip_policy="optimise",
        planner_mode="sequence",
    )
    result = recommend(state, players, run, settings)
    plan = best_plan(result)
    oracle = exact_oracle(state, players, run, settings)
    assert plan.weeks[0]["chip"] is None
    assert plan.weeks[1]["chip"] == "triple_captain"
    assert plan.net_points == oracle.net_points
    assert plan.solver["status"] == "optimal_declared_universe"
    assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)
    no_future = settings.model_copy(update={"future_chip_policy": "none"})
    forbidden = plan.model_copy(
        update={"input_fingerprint": input_fingerprint(state, players, run, no_future)}
    )
    assert "Unexpected chip or event" in validate_plan(
        forbidden, state, players, run, no_future, result.baseline_plan
    )


def test_three_event_price_path_and_future_free_hit_restore_are_independent():
    state, players, run = funding_fixture(3)
    state.chips = {"free_hit_1": True}
    state.free_transfers_at_event_start = 1
    settings = Settings(
        horizon_events=3,
        planner_mode="sequence",
        chip_schedule={9: "free_hit"},
        max_transfers_this_event=0,
        max_additional_hit_points=0,
        price_scenario={9: {16: 30, 17: 50}, 10: {16: 35, 17: 60}},
        solver_time_limit_seconds=20,
    )
    result = recommend(state, players, run, settings)
    assert result.alternatives
    plan = result.alternatives[0]
    assert plan.weeks[1]["chip"] == "free_hit"
    assert plan.weeks[2]["chip"] is None
    assert plan.weeks[2]["free_transfers_at_event_start"] == 2
    assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)
    tampered = plan.model_copy(deep=True)
    tampered.weeks[2]["bank_units"] = 999
    assert "Replay mismatch: bank_units" in validate_plan(
        tampered, state, players, run, settings, result.baseline_plan
    )


def test_financial_sequence_timing_and_price_ledger_match_small_oracle():
    state, players, run = funding_fixture(2)
    state.free_transfers_at_event_start = 1
    settings = Settings(
        horizon_events=2,
        planner_mode="sequence",
        max_transfers_this_event=1,
        max_additional_hit_points=0,
        price_scenario={9: {17: 50}},
    )
    result = recommend(state, players, run, settings)
    plan = best_plan(result)
    oracle = exact_oracle(state, players, run, settings)
    assert plan.net_points == oracle.net_points
    assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)
    for week in plan.weeks:
        for action in week["actions"]:
            if action["in"] == 17 and week["event"] == 9:
                assert action["purchase_units"] == 50


def test_unknown_quotes_cannot_be_reused_at_changed_market_price():
    state, players, _ = funding_fixture()
    pick = state.picks[0]
    pick.purchase_price_units = None
    pick.selling_price_units = players[0].market_price_units
    pick.selling_price_market_units = players[0].market_price_units
    pick.selling_price_provenance = "user_confirmed"
    changed = players[0].model_copy(
        update={"market_price_units": players[0].market_price_units + 1}
    )
    with pytest.raises(ValueError, match="stale"):
        sale_value(pick, changed)


def test_free_hit_market_changes_preserve_original_acquisition_basis():
    state, players, _ = funding_fixture()
    state.chips = {"free_hit_1": True}
    original = state.model_dump()
    temporary, _ = apply_transfers(state, players, [{"out": 2, "in": 16}], "free_hit")
    restored = advance_event(temporary)
    assert [p.model_dump() for p in restored.picks] == original["picks"]
    assert restored.bank_units == state.event_start_bank_units
    market = players[1].model_copy(update={"market_price_units": 120})
    assert sale_value(restored.picks[1], market) == 85
    assert state.model_dump() == original


def test_schedule_inventory_expiry_consecutive_fh_and_budget_are_not_invented():
    state, players, run = funding_fixture(2)
    state.next_event = 19
    for p in run.projections:
        p.event += 11
    state.chips = {"free_hit_1": True, "free_hit_2": True}
    settings = Settings(
        horizon_events=2, chip_schedule={19: "free_hit", 20: "free_hit"}, planner_mode="sequence"
    )
    result = solve_sequence(state, players, run, settings)
    assert result.weeks == [] and result.status == "no_legal_path"
    exhausted = solve_sequence(state, players, run, Settings(horizon_events=2), max_edges=1)
    assert not exhausted.complete and exhausted.weeks
    assert exhausted.net_points == sum(w["net_points"] for w in exhausted.weeks)
    state.chips = {"triple_captain_1": True}
    result = solve_sequence(
        state, players, run, Settings(horizon_events=2, chip_schedule={20: "triple_captain"})
    )
    assert not result.weeks


@pytest.mark.parametrize(
    "patch",
    [
        {"chip_schedule": {11: "bench_boost"}},
        {"price_scenario": {9: {9999: 50}}},
        {"price_scenario": {8: {1: 999}}},
    ],
)
def test_invalid_scenario_inputs_rejected_before_search(patch):
    state, players, run = funding_fixture(2)
    with pytest.raises(ValueError):
        recommend(state, players, run, Settings(horizon_events=2, **patch))


def test_price_units_reject_fractional_or_negative_money():
    for price in [5.5, -1, True]:
        with pytest.raises(ValidationError):
            Settings(price_scenario={9: {1: price}})


def test_full_catalogue_returns_independently_validated_bounded_sequence():
    from fpl_app.contracts import Player, Projection

    state, players, run = funding_fixture(2)
    # Full-league scale authored catalogue, complete forecasts; no real accuracy claim.
    for player_id in range(19, 701):
        player = Player(
            player_id=player_id,
            name=f"Authored {player_id}",
            club=1 + player_id % 20,
            position=1 + player_id % 4,
            market_price_units=50,
        )
        players.append(player)
        for event in (8, 9):
            run.projections.append(
                Projection(
                    player_id=player_id,
                    fixture_id=event * 100 + player.club,
                    event=event,
                    expected_points=1,
                    expected_minutes=90,
                    appearance_probability=1,
                )
            )
    settings = Settings(
        horizon_events=2,
        planner_mode="sequence",
        solver_time_limit_seconds=3,
        max_transfers_this_event=1,
        max_additional_hit_points=0,
    )
    result = recommend(state, players, run, settings)
    assert result.alternatives
    plan = result.alternatives[0]
    assert len(plan.weeks) == 2
    assert plan.solver["status"] == "bounded_catalogue_incumbent"
    assert plan.solver["optimality_gap"] is None
    assert (
        plan.solver["search_scope"]
        == "ordinary_events_at_most_two_replacements_complete_chip_milp_candidates"
    )
    assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)


def test_lazy_two_replacement_edges_obey_positions_locks_exclusions_and_event_cap():
    from time import monotonic

    state, players, run = funding_fixture(2)
    owned = {pick.player_id for pick in state.picks}
    settings = Settings(
        horizon_events=2,
        locked_player_ids=[2],
        excluded_player_ids=[18],
        max_transfers_this_event=0,
    )
    assert list(bounded_squads(state, players, run, settings, monotonic() + 10, 0)) == [owned]
    candidates = list(bounded_squads(state, players, run, settings, monotonic() + 10, 1))
    assert (owned - {1, 8}) | {16, 17} in candidates  # Funding pair spans positions.
    assert len(candidates) == len({frozenset(squad) for squad in candidates})
    by_id = {player.player_id: player for player in players}
    for squad in candidates:
        assert 2 in squad and 18 not in squad
        assert len(squad - owned) <= 2
        assert [sum(by_id[i].position == pos for i in squad) for pos in range(1, 5)] == [2, 5, 5, 3]


def test_restricted_search_never_reports_global_optimality_after_candidate_exhaustion():
    state, players, run = funding_fixture(1)
    settings = Settings(horizon_events=1, max_transfers_this_event=0)
    # Cardinality exceeds this edge budget, but the restricted roll-only menu is exhausted.
    result = solve_sequence(state, players, run, settings, max_edges=2)
    assert result.weeks and result.evaluated_edges == 1
    assert not result.complete
    assert result.status == "bounded_catalogue_incumbent"
