import copy

import pytest

from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.storage import Store, fingerprint


def test_shared_guard_requires_matching_forecast_and_current_outcome_revision():
    store = Store("sqlite:///:memory:")
    bundle = {"benchmark_id": "frozen", "event": 9, "season": "2026/27"}
    store.put("forecast_benchmark", "frozen", bundle)
    collection = {
        "season": "2026/27",
        "labels": [
            {
                "event": 9,
                "label_status": "final_revision",
                "available_at": "2026-11-03T10:00:00+00:00",
            }
        ],
    }
    score = {
        "benchmark_id": "frozen",
        "status": "final",
        "forecast_sha256": fingerprint(bundle),
        "source_refs": [{"resource": "event/9/live/", "available_at": "2026-11-03T11:00:00+00:00"}],
    }
    for invalid in [
        None,
        {**score, "status": "pending_finalization"},
        {**score, "forecast_sha256": "wrong"},
        {
            **score,
            "source_refs": [
                {"resource": "event/9/live/", "available_at": "2026-11-03T09:00:00+00:00"}
            ],
        },
    ]:
        if invalid is not None:
            store.put("forecast_benchmark_outcome", "score", invalid)
        with pytest.raises(ValueError, match="before refitting"):
            require_scored_collection(store, collection)
    store.put("forecast_benchmark_outcome", "score", score)
    require_scored_collection(store, collection)
    revised = copy.deepcopy(collection)
    revised["labels"][0]["available_at"] = "2026-11-03T12:00:00+00:00"
    with pytest.raises(ValueError, match="current revision required"):
        require_scored_collection(store, revised)
    score["source_refs"][0]["available_at"] = "2026-11-03T13:00:00+00:00"
    store.put("forecast_benchmark_outcome", "score", score)
    require_scored_collection(store, revised)
    # Other seasons and preliminary labels do not consume this event's labels.
    require_scored_collection(store, {**collection, "season": "2025/26"})
    revised["labels"][0]["label_status"] = "preliminary"
    require_scored_collection(store, revised)


def test_collection_trainer_rejects_unscored_labels_before_building_features(tmp_path, monkeypatch):
    from fpl_app.features import football
    from fpl_app.models.football_catboost import train_collection_experiment

    store = Store("sqlite:///:memory:")
    collection = {
        "collection_id": "c",
        "data_mode": "live",
        "season": "2026/27",
        "player_mappings": [],
        "labels": [{"event": 9, "label_status": "final_revision"}],
    }
    collection["envelope_sha256"] = fingerprint(collection)
    store.put("football_collection", "c", collection)
    store.put("forecast_benchmark", "f", {"benchmark_id": "f", "event": 9, "season": "2026/27"})

    def forbidden(*args):
        pytest.fail("feature construction must not run before shared eligibility guard")

    monkeypatch.setattr(football, "collection_frames", forbidden)
    with pytest.raises(ValueError, match="before refitting"):
        train_collection_experiment(collection, tmp_path, "fpl-2026-27", store=store)
    assert not list(tmp_path.iterdir())


def test_audited_panel_guard_matches_season_and_equivalent_deadline_instants():
    import pandas as pd

    from fpl_app.models.training_eligibility import require_scored_panel

    store = Store("sqlite:///:memory:")
    bundle = {
        "benchmark_id": "f",
        "event": 9,
        "season": "2026/27",
        "deadline": "2026-10-31T11:00:00Z",
    }
    store.put("forecast_benchmark", "f", bundle)
    panel = pd.DataFrame(
        [
            {
                "season": "2026-27",
                "decision_cutoff": "2026-10-31T11:00:00+00:00",
                "target_points": -1,
                "target_available_at": pd.Timestamp("2026-11-03T10:00:00Z"),
            }
        ]
    )
    with pytest.raises(ValueError, match="before refitting"):
        require_scored_panel(store, panel)
    panel["decision_cutoff"] = "2026-10-30T00:00:00Z"
    with pytest.raises(ValueError, match="Explicit event identity"):
        require_scored_panel(store, panel)


def test_scheduled_review_propagates_store_and_blocks_unscored_refit(tmp_path, monkeypatch):
    from fpl_app.features import football
    from fpl_app.learning.review import run_review
    from fpl_app.models import training
    from fpl_app.providers import collection as collections

    store = Store("sqlite:///:memory:")
    collection = {
        "collection_id": "c",
        "data_mode": "live",
        "season": "2026/27",
        "player_mappings": [],
        "sources": [{"resource": "bootstrap-static/", "id": "b"}],
        "labels": [
            {
                "event": 9,
                "label_status": "final_revision",
                "provider_player_id": 1,
                "fixture_id": 1,
                "revision_sha256": "r",
            }
        ],
    }
    collection["envelope_sha256"] = fingerprint(collection)
    store.put("football_collection", "c", collection)
    store.put("forecast_benchmark", "f", {"benchmark_id": "f", "event": 9, "season": "2026/27"})
    store.put(
        "review_tick",
        "tick",
        {
            "team_id": 1,
            "scheduled_for": "2026-11-03T00:00:00Z",
            "decision_sha256": {},
            "config": {"collect": True, "train": True, "include_all": False},
        },
    )
    monkeypatch.setattr(collections, "collect_football", lambda *a, **kw: collection)
    monkeypatch.setattr(store, "snapshot", lambda _: {"raw": b"{}"})
    monkeypatch.setattr(training, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        football, "collection_frames", lambda *a: pytest.fail("unscored labels reached features")
    )
    report = run_review(store, None, "tick")
    assert report["challenger"]["status"] == "unavailable_or_insufficient_data"
    assert report["challenger"]["exception_type"] == "ValueError"
    assert not list(tmp_path.iterdir())
