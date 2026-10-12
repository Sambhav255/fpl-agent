"""Benchmark rejects invented longer forecast support and avoids manager state."""

import importlib.util
from pathlib import Path

from test_upgrade_optimisation import funding_fixture

from fpl_app.domain.rules import validate_squad


def test_one_lead_run_is_not_repeated_for_four_six_eight_event_benchmarks():
    path = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_season_planning.py"
    spec = importlib.util.spec_from_file_location("planning_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, players, run = funding_fixture(1)
    state = module.synthetic_start(players, run)
    assert not validate_squad(state, players)
    assert state.team_id == -1
    assert state.bank_units == 1000 - sum(p.purchase_price_units for p in state.picks)
    report = module.benchmark(players, run)
    assert report["forecast_horizon"] == 1
    assert report["results"] == [
        {"horizon": horizon, "status": "unsupported_frozen_forecast_horizon"}
        for horizon in (4, 6, 8)
    ]
    assert report["evidence"] == "frozen forecast decision benchmark; not realized football returns"
