import pytest
from fastapi.testclient import TestClient

from fpl_app.api import create_app
from fpl_app.jobs import Queue, Worker
from fpl_app.storage import Store


def test_collection_recoverable_without_manager_and_repeat_capture(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    queue = Queue(store)
    payload = {"player_ids": [1], "force": True}
    first = queue.enqueue("collection", payload)
    assert queue.enqueue("collection", payload)["id"] == first["id"]
    worker = Worker(queue, handlers={"collection": lambda p: {"collection_id": "immutable"}})
    assert worker.run_once()
    assert queue.get(first["id"])["status"] == "succeeded"
    assert queue.enqueue("collection", payload)["id"] != first["id"]
    assert store.list("state") == []


@pytest.mark.parametrize("ids", [[0], [-1], [True], ["1"], list(range(1, 1002))])
def test_invalid_collection_ids_rejected(tmp_path, ids):
    with pytest.raises(ValueError, match="player universe"):
        Queue(Store(f"sqlite:///{tmp_path}/app.sqlite")).enqueue("collection", {"player_ids": ids})


def test_social_status_honest_and_collection_api(tmp_path):
    client = TestClient(create_app(Store(f"sqlite:///{tmp_path}/app.sqlite")))
    status = client.get("/api/v1/social/status").json()
    assert status["points_adjustment"] == 0
    assert status["accuracy_benchmark"] is None
    assert all(not p["live_fetch"] for p in status["providers"])
    response = client.post("/api/v1/data/collections", json={"player_ids": [1]})
    assert response.status_code == 202
    assert client.post("/api/v1/data/collections", json={"include_all": True}).status_code == 202
    assert (
        client.post(
            "/api/v1/data/collections", json={"include_all": True, "player_ids": [1]}
        ).status_code
        == 422
    )
    assert client.post("/api/v1/data/collections", json={"player_ids": [-1]}).status_code == 422


def test_rollover_does_not_reconfirm_unchanged_private_values(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    client = TestClient(create_app(store))
    state = client.post("/api/v1/demo").json()
    state["next_event"] += 1
    request = {"expected_version": state["state_version"], "state": state}
    rejected = client.patch("/api/v1/teams/0/state", json=request)
    assert rejected.status_code == 422
    assert "new-gameweek review" in rejected.json()["message"]
    assert store.get("state", 0)["next_event"] != state["next_event"]
    request["confirm_event_rollover"] = True
    assert client.patch("/api/v1/teams/0/state", json=request).status_code == 200
