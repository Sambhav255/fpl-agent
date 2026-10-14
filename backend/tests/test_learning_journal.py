"""Offline prospective journal and finalized outcome ingestion checks."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from fpl_app.api import create_app
from fpl_app.jobs import Worker
from fpl_app.providers import Provider, demo
from fpl_app.storage import Store

BEFORE_DEADLINE = "2026-10-09T08:00:00+00:00"
DEADLINE = "2026-10-10T10:00:00Z"


def live_bootstrap(players, *, finalized=False):
    return {
        "elements": [
            {
                "id": player["player_id"],
                "web_name": player["name"],
                "team": player["club"],
                "element_type": player["position"],
                "now_cost": player["market_price_units"],
                "points_per_game": "3.0",
                "minutes": 500,
                "goals_scored": 1,
                "assists": 1,
                "clean_sheets": 1,
                "status": "a",
            }
            for player in players
        ],
        "teams": [{"id": club} for club in range(1, 12)],
        "events": [
            {
                "id": 8,
                "deadline_time": DEADLINE,
                "is_current": True,
                "is_next": False,
                "finished": finalized,
                "data_checked": finalized,
            }
        ],
    }


def prepare_live(tmp_path, monkeypatch, *, finalized=False):
    import fpl_app.api as api_module
    import fpl_app.learning.journal as journal_module

    monkeypatch.setattr(api_module, "utcnow", lambda: BEFORE_DEADLINE)
    monkeypatch.setattr(journal_module, "utcnow", lambda: BEFORE_DEADLINE)
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    state = demo(store)
    state.data_mode = "live"
    data = store.get("dataset", state.snapshot_id)
    data.update(
        data_mode="live",
        next_event=8,
        source_cutoff="2026-10-09T00:00:00Z",
        events=[
            {
                "id": 8,
                "deadline_time": DEADLINE,
                "is_current": True,
                "is_next": False,
                "finished": finalized,
                "data_checked": finalized,
            }
        ],
    )
    store.put("dataset", state.snapshot_id, data)
    store.put("current", "live", {"snapshot_id": state.snapshot_id})
    store.put("state", state.team_id, state.model_dump(mode="json"), expected=0)
    fixtures = [
        {
            "id": fixture["fixture_id"],
            "event": 8,
            "team_h": fixture["home_club"],
            "team_a": fixture["away_club"],
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
            "finished": finalized,
        }
        for fixture in data["fixtures"]
        if fixture["event"] == 8
    ]
    return store, state, data, fixtures


def make_recommendation(client):
    prefix = "/api/v1"
    state = client.get(prefix + "/teams/0/state").json()
    queued = client.post(prefix + "/projections/runs", json={"team_id": 0, "horizon_events": 1})
    assert queued.status_code == 202, queued.text
    assert Worker(client.app.state.queue).run_once()
    run = client.get(prefix + "/jobs/" + queued.json()["job_id"]).json()["result"]
    request = {
        "team_id": 0,
        "expected_state_version": state["state_version"],
        "projection_run_id": run["projection_run_id"],
        "settings": {"horizon_events": 1, "solver_time_limit_seconds": 0.2},
    }
    queued = client.post(prefix + "/recommendations", json=request)
    assert queued.status_code == 202, queued.text
    assert Worker(client.app.state.queue).run_once()
    result = client.get(prefix + "/jobs/" + queued.json()["job_id"]).json()
    assert result["status"] == "succeeded", result
    return result["result"]


def test_freeze_is_idempotent_and_execution_paper_are_separate(tmp_path, monkeypatch):
    store, state, _, _ = prepare_live(tmp_path, monkeypatch)
    client = TestClient(create_app(store))
    recommendation = make_recommendation(client)
    body = {
        "recommendation_id": recommendation["recommendation_id"],
        "idempotency_key": "before-deadline-1",
    }
    first = client.post("/api/v1/learning/decisions", json=body)
    assert first.status_code == 201, first.text
    journal = first.json()
    assert journal["execution_status"] == "execution_unknown"
    assert journal["evidence_mode"] == "prospective_shadow"
    assert len(journal["candidate_plans"]) >= 1
    assert journal["forecast_sha256"]
    assert store.get("state", 0) == state.model_dump(mode="json")
    assert client.post("/api/v1/learning/decisions", json=body).json() == journal
    listed = client.get("/api/v1/learning/decisions?team_id=0")
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["decision_id"] == journal["decision_id"]
    assert listed.json()[0]["action_history"] == []
    assert listed.json()[0]["outcome_revisions"] == []

    actions = "/api/v1/learning/decisions/" + journal["decision_id"] + "/actions"
    chosen = journal["recommended_action_id"]
    update = {
        "idempotency_key": "manager-update-1",
        "expected_sequence": 0,
        "execution_status": "user_selected",
        "execution_action_id": chosen,
        "paper_portfolio_action_id": journal["candidate_plans"][-1]["plan_id"],
    }
    selected = client.post(actions, json=update)
    assert selected.status_code == 200, selected.text
    assert selected.json()["execution_status"] == "user_selected"
    assert selected.json()["paper_portfolio_action_id"] == update["paper_portfolio_action_id"]
    assert len(selected.json()["action_history"]) == 1
    assert (
        client.get("/api/v1/learning/decisions?team_id=0").json()[0]["execution_status"]
        == "user_selected"
    )
    assert client.post(actions, json=update).json() == selected.json()
    confirmed = {
        "idempotency_key": "manager-update-2",
        "expected_sequence": 1,
        "execution_status": "confirmed_executed",
        "execution_action_id": chosen,
    }
    assert client.post(actions, json=confirmed).json()["execution_status"] == "confirmed_executed"
    assert (
        client.post(
            actions,
            json={**confirmed, "idempotency_key": "stale-write", "expected_sequence": 1},
        ).status_code
        == 409
    )
    downgrade = {
        "idempotency_key": "downgrade",
        "expected_sequence": 2,
        "execution_status": "execution_unknown",
    }
    assert client.post(actions, json=downgrade).status_code == 409
    assert store.get("state", 0) == state.model_dump(mode="json")


def test_freeze_rejects_late_or_changed_inputs_but_retry_survives_state_change(
    tmp_path, monkeypatch
):
    store, _, _, _ = prepare_live(tmp_path, monkeypatch)
    client = TestClient(create_app(store))
    recommendation = make_recommendation(client)
    body = {"recommendation_id": recommendation["recommendation_id"], "idempotency_key": "freeze-1"}
    captured = client.post("/api/v1/learning/decisions", json=body)
    assert captured.status_code == 201
    import fpl_app.api as api_module
    import fpl_app.learning.journal as journal_module

    monkeypatch.setattr(api_module, "utcnow", lambda: "2026-10-10T10:00:01+00:00")
    monkeypatch.setattr(journal_module, "utcnow", lambda: "2026-10-10T10:00:01+00:00")
    late = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "idempotency_key": "freeze-late",
        },
    )
    assert late.status_code == 422
    monkeypatch.setattr(api_module, "utcnow", lambda: BEFORE_DEADLINE)
    monkeypatch.setattr(journal_module, "utcnow", lambda: BEFORE_DEADLINE)
    state = store.get("state", 0)
    state["state_version"] += 1
    store.put("state", 0, state, expected=1)
    # Same request returns the immutable capture even if later private inputs change.
    assert client.post("/api/v1/learning/decisions", json=body).json() == captured.json()


def test_frozen_journal_is_removed_with_private_team_and_backed_up(tmp_path, monkeypatch):
    store, _, _, _ = prepare_live(tmp_path, monkeypatch)
    client = TestClient(create_app(store))
    recommendation = make_recommendation(client)
    journal = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "idempotency_key": "delete-me",
        },
    ).json()
    assert journal["decision_id"] in [
        row["decision_id"] for row in client.get("/api/v1/backup").json()["learning_decisions"]
    ]
    assert client.delete("/api/v1/teams/0/state").status_code == 200
    assert store.list("decision_journal") == []


def test_finalization_gate_and_exact_official_fixture_join_are_revisioned(tmp_path, monkeypatch):
    store, _, data, fixtures = prepare_live(tmp_path, monkeypatch)
    live_payload = {"elements": []}
    for player in data["players"]:
        scheduled = next(
            fixture
            for fixture in fixtures
            if player["club"] in (fixture["team_h"], fixture["team_a"])
        )
        if player["player_id"] == 1:
            stats, explain = (
                {"total_points": 0, "minutes": 0, "yellow_cards": 0, "red_cards": 0},
                [],
            )
        else:
            stats = {"total_points": 2, "minutes": 90}
            explain = [
                {
                    "fixture": scheduled["id"],
                    "stats": [
                        {"identifier": "minutes", "points": 2, "value": 90},
                    ],
                }
            ]
        live_payload["elements"].append(
            {"id": player["player_id"], "stats": stats, "explain": explain}
        )
    mode = {"finalized": False, "remove_player": False}

    def respond(request):
        if request.url.path.endswith("bootstrap-static/"):
            return httpx.Response(
                200, json=live_bootstrap(data["players"], finalized=mode["finalized"])
            )
        if request.url.path.endswith("fixtures/"):
            fixtures_now = [dict(row, finished=mode["finalized"]) for row in fixtures]
            return httpx.Response(200, json=fixtures_now)
        if request.url.path.endswith("/live/"):
            result = json.loads(json.dumps(live_payload))
            if mode["remove_player"]:
                result["elements"].pop()
            return httpx.Response(200, json=result)
        raise AssertionError(request.url)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    client = TestClient(create_app(store, provider))
    recommendation = make_recommendation(client)
    journal = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "idempotency_key": "score-me",
        },
    ).json()
    pending = client.post(f"/api/v1/learning/decisions/{journal['decision_id']}/outcomes")
    assert pending.status_code == 202 and pending.json()["status"] == "pending"
    assert store.list("learning_scorecard") == []
    mode["finalized"] = True
    queued = client.post(f"/api/v1/learning/decisions/{journal['decision_id']}/outcomes")
    assert queued.status_code == 202 and queued.json()["status"] == "queued"
    worker = Worker(client.app.state.queue, provider=provider)
    assert worker.run_once()
    reviewed = client.get("/api/v1/jobs/" + queued.json()["job_id"]).json()
    assert reviewed["status"] == "succeeded", reviewed
    assert reviewed["result"]["metrics"]["n"] == len(data["players"])
    rows = store.list("learning_outcome")
    assert len(rows) == 1 and rows[0]["outcomes"][0]["status"] in {"final", "final_nonappearance"}
    assert rows[0]["outcomes"][0]["fixtures"][0]["status"] == "final_nonappearance"
    assert rows[0]["outcomes"][0]["points"] == 0
    assert rows[0]["outcomes"][1]["points"] == 2
    before_state = store.get("state", 0)

    # A later official correction creates a second immutable result/scorecard revision.
    live_payload["elements"][1]["stats"]["total_points"] = 3
    live_payload["elements"][1]["explain"][0]["stats"][0]["points"] = 3
    revised = client.post(f"/api/v1/learning/decisions/{journal['decision_id']}/outcomes")
    assert revised.status_code == 202 and revised.json()["job_id"] != queued.json()["job_id"]
    assert worker.run_once()
    second = client.get("/api/v1/jobs/" + revised.json()["job_id"]).json()
    assert second["status"] == "succeeded", second
    assert len(store.list("learning_outcome")) == 2
    assert len(store.list("learning_scorecard")) == 2
    assert store.get("state", 0) == before_state


def test_result_revision_idempotence_and_incomplete_coverage_reject(tmp_path, monkeypatch):
    store, _, data, fixtures = prepare_live(tmp_path, monkeypatch, finalized=True)
    players = data["players"]
    live = {"elements": []}
    for player in players:
        live["elements"].append(
            {
                "id": player["player_id"],
                "stats": {"total_points": 0, "minutes": 0, "yellow_cards": 0, "red_cards": 0},
                "explain": [],
            }
        )

    def respond(request):
        if request.url.path.endswith("bootstrap-static/"):
            return httpx.Response(200, json=live_bootstrap(players, finalized=True))
        if request.url.path.endswith("fixtures/"):
            return httpx.Response(200, json=fixtures)
        return httpx.Response(200, json=live)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    client = TestClient(create_app(store, provider))
    recommendation = make_recommendation(client)
    journal = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "idempotency_key": "missing-player",
        },
    ).json()
    from fpl_app.learning.outcomes import collect_finalized_outcomes, event_status

    status = event_status(provider, 8)
    live["elements"].pop()
    with pytest.raises(ValueError, match="miss forecast-universe"):
        collect_finalized_outcomes(
            store, provider, journal["decision_id"], status["finalization_sha256"]
        )
