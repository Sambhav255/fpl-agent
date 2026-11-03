import math

import pytest

from fpl_app.features.deadline import lag_features, opportunity_features


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


def test_multiscale_opportunity_excludes_current_event_and_late_revisions():
    history = [
        row(
            1,
            "2026-08-01T15:00:00Z",
            "2026-08-02T15:00:00Z",
            minutes=90,
            total_points=-1,
            expected_goals="0.5",
        ),
        row(2, "2026-08-08T15:00:00Z", "2026-08-09T15:00:00Z", minutes=0, total_points=0),
        row(3, "2026-08-15T15:00:00Z", "2026-08-16T15:00:00Z", minutes=90, total_points=99),
        row(1, "2026-08-03T15:00:00Z", "2026-08-20T15:00:00Z", minutes=90, total_points=99),
    ]
    result = opportunity_features(history, "2026-08-17T00:00:00Z", 3)
    assert result["appearance_3"] == 0.5
    assert result["sixty_3"] == 0.5
    assert result["points_10"] == -0.5
    assert 0 < result["minutes_ewm"] < 45
    assert math.isnan(result["xa_10"])


def test_advancing_folds_never_consume_preliminary_gameweek():
    from fpl_app.models.deadline_experiments import advancing_protocol

    collection = {
        "collection_id": "fixture",
        "labels": [{"event": i, "label_status": "final_revision"} for i in range(1, 10)]
        + [{"event": 10, "label_status": "preliminary"}],
    }
    spec = advancing_protocol(collection)
    assert spec["train_events"] == [1, 2, 3, 4, 5]
    assert spec["validation_events"] == [6, 7]
    assert spec["test_events"] == [8, 9]
    assert 10 not in spec["finalized_events"]
    assert not spec["active"]


def test_event_means_include_both_fixtures_of_double_and_negative_points():
    import pandas as pd

    from fpl_app.models.deadline_experiments import event_means

    future = pd.DataFrame({"player_id": [1, 1, 2], "fixture_id": [81, 82, 83]})
    assert event_means(future, [4.0, 3.0, -0.5]) == [
        {"player_id": 1, "expected_points": 7.0},
        {"player_id": 2, "expected_points": -0.5},
    ]
    with pytest.raises(ValueError, match="Finite complete"):
        event_means(future, [4.0, float("nan"), -0.5])


def test_advancing_refit_waits_for_frozen_final_scorecards(monkeypatch):
    from fpl_app.models import deadline_experiments as experiment

    collection = {
        "collection_id": "fixture",
        "envelope_sha256": "a" * 64,
        "labels": [{"event": i, "label_status": "final_revision"} for i in range(1, 10)],
    }
    monkeypatch.setattr(experiment, "load_collection", lambda _store, _id: collection)

    class Retained:
        def list(self, kind):
            return (
                [{"event": 9, "benchmark_id": "unscored"}] if kind == "forecast_benchmark" else []
            )

    with pytest.raises(ValueError, match="before refitting"):
        experiment.training_input(
            Retained(), {"protocol": experiment.advancing_protocol(collection)}
        )
