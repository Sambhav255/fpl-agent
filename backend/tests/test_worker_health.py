from datetime import UTC, datetime, timedelta

from fpl_app.jobs.health import heartbeat, process_heartbeat, worker_health
from fpl_app.storage import Store


def test_process_heartbeat_detects_downtime_and_correct_store():
    store = Store("sqlite:///:memory:")
    assert worker_health(store)["status"] == "unavailable_or_stale"
    with process_heartbeat(store, "worker"):
        row = worker_health(store)["workers"][0]
        assert row["healthy"]
        assert worker_health(Store("sqlite:///:memory:"))["status"] == "unavailable_or_stale"
        late = datetime.fromisoformat(row["observed_at"]) + timedelta(seconds=91)
        assert worker_health(store, now=late)["status"] == "unavailable_or_stale"
    assert worker_health(store)["status"] == "unavailable_or_stale"
    heartbeat(store, "restarted")
    assert worker_health(store, now=datetime.now(UTC))["status"] == "healthy"


def test_health_uses_actual_finality_score_and_fit_receipts():
    import json

    from fpl_app.storage import entities

    store = Store("sqlite:///:memory:")
    heartbeat(store, "worker")
    before = worker_health(store)["learning"]
    assert before["last_finality_check"] is None
    assert before["last_final_scoring_at"] is None
    assert before["last_successful_model_fit"] is None
    store.put("review_schedule", "enabled", {"enabled": True})
    assert worker_health(store)["learning"]["next_action"] == "await_next_enabled_review"
    assert worker_health(store)["learning"]["last_successful_model_fit"] is None

    source_id = store.archive(
        json.dumps(
            {
                "events": [
                    {"id": 8, "finished": True, "data_checked": True},
                    {"id": 9, "finished": True, "data_checked": False},
                ]
            }
        ).encode(),
        "bootstrap-static/",
    )
    stamp = datetime.now(UTC).isoformat()
    store.put(
        "forecast_benchmark_outcome",
        "8:revision",
        {
            "benchmark_id": "8",
            "status": "final",
            "scored_at": stamp,
        },
    )
    store.put("learning_refit", "fit", {"artifact_directory": "private local path"})
    activity = worker_health(store)["learning"]
    assert activity["last_finality_check"]["snapshot_id"] == source_id
    assert activity["last_finality_check"]["finalized_events"] == [8]
    assert activity["last_final_scoring_at"] == stamp
    assert activity["last_successful_model_fit"]["time_basis"] == "successful_refit_publication"
    assert "private local path" not in json.dumps(activity)
    with store.engine.begin() as connection:
        connection.execute(entities.delete().where(entities.c.kind == "learning_refit"))
    assert worker_health(store)["learning"]["last_successful_model_fit"] is None


def test_health_reports_queued_failed_and_expired_work_without_payloads():
    import json

    from sqlalchemy import insert

    from fpl_app.storage import jobs

    store = Store("sqlite:///:memory:")
    now = datetime.now(UTC)
    for identifier, status, lease in [
        ("pending", "queued", None),
        ("expired", "running", now.timestamp() - 1),
        ("failure", "failed", None),
    ]:
        with store.engine.begin() as connection:
            connection.execute(
                insert(jobs).values(
                    id=identifier,
                    kind="learning_review",
                    status=status,
                    lease_until=lease,
                    progress=0,
                    attempts=1,
                    updated_at=now.isoformat(),
                    payload={"private": "do not expose"},
                    error={"code": "COMPUTATION_FAILED", "message": "private error"},
                )
            )
    assert worker_health(store, now=now)["learning"]["next_action"] == "restart_worker"
    heartbeat(store, "worker")
    activity = worker_health(store)["learning"]
    assert activity["job_counts"] == {"queued": 1, "running": 1, "failed": 1}
    assert activity["next_action"] == "recover_expired_lease"
    assert sum(row["lease_expired"] for row in activity["pending_jobs"]) == 1
    assert activity["latest_failed_job"]["code"] == "COMPUTATION_FAILED"
    assert "private" not in json.dumps(activity)


def test_health_distinguishes_ready_and_pending_benchmarks():
    import json

    store = Store("sqlite:///:memory:")
    heartbeat(store, "worker")
    store.put(
        "forecast_benchmark",
        "original",
        {
            "benchmark_id": "original",
            "event": 9,
            "season": "2026/27",
        },
    )
    assert worker_health(store)["learning"]["next_action"] == "check_official_finality"
    for finished, expected in [
        (False, "await_official_finality"),
        (True, "score_finalized_benchmarks"),
    ]:
        store.archive(
            json.dumps(
                {"events": [{"id": 9, "finished": finished, "data_checked": finished}]}
            ).encode(),
            "bootstrap-static/",
        )
        assert worker_health(store)["learning"]["next_action"] == expected


def test_launchd_template_pins_store_and_python_without_installation(tmp_path):
    import importlib.util
    import plistlib
    from pathlib import Path

    import pytest

    script = Path(__file__).resolve().parents[2] / "scripts/macos_worker.py"
    spec = importlib.util.spec_from_file_location("macos_worker", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "project with spaces"
    python = project / "backend/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    data = tmp_path / "research data"
    template = module.worker_template(project, data)
    loaded = plistlib.loads(plistlib.dumps(template))
    assert loaded["ProgramArguments"] == [str(python), "-m", "fpl_app.jobs.worker"]
    assert loaded["EnvironmentVariables"]["DATA_DIR"] == str(data)
    assert loaded["EnvironmentVariables"]["DATABASE_URL"] == f"sqlite:///{data / 'app.sqlite'}"
    assert loaded["StandardErrorPath"].startswith(str(data))
    assert not data.exists()
    with pytest.raises(ValueError, match="absolute"):
        module.worker_template(project, Path("relative"))


def test_health_rejects_naive_clock_and_receipts():
    import pytest

    store = Store("sqlite:///:memory:")
    with pytest.raises(ValueError, match="timezone"):
        worker_health(store, now=datetime(2026, 11, 4))
    store.put(
        "worker_heartbeat",
        "corrupt",
        {
            "owner": "corrupt",
            "observed_at": "2026-11-04T12:00:00",
            "stopped": False,
        },
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        worker_health(store)


def test_api_health_exposes_actual_worker_downtime_and_recovery():
    from fastapi.testclient import TestClient

    from fpl_app.api import create_app

    store = Store("sqlite:///:memory:")
    client = TestClient(create_app(store))
    response = client.get("/api/v1/health").json()
    assert response["database"] == "ok"
    assert response["worker"]["status"] == "unavailable_or_stale"
    assert response["worker"]["learning"]["next_action"] == "restart_worker"
    heartbeat(store, "actual-worker")
    assert client.get("/api/v1/health").json()["worker"]["status"] == "healthy"
