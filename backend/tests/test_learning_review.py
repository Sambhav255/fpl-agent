import pytest
from fastapi.testclient import TestClient
from test_learning_journal import prepare_live

from fpl_app.api import create_app
from fpl_app.jobs import Queue, Worker
from fpl_app.learning.promotion import assess_promotion
from fpl_app.learning.review import configure_review, enqueue_due_reviews


def test_review_schedule_tick_idempotency_retry_and_disabled_state(tmp_path, monkeypatch):
    store, state, _data, _fixtures = prepare_live(tmp_path, monkeypatch)
    before = store.get("state", state.team_id)
    assert not enqueue_due_reviews(store, "2026-10-12T12:00:00Z")
    configure_review(store, state.team_id, enabled=True)
    first = enqueue_due_reviews(store, "2026-10-12T12:00:00Z")[0]
    again = enqueue_due_reviews(store, "2026-10-12T12:01:00Z")[0]
    assert first["id"] == again["id"]
    worker = Worker(Queue(store))
    assert worker.run_once()
    assert worker.queue.get(first["id"])["status"] == "succeeded"
    assert enqueue_due_reviews(store, "2026-10-12T12:02:00Z")[0]["id"] == first["id"]
    assert len(store.list("learning_review")) == 1
    assert store.list("learning_review")[0]["promotion"] == "retain_champions_insufficient_evidence"
    assert store.get("state", state.team_id) == before
    next_job = enqueue_due_reviews(store, "2026-10-12T18:00:00Z")[0]
    configure_review(store, state.team_id, enabled=False, expected_version=1)
    assert worker.run_once()
    assert worker.queue.get(next_job["id"])["status"] == "failed"
    assert len(store.list("learning_review")) == 1
    assert not enqueue_due_reviews(store, "2026-10-13T00:00:00Z")
    store.delete_team(state.team_id)
    assert (
        store.list("review_schedule")
        == store.list("review_tick")
        == store.list("learning_review")
        == []
    )


def test_review_queue_cancel_publishes_nothing_and_schedule_api_uses_versions(
    tmp_path, monkeypatch
):
    store, state, _data, _fixtures = prepare_live(tmp_path, monkeypatch)
    client = TestClient(create_app(store))
    url = f"/api/v1/teams/{state.team_id}/learning/schedule"
    assert client.get(url).json()["enabled"] is False
    assert client.put(url, json={"enabled": True}).status_code == 200
    assert client.put(url, json={"enabled": False, "expected_version": 0}).status_code == 409
    job = enqueue_due_reviews(store, "2026-10-12T12:00:00Z")[0]
    Queue(store).cancel(job["id"])
    assert enqueue_due_reviews(store, "2026-10-12T12:01:00Z")[0]["id"] == job["id"]
    assert not Worker(Queue(store)).run_once()
    assert not store.list("learning_review")
    with pytest.raises(ValueError, match="Refitting"):
        configure_review(store, state.team_id, train=True, expected_version=1)
    assert client.get("/api/v1/strategy/status").json()["champion"] == "numerical_planner"


def test_promotion_missing_or_synthetic_evidence_keeps_champion():
    report = assess_promotion(
        {"evidence_mode": "synthetic_mechanics", "invalid_accepted_actions": 0}
    )
    assert report["decision"] == "retain_champion"
    assert not report["automatic_activation"]
    assert "Qualified prospective evidence required" in report["reasons"]
    assert "Too few distinct football events" in report["reasons"]


def test_recurring_pending_and_final_outcomes_are_retained_separately(tmp_path, monkeypatch):
    import httpx
    from test_learning_journal import live_bootstrap, make_recommendation

    from fpl_app.providers import Provider

    store, state, data, fixtures = prepare_live(tmp_path, monkeypatch)
    finalized = {"value": False}
    live = {
        "elements": [
            {"id": p["player_id"], "stats": {"minutes": 0, "total_points": 0}, "explain": []}
            for p in data["players"]
        ]
    }

    def respond(request):
        if request.url.path.endswith("bootstrap-static/"):
            return httpx.Response(
                200, json=live_bootstrap(data["players"], finalized=finalized["value"])
            )
        if request.url.path.endswith("fixtures/"):
            return httpx.Response(
                200, json=[dict(f, finished=finalized["value"]) for f in fixtures]
            )
        return httpx.Response(200, json=live)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    client = TestClient(create_app(store, provider))
    rec = make_recommendation(client)
    journal = client.post(
        "/api/v1/learning/decisions",
        json={"recommendation_id": rec["recommendation_id"], "idempotency_key": "review-me"},
    ).json()
    configure_review(store, state.team_id, enabled=True)
    before = store.get("state", state.team_id)
    job = enqueue_due_reviews(store, "2026-10-12T12:00:00Z")[0]
    worker = Worker(Queue(store), provider=provider)
    assert worker.run_once()
    assert worker.queue.get(job["id"])["result"]["decisions"][0]["status"] == "pending_finalization"
    assert not store.list("learning_scorecard")
    finalized["value"] = True
    job = enqueue_due_reviews(store, "2026-10-12T18:00:00Z")[0]
    assert worker.run_once()
    assert worker.queue.get(job["id"])["status"] == "succeeded"
    assert (
        worker.queue.get(job["id"])["result"]["decisions"][0]["decision_id"]
        == journal["decision_id"]
    )
    assert len(store.list("learning_scorecard")) == 1
    assert store.get("state", state.team_id) == before
