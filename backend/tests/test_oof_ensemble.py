import numpy as np
import pandas as pd
import pytest

from fpl_app.models.oof_ensemble import blend_walk_forward


def panel():
    rows = []
    for event in [5, 6, 7]:
        for player in range(4):
            rows.append(
                {
                    "event": event,
                    "player_id": player,
                    "fixture_id": event,
                    "decision_cutoff": f"2026-01-{event * 3:02d}T12:00:00Z",
                    "target_available_at": f"2026-01-{event * 3 + 1:02d}T12:00:00Z",
                    "train_target_end": "2026-01-01T12:00:00Z",
                    "target_points": float(player - 1),
                    "first": float(player),
                    "second": float(player - 2),
                }
            )
    return pd.DataFrame(rows)


def test_current_and_future_outer_labels_cannot_fit_their_own_weights():
    original = panel()
    first, first_weights = blend_walk_forward(original, ["first", "second"])
    changed = original.copy()
    changed.loc[changed.event == 7, "target_points"] += 10000
    second, second_weights = blend_walk_forward(changed, ["first", "second"])
    assert first_weights == second_weights
    np.testing.assert_array_equal(first.ensemble, second.ensemble)
    changed.loc[changed.event == 6, "target_points"] -= 10000
    third, third_weights = blend_walk_forward(changed, ["first", "second"])
    assert first_weights[0] == third_weights[0]
    np.testing.assert_array_equal(
        first.loc[first.event == 6, "ensemble"], third.loc[third.event == 6, "ensemble"]
    )
    assert first_weights[0]["development_events"] == [5]
    assert first_weights[1]["development_events"] == [5, 6]
    assert set(first.event) == {6, 7}  # Warmup is never counted as held-out blend evidence.
    for record in first_weights:
        assert sum(record["weights"].values()) == pytest.approx(1)
        assert min(record["weights"].values()) >= 0


def test_delayed_earlier_labels_are_excluded_and_bad_base_training_rejected():
    rows = panel()
    rows.loc[(rows.event == 5) & (rows.player_id == 0), "target_available_at"] = (
        "2026-02-01T12:00:00Z"
    )
    _, weights = blend_walk_forward(rows, ["first", "second"])
    assert weights[0]["development_rows"] == 3
    assert weights[1]["development_rows"] == 7
    rows.loc[rows.event == 6, "train_target_end"] = "2026-02-01T12:00:00Z"
    with pytest.raises(ValueError, match="overlaps"):
        blend_walk_forward(rows, ["first", "second"])


def test_missing_coverage_and_duplicate_predictions_are_rejected():
    rows = panel()
    rows.loc[0, "first"] = np.nan
    with pytest.raises(ValueError, match="Finite complete"):
        blend_walk_forward(rows, ["first", "second"])
    with pytest.raises(ValueError, match="unique"):
        blend_walk_forward(pd.concat([panel(), panel().iloc[:1]]), ["first", "second"])
