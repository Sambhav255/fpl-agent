"""Authored counterexamples test rules, not live football performance."""

from time import monotonic

import pytest
from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import Pick, Settings
from fpl_app.domain.plans import validate_plan
from fpl_app.domain.rules import advance_event, apply_transfers, sale_value
from fpl_app.optimisation.chip_candidates import complete_chip_squads
from fpl_app.optimisation.oracle import funding_moves
from fpl_app.optimisation.planner import recommend


def full_replacement_fixture(horizon=2):
    state, players, run = funding_fixture(horizon)
    players = players[:15]
    run.projections = [p for p in run.projections if p.player_id <= 15]
    for row in run.projections:
        row.expected_points = 1
    for old in list(players):
        player = old.model_copy(update={"player_id": old.player_id + 100, "club": old.club + 10})
        players.append(player)
        for row in list(run.projections):
            if row.player_id == old.player_id:
                run.projections.append(
                    row.model_copy(update={"player_id": player.player_id, "expected_points": 10})
                )
    state.free_transfers_at_event_start = 3
    state.chips = {"wildcard_1": True, "free_hit_1": True}
    return state, players, run


@pytest.mark.parametrize("chip", ["wildcard", "free_hit"])
def test_full_replacement_candidate_and_sequence_are_independently_legal(chip):
    state, players, run = full_replacement_fixture()
    before = state.model_dump()
    settings = Settings(
        horizon_events=2,
        chip_policy=chip,
        planner_mode="sequence",
        max_additional_hit_points=0,
        solver_time_limit_seconds=15,
    )
    result = recommend(state, players, run, settings)
    assert result.alternatives
    plan = result.alternatives[0]
    assert len(plan.weeks[0]["actions"]) > 2
    assert plan.weeks[0]["total_hits"] == 0
    assert plan.weeks[0]["free_transfers_next"] == 3
    assert plan.solver["status"] == "bounded_catalogue_incumbent"
    assert plan.solver["optimality_gap"] is None
    assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)
    first, _ = apply_transfers(
        state, players, [{"out": a["out"], "in": a["in"]} for a in plan.weeks[0]["actions"]], chip
    )
    after = advance_event(first)
    if chip == "free_hit":
        assert [p.model_dump() for p in after.picks] == before["picks"]
        assert after.bank_units == before["event_start_bank_units"]
        assert after.previous_free_hit_event == 8
    else:
        assert {p.player_id for p in after.picks} == set(plan.weeks[0]["squad_ids"])
    assert after.chips[f"{chip}_1"] is False
    assert state.model_dump() == before


def test_liquidation_budget_preserves_sale_profit_and_move_cap_locks_exclusions():
    state, players, run = full_replacement_fixture(1)
    # Owned market100, purchase50 sells75, so spending cannot use market100.
    players[0].market_price_units = 100
    state.picks[0] = Pick(player_id=1, purchase_price_units=50, position=1)
    state.event_start_picks = [p.model_copy(deep=True) for p in state.picks]
    settings = Settings(
        horizon_events=1,
        chip_policy="wildcard",
        locked_player_ids=[1],
        excluded_player_ids=[102],
        max_transfers_this_event=4,
    )
    candidates = list(
        complete_chip_squads(state, players, run, settings, monotonic() + 5, 0, "wildcard")
    )
    assert candidates
    selected = candidates[0]
    assert 1 in selected and 102 not in selected
    assert 2 < len(selected - {p.player_id for p in state.picks}) <= 4
    changed, ledger = apply_transfers(
        state, players, funding_moves(state, players, selected), "wildcard"
    )
    assert sale_value(state.picks[0], players[0]) == 75
    assert changed.bank_units == state.bank_units + sum(
        action["sale_units"] - action["purchase_units"] for action in ledger
    )
    capped = settings.model_copy(update={"max_transfers_this_event": 0})
    assert list(
        complete_chip_squads(state, players, run, capped, monotonic() + 5, 0, "wildcard")
    ) == [{p.player_id for p in state.picks}]


def test_sparse_multilead_ownership_xi_captain_matches_exhaustive_frozen_squads():
    from itertools import combinations, product

    from fpl_app.domain.plans import _week
    from fpl_app.domain.rules import RULES
    from fpl_app.optimisation.planner import _highs_candidate

    state, players, run = funding_fixture(2)
    state.chips = {"wildcard_1": True}
    for row in run.projections:
        if row.player_id == 17:
            row.expected_points = 3 if row.event == 8 else 40
    settings = Settings(horizon_events=2, chip_policy="wildcard")
    groups = [
        list(combinations([p.player_id for p in players if p.position == pos], count))
        for pos, count in enumerate(RULES.squad_counts, 1)
    ]
    scores = []
    for groups_chosen in product(*groups):
        selected = {i for group in groups_chosen for i in group}
        try:
            first, ledger = apply_transfers(
                state, players, funding_moves(state, players, selected), "wildcard"
            )
        except ValueError:
            continue
        first_points = _week(first, players, run, "wildcard", ledger)["net_points"]
        second_points = _week(advance_event(first), players, run, None, [])["net_points"]
        scores.append(first_points + second_points)
    moves, metadata = _highs_candidate(state, players, run, settings, 5, "wildcard", 15)
    first, ledger = apply_transfers(state, players, moves, "wildcard")
    actual = (
        _week(first, players, run, "wildcard", ledger)["net_points"]
        + _week(advance_event(first), players, run, None, [])["net_points"]
    )
    assert actual == max(scores)
    assert metadata["candidate_status"] == 0
    assert "candidate only" in metadata["candidate_gap_scope"]
