import itertools
import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit('Usage: python audit_probes.py /absolute/path/to/fpl-agent')
project_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(project_root / 'backend/src'))
from fpl_app.contracts import Fixture, ManagerState, Pick, Player, Projection, ProjectionRun, Settings
from fpl_app.domain.rules import apply_transfers, select_lineup, readiness
from fpl_app.optimisation.planner import recommend
from fpl_app.models.baseline import baseline_run
from fpl_app.features.pipeline import NUMERIC_FEATURES

positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3
players = [Player(player_id=i+1, name=f'P{i+1}', club=i//3+1, position=pos, market_price_units=50) for i,pos in enumerate(positions)]
players += [Player(player_id=16, name='Cheap reserve GK', club=7, position=1, market_price_units=45), Player(player_id=17, name='Premium MID', club=8, position=3, market_price_units=55), Player(player_id=18, name='GK upgrade', club=9, position=1, market_price_units=50)]
picks = [Pick(player_id=p.player_id, purchase_price_units=50, position=i+1, acquisition_id=f'original-{p.player_id}') for i,p in enumerate(players[:15])]
state = ManagerState(team_id=1, current_chip_confirmed=True, snapshot_id='audit', bank_units=0, free_transfers_at_event_start=2, transfers_made_this_event=0, confirmed_hit_points=0, picks=picks, chips={f'{c}_{w}':True for c in ['wildcard','free_hit','bench_boost','triple_captain'] for w in [1,2]}, event_start_picks=[p.model_copy(deep=True) for p in picks], event_start_bank_units=0)
values = [10,9,7,6,5,4,3,9,8,7,6,5,6,5,4,0,16,15]
fixtures = [Fixture(fixture_id=c,event=8,home_club=c,away_club=c+100) for c in {p.club for p in players}]
projections = [Projection(player_id=p.player_id,fixture_id=p.club,event=8,expected_points=float(v),expected_minutes=90,appearance_probability=1) for p,v in zip(players,values)]
run = ProjectionRun(projection_run_id='audit',snapshot_id='audit',source_cutoff='2026-10-09T00:00:00Z',data_mode='demo',horizon_events=1,projections=projections,fixtures=fixtures)
settings=Settings(horizon_events=1,max_additional_hit_points=0,max_transfers_this_event=2,solver_time_limit_seconds=15)
assert readiness(state,players)['transfers_ready']
rec=recommend(state,players,run,settings)
baseline=rec.baseline_plan.net_points
best_returned=max([baseline]+[p.net_points for p in rec.alternatives])
oracle=baseline
oracle_moves=[]
legal_single=[{'out':o.player_id,'in':p.player_id} for o in picks for p in players[15:] if players[o.player_id-1].position==p.position]
for n in [1,2]:
    for moves in itertools.combinations(legal_single,n):
        if len({m['out'] for m in moves})<n or len({m['in'] for m in moves})<n: continue
        for ordering in itertools.permutations(moves):
            try:
                changed,_=apply_transfers(state,players,list(ordering),None)
                score=select_lineup(changed,players,projections,8)['expected_points']
                if score>oracle:
                    oracle,oracle_moves=score,list(ordering)
            except ValueError:
                pass
result={'audit_commit':'e759bcfb299d3f818d2e80ebb017796874cf8019','candidate_search_probe':{'synthetic':True,'baseline_points':baseline,'best_returned_points':best_returned,'exhaustive_legal_best_points':oracle,'missed_points':oracle-best_returned,'oracle_moves':oracle_moves,'returned': [{'points':p.net_points,'moves':p.actions} for p in rec.alternatives], 'solver':rec.baseline_plan.solver},'catboost_feature_columns':NUMERIC_FEATURES}
injured=Player(player_id=1,name='Injured',club=1,position=3,market_price_units=50,points_per_game=6,minutes=630,appearances=7,availability=0)
future=[Fixture(fixture_id=100+e,event=e,home_club=1,away_club=2) for e in range(8,16)]
injury_run=baseline_run([injured],future,'audit','2026-10-09T00:00:00Z','live',8,8)
result['injury_horizon_probe']={'synthetic':True,'event_points':{p.event:p.expected_points for p in injury_run.projections},'event_minutes':{p.event:p.expected_minutes for p in injury_run.projections}}
print(json.dumps(result,indent=2))
Path(__file__).with_name('audit_probe_results.json').write_text(json.dumps(result,indent=2))
