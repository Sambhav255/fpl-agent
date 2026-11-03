"""Synthetic mechanics, never evidence of a live strategy advantage."""

import pytest
from pydantic import ValidationError
from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import ManagerState, Pick, Player, Projection, ProjectionRun, Settings
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
        == "ordinary_events_up_to_free_inventory_or_two_replacements_complete_chip_milp_candidates"
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


@pytest.mark.parametrize("reverse_catalogue", [False, True])
def test_budgeted_sequence_seeds_immediate_upgrade_before_future_subtrees(reverse_catalogue):
    """Synthetic root budget regression from the GW7 handoff; no real forecast claim."""
    positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
    players = [
        Player(
            player_id=i + 1,
            name=f"Owned{i + 1}",
            club=i // 3 + 1,
            position=position,
            market_price_units=50,
        )
        for i, position in enumerate(positions)
    ]
    players += [
        Player(player_id=i, name=f"Candidate{i}", club=i + 10, position=3, market_price_units=50)
        for i in range(16, 81)
    ]
    picks = [
        Pick(player_id=p.player_id, purchase_price_units=50, position=i + 1)
        for i, p in enumerate(players[:15])
    ]
    state = ManagerState(
        team_id=1,
        current_chip_confirmed=True,
        snapshot_id="probe",
        next_event=7,
        bank_units=0,
        free_transfers_at_event_start=1,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        picks=picks,
        event_start_picks=[p.model_copy(deep=True) for p in picks],
        event_start_bank_units=0,
    )
    run = ProjectionRun(
        projection_run_id="probe",
        snapshot_id="probe",
        source_cutoff="2026-10-16T00:00:00Z",
        data_mode="demo",
        horizon_events=4,
        projections=[
            Projection(
                player_id=p.player_id,
                fixture_id=e * 1000 + p.club,
                event=e,
                expected_points=25 if p.player_id == 16 else 4 if p.player_id <= 15 else 0,
                expected_minutes=90,
                appearance_probability=1,
            )
            for e in range(7, 11)
            for p in players
        ],
    )
    settings = Settings(
        horizon_events=4,
        max_additional_hit_points=0,
        max_transfers_this_event=1,
        solver_time_limit_seconds=10,
        planner_mode="sequence",
    )
    if reverse_catalogue:
        players.reverse()
    result = solve_sequence(state, players, run, settings, max_edges=100)
    assert result.net_points == 360
    assert {action["in"] for action in result.weeks[0]["actions"]} == {16}
    assert result.root_actions_considered > 1
    assert result.root_actions_seeded > 0
    assert result.incumbent_source in {"root_seed", "depth_search"}
    assert result.evaluated_edges <= 100
    assert not result.complete
    excluded = settings.model_copy(update={"excluded_player_ids": [16]})
    without_upgrade = solve_sequence(state, players, run, excluded, max_edges=100)
    assert all(action["in"] != 16 for week in without_upgrade.weeks for action in week["actions"])


def test_budgeted_sequence_seeds_funding_pair_and_keeps_valid_path():
    state, players, run = funding_fixture()
    for player_id in range(19, 81):
        player = Player(
            player_id=player_id,
            name=f"Extra{player_id}",
            club=player_id + 10,
            position=1 + player_id % 4,
            market_price_units=50,
        )
        players.append(player)
        run.projections.append(
            Projection(
                player_id=player_id,
                fixture_id=8000 + player.club,
                event=8,
                expected_points=0,
                expected_minutes=90,
                appearance_probability=1,
            )
        )
    settings = Settings(
        horizon_events=1,
        max_additional_hit_points=0,
        max_transfers_this_event=2,
        solver_time_limit_seconds=10,
        planner_mode="sequence",
    )
    result = solve_sequence(state, players, run, settings, max_edges=100)
    assert result.net_points == 101
    assert {action["in"] for action in result.weeks[0]["actions"]} == {16, 17}
    assert result.root_actions_seeded > 0
    assert result.evaluated_edges <= 100
    assert not result.complete


def test_three_free_transfer_restructure_matches_exact_small_oracle_when_budgeted():
    """A two-move cap misses the third independent no-hit upgrade."""
    from time import monotonic

    from fpl_app.domain.plans import _week
    from fpl_app.domain.rules import apply_transfers
    from fpl_app.optimisation.oracle import funding_moves

    state, players, run = funding_fixture(1)
    players = players[:15] + [players[17]]
    for identifier, position in [(19, 2), (20, 4)]:
        players.append(
            Player(
                player_id=identifier,
                name=f"Upgrade {identifier}",
                club=identifier,
                position=position,
                market_price_units=50,
            )
        )
    allowed = {p.player_id for p in players}
    run.projections = [p for p in run.projections if p.player_id in allowed]
    for row in run.projections:
        if row.player_id == 18:
            row.expected_points = 30
    for player in players[-2:]:
        run.projections.append(
            Projection(
                player_id=player.player_id,
                fixture_id=800 + player.club,
                event=8,
                expected_points=30,
                expected_minutes=90,
                appearance_probability=1,
            )
        )
    state.free_transfers_at_event_start = 3
    settings = Settings(
        horizon_events=1,
        planner_mode="sequence",
        max_additional_hit_points=0,
        max_transfers_this_event=3,
        solver_time_limit_seconds=10,
    )
    oracle = exact_oracle(state, players, run, settings)
    # Force bounded search over a universe of 72 squads and just 40 edges.
    bounded = solve_sequence(state, players, run, settings, max_edges=40)
    assert not bounded.complete
    assert bounded.net_points == oracle.net_points
    assert len(bounded.weeks[0]["actions"]) == 3
    assert bounded.weeks[0]["total_hits"] == 0
    assert {move["in"] for move in bounded.weeks[0]["actions"]} == {18, 19, 20}
    old_scores = []
    for squad in bounded_squads(state, players, run, settings, monotonic() + 10, 0):
        moves = funding_moves(state, players, squad)
        if len(moves) <= 2:
            changed, ledger = apply_transfers(state, players, moves)
            old_scores.append(_week(changed, players, run, None, ledger)["net_points"])
    assert max(old_scores) < oracle.net_points
    assert bounded.root_actions_seeded > 0


def test_three_moves_in_same_position_and_mixed_positions_preserve_quotas():
    from time import monotonic

    state, players, run = funding_fixture(1)
    for identifier in [19, 20, 21]:
        players.append(
            Player(
                player_id=identifier,
                name=f"MID {identifier}",
                club=identifier,
                position=3,
                market_price_units=50,
            )
        )
    state.free_transfers_at_event_start = 3
    settings = Settings(horizon_events=1, max_transfers_this_event=3)
    owned = {p.player_id for p in state.picks}
    squads = list(bounded_squads(state, players, run, settings, monotonic() + 10, 0))
    assert (owned - {8, 9, 10}) | {19, 20, 21} in squads
    assert (owned - {1, 8, 9}) | {16, 19, 20} in squads
    by_id = {p.player_id: p for p in players}
    assert len(squads) == len({frozenset(s) for s in squads})
    assert all(
        [sum(by_id[i].position == pos for i in squad) for pos in range(1, 5)] == [2, 5, 5, 3]
        for squad in squads
    )


@pytest.mark.parametrize("inventory", [3, 4, 5])
def test_banked_inventory_can_restructure_up_to_five_without_expanding_hit_menu(inventory):
    from time import monotonic

    state, players, run = funding_fixture(1)
    players = players[:15]
    for identifier in range(19, 24):
        players.append(
            Player(
                player_id=identifier,
                name=f"MID {identifier}",
                club=identifier,
                position=3,
                market_price_units=50,
            )
        )
    state.free_transfers_at_event_start = inventory
    owned = {p.player_id for p in state.picks}
    mids = {p.player_id for p in players[:15] if p.position == 3}
    settings = Settings(horizon_events=1, locked_player_ids=sorted(owned - mids))
    squads = list(bounded_squads(state, players, run, settings, monotonic() + 10, 0))
    desired = (owned - set(sorted(mids)[:inventory])) | set(range(19, 19 + inventory))
    assert desired in squads
    assert max(len(squad - owned) for squad in squads) == inventory
    # Already used inventory must not be offered a second time.
    state.transfers_made_this_event = inventory - 1
    squads = list(bounded_squads(state, players, run, settings, monotonic() + 10, 0))
    assert max(len(squad - owned) for squad in squads) == 2
