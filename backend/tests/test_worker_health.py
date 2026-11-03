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
