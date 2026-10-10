from copy import deepcopy

import pytest
from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import Settings
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.strategy import (
    ReplayOrigin,
    compare_policies,
    greedy_policy,
    keep_policy,
    planner_policy,
    proxy_planner_policy,
    replay_policy,
)


def origin():
    state, players, run = funding_fixture()
    outcomes = {p.player_id: [MatchStats(minutes=90, goals_conceded_on_pitch=1)] for p in players}
    return state, ReplayOrigin(
        "2026-10-10T12:00:00Z", "2026-10-09T00:00:00Z", players, run, outcomes
    )


def test_replay_exact_scoring_captain_fallback_and_missing_coverage():
    state, item = origin()
    # Forecast captain is P1; absent captain falls back to P8, with reserve GK autosub.
    item.outcomes[1] = [MatchStats()]
    item.outcomes[8] = [MatchStats(minutes=90, goals=1, goals_conceded_on_pitch=1)]
    report = replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    assert report["rows"][0]["scoring"]["effective_captain"] == 8
    assert (
        report["realised_net_points"] == 34
    )  # 22 appearance (reserve GK enters) + 5 goal + 7 vice multiplier
    assert report["legal"]
    del item.outcomes[2]
    with pytest.raises(ValueError, match="Missing outcome"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


def test_future_inputs_rejected_and_outcomes_not_visible_to_actions():
    state, item = origin()
    settings = Settings(horizon_events=1, max_additional_hit_points=0, max_transfers_this_event=2)
    first = replay_policy(state, [item], planner_policy, settings)
    changed = deepcopy(item)
    changed.outcomes = {p.player_id: [MatchStats(minutes=90, goals=4)] for p in item.players}
    second = replay_policy(state, [changed], planner_policy, settings)
    assert first["rows"][0]["actions"] == second["rows"][0]["actions"]
    assert first["realised_net_points"] != second["realised_net_points"]
    changed.information_available_at = "2026-10-11T00:00:00Z"
    with pytest.raises(ValueError, match="Future"):
        replay_policy(state, [changed], planner_policy, settings)
    item.forecasts.source_cutoff = "2026-10-11T00:00:00Z"
    with pytest.raises(ValueError, match="Future"):
        replay_policy(state, [item], keep_policy, settings)


def test_multiple_starts_paired_report_and_unknown_financial_gate():
    state, item = origin()
    settings = Settings(horizon_events=1, max_additional_hit_points=0)
    report = compare_policies(
        [state, state.model_copy(deep=True)],
        [item],
        {
            "keep": keep_policy,
            "planner": planner_policy,
            "proxy": proxy_planner_policy,
            "greedy": greedy_policy,
        },
        settings,
    )
    assert len(report["starts"]) == 2
    assert all(s["paired_incremental_points"]["keep"] == 0 for s in report["starts"])
    state.bank_units = None
    with pytest.raises(ValueError, match="Unknown finances"):
        replay_policy(state, [item], keep_policy, settings)


def test_replay_advances_inventory_without_mutating_start():
    state, item = origin()
    state.free_transfers_at_event_start = 5
    second = deepcopy(item)
    second.deadline = "2026-10-17T12:00:00Z"
    second.information_available_at = "2026-10-16T00:00:00Z"
    second.forecasts.source_cutoff = second.information_available_at
    second.forecasts.snapshot_id = "second"
    for projection in second.forecasts.projections:
        projection.event = 9
    original = state.model_dump()
    report = replay_policy(state, [item, second], keep_policy, Settings(horizon_events=1))
    assert [row["event"] for row in report["rows"]] == [8, 9]
    assert report["realised_net_points"] == 48
    assert report["final_state"]["free_transfers_at_event_start"] == 5
    assert state.model_dump() == original
