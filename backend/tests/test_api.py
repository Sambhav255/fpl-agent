import pytest
from fastapi.testclient import TestClient

from fpl_app.api import create_app
from fpl_app.jobs import Worker
from fpl_app.storage import Store


def test_offline_full_flow_and_save_reload(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    app = create_app(store)
    client = TestClient(app)
    prefix = "/api/v1"
    assert client.get(prefix + "/health").status_code == 200
    state = client.post(prefix + "/demo").json()
    assert state["data_mode"] == "demo" and len(state["picks"]) == 15
    assert client.get(prefix + "/players").json()["data_mode"] == "demo"
    assert client.get(prefix + "/status").json()["provenance"] == "synthetic"
    job = client.post(prefix + "/projections/runs", json={"team_id": 0, "horizon_events": 1}).json()
    assert Worker(app.state.queue).run_once()
    completed = client.get(prefix + "/jobs/" + job["job_id"]).json()
    assert completed["status"] == "succeeded", completed
    run = completed["result"]
    request = {
        "team_id": 0,
        "expected_state_version": state["state_version"],
        "projection_run_id": run["projection_run_id"],
        "settings": {"horizon_events": 1, "solver_time_limit_seconds": 0.1},
    }
    response = client.post(prefix + "/recommendations", json=request)
    assert response.status_code == 202, response.text
    assert Worker(app.state.queue).run_once()
    result = client.get(prefix + "/jobs/" + response.json()["job_id"]).json()
    assert result["status"] == "succeeded", result
    recommendation = result["result"]
    body = {
        "recommendation_id": recommendation["recommendation_id"],
        "plan_id": recommendation["baseline_plan"]["plan_id"],
    }
    saved = client.post(prefix + "/plans", json=body)
    assert saved.status_code == 200, saved.text
    optimum = recommendation["gameweek_optimum"]
    assert optimum is not None
    optimum_saved = client.post(
        prefix + "/plans",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "plan_id": optimum["plan_id"],
        },
    )
    assert optimum_saved.status_code == 200, optimum_saved.text
    reopened = TestClient(create_app(Store(f"sqlite:///{tmp_path}/app.sqlite")))
    assert reopened.get(prefix + "/plans/" + body["plan_id"]).json()["stale_reasons"] == []
    assert reopened.get(prefix + "/plans/" + body["plan_id"] + "/export").status_code == 200
    state["bank_units"] += 1
    patch = client.patch(prefix + "/teams/0/state", json={"expected_version": 1, "state": state})
    assert patch.status_code == 200, patch.text
    assert (
        client.patch(
            prefix + "/teams/0/state", json={"expected_version": 1, "state": state}
        ).json()["code"]
        == "STATE_VERSION_CONFLICT"
    )
    assert client.get(prefix + "/plans/" + body["plan_id"]).json()["stale_reasons"]
    assert client.post(prefix + "/plans", json=body).status_code == 409
    assert client.delete(prefix + "/teams/0/state").status_code == 200
    assert client.get(prefix + "/teams/0/state").status_code == 404


def test_unknown_finances_lineup_and_transfer_preflight(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    app = create_app(store)
    client = TestClient(app)
    state = client.post("/api/v1/demo").json()
    state.update(
        bank_units=None,
        free_transfers_at_event_start=None,
        confirmed_hit_points=None,
        transfers_made_this_event=None,
    )
    for pick in state["picks"]:
        pick.update(purchase_price_units=None, selling_price_units=None)
    response = client.patch("/api/v1/teams/0/state", json={"expected_version": 1, "state": state})
    assert response.status_code == 200, response.text
    job = client.post("/api/v1/projections/runs", json={"team_id": 0, "horizon_events": 1}).json()
    Worker(app.state.queue).run_once()
    result = client.get("/api/v1/jobs/" + job["job_id"]).json()
    assert result["status"] == "succeeded", result
    request = {
        "team_id": 0,
        "expected_state_version": 2,
        "projection_run_id": result["result"]["projection_run_id"],
        "settings": {"horizon_events": 1},
    }
    assert client.post("/api/v1/lineup", json=request).status_code == 200
    response = client.post("/api/v1/recommendations", json=request)
    assert response.status_code == 422
    assert response.json()["code"] == "INCOMPLETE_MANAGER_STATE"
    request["analysis_mode"] = "lineup"
    response = client.post("/api/v1/recommendations", json=request)
    assert response.status_code == 202, response.text
    Worker(app.state.queue).run_once()
    completed = client.get("/api/v1/jobs/" + response.json()["job_id"]).json()
    assert completed["status"] == "succeeded", completed
    assert completed["result"]["baseline_plan"]["bank_units"] is None
    assert completed["result"]["baseline_plan"]["solver"]["status"] == "lineup_only"
    assert not completed["result"]["alternatives"]
    saved = client.post(
        "/api/v1/plans",
        json={
            "recommendation_id": completed["result"]["recommendation_id"],
            "plan_id": completed["result"]["baseline_plan"]["plan_id"],
        },
    )
    assert saved.status_code == 200, saved.text


def test_openapi_and_request_errors(tmp_path):
    app = create_app(Store(f"sqlite:///{tmp_path}/app.sqlite"))
    names = app.openapi()["components"]["schemas"]
    assert all(
        name in names for name in ("Player", "ManagerState", "ProjectionRun", "Recommendation")
    )
    response = TestClient(app).post("/api/v1/teams/import", json={"url": "https://evil.com/"})
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "details", "request_id"}


def test_refresh_correction_and_projection_staleness(tmp_path):
    from fpl_app.providers import demo

    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    app = create_app(store)
    client = TestClient(app)
    state = client.post("/api/v1/demo").json()
    job = client.post("/api/v1/projections/runs", json={"team_id": 0, "horizon_events": 1}).json()
    Worker(app.state.queue).run_once()
    result = client.get("/api/v1/jobs/" + job["job_id"]).json()["result"]
    new_state = demo(store)
    assert new_state.snapshot_id != state["snapshot_id"]
    old_request = {
        "team_id": 0,
        "expected_state_version": 1,
        "projection_run_id": result["projection_run_id"],
        "settings": {"horizon_events": 1},
    }
    assert client.post("/api/v1/recommendations", json=old_request).json()["code"] == "STALE_INPUTS"
    state["snapshot_id"] = new_state.snapshot_id
    response = client.patch("/api/v1/teams/0/state", json={"expected_version": 1, "state": state})
    assert response.status_code == 200, response.text
    old_request["expected_state_version"] = 2
    assert client.post("/api/v1/recommendations", json=old_request).status_code == 409
    assert client.get("/api/v1/status").json()["snapshot_id"] == new_state.snapshot_id


def test_canonical_data_configuration(monkeypatch):
    from pathlib import Path

    from fpl_app.storage import database_url

    root = Path(__file__).resolve().parents[2]
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FPL_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert database_url() == f"sqlite:///{root}/data/app.sqlite"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///../data/custom.sqlite")
    assert database_url() == f"sqlite:///{root}/data/custom.sqlite"


def test_impossible_selling_price_rejected_without_mutation(tmp_path):
    client = TestClient(create_app(Store(f"sqlite:///{tmp_path}/app.sqlite")))
    state = client.post("/api/v1/demo").json()
    pick = state["picks"][0]
    market = pick["selling_price_market_units"]
    pick["selling_price_units"] = market + 1
    response = client.patch("/api/v1/teams/0/state", json={"expected_version": 1, "state": state})
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/teams/0/state").json()["state_version"] == 1
    pick["selling_price_units"] = market - 1
    response = client.patch("/api/v1/teams/0/state", json={"expected_version": 1, "state": state})
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/teams/0/state").json()["state_version"] == 1


@pytest.fixture
def public_import(tmp_path, monkeypatch):
    from fpl_app.providers import Provider, demo

    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    provider = Provider(store)
    public = demo(store)
    public.team_id = 123
    public.data_mode = "live"
    public.public_source_event = 7
    public.bank_units = None
    public.free_transfers_at_event_start = None
    public.transfers_made_this_event = None
    public.confirmed_hit_points = None
    public.financial_provenance = {"bank_units": "unknown"}
    public.chips = {"free_hit": None, "wildcard": None}
    public.persistent_picks = None
    public.event_start_picks = None
    for pick in public.picks:
        pick.purchase_price_units = None
        pick.selling_price_units = None
        pick.selling_price_market_units = None
        pick.selling_price_provenance = "unknown"
        pick.confirmed_at = None
        pick.acquisition_id = None
    public.warnings = ["Public picks source snapshot: original"]
    monkeypatch.setattr(provider, "import_team", lambda value: public.model_copy(deep=True))
    return store, TestClient(create_app(store, provider)), public


@pytest.mark.parametrize("confirmed", [False, True])
def test_identical_reimport_preserves_all_private_state(public_import, confirmed):
    from fpl_app.contracts import ManagerState

    store, client, public = public_import
    first = client.post("/api/v1/teams/import", json={"team_id": 123})
    assert first.status_code == 200, first.text
    assert first.json() == public.model_dump(mode="json")
    state = first.json()
    if confirmed:
        state.update(
            bank_units=17,
            free_transfers_at_event_start=2,
            transfers_made_this_event=3,
            confirmed_hit_points=4,
            financial_provenance={"bank_units": "user_confirmed"},
            financial_confirmed_at="2026-10-10T10:00:00Z",
            chips={"free_hit": False, "wildcard": True, "bench_boost": None},
            current_chip="free_hit",
            current_chip_confirmed=True,
            previous_free_hit_event=6,
            event_start_bank_units=23,
            club_limit_exception=True,
            transfer_ledger=[{"event": 8, "out": 1, "in": 2, "source": "user_confirmed"}],
        )
        state["picks"][0].update(
            purchase_price_units=44,
            selling_price_units=44,
            selling_price_market_units=45,
            selling_price_provenance="user_confirmed",
            confirmed_at="2026-10-10T10:00:00Z",
            acquisition_id="private-acquisition",
        )
        state["persistent_picks"] = [dict(p) for p in state["picks"]]
        state["persistent_picks"][0]["player_id"] = 999
        state["event_start_picks"] = [dict(p) for p in state["persistent_picks"]]
    # Store a valid private-state version without the correction endpoint rewriting provenance.
    state["state_version"] = 2
    store.put("state", 123, ManagerState.model_validate(state).model_dump(mode="json"), expected=1)
    public.snapshot_id = "refreshed-bootstrap"
    public.public_source_event = 6
    public.warnings = ["Public picks source snapshot: refreshed"]
    public.picks.reverse()  # Same ownership does not mean the same public lineup.
    public.picks[0].is_captain = not public.picks[0].is_captain
    for _ in range(2):
        response = client.post("/api/v1/teams/import", json={"team_id": 123})
        assert response.status_code == 200, response.text
        result = response.json()
        state.update(
            state_version=state["state_version"] + 1,
            snapshot_id=public.snapshot_id,
            public_source_event=public.public_source_event,
            warnings=[
                "Public picks source snapshot: refreshed",
                (
                    "Public deadline picks may differ from the current private squad or lineup; "
                    "existing private corrections have been preserved."
                ),
            ],
        )
        assert set(result["warnings"]) == set(state["warnings"])
        assert len(result["warnings"]) == len(state["warnings"])
        state["warnings"] = result["warnings"]
        assert result == state
        assert client.get("/api/v1/teams/123/state").json() == state


@pytest.mark.parametrize("change", ["next_event", "squad", "season"])
def test_changed_public_import_refuses_to_overwrite(public_import, change):
    store, client, public = public_import
    before = client.post("/api/v1/teams/import", json={"team_id": 123}).json()
    if change == "next_event":
        public.next_event += 1
    elif change == "season":
        public.season = "2027/28"
    else:
        public.picks[0].player_id = 999
    response = client.post("/api/v1/teams/import", json={"team_id": 123})
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "STALE_INPUTS"
    assert "must be reviewed" in response.json()["message"]
    assert store.get("state", 123) == before


def test_reimport_cas_preserves_concurrent_correction(public_import, monkeypatch):
    store, client, public = public_import
    before = client.post("/api/v1/teams/import", json={"team_id": 123}).json()
    original_put = store.put
    corrected = dict(before, bank_units=19, state_version=2)

    def concurrent_put(kind, identifier, payload, expected=None):
        if kind == "state":
            original_put(kind, identifier, corrected, expected=1)
        return original_put(kind, identifier, payload, expected)

    monkeypatch.setattr(store, "put", concurrent_put)
    public.snapshot_id = "refreshed"
    response = client.post("/api/v1/teams/import", json={"team_id": 123})
    assert response.status_code == 409, response.text
    assert store.get("state", 123) == corrected
