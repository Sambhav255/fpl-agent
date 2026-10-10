# Integration contracts
Lead owns contracts.py, dependency manifests/locks, root scripts and generated OpenAPI types. Agents own disjoint directories; request shared changes through lead.

Domain public functions: validate_squad(state, players) -> list[str]; readiness(state, players) -> dict; selling_price(purchase, market) -> int; select_lineup(state, players, projections, event, chip=None) -> dict; recommend(state, players, run, settings) -> Recommendation. Players are list[Player], projections list[Projection]. Invalid inputs raise ValueError. Full independent validation in domain required.

Models: baseline_run(players, fixtures, snapshot_id, cutoff, data_mode, next_event, horizon) -> ProjectionRun; registry() -> list[dict]. Pipeline CLI helpers documented by model agent.

Storage: SQLite via SQLAlchemy; JSON payload envelopes for versioned entities, immutable raw snapshots, persisted jobs with leases. Backend agent owns schema/storage migration code; lead reviews schema. API prefix /api/v1; see spec endpoints. POST /demo returns ManagerState; GET /teams/{id}/state returns ManagerState. GET /players returns {players: Player[], snapshot_id, data_mode}; status returns freshness metadata. PATCH state body {expected_version, state: ManagerState}; projection POST body {team_id,horizon_events}; recommendation uses AnalysisRequest. Job GET returns {job_id,status,progress,result,error}; succeeded result is full ProjectionRun or Recommendation. POST /plans body {recommendation_id,plan_id}; GET /plans returns list; GET /models returns {models:list}; all frontend contracts generated from OpenAPI.

Frontend agent owns apps/web except package.json, package-lock.json and generated types. Uses above API. Lead creates manifests.

AnalysisRequest.analysis_mode explicitly selects lineup or transfers (default transfers). Unknown finances may only enter lineup mode; Worker uses recommend(...,lineup_only=True). ManagerState.current_chip_confirmed distinguishes unknown from confirmed no active chip; club_limit_exception permits a marked real-world-club-transfer starting squad for lineup, but every resulting transfer squad remains strictly compliant. WC/FH total event transfer count has no20 cap; ordinary accounting does. ProjectionRun.fixtures retains frozen complete horizon schedule.
