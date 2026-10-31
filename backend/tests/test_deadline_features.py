import math

import pytest

from fpl_app.features.deadline import lag_features


def row(event, kickoff, available, **stats):
    return {"event": event, "kickoff": kickoff, "available_at": available, "stats": stats}


def test_lags_exclude_current_fixture_and_late_statistics():
    history = [
        row(
            1,
            "2026-08-01T15:00:00Z",
            "2026-08-02T15:00:00Z",
            minutes=90,
            starts=1,
            expected_goals="0.5",
            expected_assists="0.1",
            defensive_contribution=12,
        ),
        row(
            2,
            "2026-08-08T15:00:00Z",
            "2026-08-20T00:00:00Z",
            minutes=90,
            starts=1,
            expected_goals="99",
        ),
        row(
            3,
            "2026-08-15T15:00:00Z",
            "2026-08-15T16:00:00Z",
            minutes=90,
            starts=1,
            expected_goals="100",
        ),
    ]
    features = lag_features(history, "2026-08-16T00:00:00Z", 3)
    assert features["xg_5"] == 0.5
    assert features["defcon_5"] == 12
    assert features["xg_missing"] == 0
    assert features["xg90_shrunk"] < 0.5


def test_missing_statistics_stay_missing_instead_of_becoming_zero():
    features = lag_features(
        [row(1, "2026-08-01T15:00:00Z", "2026-08-02T15:00:00Z", minutes=None)],
        "2026-08-03T00:00:00Z",
        2,
    )
    assert math.isnan(features["xg_5"])
    assert math.isnan(features["minutes_last"])
    assert features["xg_missing"] == 1


def test_experiment_registration_rejects_test_targets_in_validation(monkeypatch):
    from fpl_app.models import deadline_experiments as experiment

    monkeypatch.setattr(
        experiment, "load_collection", lambda _store, _id: {"envelope_sha256": "a" * 64}
    )
    spec = experiment.protocol("fixture-collection")
    assert experiment.training_input(None, {"protocol": spec})
    spec["validation_events"] = [5, 6, 7]
    with pytest.raises(ValueError, match="protocol"):
        experiment.training_input(None, {"protocol": spec})
