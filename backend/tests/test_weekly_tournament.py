import numpy as np
import pandas as pd
import pytest

from fpl_app.evaluation.tournament import auxiliary_metrics, evaluate_panel, score_frozen_rows
from fpl_app.features.football import CATEGORICAL
from fpl_app.models.simple_experiments import COLUMNS
from fpl_app.models.weekly_tournament import METHODS, _unit, protocol


def panel(n=80):
    random = np.random.default_rng(43)
    frame = pd.DataFrame(
        {c: random.normal(size=n) if c not in CATEGORICAL else ["MID"] * n for c in COLUMNS}
    )
    frame["event"] = np.arange(n) // 20 + 1
    frame["player_id"] = np.arange(n)
    frame["fixture_id"] = np.arange(n)
    frame["target_points"] = random.integers(-2, 12, n)
    frame["target_minutes"] = random.choice([0, 15, 90], n)
    frame["history_count"] = 5
    frame["minutes_5"] = 60
    return frame


def test_real_small_fits_reload_resume_and_unconditional_means(tmp_path):
    pytest.importorskip("sklearn")
    pytest.importorskip("lightgbm")
    frame = panel()
    spec = protocol("collection", "test")
    spec.update(iterations=5, trees=5)
    first = _unit(
        tmp_path, "identity", "fold", frame.iloc[:40], frame.iloc[40:60], frame.iloc[60:], spec
    )
    assert all(np.isfinite(first[m]).all() for m in METHODS)
    assert (first.sixty_probability <= first.appearance_probability).all()
    assert (first.expected_minutes <= 90 * first.appearance_probability + 1e-9).all()
    assert (first["q0.1"] <= first["q0.5"]).all()
    second = _unit(
        tmp_path, "identity", "fold", frame.iloc[:40], frame.iloc[40:60], frame.iloc[60:], spec
    )
    pd.testing.assert_frame_equal(first, second)
    future = frame.iloc[60:].drop(columns=["target_points", "target_minutes"])
    live = _unit(tmp_path, "identity", "current", frame, frame.iloc[:0], future, spec)
    assert len(live) == 20
    assert not (live[METHODS].to_numpy() == 0).all()
    assert evaluate_panel(first, METHODS)["distinct_events"] == 1


def test_metrics_known_values_missing_aux_and_top_k_not_policy():
    frame = pd.DataFrame(
        {
            "target_points": [0.0, 10.0],
            "predicted": [2.0, 8.0],
            "target_minutes": [0, 90],
            "expected_minutes": [10, 80],
            "appearance_probability": [0.2, 0.8],
            "sixty_probability": [0.1, 0.7],
            "event": [1, 1],
            "player_id": [1, 2],
            "fixture_id": [1, 1],
            "position": ["MID", "MID"],
            "minutes_5": [80, 80],
            "history_count": [5, 5],
        }
    )
    result = evaluate_panel(frame, ["predicted"])
    assert result["event_point_metrics"]["predicted"]["mae"] == 2
    assert result["fixture_auxiliary_metrics"]["appearance"]["brier"] == pytest.approx(0.04)
    assert result["fixture_auxiliary_metrics"]["minutes_mae"] == 10
    with pytest.raises(ValueError):
        auxiliary_metrics(frame.assign(appearance_probability=2))
    assert score_frozen_rows([], {}) == {"n": 0}
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate_panel(pd.concat([frame, frame]), ["predicted"])


def test_weekly_registration_is_opt_in_and_one_per_event(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    import fpl_app.jobs
    from fpl_app.learning.tournament import enqueue_tournament
    from fpl_app.storage import Store

    store = Store("sqlite:///" + str(tmp_path / "schedule.sqlite"))
    now = datetime.now(UTC)
    collection = {
        "collection_id": "test",
        "season": "2026/27",
        "captured_at": now.isoformat(),
        "event_evidence": [{"event": 10, "actual_deadline": (now + timedelta(days=1)).isoformat()}],
    }
    assert enqueue_tournament(store, collection) is None
    store.put("weekly_tournament_settings", "default", {"enabled": True, "study_id": "fixed"})
    import json

    source = store.archive(
        json.dumps({"events": [{"id": 9, "finished": True, "data_checked": True}]}).encode(),
        "bootstrap-static/",
    )
    collection["sources"] = [{"resource": "bootstrap-static/", "id": source}]
    calls = []

    class FakeQueue:
        def __init__(self, store):
            pass

        def enqueue(self, kind, payload):
            calls.append((kind, payload))
            return {"id": "job", "status": "queued"}

    monkeypatch.setattr(fpl_app.jobs, "Queue", FakeQueue)
    assert enqueue_tournament(store, collection)["status"] == "queued"
    assert enqueue_tournament(store, collection)["job_id"] == "job"
    assert len(calls) == 1
    store.put(
        "forecast_benchmark",
        "frozen",
        {
            "event": 10,
            "season": "2026/27",
            "protocol": {"study_id": "fixed"},
            "benchmark_id": "frozen",
        },
    )
    assert enqueue_tournament(store, collection)["status"] == "already_frozen"
    assert len(calls) == 1


def test_completed_job_recovery_preserves_frozen_publication(tmp_path, monkeypatch):
    import json

    from fpl_app.models import weekly_tournament as tournament
    from fpl_app.models.rolling_experiments import _sha
    from fpl_app.storage import fingerprint

    identity = "a" * 64
    root = tmp_path / "models/weekly_tournament" / identity[:24]
    root.mkdir(parents=True)
    body = {"published_at": "2026-01-01T00:00:00Z", "models": {"test": {"predictions": []}}}
    benchmark = {**body, "benchmark_id": fingerprint(body)}
    report = {"benchmark_id": benchmark["benchmark_id"], "input_fingerprint": identity}
    for name, value in [
        ("report.json", report),
        ("benchmark.json", benchmark),
        ("news_sensitivity.json", {"benchmark_id": "sensitivity"}),
    ]:
        (root / name).write_text(json.dumps(value))
    (root / "complete.json").write_text(
        json.dumps(
            {
                "input_fingerprint": identity,
                "files": {p.name: _sha(p) for p in root.iterdir() if p.is_file()},
            }
        )
    )
    monkeypatch.setattr(tournament, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(tournament, "training_input", lambda *a: identity)
    monkeypatch.setattr(tournament, "load_collection", lambda *a: {})
    monkeypatch.setattr(
        tournament, "_unit", lambda *a: pytest.fail("completed retry must not refit")
    )
    value = tournament.train_job(None, {"protocol": {"collection_id": "test"}})
    assert value["benchmark_id"] == benchmark["benchmark_id"]
    assert len(value["_artifacts"]) == 3
    (root / "benchmark.json").write_text("corrupted")
    with pytest.raises(ValueError, match="checksum"):
        tournament.train_job(None, {"protocol": {"collection_id": "test"}})


def test_partial_universe_is_rejected_before_fitting(monkeypatch):
    import json

    from fpl_app.models import weekly_tournament as tournament

    spec = protocol("partial", "test")

    class FakeStore:
        def get(self, *a):
            return spec

        def snapshot(self, *a):
            return {"raw": json.dumps({"elements": [{"id": 1}, {"id": 2}]}).encode()}

    collection = {"player_ids": [1], "sources": [{"resource": "bootstrap-static/", "id": "source"}]}
    monkeypatch.setattr(tournament, "load_collection", lambda *a: collection)
    with pytest.raises(ValueError, match="full captured bootstrap universe"):
        tournament.training_input(FakeStore(), {"protocol": spec})
