import copy
import json
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from fpl_app.models import rolling_experiments as rolling
from fpl_app.storage import Store, fingerprint


def panel(events=8, players=8):
    rows = []
    for event in range(1, events + 1):
        origin = pd.Timestamp("2026-08-01T00:00:00Z") + timedelta(days=7 * event)
        for player in range(1, players + 1):
            rows.append(
                {
                    "event": event,
                    "player_id": player,
                    "fixture_id": event * 100 + player,
                    "decision_cutoff": origin.isoformat(),
                    "target_available_at": (origin + timedelta(days=1)).isoformat(),
                    "actual_label_available_at": "2026-10-30T00:00:00Z",
                    "target_points": [0, -2, 1, 5][player % 4],
                    "position": "MID",
                    "points_5": float(player % 4),
                    "minutes_5": 80.0,
                    "app_baseline_reconstructed": 2.0,
                }
            )
    return pd.DataFrame(rows)


def collection(frame):
    return {
        "collection_id": "collection",
        "envelope_sha256": "collection-sha",
        "captured_at": "2026-11-01T00:00:00Z",
        "sources": [{"resource": "fixtures/", "id": "fixtures"}],
        "labels": [
            {
                "event": int(row.event),
                "provider_player_id": int(row.player_id),
                "fixture_id": int(row.fixture_id),
                "available_at": row.actual_label_available_at,
                "label_status": "final_revision",
            }
            for row in frame.itertuples()
        ],
    }


def test_expanding_distinct_outer_events_and_actual_capture_gate():
    frame = panel()
    folds = rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")
    assert [f["test_events"] for f in folds] == [[5], [6], [7], [8]]
    assert [f["train_events"] for f in folds] == [list(range(1, n)) for n in range(4, 8)]
    for fold in folds:
        assert pd.Timestamp(fold["train_target_end"]) < pd.Timestamp(fold["validation_origin"])
        assert pd.Timestamp(fold["validation_target_end"]) < pd.Timestamp(fold["test_origin"])
        assert len(fold["validation_events"]) == len(fold["test_events"]) == 1
    frame.loc[frame.event == 8, "actual_label_available_at"] = "2026-11-02T00:00:00Z"
    assert [
        f["test_events"] for f in rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")
    ] == [[5], [6], [7]]


def test_purge_uses_strict_inner_and_outer_boundaries():
    frame = panel()
    validation_origin = frame.loc[frame.event == 4, "decision_cutoff"].iloc[0]
    outer_origin = frame.loc[frame.event == 5, "decision_cutoff"].iloc[0]
    bad_train = frame.index[(frame.event == 3) & (frame.player_id == 1)][0]
    bad_validation = frame.index[(frame.event == 4) & (frame.player_id == 1)][0]
    frame.loc[bad_train, "target_available_at"] = validation_origin
    frame.loc[bad_validation, "target_available_at"] = outer_origin
    fold = rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")[0]
    assert bad_train not in fold["indices"]["train"]
    assert bad_validation not in fold["indices"]["validation"]
    assert fold["purged_rows"] == {"train": 1, "validation": 1, "test": 0}
    frame.loc[frame.event == 3, "target_available_at"] = validation_origin
    assert rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")[0]["test_events"] == [6]


def test_late_outer_labels_and_missing_timestamps_are_not_filled():
    frame = panel()
    frame.loc[frame.event == 8, "target_available_at"] = "2026-11-02T00:00:00Z"
    assert rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")[-1]["test_events"] == [7]
    frame.loc[0, "target_available_at"] = None
    with pytest.raises(ValueError, match="timezone aware"):
        rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")


def test_double_rows_share_origin_and_are_aggregated_as_points():
    frame = panel(events=5, players=2)
    extra = frame.iloc[[-1]].copy()
    extra.fixture_id += 1
    frame = pd.concat([frame, extra], ignore_index=True)
    assert (
        len(rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")[0]["indices"]["test"]) == 3
    )
    frame["model"] = frame.target_points
    metrics = rolling._metrics(frame[frame.event == 5], ["model"])
    assert metrics["player_fixture"]["model"]["n"] == 3
    assert metrics["player_event"]["model"]["n"] == 2
    extra.decision_cutoff = "2026-09-06T00:00:00Z"
    with pytest.raises(ValueError, match="share one deadline"):
        rolling.chronological_folds(pd.concat([frame, extra]), "2026-11-01T00:00:00Z")


def test_protocol_registration_binds_fixed_configs_collection_and_code(monkeypatch):
    store = Store("sqlite:///:memory:")
    captured = collection(panel())
    monkeypatch.setattr(rolling, "load_collection", lambda *_: captured)
    spec = rolling.protocol(captured)
    with pytest.raises(KeyError):
        rolling.training_input(store, {"protocol": spec})
    store.put("rolling_experiment_protocol", fingerprint(spec), spec, expected=0)
    identity = rolling.training_input(store, {"protocol": spec})
    assert [c["name"] for c in spec["configurations"]] == [
        "full_second_seed",
        "opportunity_multiscale",
        "points_hurdle",
    ]
    assert spec["thread_count"] == 2 and not spec["serving_refit"]
    changed = copy.deepcopy(spec)
    changed["iterations"] = 9
    with pytest.raises(ValueError, match="Unknown rolling"):
        rolling.training_input(store, {"protocol": changed})
    captured["envelope_sha256"] = "new-content"
    assert identity != rolling.training_input(store, {"protocol": spec})
    captured["envelope_sha256"] = "collection-sha"
    monkeypatch.setattr(rolling, "_sha", lambda _: "changed-code")
    assert identity != rolling.training_input(store, {"protocol": spec})


def test_retained_prospective_forecasts_must_be_scored_before_label_reuse(monkeypatch):
    store = Store("sqlite:///:memory:")
    captured = collection(panel())
    monkeypatch.setattr(rolling, "load_collection", lambda *_: captured)
    spec = rolling.protocol(captured)
    store.put("rolling_experiment_protocol", fingerprint(spec), spec, expected=0)
    store.put("forecast_benchmark", "frozen", {"benchmark_id": "frozen", "event": 8})
    with pytest.raises(ValueError, match="Score finalized frozen benchmarks"):
        rolling.training_input(store, {"protocol": spec})
    store.put(
        "forecast_benchmark_outcome",
        "frozen",
        {"benchmark_id": "frozen", "status": "pending_finalization"},
    )
    with pytest.raises(ValueError, match="Score finalized frozen benchmarks"):
        rolling.training_input(store, {"protocol": spec})
    store.put(
        "forecast_benchmark_outcome",
        "frozen",
        {
            "benchmark_id": "frozen",
            "status": "final",
            "forecast_sha256": fingerprint(store.get("forecast_benchmark", "frozen")),
            "source_refs": [{"resource": "event/8/live/", "available_at": captured["captured_at"]}],
        },
    )
    assert rolling.training_input(store, {"protocol": spec})
    # A still-preliminary event is not consumed and does not block historical folds.
    store.put("forecast_benchmark", "future", {"benchmark_id": "future", "event": 9})
    assert rolling.training_input(store, {"protocol": spec})


@pytest.mark.parametrize("method", [None, "points_hurdle"])
def test_real_fit_outer_targets_do_not_influence_training_and_resume_is_checked(
    tmp_path, monkeypatch, method
):
    frame = panel(events=5, players=12)
    fold = rolling.chronological_folds(frame, "2026-11-01T00:00:00Z")[0]
    config = {"name": "tiny", "features": ["points_5"], "depth": 2, "l2_leaf_reg": 10, "seed": 43}
    if method:
        config["method"] = method
    spec = {"learning_rate": 0.04, "thread_count": 2, "iterations": 8, "early_stopping_rounds": 3}
    first = rolling._fit_unit(tmp_path / "a", "input", fold, config, spec, frame)
    altered = frame.copy()
    altered.loc[altered.event == 5, "target_points"] += 1000
    second = rolling._fit_unit(tmp_path / "b", "input", fold, config, spec, altered)
    np.testing.assert_array_equal(first.predicted_points, second.predicted_points)
    import catboost

    monkeypatch.setattr(
        catboost.CatBoostRegressor,
        "fit",
        lambda *a, **k: pytest.fail("Completed unit was refitted"),
    )
    resumed = rolling._fit_unit(tmp_path / "a", "input", fold, config, spec, frame)
    np.testing.assert_array_equal(first.predicted_points, resumed.predicted_points)
    with pytest.raises(ValueError, match="input fingerprint"):
        rolling._fit_unit(tmp_path / "a", "different-input", fold, config, spec, frame)
    predictions = tmp_path / "a" / fold["fold_id"] / "tiny/predictions.parquet"
    predictions.write_bytes(predictions.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        rolling._fit_unit(tmp_path / "a", "input", fold, config, spec, frame)


def test_job_retains_temporal_oof_and_rejects_changed_reconstructed_inputs(tmp_path, monkeypatch):
    frame = panel()
    captured = collection(frame)
    store = Store("sqlite:///:memory:")
    monkeypatch.setattr(rolling, "load_collection", lambda *_: captured)
    monkeypatch.setattr(
        rolling, "enriched_panels", lambda *_: (frame.copy(), pd.DataFrame(), pd.DataFrame())
    )
    monkeypatch.setattr(store, "snapshot", lambda _: {"raw": b"[]"})
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    spec = rolling.protocol(captured)
    store.put("rolling_experiment_protocol", fingerprint(spec), spec, expected=0)
    calls = []

    def fit_unit(root, identity, fold, config, spec, panel):
        calls.append((fold["fold_id"], config["name"]))
        result = panel.loc[fold["indices"]["test"]].copy()
        result["predicted_points"] = 1.0
        result["selected_iterations"] = "3"
        return result

    monkeypatch.setattr(rolling, "_fit_unit", fit_unit)
    result = rolling.train_job(store, {"protocol": spec})
    assert len(calls) == 12
    assert result["outer_events"] == [5, 6, 7, 8]
    assert result["_artifacts"][0][0] == "rolling_experiment"
    root = rolling.Path(result["directory"])
    oof = pd.read_parquet(root / "oof_predictions.parquet")
    assert set(oof.model) == set(result["comparators"])
    assert set(oof.historical_timing) == {rolling.TIMING}
    assert oof.actual_label_available_at.notna().all()
    assert all(json.loads(v)[0] < event for v, event in zip(oof.validation_events, oof.event))
    assert (
        pd.to_datetime(oof.validation_target_end, utc=True)
        < pd.to_datetime(oof.test_origin, utc=True)
    ).all()
    before = json.loads((root / "report.json").read_text())
    assert rolling.train_job(store, {"protocol": spec})["files"] == before["files"]
    frame.loc[0, "points_5"] = 987.0
    with pytest.raises(ValueError, match="Immutable artifact differs: inputs.json"):
        rolling.train_job(store, {"protocol": spec})
