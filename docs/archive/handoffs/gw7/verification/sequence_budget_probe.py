"""Synthetic node budget probe. Actual planner source, no FPL network calls.

No planner, domain, model or storage functions are mocked. No database is used.
"""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('repository', type=Path)
parser.add_argument('--expect-fixed', action='store_true')
args = parser.parse_args()
root = args.repository.resolve()
sys.path.insert(0, str(root/'backend/src'))

from fpl_app.contracts import ManagerState, Pick, Player, Projection, ProjectionRun, Settings
from fpl_app.domain.plans import _week
from fpl_app.domain.rules import advance_event, apply_transfers
from fpl_app.optimisation.sequence import solve_sequence

positions = [1]*2 + [2]*5 + [3]*5 + [4]*3
players = [Player(player_id=i+1, name=f'Owned{i+1}', club=i//3+1, position=p, market_price_units=50) for i,p in enumerate(positions)]
players += [Player(player_id=i, name=f'Candidate{i}', club=i+10, position=3, market_price_units=50) for i in range(16,81)]
picks = [Pick(player_id=p.player_id, purchase_price_units=50, position=i+1) for i,p in enumerate(players[:15])]
state = ManagerState(team_id=1, current_chip_confirmed=True, snapshot_id='probe', next_event=7, bank_units=0, free_transfers_at_event_start=1, transfers_made_this_event=0, confirmed_hit_points=0, picks=picks, event_start_picks=[p.model_copy(deep=True) for p in picks], event_start_bank_units=0)
run = ProjectionRun(projection_run_id='probe', snapshot_id='probe', source_cutoff='2026-10-16T00:00:00Z', data_mode='demo', horizon_events=4, projections=[Projection(player_id=p.player_id, fixture_id=e*1000+p.club, event=e, expected_points=25 if p.player_id==16 else 4 if p.player_id<=15 else 0, expected_minutes=90, appearance_probability=1) for e in range(7,11) for p in players])
settings = Settings(horizon_events=4, max_additional_hit_points=0, max_transfers_this_event=1, solver_time_limit_seconds=10, planner_mode='sequence')
report = solve_sequence(state, players, run, settings, max_edges=100)

def feasible_total(immediate):
    current = state.model_copy(deep=True)
    weeks = []
    for event in range(7,11):
        moves = [{'out':8,'in':16}] if immediate and event==7 else []
        current, ledger = apply_transfers(current, players, moves, None)
        weeks.append(_week(current, players, run, None, ledger))
        if event < 10:
            current=advance_event(current)
    return sum(w['net_points'] for w in weeks)

out = {'commit':'a3754b39f1a81b05a59b668bfdd363bb89d48d6d','synthetic':True,'mocked_functions':False,'node_budget':100,'planner_points':report.net_points,'planner_actions_by_event':[w['actions'] for w in report.weeks],'status':report.status,'evaluated_edges':report.evaluated_edges,'keep_points':feasible_total(False),'legal_buy_now_hold_points':feasible_total(True)}
if args.expect_fixed:
    assert out['planner_points'] >= out['legal_buy_now_hold_points'], 'Root budget starvation remains'
    assert any(a['in'] == 16 for a in report.weeks[0]['actions']), 'Immediate upgrade was not considered'
else:
    assert out['legal_buy_now_hold_points'] > out['planner_points'], 'Historical defect no longer reproduces; use --expect-fixed'
print(json.dumps(out,indent=2))
