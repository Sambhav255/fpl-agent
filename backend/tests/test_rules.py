from dataclasses import FrozenInstanceError

import pytest

from fpl_app.contracts import ManagerState, Pick, Player, Projection
from fpl_app.domain import (
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


def sample():
    positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
    players = [
        Player(
            player_id=i + 1, name=f"P{i + 1}", club=i // 3 + 1, position=pos, market_price_units=50
        )
        for i, pos in enumerate(positions)
    ]
    players += [
        Player(player_id=16 + pos, name=f"New{pos}", club=7, position=pos, market_price_units=50)
        for pos in range(1, 5)
    ]
    picks = [
        Pick(
            player_id=p.player_id,
            purchase_price_units=50,
            position=i + 1,
            acquisition_id=f"original-{p.player_id}",
        )
        for i, p in enumerate(players[:15])
    ]
    state = ManagerState(
        team_id=1,
        current_chip_confirmed=True,
        snapshot_id="test",
        bank_units=5,
        free_transfers_at_event_start=2,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        picks=picks,
        chips={
            f"{c}_{w}": True
            for c in ("wildcard", "free_hit", "bench_boost", "triple_captain")
            for w in (1, 2)
        },
        event_start_picks=[p.model_copy(deep=True) for p in picks],
        event_start_bank_units=5,
    )
    return state, players


def forecasts(players, event=8):
    return [
        Projection(
            player_id=p.player_id,
            fixture_id=p.club,
            event=event,
            expected_points=float(p.player_id % 7),
            expected_minutes=80,
        )
        for p in players
    ]


@pytest.mark.parametrize(
    "buy,market,sale", [(75, 78, 76), (75, 76, 75), (75, 79, 77), (75, 74, 74)]
)
def test_money(buy, market, sale):
    assert selling_price(buy, market) == sale


@pytest.mark.parametrize("bad", [True, 1.2, -1])
def test_money_rejects_noninteger(bad):
    with pytest.raises(ValueError):
        selling_price(bad, 75)


@pytest.mark.parametrize(
    "free,made,hits,nxt",
    [
        (1, 0, 0, 2),
        (1, 1, 0, 1),
        (1, 2, 4, 1),
        (2, 1, 0, 2),
        (2, 3, 4, 1),
        (5, 0, 0, 5),
        (5, 4, 0, 2),
    ],
)
def test_rollover(free, made, hits, nxt):
    result = transfer_accounting(free, made)
    assert result["total_hits"] == hits
    assert result["free_transfers_next"] == nxt


def test_committed_moves_and_event_limit():
    assert transfer_accounting(2, 1, 1)["incremental_hits"] == 0
    assert transfer_accounting(2, 1, 2)["total_hits"] == 4
    assert transfer_accounting(1, 2, 1)["incremental_hits"] == 4
    with pytest.raises(ValueError):
        transfer_accounting(1, 20, 1)
    assert transfer_accounting(2, 20, 10, "wildcard")["free_transfers_next"] == 2


def test_squad_formations_and_club_limit():
    state, players = sample()
    assert not validate_squad(state, players)
    assert not validate_formation([1, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14], players)
    assert not validate_formation([1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13], players)
    assert validate_formation([1, 3, 4, 8, 9, 10, 11, 12, 13, 14, 15], players)
    players[3].club = 1
    assert validate_squad(state, players)
    state.picks[1].player_id = 1
    assert validate_squad(state, players)


def test_financial_unknown_and_stale():
    state, players = sample()
    state.bank_units = None
    assert readiness(state, players)["lineup_ready"]
    assert not readiness(state, players)["transfers_ready"]
    assert select_lineup(state, players, forecasts(players), 8)
    state.bank_units = 5
    state.picks[0].purchase_price_units = None
    state.picks[0].selling_price_units = 50
    state.picks[0].selling_price_market_units = 49
    state.picks[0].selling_price_provenance = "user_confirmed"
    assert not readiness(state, players)["transfers_ready"]
    state.picks[0].selling_price_market_units = 50
    assert readiness(state, players)["transfers_ready"]


def test_affordability_ledger_rebuy_and_no_mutation():
    state, players = sample()
    players[-3].market_price_units = 55
    changed, ledger = apply_transfers(state, players, [{"out": 3, "in": 18}])
    assert changed.bank_units == 0 and state.bank_units == 5
    assert ledger == changed.transfer_ledger
    assert changed.picks[2].purchase_price_units == 55
    assert changed.picks[2].acquisition_id != state.picks[2].acquisition_id
    rebought, _ = apply_transfers(changed, players, [{"out": 18, "in": 3}])
    assert rebought.picks[2].acquisition_id != "original-3"
    assert rebought.transfers_made_this_event == 2
    players[-3].market_price_units = 56
    with pytest.raises(ValueError, match="Unaffordable"):
        apply_transfers(state, players, [{"out": 3, "in": 18}])


def test_hit_reconciliation():
    state, players = sample()
    state.transfers_made_this_event = 3
    assert not readiness(state, players)["transfers_ready"]
    state.confirmed_hit_points = 4
    assert readiness(state, players)["transfers_ready"]


@pytest.mark.parametrize("chip", ["wildcard", "free_hit"])
def test_chip_cancels_existing_hits_preserves_allowance(chip):
    state, players = sample()
    state.transfers_made_this_event = 3
    state.confirmed_hit_points = 4
    changed, _ = apply_transfers(state, players, [{"out": 3, "in": 18}], chip)
    assert changed.confirmed_hit_points == 0
    assert advance_event(changed).free_transfers_at_event_start == 2


def test_free_hit_restore_acquisition_bank_and_windows():
    state, players = sample()
    state.next_event = 19
    temporary, _ = apply_transfers(state, players, [{"out": 3, "in": 18}], "free_hit")
    restored = advance_event(temporary)
    assert [p.model_dump() for p in restored.picks] == [p.model_dump() for p in state.picks]
    assert restored.bank_units == 5
    assert validate_chip(restored, "free_hit")
    assert restored.chips["free_hit_1"] is False
    assert restored.chips["free_hit_2"] is True
    restored.next_event = 21
    assert not validate_chip(restored, "free_hit")
    restored.event_start_picks = None
    assert validate_chip(restored, "free_hit")


def test_wildcard_permanent_and_unknown_chip_inventory():
    state, players = sample()
    changed, _ = apply_transfers(state, players, [{"out": 3, "in": 18}], "wildcard")
    assert advance_event(changed).picks[2].player_id == 18
    state.chips = {}
    assert validate_chip(state, "wildcard")
    state.next_event = 1
    assert validate_chip(state, "free_hit")
    state.current_chip = "bench_boost"
    assert validate_chip(state, "triple_captain")


@pytest.mark.parametrize("minutes,expected", [(0, 0), (1, 1), (59, 1), (60, 2), (90, 2)])
def test_appearance_scoring(minutes, expected):
    assert score_match(4, MatchStats(minutes=minutes)) == expected


@pytest.mark.parametrize("position,goal", [(1, 10), (2, 6), (3, 5), (4, 4)])
def test_goal_scoring(position, goal):
    assert score_match(position, MatchStats(minutes=1, goals=1)) == 1 + goal


@pytest.mark.parametrize("saves,points", [(2, 0), (3, 1), (5, 1), (6, 2)])
def test_saves_and_position(saves, points):
    assert score_match(1, MatchStats(saves=saves)) == points
    assert score_match(3, MatchStats(saves=saves, penalty_saves=1)) == 0


@pytest.mark.parametrize("goals,points", [(1, 0), (2, -1), (3, -1), (4, -2)])
def test_concessions(goals, points):
    assert score_match(2, MatchStats(goals_conceded_on_pitch=goals)) == points


def test_clean_sheet_red_cards_and_negative_points():
    assert score_match(2, MatchStats(minutes=60)) == 6
    assert score_match(2, MatchStats(minutes=59)) == 1
    assert score_match(2, MatchStats(minutes=60, goals_conceded_after_red=2)) == 6
    assert (
        score_match(
            2, MatchStats(minutes=60, red_cards=1, yellow_cards=1, goals_conceded_after_red=2)
        )
        == -2
    )
    assert (
        score_match(4, MatchStats(red_cards=1, yellow_cards=2, own_goals=1, penalty_misses=1)) == -7
    )
    assert score_match(1, MatchStats(penalty_saves=1)) == 5


@pytest.mark.parametrize(
    "position,actions,recoveries,expected",
    [(2, 9, 99, 0), (2, 10, 0, 2), (2, 20, 0, 2), (3, 11, 0, 0), (3, 11, 1, 2), (4, 12, 0, 2)],
)
def test_defensive_contributions(position, actions, recoveries, expected):
    assert score_match(position, MatchStats(tackles=actions, recoveries=recoveries)) == expected


def test_bonus_ties():
    assert bonus_points({1: 20, 2: 20, 3: 15, 4: 10}) == {1: 3, 2: 3, 3: 1, 4: 0}
    assert bonus_points({1: 20, 2: 15, 3: 15, 4: 10}) == {1: 3, 2: 2, 3: 2, 4: 0}
    assert bonus_points({1: 20, 2: 15, 3: 10, 4: 10}) == {1: 3, 2: 2, 3: 1, 4: 1}


def fixed_lineup():
    return {
        "starters": [1, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14],
        "bench": [2, 15, 6, 7],
        "captain": 3,
        "vice_captain": 8,
    }


def test_autosubs_bench_priority_goalkeeper_cards_and_cameo():
    state, players = sample()
    lineup = fixed_lineup()
    outcomes = {p.player_id: [MatchStats(minutes=90)] for p in players}
    outcomes[1] = []
    outcomes[3] = []
    scored = score_lineup(lineup, state, players, outcomes)
    assert 2 in scored["scoring_players"] and 6 in scored["scoring_players"]
    assert 15 not in scored["scoring_players"]
    assert scored["effective_captain"] == 8
    outcomes[3] = [MatchStats(yellow_cards=1)]
    scored = score_lineup(lineup, state, players, outcomes)
    assert 3 in scored["scoring_players"] and 6 not in scored["scoring_players"]
    assert scored["effective_captain"] == 8
    outcomes[3] = [MatchStats(minutes=1)]
    assert score_lineup(lineup, state, players, outcomes)["effective_captain"] == 3
    outcomes[3] = [MatchStats(minutes=0), MatchStats(minutes=1)]
    assert score_lineup(lineup, state, players, outcomes)["effective_captain"] == 3
    outcomes[3] = []
    outcomes[8] = []
    assert score_lineup(lineup, state, players, outcomes)["effective_captain"] is None


def test_multiple_missing_and_boost_no_double_count():
    state, players = sample()
    lineup = fixed_lineup()
    outcomes = {p.player_id: [MatchStats(minutes=1)] for p in players}
    outcomes[3] = []
    outcomes[4] = []
    outcomes[8] = []
    scored = score_lineup(lineup, state, players, outcomes)
    assert not validate_formation(scored["scoring_players"], players)
    assert {6, 7, 15} <= set(scored["scoring_players"])
    bb = score_lineup(lineup, state, players, outcomes, "bench_boost")
    assert len(set(bb["scoring_players"])) == 15
    assert bb["points"] == 12
    tc = score_lineup(
        lineup, state, players, {i: [MatchStats(minutes=1)] for i in range(1, 16)}, "triple_captain"
    )
    assert tc["points"] == 13


def test_bench_goalkeeper_and_captain_validation():
    state, players = sample()
    lineup = fixed_lineup()
    assert not validate_lineup(lineup, state, players)
    lineup["bench"] = [15, 2, 6, 7]
    assert validate_lineup(lineup, state, players)
    lineup = fixed_lineup()
    lineup["captain"] = 15
    assert validate_lineup(lineup, state, players)


def test_frozen_rules():
    assert RULES.sources and RULES.verified_at.endswith("Z")
    with pytest.raises(FrozenInstanceError):
        RULES.hit_cost = 8


@pytest.mark.parametrize(
    "missing",
    [
        "bank_units",
        "free_transfers_at_event_start",
        "transfers_made_this_event",
        "confirmed_hit_points",
    ],
)
def test_each_unknown_financial_field_blocks_only_transfers(missing):
    state, players = sample()
    setattr(state, missing, None)
    assert readiness(state, players)["lineup_ready"]
    assert not readiness(state, players)["transfers_ready"]
    with pytest.raises(ValueError, match="Incomplete"):
        apply_transfers(state, players, [{"out": 3, "in": 18}])


def test_unknown_selling_confirmation_provenance():
    state, players = sample()
    state.picks[0].purchase_price_units = None
    state.picks[0].selling_price_units = 50
    state.picks[0].selling_price_market_units = 50
    assert not readiness(state, players)["transfers_ready"]
    state.picks[0].selling_price_provenance = "private_verified"
    assert readiness(state, players)["transfers_ready"]


def test_free_hit_restores_market_profit_not_obsolete_selling_confirmation():
    state, players = sample()
    temp, _ = apply_transfers(state, players, [{"out": 3, "in": 18}], "free_hit")
    players[2].market_price_units = 55
    restored = advance_event(temp)
    changed, ledger = apply_transfers(restored, players, [{"out": 3, "in": 18}])
    assert ledger[0]["sale_units"] == 52
    assert changed.bank_units == 7


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0.5, True])
def test_match_stats_invalid(bad):
    with pytest.raises(ValueError):
        score_match(2, MatchStats(minutes=bad))


def test_red_card_without_minutes_prevents_sub_but_not_captain_fallback():
    state, players = sample()
    lineup = fixed_lineup()
    outcomes = {i: [MatchStats(minutes=1)] for i in range(1, 16)}
    outcomes[3] = [MatchStats(red_cards=1)]
    scored = score_lineup(lineup, state, players, outcomes)
    assert 3 in scored["scoring_players"]
    assert scored["effective_captain"] == 8


def test_unavailable_reserve_keeper_cannot_be_replaced_by_outfield():
    state, players = sample()
    lineup = fixed_lineup()
    outcomes = {i: [MatchStats(minutes=1)] for i in range(1, 16)}
    outcomes[1] = []
    outcomes[2] = []
    scored = score_lineup(lineup, state, players, outcomes)
    assert 15 not in scored["scoring_players"]
    assert 1 in scored["scoring_players"]  # inert starter retains nominal formation


def test_chip_inventory_does_not_cross_window():
    state, _ = sample()
    state.next_event = 19
    state.chips = {"bench_boost": True}
    state = advance_event(state)
    assert validate_chip(state, "bench_boost")


def test_unknown_active_chip_blocks_transfers_but_not_lineup():
    state, players = sample()
    state.current_chip_confirmed = False
    report = readiness(state, players)
    assert report["lineup_ready"] and not report["transfers_ready"]
    assert "Current chip status is unconfirmed" in report["missing_fields"]


def test_chip_unlimited_event_transfer_count_contract_and_accounting():
    state, players = sample()
    state.current_chip = "wildcard"
    state.transfers_made_this_event = 25
    assert readiness(state, players)["transfers_ready"]
    assert transfer_accounting(2, 25, chip="wildcard")["total_hits"] == 0
    state.current_chip = None
    assert not readiness(state, players)["transfers_ready"]


def test_real_club_transfer_exception_lineup_allowed_resulting_squad_strict():
    state, players = sample()
    players[3].club = players[0].club
    assert validate_squad(state, players)
    state.club_limit_exception = True
    assert not validate_squad(state, players)
    assert select_lineup(state, players, forecasts(players), state.next_event)
    with pytest.raises(ValueError, match="Club limit"):
        apply_transfers(state, players, [])
    corrected, _ = apply_transfers(state, players, [{"out": 4, "in": 18}])
    assert not validate_squad(corrected, players, allow_club_exception=False)


def test_impossible_selling_price_cannot_create_funds():
    state, players = sample()
    pick = state.picks[0]
    pick.purchase_price_units = None
    pick.selling_price_units = 500
    pick.selling_price_market_units = 50
    pick.selling_price_provenance = "user_confirmed"
    assert not readiness(state, players)["transfers_ready"]
    with pytest.raises(ValueError):
        apply_transfers(state, players, [{"out": 1, "in": 17}])


def test_confirmation_must_reconcile_known_purchase_price():
    state, players = sample()
    pick = state.picks[0]
    pick.selling_price_units = 49
    pick.selling_price_market_units = 50
    pick.selling_price_provenance = "user_confirmed"
    assert not readiness(state, players)["transfers_ready"]
