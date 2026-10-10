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
