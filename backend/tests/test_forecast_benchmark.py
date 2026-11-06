import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from fpl_app.jobs import Queue, Worker
from fpl_app.learning.forecast_benchmark import (
    checked_benchmark,
    enqueue_due_benchmarks,
    make_benchmark,
    score_benchmark,
)
from fpl_app.storage import Store, fingerprint


def fixture(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "benchmark.sqlite"))
    now = datetime.now(UTC)
    deadline = (now + timedelta(hours=2)).isoformat()
    bootstrap = {
        "events": [{"id": 9, "deadline_time": deadline, "finished": False, "data_checked": False}],
        "elements": [{"id": 1, "team": 1}, {"id": 2, "team": 2}],
    }
    fixtures = [
        {
            "id": 81,
            "event": 9,
            "team_h": 1,
            "team_a": 2,
            "started": False,
            "kickoff_time": (now + timedelta(hours=3)).isoformat(),
        }
    ]
    bootstrap_id = store.archive(json.dumps(bootstrap).encode(), "bootstrap-static/")
    fixtures_id = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    models = {
        "reference": {
            "published_at": datetime.now(UTC).isoformat(),
            "predictions": [
                {"player_id": 1, "expected_points": 4.0},
                {"player_id": 2, "expected_points": -0.5},
            ],
        }
    }
    frozen = make_benchmark(
        store,
        bootstrap_id,
        fixtures_id,
        9,
        models,
        produced_at=datetime.now(UTC).isoformat(),
        protocol={"test": "authored mechanics"},
    )
    store.put("forecast_benchmark", frozen["benchmark_id"], frozen)
    return store, frozen, bootstrap, fixtures


class RetainedProvider:
    def __init__(self, store, bootstrap, fixtures, *, finalized=False, missing=False):
        self.store, self.bootstrap, self.fixtures = store, copy.deepcopy(bootstrap), fixtures
        self.bootstrap["events"][0].update(finished=finalized, data_checked=finalized)
        self.missing = missing

    def fetch(self, resource, force=False):
        if resource == "bootstrap-static/":
            value = self.bootstrap
        elif resource == "fixtures/":
            value = self.fixtures
        else:
            value = {
                "elements": [{"id": 1, "stats": {"total_points": 6, "minutes": 90}}]
                + ([] if self.missing else [{"id": 2, "stats": {"total_points": 0, "minutes": 0}}])
            }
        return self.store.snapshot(self.store.archive(json.dumps(value).encode(), resource))


def test_preliminary_event_does_not_score_or_rewrite_predictions(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    before = fingerprint(frozen)
    result = score_benchmark(
        store, RetainedProvider(store, bootstrap, fixtures), frozen["benchmark_id"]
    )
    assert result["status"] == "pending_finalization"
    assert "metrics" not in result
    assert fingerprint(checked_benchmark(store, frozen["benchmark_id"])) == before


def test_final_score_uses_official_zero_and_preserves_negative_forecast(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    result = score_benchmark(
        store, RetainedProvider(store, bootstrap, fixtures, finalized=True), frozen["benchmark_id"]
    )
    assert result["status"] == "final"
    assert result["metrics"]["reference"]["n"] == 2
    assert result["metrics"]["reference"]["mae"] == 1.25
    assert result["metrics"]["reference"]["bias"] == -1.25


def test_missing_outcome_is_not_zero_and_fixture_changes_are_excluded(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    result = score_benchmark(
        store,
        RetainedProvider(store, bootstrap, fixtures, finalized=True, missing=True),
        frozen["benchmark_id"],
    )
    assert result["status"] == "incomplete_outcome_coverage"
    assert result["metrics"]["reference"]["n"] == 1
    assert result["metrics"]["reference"]["coverage"]["missing_outcome"] == 1
    altered = [{**fixtures[0], "event": 10}]
    result = score_benchmark(
        store, RetainedProvider(store, bootstrap, altered, finalized=True), frozen["benchmark_id"]
    )
    assert result["metrics"]["reference"]["n"] == 0
    assert result["metrics"]["reference"]["coverage"]["schedule_changed"] == 2


def test_mutation_and_late_publication_are_rejected(tmp_path):
    store, frozen, _bootstrap, _fixtures = fixture(tmp_path)
    changed = copy.deepcopy(frozen)
    changed["models"]["reference"]["predictions"][0]["expected_points"] = 99
    store.put("forecast_benchmark", frozen["benchmark_id"], changed)
    with pytest.raises(ValueError, match="changed"):
        checked_benchmark(store, frozen["benchmark_id"])
    with pytest.raises(ValueError, match="before its deadline"):
        make_benchmark(
            store,
            frozen["sources"][0]["id"],
            frozen["sources"][1]["id"],
            9,
            frozen["models"],
            produced_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
            protocol={},
        )


def test_due_scoring_is_durable_idempotent_and_rechecks_later_revisions(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    assert not enqueue_due_benchmarks(store)
    due = frozen["check_after"]
    first = enqueue_due_benchmarks(store, due)[0]
    assert enqueue_due_benchmarks(store, due)[0]["id"] == first["id"]
    worker = Worker(
        Queue(store), provider=RetainedProvider(store, bootstrap, fixtures, finalized=True)
    )
    assert worker.run_once()
    assert worker.queue.get(first["id"])["status"] == "succeeded"
    assert len(store.list("forecast_benchmark_outcome")) == 1
    assert enqueue_due_benchmarks(store, due)[0]["id"] == first["id"]
    later = (datetime.fromisoformat(due) + timedelta(hours=6)).isoformat()
    assert enqueue_due_benchmarks(store, later)[0]["id"] != first["id"]


def test_team_goals_and_different_model_universes_are_compared_explicitly(tmp_path):
    store, first, bootstrap, fixtures = fixture(tmp_path)
    models = copy.deepcopy(first["models"])
    models["subset"] = {
        "published_at": datetime.now(UTC).isoformat(),
        "predictions": [{"player_id": 1, "expected_points": 5.0}],
    }
    frozen = make_benchmark(
        store,
        first["sources"][0]["id"],
        first["sources"][1]["id"],
        9,
        models,
        produced_at=datetime.now(UTC).isoformat(),
        protocol={},
        team_predictions={
            "goals": [{"fixture_id": 81, "home_mean_goals": 1.5, "away_mean_goals": 0.5}]
        },
    )
    store.put("forecast_benchmark", frozen["benchmark_id"], frozen)
    fixtures[0].update(team_h_score=2, team_a_score=0)
    result = score_benchmark(
        store, RetainedProvider(store, bootstrap, fixtures, finalized=True), frozen["benchmark_id"]
    )
    assert result["metrics"]["reference"]["n"] == 2
    assert result["metrics"]["reference"]["common_n"] == 1
    assert result["metrics"]["reference"]["common_mae"] == 2
    assert result["team_goal_metrics"]["goals"]["rmse"] == 0.5


def test_frozen_auxiliary_scores_only_final_observed_rows(tmp_path):
    store, old, bootstrap, fixtures = fixture(tmp_path)
    models = copy.deepcopy(old["models"])
    for row in models["reference"]["predictions"]:
        row.update(
            expected_minutes=45.0,
            appearance_probability=0.5,
            sixty_probability=0.4,
            position=3,
            **{"q0.1": -1.0, "q0.5": 2.0, "q0.9": 8.0},
        )
    frozen = make_benchmark(
        store,
        old["sources"][0]["id"],
        old["sources"][1]["id"],
        9,
        models,
        produced_at=datetime.now(UTC).isoformat(),
        protocol={"new_auxiliary": True},
    )
    store.put("forecast_benchmark", frozen["benchmark_id"], frozen)
    result = score_benchmark(
        store,
        RetainedProvider(store, bootstrap, fixtures, finalized=True, missing=True),
        frozen["benchmark_id"],
    )
    aux = result["metrics"]["reference"]["diagnostics"]["auxiliary"]
    assert aux["appearance"]["n"] == 1
    assert aux["appearance"]["brier"] == 0.25
    assert aux["minutes_mae"] == 45
    assert result["metrics"]["reference"]["coverage"]["missing_outcome"] == 1
    models["reference"]["predictions"][0]["appearance_probability"] = 2
    with pytest.raises(ValueError, match="probabilities"):
        make_benchmark(
            store,
            old["sources"][0]["id"],
            old["sources"][1]["id"],
            9,
            models,
            produced_at=datetime.now(UTC).isoformat(),
            protocol={},
        )


def test_official_zero_sensitivity_preserves_parent_and_doubtful_signed_means(tmp_path):
    from fpl_app.models.news_sensitivity import freeze_news_sensitivity

    store, old, bootstrap, _fixtures = fixture(tmp_path)
    bootstrap["elements"][0].update(status="s", chance_of_playing_next_round=0)
    bootstrap["elements"][1].update(status="d", chance_of_playing_next_round=75)
    source = store.archive(json.dumps(bootstrap).encode(), "bootstrap-static/")
    parent = make_benchmark(
        store,
        source,
        old["sources"][1]["id"],
        9,
        old["models"],
        produced_at=datetime.now(UTC).isoformat(),
        protocol={"study_id": "test"},
    )
    store.put("forecast_benchmark", parent["benchmark_id"], parent)
    before = fingerprint(parent)
    scenario = freeze_news_sensitivity(store, parent["benchmark_id"])
    values = scenario["models"]["reference"]["predictions"]
    assert values[0]["expected_points"] == 0
    assert values[1]["expected_points"] == -0.5
    assert fingerprint(checked_benchmark(store, parent["benchmark_id"])) == before
    store.put("forecast_benchmark", scenario["benchmark_id"], scenario)
    assert freeze_news_sensitivity(store, parent["benchmark_id"]) == scenario
