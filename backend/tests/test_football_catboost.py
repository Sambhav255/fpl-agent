from pathlib import Path

import pandas as pd
import pytest

from fpl_app.features.football import FEATURES, frozen_features
from fpl_app.models.football_catboost import (
    chronological_folds,
    forecast_frozen,
    train_experiment,
)


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


def test_expanding_folds_grow_only_when_new_labels_are_available():
    rows = []
    for event in range(1, 8):
        cutoff = pd.Timestamp("2026-08-01T00:00:00Z") + pd.Timedelta(7 * event, unit="D")
        rows.append(
            {
                "event": event,
                "decision_cutoff": cutoff.isoformat(),
                "target_available_at": (cutoff + pd.Timedelta(1, unit="D")).isoformat(),
            }
        )
    panel = pd.DataFrame(rows)
    before_event_7 = chronological_folds(panel, "2026-09-19T12:00:00Z")
    assert [fold["test"] for fold in before_event_7] == [[5], [6]]
    panel.loc[panel.event == 7, "target_available_at"] = "2026-09-19T00:00:00Z"
    after_event_7 = chronological_folds(panel, "2026-09-19T12:00:00Z")
    assert [fold["test"] for fold in after_event_7] == [[5], [6], [7]]
    assert after_event_7[-1] == {
        "train": [1, 2, 3, 4],
        "validation": [5],
        "calibration": [6],
        "test": [7],
    }
    naive = panel.copy()
    naive["target_available_at"] = naive.target_available_at.str.replace("+00:00", "")
    with pytest.raises(ValueError, match="timezone aware"):
        chronological_folds(naive, "2026-09-30T00:00:00Z")
    with pytest.raises(ValueError, match="timezone aware"):
        chronological_folds(panel, "2026-09-30")


def test_chronological_evaluation_excludes_labels_unavailable_at_cutoff(tmp_path, monkeypatch):
    import fpl_app.models.football_catboost as model_module

    rows = []
    for event in range(1, 8):
        cutoff = pd.Timestamp("2026-08-01T00:00:00Z") + pd.Timedelta(7 * event, unit="D")
        for player in range(2):
            available = cutoff + pd.Timedelta(1, unit="D")
            if (event, player) in {(5, 1), (7, 0)}:
                available = pd.Timestamp("2026-09-20T00:00:00Z")
            rows.append(
                {
                    "event": event,
                    "player_id": player + 1,
                    "fixture_id": event * 10 + player,
                    "decision_cutoff": cutoff.isoformat(),
                    "target_available_at": available.isoformat(),
                    "target_points": float(event + player),
                    "target_minutes": 90.0,
                    "points_5": float(event),
                    "minutes_mean": 90.0,
                    "appearance_probability": 1.0,
                    "sixty_probability": 1.0,
                }
            )

    def fake_fit(panel, output_root, provenance, partitions, rules, **kwargs):
        artifact = output_root / f"fold-{partitions['test'][0]}"
        artifact.mkdir()
        result = panel[panel.event.isin(partitions["test"])].copy()
        result["points_mean"] = result.points_5
        for name in [
            "points_position",
            "points_minutes_role",
            "points_minutes_role_fixture",
        ]:
            result[f"ablation_{name}"] = result.points_5
        result["population_train_mean"] = float(
            panel[panel.event.isin(partitions["train"])].target_points.mean()
        )
        result.to_parquet(artifact / "test_predictions.parquet", index=False)
        return artifact

    monkeypatch.setattr(model_module, "_fit", fake_fit)
    _, report = model_module.evaluate_chronological(
        pd.DataFrame(rows),
        tmp_path,
        {"source_ref": "offline-test"},
        "test-rules",
        "2026-09-19T12:00:00Z",
    )
    assert report["held_out_events"] == [5, 6]
    assert report["held_out_rows"] == 3  # late event-5 label and event 7 are excluded
    assert report["folds"][0]["rows"] == 1
    assert [row["name"] for row in report["feature_ablation_sequence"]] == [
        "points_position",
        "points_minutes_role",
        "points_minutes_role_fixture",
    ]


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
