import numpy as np
import pandas as pd
import pytest

from fpl_app.evaluation import chronological_folds, fit_ensemble, forecast_metrics
from fpl_app.evaluation.metrics import block_difference


def test_chronological_fold_purges_overlapping_and_not_known_targets():
    frame = pd.DataFrame(
        {
            "decision_cutoff": [f"2024-01-{i:02d}T10:00:00Z" for i in range(1, 9)],
            "target_available_at": [f"2024-01-{i:02d}T11:00:00Z" for i in range(2, 10)],
        }
    )
    for train, val in chronological_folds(frame, 3, 2):
        assert max(pd.to_datetime(frame.loc[train, "target_available_at"], utc=True)) < min(
            pd.to_datetime(frame.loc[val, "decision_cutoff"], utc=True)
        )
        assert not set(train) & set(val)


def test_mean_metrics_negative_points_and_quantiles():
    metrics = forecast_metrics(
        [-2, 4],
        [-1, 3],
        probabilities=[0.1, 0.8],
        appearance=[0, 1],
        quantiles={0.1: [-3, 1], 0.5: [-1, 3], 0.9: [1, 5]},
    )
    assert metrics["mae"] == 1 and metrics["rmse"] == 1
    assert metrics["interval_coverage"] == 1
    with pytest.raises(ValueError, match="crossing"):
        forecast_metrics([1], [1], quantiles={0.1: [3], 0.9: [2]})


def test_ensemble_never_test_or_overlapping_training_and_can_zero_weight():
    frame = pd.DataFrame(
        {
            "partition": ["validation"] * 4,
            "decision_cutoff": ["2024-01-10T00:00:00Z"] * 4,
            "train_target_end": ["2024-01-05T00:00:00Z"] * 4,
            "target_points": [1, 2, 3, 4],
            "good": [1, 2, 3, 4],
            "bad": [10, 10, 10, 10],
        }
    )
    blend = fit_ensemble(frame, ["good", "bad"])
    assert blend["weights"]["bad"] < 1e-5 and sum(blend["weights"].values()) == pytest.approx(1)
    frame["partition"] = "test"
    with pytest.raises(ValueError, match="validation-only"):
        fit_ensemble(frame, ["good", "bad"])
    frame["partition"] = "validation"
    frame["train_target_end"] = frame["decision_cutoff"]
    with pytest.raises(ValueError, match="overlaps"):
        fit_ensemble(frame, ["good", "bad"])


def test_bootstrap_uses_event_blocks():
    result = block_difference([1, 2, 3, 4], [2, 3, 4, 5], [1, 2, 3, 4], [1, 1, 2, 2], draws=50)
    assert result["event_blocks"] == 2 and result["mean_mae_difference"] == 1
    assert np.isfinite(result["bootstrap_p975"])
