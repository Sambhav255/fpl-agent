import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import update

from fpl_app.jobs import Queue, Worker
from fpl_app.providers import demo
from fpl_app.storage import Conflict, Store, jobs


def prepared(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    state = demo(store)
    store.put("state", 0, state.model_dump(mode="json"))
    return store, Queue(store), state


def test_duplicate_recovery_fencing_cancel_and_restart(tmp_path):
    store, queue, _ = prepared(tmp_path)
    payload = {"team_id": 0, "horizon_events": 1}
    first = queue.enqueue("projection", payload)
    assert first["id"] == queue.enqueue("projection", payload)["id"]
    assert queue.claim("old")["id"] == first["id"]
    with store.engine.begin() as connection:
        connection.execute(
            update(jobs).where(jobs.c.id == first["id"]).values(lease_until=time.time() - 1)
        )
    reopened = Queue(Store(f"sqlite:///{tmp_path}/app.sqlite"))
    assert reopened.claim("new")["attempts"] == 2
    assert not queue.finish(first["id"], "old", result={})
    assert not queue.heartbeat(first["id"], "old")
    reopened.cancel(first["id"])
    assert not reopened.finish(first["id"], "new", result={})
    assert reopened.get(first["id"])["status"] == "cancelled"
    assert reopened.get(first["id"])["result"] is None


def test_queued_stale_inputs(tmp_path):
    store, queue, state = prepared(tmp_path)
    job = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    state.bank_units = 2
    state.state_version = 2
    store.put("state", 0, state.model_dump(mode="json"), expected=1)
    assert Worker(queue).run_once()
    assert queue.get(job["id"])["error"]["code"] == "STALE_INPUTS"


def test_bounded_recovery(tmp_path):
    store, queue, _ = prepared(tmp_path)
    queue.max_attempts = 1
    job = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    queue.claim("old")
    with store.engine.begin() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(lease_until=0))
    assert queue.claim("new") is None
    assert queue.get(job["id"])["status"] == "failed"


def test_atomic_version_edits(tmp_path):
    store, _, _ = prepared(tmp_path)

    def edit(value):
        try:
            store.put("state", 0, {"value": value}, expected=1)
            return "ok"
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, [1, 2]))
    assert sorted(results) == ["conflict", "ok"]


def test_current_snapshot_stale(tmp_path):
    store, queue, _ = prepared(tmp_path)
    demo(store)
    with pytest.raises(Conflict):
        queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})


def test_cancel_during_compute_never_publishes(tmp_path):
    store, queue, _ = prepared(tmp_path)
    job = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})

    def compute(payload):
        queue.cancel(job["id"])
        return {"projection_run_id": "must-not-publish"}

    Worker(queue, handlers={"projection": compute}).run_once()
    assert queue.get(job["id"])["status"] == "cancelled"
    assert not store.list("projection")


def test_publish_fences_artifacts_in_same_transaction(tmp_path):
    store, queue, _ = prepared(tmp_path)
    queued = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    job = queue.claim("worker")
    queue.cancel(queued["id"])
    assert not queue.publish(job, "worker", {"value": 1}, [("projection", "new", {"value": 1})])
    assert not store.list("projection")


def test_publish_rechecks_stale_inputs(tmp_path):
    store, queue, state = prepared(tmp_path)
    queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    job = queue.claim("worker")
    state.state_version = 2
    store.put("state", 0, state.model_dump(mode="json"), expected=1)
    with pytest.raises(Conflict):
        queue.publish(job, "worker", {"value": 1}, [("projection", "new", {"value": 1})])
    assert not store.list("projection")


def test_heartbeat_extends_lease(tmp_path):
    _, queue, _ = prepared(tmp_path)
    job = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    queue.claim("worker")
    before = queue.get(job["id"])["lease_until"]
    assert queue.heartbeat(job["id"], "worker", 0.4)
    after = queue.get(job["id"])
    assert after["lease_until"] >= before
    assert after["progress"] == 0.4


def test_successful_refresh_can_be_requested_again(tmp_path):
    _, queue, _ = prepared(tmp_path)
    first = queue.enqueue("refresh", {"force": True})
    job = queue.claim("worker")
    assert queue.publish(job, "worker", {"refreshed": True}, [])
    assert queue.enqueue("refresh", {"force": True})["id"] != first["id"]
