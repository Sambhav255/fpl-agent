from pathlib import Path

import pandas as pd
import pytest

from fpl_app.features.football import FEATURES, frozen_features
from fpl_app.models.football_catboost import forecast_frozen, train_experiment


def test_origin_rejects_future_and_same_event_double():
    history = pd.DataFrame(
        [
            {
                "player_key": "fpl:2024-25:1",
                "fixture_id": 1,
                "event": 1,
                "kickoff": pd.Timestamp("2024-08-01T00:00Z"),
                "available_at": pd.Timestamp("2024-08-08T00:00Z"),
                "points": 4,
                "minutes": 90,
                "starts": 1,
            },
            {
                "player_key": "fpl:2024-25:1",
                "fixture_id": 2,
                "event": 2,
                "kickoff": pd.Timestamp("2024-08-10T00:00Z"),
                "available_at": pd.Timestamp("2024-08-17T00:00Z"),
                "points": 99,
                "minutes": 90,
                "starts": 1,
            },
            {
                "player_key": "fpl:2024-25:1",
                "fixture_id": 3,
                "event": 3,
                "kickoff": pd.Timestamp("2024-08-09T00:00Z"),
                "available_at": pd.Timestamp("2024-08-10T00:00Z"),
                "points": 99,
                "minutes": 90,
                "starts": 1,
            },
        ]
    )
    exposure = {
        "player_key": "fpl:2024-25:1",
        "event": 3,
        "fixture_id": 4,
        "position": "MID",
        "club": "1",
        "opponent": "2",
        "home": "True",
        "rule_era": "fpl-2024-25",
    }
    row = frozen_features(history, exposure, pd.Timestamp("2024-08-11T00:00Z"))
    assert row["points_5"] == 4
    assert row["history_count"] == 1
    assert not any("xP" in col or col.startswith("target") for col in FEATURES)
    exposure["player_key"] = "unknown"
    assert (
        frozen_features(history, exposure, pd.Timestamp("2024-08-11T00:00Z"))["history_missing"]
        == 1
    )


def test_pin_mismatch_fails_before_fitting(tmp_path: Path):
    csv = tmp_path / "merged_gw.csv"
    csv.write_text("wrong")
    (tmp_path / "source.json").write_text('{"git_commit":"pinned", "sha256":"bad"}')
    with pytest.raises(ValueError, match="pinned"):
        train_experiment(csv, tmp_path / "out", "pinned")


def test_artifact_origin_fails_before_features(tmp_path: Path):
    (tmp_path / "manifest.json").write_text('{"artifact_available_at":"2026-10-10T00:00:00Z"}')
    with pytest.raises(ValueError, match="did not exist"):
        forecast_frozen(tmp_path, pd.DataFrame(), pd.DataFrame(), "2024-08-01T00:00Z")


@pytest.fixture
def fitted(tmp_path: Path) -> Path:
    from fpl_app.features.football import CATEGORICAL, FEATURE_VERSION, NUMERIC
    from fpl_app.models.football_catboost import _fit

    rows = []
    for event in range(1, 6):
        for player in range(1, 5):
            row = {key: "same" for key in CATEGORICAL}
            row.update({key: float(player) for key in NUMERIC})
            row.update(
                rule_era="fpl-2026-27",
                player_key=f"official_fpl:2026/27:element:{player}",
                player_id=player,
                fixture_id=event,
                event=event,
                target_points=float(player + event),
                target_minutes=float(30 * (player % 4)),
                target_start=float(player > 2),
                decision_cutoff=f"2026-08-{event * 5:02d}T00:00:00+00:00",
                target_available_at=f"2026-08-{event * 5 + 1:02d}T00:00:00+00:00",
                feature_version=FEATURE_VERSION,
            )
            rows.append(row)
    return _fit(
        pd.DataFrame(rows),
        tmp_path,
        {"season": "2026/27", "source_ref": "synthetic-test-only"},
        {"train": [1, 2], "validation": [3], "calibration": [4], "test": [5]},
        "fpl-2026-27",
    )


def test_reload_future_mapping_era_and_checksum(fitted: Path):
    from fpl_app.features.football import FEATURE_VERSION

    frame = pd.read_parquet(fitted / "features.parquet").iloc[:4].copy()
    origin = "2030-01-01T00:00:00+00:00"
    frame["decision_cutoff"] = origin
    frame["source_available_at"] = "2026-10-10T00:00:00+00:00"
    frame["source_ref"] = "synthetic-frozen"
    frame["feature_version"] = FEATURE_VERSION
    mappings = (
        frame[["player_id", "player_key"]]
        .rename(columns={"player_id": "current_player_id"})
        .assign(season="2026/27", source_ref="explicit-test")
    )
    a = forecast_frozen(fitted, frame, mappings, origin)
    b = forecast_frozen(fitted, frame, mappings, origin)
    pd.testing.assert_frame_equal(a, b)
    assert (a.sixty_probability <= a.appearance_probability).all()
    assert (a.q10 <= a.points_median).all()
    assert (a.points_median <= a.q90).all()
    with pytest.raises(ValueError, match="unmapped"):
        forecast_frozen(fitted, frame, mappings.iloc[:1], origin)
    wrong = frame.copy()
    wrong["rule_era"] = "fpl-2024-25"
    with pytest.raises(ValueError, match="scoring era"):
        forecast_frozen(fitted, wrong, mappings, origin)
    wrong = frame.copy()
    wrong["source_available_at"] = "2031-01-01T00:00Z"
    with pytest.raises(ValueError, match="future"):
        forecast_frozen(fitted, wrong, mappings, origin)
    with (fitted / "points.cbm").open("ab") as out:
        out.write(b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        forecast_frozen(fitted, frame, mappings, origin)
