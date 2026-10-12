import pytest

from fpl_app.contracts import Settings
from fpl_app.jobs import Queue, Worker
from fpl_app.storage import Store


def payload():
    return {
        "synthetic_smoke": True,
        "timesteps": 64,
        "seeds": 5,
        "settings": Settings(horizon_events=2).model_dump(),
    }


def test_policy_fit_is_durable_idempotent_and_cancellable(tmp_path):
    store = Store(f"sqlite:///{tmp_path / 'jobs.db'}")
    queue = Queue(store)
    first = queue.enqueue("strategy_training", payload())
    assert queue.enqueue("strategy_training", payload())["id"] == first["id"]
    queue.cancel(first["id"])
    assert not Worker(queue).run_once()
    second = queue.enqueue("strategy_training", payload())
    assert second["id"] != first["id"]
    worker = Worker(
        queue,
        handlers={"strategy_training": lambda _: {"active": False, "status": "test_handler_only"}},
    )
    assert worker.run_once()
    assert queue.get(second["id"])["status"] == "succeeded"
    assert queue.enqueue("strategy_training", payload())["id"] == second["id"]
    assert not store.list("state")


def test_policy_queue_rejects_paths_unbounded_configs_and_ambiguous_sources(tmp_path):
    queue = Queue(Store(f"sqlite:///{tmp_path / 'jobs.db'}"))
    for change in [
        {"seeds": 1},
        {"timesteps": True},
        {"output": "/private/file"},
        {"episodes_data": {}},
        {"synthetic_smoke": False},
    ]:
        with pytest.raises(ValueError):
            queue.enqueue("strategy_training", {**payload(), **change})
