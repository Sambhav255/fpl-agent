"""Legal paired comparisons; synthetic fixtures are mechanics evidence only."""

from copy import deepcopy

import pytest
from test_strategy_replay import origin

from fpl_app.contracts import Settings
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.strategy import (
    ForecastPolicy,
    compare_forecast_policies,
    keep_policy,
    planner_policy,
)


def test_same_state_different_forecasts_separate_model_and_planner_effects():
    initial, reference = origin()
    reference.evidence_mode = "synthetic_mechanics"
    # No hidden outcomes enter either policy. The same realized GK haul is
    # deliberately assigned before comparing two fixed forecast streams.
    reference.outcomes[18] = [MatchStats(minutes=90, penalty_saves=2)]
    challenger = deepcopy(reference)
    challenger.forecasts.projection_run_id = "challenger"
    for row in challenger.forecasts.projections:
        if row.player_id == 18:
            row.expected_points = 50
    before = initial.model_dump()
    settings = Settings(horizon_events=1, max_additional_hit_points=0)
    result = compare_forecast_policies(
        initial,
        {
            "keep": ForecastPolicy([reference], keep_policy),
            "roll": ForecastPolicy([reference], keep_policy),
            "baseline_planner": ForecastPolicy([reference], planner_policy),
            "challenger_planner": ForecastPolicy([challenger], planner_policy),
        },
        settings,
    )
    assert result["paired_incremental_points"]["roll"] == 0
    reports = result["reports"]
    base = reports["baseline_planner"]["rows"][0]
    new = reports["challenger_planner"]["rows"][0]
    assert base["forecast_fingerprint"] != new["forecast_fingerprint"]
    assert base["state_before"] == new["state_before"]
    assert any(move["in"] == 18 for move in new["actions"])
    assert base["actions"] != new["actions"]
    assert new["state_after_actions"]["bank_units"] >= 0
    assert new["lineup"]["captain"] in new["lineup"]["starters"]
    assert result["covered_events"] == 1 and result["distinct_season_paths"] == 1
    assert initial.model_dump() == before


@pytest.mark.parametrize("change", ["price", "outcome", "origin", "schedule"])
def test_mismatched_experimental_inputs_fail_before_any_policy_runs(change):
    initial, first = origin()
    second = deepcopy(first)
    if change == "price":
        second.players[0].market_price_units += 1
    elif change == "outcome":
        second.outcomes[1] = [MatchStats(minutes=90, goals=3)]
    elif change == "origin":
        second.information_available_at = "2026-10-09T01:00:00Z"
    else:
        second.forecasts.horizon_events += 1

    def must_not_run(*args):
        raise AssertionError("policy executed before paired input validation")

    with pytest.raises(ValueError, match="identical origin"):
        compare_forecast_policies(
            initial,
            {
                "keep": ForecastPolicy([first], must_not_run),
                "other": ForecastPolicy([second], must_not_run),
            },
            Settings(horizon_events=1),
        )


def test_complete_trajectory_carries_inventory_and_committed_hits_once():
    initial, first = origin()
    initial.confirmed_hit_points = 4
    initial.transfers_made_this_event = 3
    second = deepcopy(first)
    second.deadline = "2026-10-17T12:00:00Z"
    second.information_available_at = "2026-10-16T00:00:00Z"
    second.forecasts.source_cutoff = second.information_available_at
    second.forecasts.snapshot_id = "next-event"
    for row in second.forecasts.projections:
        row.event = 9
    result = compare_forecast_policies(
        initial, {"keep": ForecastPolicy([first, second], keep_policy)}, Settings(horizon_events=1)
    )
    rows = result["reports"]["keep"]["rows"]
    assert rows[0]["hits"] == 4 and rows[1]["hits"] == 0
    assert rows[0]["next_origin_state"]["next_event"] == rows[1]["state_before"]["next_event"]
    assert (
        rows[0]["next_origin_state"]["free_transfers_at_event_start"]
        == rows[1]["state_before"]["free_transfers_at_event_start"]
    )
    assert rows[1]["next_origin_state"] is None
    assert rows[0]["scoring"]["points"] - 4 == rows[0]["realised_net_points"]


def test_comparison_cli_publishes_once_without_overwriting(tmp_path):
    import json
    import os
    import subprocess
    import sys
    from dataclasses import asdict
    from pathlib import Path

    initial, item = origin()
    item.evidence_mode = "synthetic_mechanics"
    serialized = {
        "deadline": item.deadline,
        "information_available_at": item.information_available_at,
        "players": [p.model_dump(mode="json") for p in item.players],
        "forecasts": item.forecasts.model_dump(mode="json"),
        "outcomes": {key: [asdict(stats) for stats in rows] for key, rows in item.outcomes.items()},
        "evidence_mode": item.evidence_mode,
    }
    payload = {
        "initial_state": initial.model_dump(mode="json"),
        "settings": Settings(horizon_events=1).model_dump(mode="json"),
        "candidates": {"keep": {"policy": "keep", "origins": [serialized]}},
    }
    source, output = tmp_path / "input.json", tmp_path / "report.json"
    source.write_text(json.dumps(payload))
    root = Path(__file__).resolve().parents[2]
    command = [
        sys.executable,
        str(root / "scripts/research/compare_paper_policies.py"),
        "--input",
        str(source),
        "--output",
        str(output),
    ]
    env = {**os.environ, "PYTHONPATH": str(root / "backend/src")}
    first = subprocess.run(command, check=False, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    original = output.read_bytes()
    result = json.loads(original)
    assert result["covered_events"] == 1
    assert result["reports"]["keep"]["legal"]
    second = subprocess.run(command, check=False, env=env, capture_output=True, text=True)
    assert second.returncode != 0
    assert output.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.json", "report.json"]
