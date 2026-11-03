import json

import numpy as np
import pandas as pd
import pytest

from fpl_app.models.simple_experiments import fit_preprocessing, fit_ridge, transform


def test_preprocessing_is_fit_on_training_only_and_retains_missingness():
    train = pd.DataFrame({"history_count": [0.0, 2.0, np.nan], "position": ["1", "2", "1"]})
    metadata = fit_preprocessing(train, ["history_count", "position"])
    frozen = json.dumps(metadata, sort_keys=True)
    future = pd.DataFrame({"history_count": [np.nan, 1000.0], "position": ["new", "1"]})
    result = transform(future, metadata)
    assert json.dumps(metadata, sort_keys=True) == frozen
    assert metadata["medians"] == [1.0]
    assert metadata["categories"]["position"] == ["1", "2"]
    assert result[0].tolist() == [0, 1, 0, 0]
    assert np.isfinite(result).all()


def test_ridge_preserves_negative_targets_and_save_reload():
    x = np.array([[-2.0], [-1.0], [0.0], [1.0], [2.0]])
    target = 2 * x[:, 0] - 10
    coefficients = fit_ridge(x, target, 0.1)
    restored = np.asarray(json.loads(json.dumps(coefficients.tolist())))
    predicted = np.column_stack([np.ones(len(x)), x]) @ restored
    assert (predicted < 0).all()
    assert np.abs(predicted - target).max() < 0.05
    assert coefficients[0] == pytest.approx(-10)


def test_missing_lightgbm_does_not_break_module_import():
    # All optional dependency imports live inside fitting; linear and startup stay available.
    import subprocess
    import sys

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import fpl_app.models.simple_experiments; assert 'lightgbm' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr


def test_ridge_checkpoint_is_independent_of_outer_targets_and_detects_corruption(tmp_path):
    from fpl_app.features.football import CATEGORICAL
    from fpl_app.models.simple_experiments import COLUMNS, _fit_unit

    panel = pd.DataFrame(
        {c: ["a"] * 12 if c in CATEGORICAL else np.arange(12, dtype=float) for c in COLUMNS}
    )
    panel["target_points"] = np.arange(12, dtype=float) - 10
    panel["player_id"] = range(12)
    panel["fixture_id"] = range(12)
    fold = {
        "fold_id": "outer-event-5",
        "indices": {"train": list(range(8)), "validation": [8, 9], "test": [10, 11]},
    }
    spec = {"features": COLUMNS, "ridge_alpha": 10}
    first = _fit_unit(tmp_path / "first", "identity", spec, fold, panel, "ridge")
    panel.loc[[10, 11], "target_points"] = [99999, -99999]
    second = _fit_unit(tmp_path / "second", "identity", spec, fold, panel, "ridge")
    np.testing.assert_array_equal(first.predicted_points, second.predicted_points)
    retained = _fit_unit(tmp_path / "first", "identity", spec, fold, panel, "ridge")
    np.testing.assert_array_equal(first.predicted_points, retained.predicted_points)
    (tmp_path / "first/outer-event-5/ridge/ridge.json").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        _fit_unit(tmp_path / "first", "identity", spec, fold, panel, "ridge")
