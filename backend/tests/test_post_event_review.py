import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from fpl_app.learning.forecast_benchmark import make_benchmark
from fpl_app.learning.post_event import registered_reviews, review_forecasts
from fpl_app.storage import Store, fingerprint


def captured_review(monkeypatch, tmp_path, *, final=False, missing=False):
    now = datetime.now(UTC)
    old = now - timedelta(days=3)
    monkeypatch.setattr("fpl_app.storage.utcnow", lambda: old.isoformat())
    store = Store("sqlite:///" + str(tmp_path / "review.sqlite"))
    b = {
        "events": [{"id": 9, "deadline_time": (old + timedelta(hours=2)).isoformat()}],
        "elements": [
            {"id": 1, "team": 1, "element_type": 4},
            {"id": 2, "team": 2, "element_type": 1},
        ],
    }
    fixtures = [
        {
            "id": 81,
            "event": 9,
            "team_h": 1,
            "team_a": 2,
            "started": False,
            "kickoff_time": (old + timedelta(hours=3)).isoformat(),
        }
    ]
    b_id = store.archive(json.dumps(b).encode(), "bootstrap-static/")
    f_id = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    models = {
        "reference": {
            "published_at": old.isoformat(),
            "predictions": [
                {"player_id": 1, "expected_points": 4.0},
                {"player_id": 2, "expected_points": -0.5},
            ],
        },
        "subset": {
            "published_at": old.isoformat(),
            "predictions": [{"player_id": 1, "expected_points": 5.0}],
        },
    }
    frozen = make_benchmark(
        store,
        b_id,
        f_id,
        9,
        models,
        produced_at=(old + timedelta(minutes=1)).isoformat(),
        protocol={},
    )
    store.put("forecast_benchmark", frozen["benchmark_id"], frozen)
    monkeypatch.setattr("fpl_app.storage.utcnow", lambda: now.isoformat())
    b["events"][0].update(finished=final, data_checked=final)
    fixtures[0].update(finished=final, finished_provisional=True, team_h_score=2, team_a_score=0)
    outcomes = [
        {"id": 1, "stats": {"total_points": 6, "minutes": 90}},
        {"id": 2, "stats": {"total_points": 0, "minutes": 0}},
    ]
    if missing:
        outcomes = outcomes[1:]
    sources = [
        store.archive(json.dumps(value).encode(), resource)
        for value, resource in (
            (b, "bootstrap-static/"),
            (fixtures, "fixtures/"),
            ({"elements": outcomes}, "event/9/live/"),
        )
    ]
    return store, frozen, sources


def test_provisional_diagnostics_use_common_coverage_without_publishing_labels(
    monkeypatch, tmp_path
):
    store, frozen, sources = captured_review(monkeypatch, tmp_path)
    before = fingerprint(frozen)
    report = review_forecasts(store, [frozen["benchmark_id"]], *sources)
    assert report["status"] == "provisional"
    assert report["training_eligible"] is False
    assert report["comparisons"]["reference"]["full_coverage"]["mae"] == 1.25
    assert report["comparisons"]["reference"]["groups"]["all_common_players"]["mae"] == 2
    assert report["comparisons"]["subset"]["groups"]["all_common_players"]["mae"] == 1
    assert not store.list("forecast_benchmark_outcome")
    assert fingerprint(store.get("forecast_benchmark", frozen["benchmark_id"])) == before


def test_missing_outcomes_stay_missing_and_empty_metrics_stay_unavailable(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path, missing=True)
    report = review_forecasts(store, [frozen["benchmark_id"]], *sources)
    assert report["common_player_ids"] == []
    assert report["comparisons"]["subset"]["missing_or_invalid_ids"] == [1]
    assert report["comparisons"]["subset"]["full_coverage"]["rmse"] is None


def test_final_status_requires_both_official_gate_and_completed_fixtures(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path, final=True)
    assert review_forecasts(store, [frozen["benchmark_id"]], *sources)["status"] == "final"
    fixtures = json.loads(store.snapshot(sources[1])["raw"])
    fixtures[0]["finished"] = False
    sources[1] = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    assert review_forecasts(store, [frozen["benchmark_id"]], *sources)["status"] == "provisional"


def test_wrong_resource_and_schedule_changes_rejected(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="resource"):
        review_forecasts(store, [frozen["benchmark_id"]], sources[1], sources[0], sources[2])
    fixtures = json.loads(store.snapshot(sources[1])["raw"])
    fixtures[0]["team_h"] = 3
    sources[1] = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    with pytest.raises(ValueError, match="Schedule changed"):
        review_forecasts(store, [frozen["benchmark_id"]], *sources)


def test_late_analysis_plan_is_never_described_as_predeclared(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path)
    plan = {
        "event": 9,
        "registered_at": datetime.now(UTC).isoformat(),
        "benchmark_ids": [frozen["benchmark_id"]],
        "subgroups": {"chosen_after_outcome": [1]},
    }
    report = review_forecasts(
        store, [frozen["benchmark_id"]], *sources, analysis_plan=copy.deepcopy(plan)
    )
    assert not report["subgroups_predeclared"]


def test_registered_diagnostics_wait_for_final_score_and_publish_all_models(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path, final=True)
    plan = {
        "event": 9,
        "registered_at": frozen["published_at"],
        "benchmark_ids": [frozen["benchmark_id"]],
        "subgroups": {"forwards": [1]},
    }
    digest = fingerprint(plan)
    store.put("forecast_analysis_plan", digest, {"plan": plan, "plan_sha256": digest})
    scorecard = {"status": "pending_finalization"}
    assert registered_reviews(store, scorecard) == []
    scorecard = {
        "status": "final",
        "benchmark_id": frozen["benchmark_id"],
        "source_refs": [{"resource": store.snapshot(i)["resource"], "id": i} for i in sources],
    }
    artifacts = registered_reviews(store, scorecard)
    assert len(artifacts) == 1
    kind, identifier, report = artifacts[0]
    assert kind == "forecast_event_review"
    assert identifier == report["revision"]
    assert report["status"] == "final"
    assert set(report["comparisons"]) == {"reference", "subset"}
    assert not report["training_eligible"]


def test_actual_worker_publishes_scorecard_and_registered_review_together(monkeypatch, tmp_path):
    from fpl_app.jobs import Queue, Worker

    store, frozen, sources = captured_review(monkeypatch, tmp_path, final=True)
    plan = {
        "event": 9,
        "registered_at": frozen["published_at"],
        "benchmark_ids": [frozen["benchmark_id"]],
        "subgroups": {"forwards": [1]},
    }
    digest = fingerprint(plan)
    store.put("forecast_analysis_plan", digest, {"plan": plan, "plan_sha256": digest})
    source_by_resource = {store.snapshot(i)["resource"]: store.snapshot(i) for i in sources}

    class RetainedProvider:
        def fetch(self, resource, force=False):
            return source_by_resource[resource]

    queue = Queue(store)
    job = queue.enqueue(
        "forecast_benchmark_score", {"benchmark_id": frozen["benchmark_id"], "check_slot": 1}
    )
    assert Worker(queue, provider=RetainedProvider()).run_once()
    assert queue.get(job["id"])["status"] == "succeeded"
    assert len(store.list("forecast_benchmark_outcome")) == 1
    assert len(store.list("forecast_event_review")) == 1
    assert store.list("forecast_event_review")[0]["status"] == "final"


def test_finalized_event_with_missing_outcomes_is_not_complete(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path, final=True, missing=True)
    report = review_forecasts(store, [frozen["benchmark_id"]], *sources)
    assert report["status"] == "incomplete_outcome_coverage"
