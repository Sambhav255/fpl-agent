import numpy as np
import pandas as pd
import pytest

from fpl_app.models.points_hurdle import fit_hurdle, predict_hurdle


def test_hurdle_retains_negative_zero_minute_disciplinary_outcomes(tmp_path):
    # Zero minutes does not guarantee zero FPL points: disciplinary outcomes count.
    frame = pd.DataFrame(
        {
            "form": np.arange(60, dtype=float),
            "target_points": np.tile([0, -2], 30),
            "target_minutes": 0,
        }
    )
    selected = fit_hurdle(
        frame.iloc[:40],
        frame.iloc[40:],
        ["form"],
        [],
        {"verbose": False, "allow_writing_files": False, "thread_count": 1, "random_seed": 43},
        10,
        3,
        tmp_path / "selection",
    )
    fit_hurdle(
        frame,
        None,
        ["form"],
        [],
        {"verbose": False, "allow_writing_files": False, "thread_count": 1, "random_seed": 43},
        selected,
        3,
        tmp_path / "current",
    )
    prediction = predict_hurdle(tmp_path / "current", frame, ["form"])
    assert np.isfinite(prediction).all()
    assert (prediction < 0).all()
    assert (prediction > -2).all()
    np.testing.assert_array_equal(prediction, predict_hurdle(tmp_path / "current", frame, ["form"]))


def test_hurdle_refuses_unidentifiable_gate(tmp_path):
    frame = pd.DataFrame({"form": [0.0, 1.0], "target_points": [0, 0]})
    with pytest.raises(ValueError, match="both zero and nonzero"):
        fit_hurdle(frame, None, ["form"], [], {}, 10, 3, tmp_path)
