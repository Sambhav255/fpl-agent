"""Read only synthetic probes against the supplied repository. No provider calls.

With --minimal-storage, only storage fingerprint/utcnow are substituted because
the audit runtime lacks SQLAlchemy. Solver, contracts, rules and replay are real.
This does not test database, API, worker, model fitting or the full test suite.
"""
import argparse
import ast
import hashlib
import json
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("repository", type=Path)
parser.add_argument("--minimal-storage", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(args.repository.resolve() / "backend/src"))
if args.minimal_storage:
    adapter = types.ModuleType("fpl_app.storage")
    adapter.fingerprint = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    adapter.utcnow = lambda: datetime.now(UTC).isoformat()
    sys.modules["fpl_app.storage"] = adapter

from fpl_app.contracts import Fixture, ManagerState, Pick, Player, Projection, ProjectionRun, Settings
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.strategy import ReplayOrigin, keep_policy, replay_policy
from fpl_app.models.baseline import baseline_run
from fpl_app.optimisation.oracle import exact_oracle
from fpl_app.optimisation.planner import recommend

positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
players = [Player(player_id=i + 1, name=f"P{i + 1}", club=i // 3 + 1, position=position, market_price_units=50) for i, position in enumerate(positions)]
players += [Player(player_id=16, name="Cheap GK", club=7, position=1, market_price_units=45), Player(player_id=17, name="Premium MID", club=8, position=3, market_price_units=55), Player(player_id=18, name="Upgrade GK", club=9, position=1, market_price_units=50)]
picks = [Pick(player_id=p.player_id, purchase_price_units=50, position=i + 1) for i, p in enumerate(players[:15])]
state = ManagerState(team_id=1, current_chip_confirmed=True, snapshot_id="audit", bank_units=0, free_transfers_at_event_start=2, transfers_made_this_event=0, confirmed_hit_points=0, picks=picks, event_start_picks=[p.model_copy(deep=True) for p in picks], event_start_bank_units=0)
values = [10, 9, 7, 6, 5, 4, 3, 9, 8, 7, 6, 5, 6, 5, 4, 0, 16, 15]
run = ProjectionRun(projection_run_id="audit", snapshot_id="audit", source_cutoff="2026-10-09T00:00:00Z", data_mode="demo", horizon_events=1, projections=[Projection(player_id=p.player_id, fixture_id=800 + p.club, event=8, expected_points=float(v), expected_minutes=90, appearance_probability=1) for p, v in zip(players, values, strict=True)])
settings = Settings(horizon_events=1, max_additional_hit_points=0, max_transfers_this_event=2)
new = recommend(state, players, run, settings)
old = recommend(state, players, run, settings, candidate_mode="squad_proxy")
best = lambda result: max([result.baseline_plan.net_points] + [p.net_points for p in result.alternatives])
oracle = exact_oracle(state, players, run, settings)

injured = Player(player_id=1, name="Injured", club=1, position=3, market_price_units=50, points_per_game=6, minutes=630, appearances=7, availability=0)
future = [Fixture(fixture_id=100 + e, event=e, home_club=1, away_club=2) for e in range(8, 16)]
injury = baseline_run([injured], future, "audit", "2026-10-09T00:00:00Z", "live", 8, 8)

observed_horizons = []
def observing_policy(current, catalogue, forecast, policy_settings):
    observed_horizons.append(policy_settings.horizon_events)
    return keep_policy(current, catalogue, forecast, policy_settings)

outcomes = {p.player_id: [MatchStats(minutes=90, goals_conceded_on_pitch=1)] for p in players}
origin = ReplayOrigin("2026-10-10T12:00:00Z", "2026-10-09T00:00:00Z", players, run, outcomes)
replay_policy(state, [origin], observing_policy, Settings(horizon_events=6))
future_origin_run = run.model_copy(deep=True)
future_origin_run.prediction_origin = "2026-10-11T00:00:00Z"
future_origin_item = ReplayOrigin(origin.deadline, origin.information_available_at, players, future_origin_run, outcomes)
future_origin_accepted = replay_policy(state, [future_origin_item], keep_policy, Settings(horizon_events=1))["legal"]

syntax_files = sorted(args.repository.rglob("*.py"))
syntax_files = [p for p in syntax_files if ".venv" not in p.parts]
for path in syntax_files:
    ast.parse(path.read_text(), filename=str(path))
result = {"audit_commit": "840c1185d005270717c7453fb278dc30a03c05f3", "synthetic": True, "minimal_storage": args.minimal_storage, "syntax_files": len(syntax_files), "funding": {"keep": new.baseline_plan.net_points, "old_proxy": best(old), "new_planner": best(new), "exact_oracle": oracle.net_points}, "availability": [{"event": p.event, "points": p.expected_points, "appearance_probability": p.appearance_probability, "scenario_endpoints": p.availability_scenario_points} for p in injury.projections], "replay_horizon": {"requested": 6, "observed_by_policy": observed_horizons}, "replay_future_prediction_origin": {"deadline": origin.deadline, "prediction_origin": future_origin_run.prediction_origin, "accepted": future_origin_accepted}}
assert result["funding"] == {"keep": 84.0, "old_proxy": 94.0, "new_planner": 101.0, "exact_oracle": 101.0}
assert observed_horizons == [1]
assert injury.projections[0].expected_points == 0
assert all(p.expected_points > 0 and p.appearance_probability is None for p in injury.projections[1:])
print(json.dumps(result, indent=2))
