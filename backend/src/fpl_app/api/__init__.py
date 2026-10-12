"""Local advisory API. Provider access occurs only on the backend."""

import json
import uuid
from datetime import UTC
from typing import Annotated, Any, Literal

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from fpl_app.contracts import (
    AnalysisRequest,
    Fixture,
    ManagerState,
    Plan,
    Player,
    ProjectionRun,
    Recommendation,
)
from fpl_app.jobs import Queue, input_state, inputs, projection_players
from fpl_app.providers import Provider, demo
from fpl_app.storage import Conflict, Store, utcnow


class StateEdit(BaseModel):
    expected_version: int = Field(ge=1)
    state: ManagerState
    confirm_event_rollover: bool = Field(default=False, strict=True)


class ImportRequest(BaseModel):
    team_id: int | str | None = None
    url: str | None = None


class ProjectionRequest(BaseModel):
    provider: str = "baseline"
    mode: Literal["default", "experimental", "shadow"] = "default"
    artifact_id: str | None = None
    serving_bundle_id: str | None = None
    team_id: int
    horizon_events: int = Field(default=6, ge=1, le=8)


class RefreshRequest(BaseModel):
    resources: list[str] = Field(default_factory=lambda: ["bootstrap", "fixtures"])
    force: bool = False


class CollectionRequest(BaseModel):
    player_ids: list[Annotated[int, Field(gt=0, strict=True)]] = Field(
        default_factory=list, max_length=100
    )
    force: bool = True


class ServingBundleRequest(BaseModel):
    team_id: int
    collection_id: str
    artifact_id: str


class Incomplete(ValueError):
    pass


class StateVersionConflict(Conflict):
    pass


class SaveRequest(BaseModel):
    recommendation_id: str
    plan_id: str


class PlayersResponse(BaseModel):
    players: list[Player]
    snapshot_id: str
    data_mode: str


class FixturesResponse(BaseModel):
    fixtures: list[Fixture]
    snapshot_id: str
    data_mode: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    result: ProjectionRun | Recommendation | dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class SellingPriceSuggestion(BaseModel):
    player_id: int
    purchase_event: int
    purchase_price_units: int
    market_price_units: int
    selling_price_units: int
    provenance: Literal["published_gameweek_price_estimate"]
    estimate: Literal[True] = True


class SellingPriceSuggestions(BaseModel):
    team_id: int
    provenance: Literal["published_gameweek_price_estimate"]
    estimate: Literal[True] = True
    note: str
    suggestions: list[SellingPriceSuggestion]
    missing: list[dict[str, Any]] = Field(default_factory=list)


class SavedPlan(BaseModel):
    plan_id: str
    team_id: int
    recommendation_id: str
    plan: Plan
    input_fingerprint: str
    saved_at: str
    stale_reasons: list[str] = Field(default_factory=list)


def job_response(job: dict[str, Any]) -> JobResponse:
    return JobResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"],
    )


def create_app(store: Store | None = None, provider: Provider | None = None) -> FastAPI:
    app = FastAPI(title="FPL Assistant", version="0.1.0")
    database = store or Store()
    source = provider or Provider(database)
    queue = Queue(database)
    app.state.store, app.state.queue, app.state.provider = database, queue, source
    prefix = "/api/v1"

    @app.middleware("http")
    async def request_id(request: Request, call_next: Any) -> Any:
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error(
        request: Request, status: int, code: str, message: str, details: Any = None
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "details": details,
                "request_id": getattr(request.state, "request_id", uuid.uuid4().hex),
            },
        )

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict) -> JSONResponse:
        return error(
            request,
            409,
            "STATE_VERSION_CONFLICT" if isinstance(exc, StateVersionConflict) else "STALE_INPUTS",
            str(exc),
        )

    @app.exception_handler(KeyError)
    async def missing(request: Request, exc: KeyError) -> JSONResponse:
        return error(request, 404, "NOT_FOUND", "Requested local entity does not exist")

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError) -> JSONResponse:
        return error(
            request,
            422,
            "INCOMPLETE_MANAGER_STATE" if isinstance(exc, Incomplete) else "INVALID_INPUT",
            str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(
            request,
            422,
            "VALIDATION_ERROR",
            "Invalid request fields",
            [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
        )

    @app.exception_handler(httpx.HTTPError)
    async def unavailable(request: Request, exc: httpx.HTTPError) -> JSONResponse:
        return error(
            request, 503, "PROVIDER_UNAVAILABLE", "Provider unavailable; last good data retained"
        )

    @app.get(prefix + "/health")
    def health() -> dict[str, Any]:
        from sqlalchemy import text

        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok", "schema_version": 1}

    def current_data(mode: str) -> dict[str, Any]:
        if mode not in ("demo", "live"):
            raise ValueError("Unknown data mode")
        return database.get("dataset", database.get("current", mode)["snapshot_id"])

    @app.get(prefix + "/status")
    def status(data_mode: str = "demo") -> dict[str, Any]:
        from fpl_app.models import registry

        try:
            data = current_data(data_mode)
        except KeyError:
            return {"data_mode": data_mode, "available": False, "models": registry()}
        snapshot = database.snapshot(data["snapshot_id"])
        from datetime import datetime

        age = (datetime.now(UTC) - datetime.fromisoformat(data["source_cutoff"])).total_seconds()
        return {
            "available": True,
            "data_mode": data_mode,
            "season": "2026/27",
            "next_event": data["next_event"],
            "snapshot_id": data["snapshot_id"],
            "captured_at": snapshot["captured_at"],
            "source_cutoff": data["source_cutoff"],
            "stale": age > 21600,
            "age_seconds": age,
            "models": registry(),
            "provenance": "synthetic" if data_mode == "demo" else "official_fpl",
            "deadline": next(
                (e["deadline_time"] for e in data["events"] if e["id"] == data["next_event"]), None
            ),
        }

    def persist(state: ManagerState, expected_version: int | None = None) -> ManagerState:
        if expected_version is None:
            try:
                previous = database.get("state", state.team_id)
                version = previous["state_version"]
            except KeyError:
                version = 0
        else:
            version = expected_version
        state.state_version = version + 1
        database.put("state", state.team_id, state.model_dump(mode="json"), expected=version)
        return state

    @app.post(prefix + "/demo", response_model=ManagerState)
    def load_demo() -> ManagerState:
        return persist(demo(database))

    @app.post(prefix + "/teams/import", response_model=ManagerState)
    def import_team(body: ImportRequest) -> ManagerState:
        if (body.team_id is None) == (body.url is None):
            raise ValueError("Provide exactly one team ID or official URL")
        value = body.team_id if body.team_id is not None else body.url
        assert value is not None
        imported = source.import_team(value)
        try:
            existing = ManagerState.model_validate(database.get("state", imported.team_id))
        except KeyError:
            return persist(imported, expected_version=0)
        if (
            existing.data_mode != "live"
            or imported.data_mode != "live"
            or existing.season != imported.season
            or existing.next_event != imported.next_event
            or {p.player_id for p in existing.picks} != {p.player_id for p in imported.picks}
        ):
            raise Conflict(
                "Public import differs from the existing season, next event or owned squad. "
                "Existing manager state must be reviewed before replacing it; "
                "private state has been retained."
            )
        existing.snapshot_id = imported.snapshot_id
        existing.public_source_event = imported.public_source_event
        source_prefix = "Public picks source snapshot: "
        existing.warnings = list(
            dict.fromkeys(
                [w for w in existing.warnings if not w.startswith(source_prefix)]
                + [w for w in imported.warnings if w.startswith(source_prefix)]
                + [
                    (
                        "Public deadline picks may differ from the current private squad or lineup; "
                        "existing private corrections have been preserved."
                    )
                ]
            )
        )
        return persist(existing, expected_version=existing.state_version)

    @app.get(prefix + "/teams/{team_id}/state", response_model=ManagerState)
    def get_state(team_id: int) -> ManagerState:
        return ManagerState.model_validate(database.get("state", team_id))

    @app.patch(prefix + "/teams/{team_id}/state", response_model=ManagerState)
    def patch_state(team_id: int, body: StateEdit) -> ManagerState:
        from fpl_app.domain import validate_squad

        old = get_state(team_id)
        if body.expected_version != old.state_version:
            raise StateVersionConflict("State version changed")
        state = body.state
        if (
            state.next_event != old.next_event
            and not body.confirm_event_rollover
            and (
                any(
                    getattr(state, field) is not None
                    for field in (
                        "bank_units",
                        "free_transfers_at_event_start",
                        "transfers_made_this_event",
                        "confirmed_hit_points",
                    )
                )
                or state.current_chip_confirmed
                or any(p.selling_price_units is not None for p in state.picks)
            )
        ):
            raise ValueError("Explicit new-gameweek review required for private confirmations")
        if state.team_id != team_id or state.data_mode != old.data_mode:
            raise ValueError("Team identity and data mode cannot change")
        current = current_data(state.data_mode)
        if state.snapshot_id != current["snapshot_id"]:
            raise Conflict("Correction must use current snapshot")
        if state.data_mode == "live" and state.next_event != current["next_event"]:
            raise Conflict(
                "Correction must review the current gameweek and private financial state"
            )
        problems = validate_squad(state, [Player.model_validate(p) for p in current["players"]])
        if problems:
            raise ValueError("; ".join(problems))
        state.state_version = old.state_version + 1
        if state.public_source_event is not None:
            state.warnings = list(
                dict.fromkeys(
                    state.warnings
                    + [
                        "Public deadline import corrected by user; current private squad not verified."
                    ]
                )
            )
        timestamp = utcnow()
        for name in (
            "bank_units",
            "free_transfers_at_event_start",
            "transfers_made_this_event",
            "confirmed_hit_points",
        ):
            state.financial_provenance[name] = (
                "user_confirmed" if getattr(state, name) is not None else "unknown"
            )
        state.financial_confirmed_at = timestamp
        for pick in state.picks:
            if pick.selling_price_units is not None:
                if pick.selling_price_market_units is None:
                    raise ValueError("Confirmed selling price requires market snapshot price")
                market = next(
                    p["market_price_units"]
                    for p in current["players"]
                    if p["player_id"] == pick.player_id
                )
                if pick.selling_price_units > market:
                    raise ValueError("Selling price cannot exceed market price")
                if pick.purchase_price_units is not None:
                    from fpl_app.domain import selling_price

                    if pick.selling_price_units != selling_price(pick.purchase_price_units, market):
                        raise ValueError(
                            "Selling price conflicts with acquisition and current market price"
                        )
                if pick.selling_price_market_units != market:
                    raise ValueError("Selling price confirmation is stale")
                pick.selling_price_provenance = "user_confirmed"
                pick.confirmed_at = timestamp
        database.put("state", team_id, state.model_dump(mode="json"), body.expected_version)
        return state

    @app.delete(prefix + "/teams/{team_id}/state")
    def delete_state(team_id: int) -> dict[str, Any]:
        database.delete_team(team_id)
        return {"deleted": True, "team_id": team_id}

    @app.get(prefix + "/teams/{team_id}/export")
    def export_state(team_id: int) -> Response:
        return Response(
            get_state(team_id).model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="fpl-state.json"'},
        )

    @app.get(
        prefix + "/teams/{team_id}/selling-price-suggestions",
        response_model=SellingPriceSuggestions,
    )
    def selling_price_suggestions(team_id: int) -> SellingPriceSuggestions:
        from fpl_app.providers import team_id as parse_team_id
        from fpl_app.providers.prices import suggest_selling_prices

        identifier = parse_team_id(team_id)
        state = get_state(identifier)
        data = current_data(state.data_mode)
        if state.snapshot_id != data["snapshot_id"]:
            raise Conflict("Selling-price estimate requires the current snapshot")
        markets = {p["player_id"]: p["market_price_units"] for p in data["players"]}
        history = json.loads(source.fetch(f"entry/{identifier}/history/")["raw"])
        transfers = json.loads(source.fetch(f"entry/{identifier}/transfers/")["raw"])
        element_histories = {}
        for pick in state.picks:
            if type(pick.player_id) is not int or pick.player_id < 1:
                raise ValueError("Invalid squad player")
            summary = json.loads(source.fetch(f"element-summary/{pick.player_id}/")["raw"])
            element_histories[pick.player_id] = summary["history"]
        suggestions, missing = suggest_selling_prices(
            [pick.player_id for pick in state.picks],
            markets,
            transfers,
            history,
            element_histories,
        )
        return SellingPriceSuggestions(
            team_id=identifier,
            provenance="published_gameweek_price_estimate",
            note=(
                "Estimate from the published price in the gameweek the player was bought. "
                "Not a stored confirmation. Free transfers are not inferred from season history."
            ),
            suggestions=[SellingPriceSuggestion.model_validate(row) for row in suggestions],
            missing=missing,
        )

    @app.get(prefix + "/teams/{team_id}/readiness")
    def get_readiness(team_id: int) -> dict[str, Any]:
        from fpl_app.domain import readiness

        state, data = input_state(database, team_id)
        return dict(readiness(state, [Player.model_validate(p) for p in data["players"]]))

    @app.get(prefix + "/players", response_model=PlayersResponse)
    def players(
        data_mode: str = "demo",
        position: int | None = None,
        search: str = "",
        max_price_units: int | None = None,
        event: int | None = None,
        projection_run_id: str | None = None,
    ) -> PlayersResponse:
        data = current_data(data_mode)
        if projection_run_id:
            run = get_projection(projection_run_id)
            if run.snapshot_id != data["snapshot_id"]:
                raise Conflict("Player projection is stale")
        selected = [
            Player.model_validate(p)
            for p in data["players"]
            if (position is None or p["position"] == position)
            and search.casefold() in p["name"].casefold()
            and (max_price_units is None or p["market_price_units"] <= max_price_units)
        ]
        if event is not None:
            clubs = {
                f[k]
                for f in data["fixtures"]
                if f["event"] == event
                for k in ("home_club", "away_club")
            }
            selected = [p for p in selected if p.club in clubs]
        return PlayersResponse(
            players=selected, snapshot_id=data["snapshot_id"], data_mode=data_mode
        )

    @app.get(prefix + "/fixtures", response_model=FixturesResponse)
    def fixtures(
        data_mode: str = "demo", event_start: int = 1, event_end: int = 38
    ) -> FixturesResponse:
        data = current_data(data_mode)
        return FixturesResponse(
            fixtures=[
                Fixture.model_validate(f)
                for f in data["fixtures"]
                if f["event"] is not None and event_start <= f["event"] <= event_end
            ],
            snapshot_id=data["snapshot_id"],
            data_mode=data_mode,
        )

    @app.post(prefix + "/data/refresh", response_model=JobResponse, status_code=202)
    def refresh(body: RefreshRequest) -> JobResponse:
        if set(body.resources) - {"bootstrap", "fixtures", "bootstrap-static"}:
            raise ValueError("Only bootstrap and fixtures refresh supported")
        return job_response(queue.enqueue("refresh", body.model_dump()))

    @app.post(prefix + "/projections/runs", response_model=JobResponse, status_code=202)
    def project(body: ProjectionRequest) -> JobResponse:
        return job_response(queue.enqueue("projection", body.model_dump()))

    @app.post(prefix + "/projections/bundles", status_code=201)
    def serving_bundle(body: ServingBundleRequest) -> dict[str, Any]:
        from fpl_app.models.router import create_serving_bundle

        state, _ = input_state(database, body.team_id)
        return create_serving_bundle(database, state, body.collection_id, body.artifact_id)

    @app.post(prefix + "/data/collections", response_model=JobResponse, status_code=202)
    def collect(body: CollectionRequest) -> JobResponse:
        return job_response(queue.enqueue("collection", body.model_dump()))

    @app.get(prefix + "/data/collections/{collection_id}")
    def collection(collection_id: str) -> dict[str, Any]:
        from fpl_app.providers.collection import load_collection

        return load_collection(database, collection_id)

    @app.get(prefix + "/data/collections")
    def collections() -> dict[str, Any]:
        return {
            "collections": [
                {
                    "collection_id": c["collection_id"],
                    "captured_at": c["captured_at"],
                    "actual_deadline": c.get("actual_deadline"),
                    "player_count": len(c.get("player_ids", [])),
                }
                for c in database.list("football_collection")
            ]
        }

    @app.get(prefix + "/social/status")
    def social_status() -> dict[str, Any]:
        from fpl_app.social.providers import RedditAdapter, XAdapter

        return {
            "providers": [a.status().model_dump() for a in (RedditAdapter(), XAdapter())],
            "points_adjustment": 0,
            "extraction_status": "offline_experimental",
            "accuracy_benchmark": None,
        }

    @app.get(prefix + "/projections/runs/{run_id}", response_model=ProjectionRun)
    def get_projection(run_id: str) -> ProjectionRun:
        return ProjectionRun.model_validate(database.get("projection", run_id))

    @app.post(prefix + "/lineup")
    def lineup(body: AnalysisRequest) -> dict[str, Any]:
        from fpl_app.domain import select_lineup

        inputs(database, "recommendation", body.model_dump(mode="json"))
        state, data = input_state(database, body.team_id)
        run = get_projection(body.projection_run_id)
        return select_lineup(
            state,
            projection_players(state, data, run),
            run.projections,
            state.next_event,
        )

    @app.post(prefix + "/recommendations", response_model=JobResponse, status_code=202)
    def analyse(body: AnalysisRequest) -> JobResponse:
        from fpl_app.domain import readiness

        inputs(database, "recommendation", body.model_dump(mode="json"))
        state, data = input_state(database, body.team_id)
        ready = readiness(state, [Player.model_validate(p) for p in data["players"]])
        if body.analysis_mode == "transfers" and not ready["transfers_ready"]:
            raise Incomplete(
                "Confirm manager state before transfers: "
                + "; ".join(ready["missing_fields"] + ready["errors"])
            )
        return job_response(queue.enqueue("recommendation", body.model_dump(mode="json")))

    @app.get(prefix + "/recommendations/{recommendation_id}", response_model=Recommendation)
    def get_recommendation(recommendation_id: str) -> Recommendation:
        return Recommendation.model_validate(database.get("recommendation", recommendation_id))

    @app.get(prefix + "/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str) -> JobResponse:
        return job_response(queue.get(job_id))

    @app.post(prefix + "/jobs/{job_id}/cancel", response_model=JobResponse)
    def cancel_job(job_id: str) -> JobResponse:
        return job_response(queue.cancel(job_id))

    def stale(saved: dict[str, Any]) -> list[str]:
        reference = database.get("recommendation_input", saved["recommendation_id"])
        try:
            current = inputs(database, "recommendation", reference["payload"])
            return (
                [] if current == saved["input_fingerprint"] else ["Recommendation inputs changed"]
            )
        except (KeyError, Conflict):
            return ["Manager state, projection or source snapshot changed"]

    @app.post(prefix + "/plans", response_model=SavedPlan)
    def save_plan(body: SaveRequest) -> SavedPlan:
        recommendation = get_recommendation(body.recommendation_id)
        reference = database.get("recommendation_input", body.recommendation_id)
        current = inputs(database, "recommendation", reference["payload"])
        if current != reference["fingerprint"]:
            raise Conflict("Recommendation inputs changed before save")
        plan = next(
            (
                p
                for p in [
                    recommendation.baseline_plan,
                    *recommendation.alternatives,
                    *([recommendation.gameweek_optimum] if recommendation.gameweek_optimum else []),
                ]
                if p.plan_id == body.plan_id
            ),
            None,
        )
        if plan is None:
            raise ValueError("Plan does not belong to recommendation")
        from fpl_app.optimisation import validate_plan

        state, data = input_state(database, reference["payload"]["team_id"])
        request = AnalysisRequest.model_validate(reference["payload"])
        run = get_projection(request.projection_run_id)
        errors = validate_plan(
            plan,
            state,
            projection_players(state, data, run),
            run,
            request.settings,
            recommendation.baseline_plan,
            enforce_preferences=plan.plan_id != recommendation.baseline_plan.plan_id,
        )
        if errors:
            raise ValueError("Saved plan failed independent validation: " + "; ".join(errors))
        saved = SavedPlan(
            plan_id=plan.plan_id,
            team_id=reference["payload"]["team_id"],
            recommendation_id=body.recommendation_id,
            plan=plan,
            input_fingerprint=current,
            saved_at=utcnow(),
        )

        def verify() -> None:
            if inputs(database, "recommendation", reference["payload"]) != reference["fingerprint"]:
                raise Conflict("Recommendation inputs changed during save")

        database.put_checked("plan", plan.plan_id, saved.model_dump(mode="json"), verify)
        return saved

    @app.get(prefix + "/plans", response_model=list[SavedPlan])
    def list_plans() -> list[SavedPlan]:
        return [
            SavedPlan.model_validate({**p, "stale_reasons": stale(p)})
            for p in database.list("plan")
        ]

    @app.get(prefix + "/plans/{plan_id}", response_model=SavedPlan)
    def get_plan(plan_id: str) -> SavedPlan:
        saved = database.get("plan", plan_id)
        return SavedPlan.model_validate({**saved, "stale_reasons": stale(saved)})

    @app.get(prefix + "/plans/{plan_id}/export")
    def export_plan(plan_id: str) -> Response:
        plan = get_plan(plan_id)
        return Response(
            plan.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="fpl-plan.json"'},
        )

    @app.get(prefix + "/backup")
    def backup() -> dict[str, Any]:
        return {
            "schema_version": 1,
            "created_at": utcnow(),
            "states": database.list("state"),
            "saved_plans": [p.model_dump(mode="json") for p in list_plans()],
            "projections": database.list("projection"),
        }

    @app.get(prefix + "/models")
    def models() -> dict[str, Any]:
        from fpl_app.models import registry

        return {"models": registry()}

    @app.get(prefix + "/evaluations")
    def evaluations() -> list[dict[str, Any]]:
        return database.list("evaluation")

    return app
