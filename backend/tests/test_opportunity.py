"""Opportunity invariants, typed dispatch and deliberate missing-label behavior."""

import numpy as np
import pandas as pd
import pytest

from fpl_app.features.football import CATEGORICAL, FEATURES, NUMERIC
from fpl_app.models.football_catboost import _predict
from fpl_app.models.opportunity import (
    ConstantProbability,
    calibrate,
    fit_head,
    fit_sigmoid,
    load_head,
    probability,
)


def features(n=32):
    frame = pd.DataFrame({key: ["same"] * n for key in CATEGORICAL})
    for key in NUMERIC:
        frame[key] = np.arange(n) % 4
    return frame


def test_probability_uses_positive_class_not_class_prediction():
    class ReversedClassifier:
        classes_ = np.array([1, 0])

        def predict_proba(self, frame):
            return np.tile([0.2, 0.8], (len(frame), 1))

        def predict(self, frame):
            raise AssertionError("class prediction must not be used")

    assert probability(ReversedClassifier(), features(2)).tolist() == [0.2, 0.2]


def test_actual_binary_head_reload_missing_and_one_class(tmp_path):
    frame = features()
    frame["start"] = [0.0, 1.0, np.nan, 1.0] * 8
    model, metadata = fit_head("start", frame, "start")
    assert metadata["kind"] == "classifier"
    assert metadata["missing_labels"] == 8
    model.save_model(str(tmp_path / "start.cbm"))
    loaded = load_head(tmp_path / "start.cbm", metadata)
    np.testing.assert_array_equal(
        probability(model, frame[FEATURES]), probability(loaded, frame[FEATURES])
    )
    with pytest.raises(ValueError, match="mapping"):
        load_head(tmp_path / "start.cbm", {**metadata, "class_mapping": [1, 0]})
    frame["start"] = 0.0
    model, metadata = fit_head("start", frame, "start")
    assert metadata["reason"] == "one class training fold"
    assert 0 < model.probability < 1
    assert load_head(tmp_path / "not-needed.cbm", metadata).probability == model.probability
    frame["start"] = np.nan
    model, metadata = fit_head("start", frame, "start")
    assert model is None and metadata["kind"] == "unavailable"


def test_coherent_minutes_preserves_signed_unconditional_points_and_missing_starts():
    models = {
        name: ConstantProbability(value)
        for name, value in {
            "appearance": 0.1,
            "sixty": 0.8,
            "minutes": 90.0,
            "points": -1.0,
            "q10": -4.0,
            "q50": -1.0,
            "q90": 7.0,
        }.items()
    }
    result = _predict(models, {}, features(2))
    assert result.start_probability.isna().all()
    assert result.points_mean.tolist() == [-1.0, -1.0]
    assert (result.sixty_probability <= result.appearance_probability).all()
    assert (result.minutes_mean <= 90 * result.appearance_probability).all()
    assert (
        result.minutes_mean >= result.appearance_probability + 59 * result.sixty_probability
    ).all()
    assert (result.minutes_projection_delta < 0).all()
    models["start"] = ConstantProbability(0.01)
    result = _predict(models, {}, features(2))
    assert (result.sixty_probability > result.start_probability).all()
    legacy = _predict(models, {}, features(2), coherent=False)
    assert legacy.minutes_mean.tolist() == [90.0, 90.0]
    # Each fixture can independently reach 90; a double's mean is allowed above 90.
    models.update(appearance=ConstantProbability(1.0), sixty=ConstantProbability(1.0))
    assert _predict(models, {}, features(2)).minutes_mean.sum() == 180


def test_sigmoid_records_model_binding_and_does_not_claim_sparse_calibration():
    y = pd.Series([0.0, 1.0] * 20)
    raw = np.tile([0.3, 0.7], 20)
    fitted = fit_sigmoid(
        raw, y, model_sha256="model-a", origin_min="2026-08-01", feature_version="test-v1"
    )
    assert fitted["kind"] == "sigmoid"
    assert fitted["sample_size"] == 40
    assert fitted["positive_count"] == 20
    assert fitted["model_sha256"] == "model-a"
    result = calibrate(raw, fitted)
    assert ((0 <= result) & (result <= 1)).all()
    missing = fit_sigmoid(raw[:4], y.iloc[:4])
    assert missing["kind"] == "unavailable"
    np.testing.assert_array_equal(calibrate(raw[:4], missing), raw[:4])


def test_outer_targets_cannot_fit_heads_or_calibration(tmp_path):
    import json

    from fpl_app.models.football_catboost import _fit

    parts = []
    for event in range(1, 6):
        frame = features()
        frame["event"] = event
        frame["target_points"] = np.arange(32) % 7 - 1.0
        frame["target_minutes"] = np.tile([0.0, 30.0, 60.0, 90.0], 8)
        frame["target_start"] = np.tile([0.0, 0.0, 1.0, np.nan], 8)
        frame["decision_cutoff"] = f"2026-08-{event * 5:02d}T00:00:00Z"
        frame["target_available_at"] = f"2026-08-{event * 5 + 1:02d}T00:00:00Z"
        frame["player_id"] = np.arange(32)
        frame["player_key"] = "synthetic"
        parts.append(frame)
    panel = pd.concat(parts, ignore_index=True)
    partitions = {"train": [1, 2], "validation": [3], "calibration": [4], "test": [5]}
    original = _fit(
        panel, tmp_path, {"season": "test", "source_ref": "synthetic"}, partitions, "test"
    )
    changed = panel.copy()
    changed.loc[changed.event == 5, ["target_minutes", "target_points", "target_start"]] = 0.0
    other = _fit(
        changed, tmp_path, {"season": "test", "source_ref": "synthetic"}, partitions, "test"
    )
    first = pd.read_parquet(original / "test_predictions.parquet")
    second = pd.read_parquet(other / "test_predictions.parquet")
    for col in [
        "points_mean",
        "minutes_mean",
        "appearance_probability",
        "sixty_probability",
        "start_probability",
    ]:
        np.testing.assert_array_equal(first[col], second[col])
    a = json.loads((original / "calibration.json").read_text())
    b = json.loads((other / "calibration.json").read_text())
    for head in ["appearance", "sixty", "start"]:
        assert a[head]["kind"] == "sigmoid"
        assert a[head]["slope"] == b[head]["slope"]
        assert a[head]["intercept"] == b[head]["intercept"]
        assert a[head]["label_available_through"] < first.decision_cutoff.min()
