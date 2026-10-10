import json
from pathlib import Path

import pandas as pd
import pytest

from fpl_app.features import build_features, ingest_bundle, utc
from fpl_app.features.pipeline import lagged_summary


def bundle():
    early = "2024-08-01T00:00:00Z"
    cutoff = "2024-08-10T10:00:00Z"

    def provenance(**kwargs):
        return dict(
            season="2024-25",
            available_at=early,
            source_ref="captured",
            timing_verified=True,
            **kwargs,
        )

    return {
        "season": "2024-25",
        "provider": "test",
        "data_mode": "demo",
        "mappings": [
            {
                "season": "2024-25",
                "provider_player_id": i,
                "canonical_player_id": f"person{i}",
                "reviewed": True,
            }
            for i in (1, 2)
        ],
        "team_mappings": [
            {
                "season": "2024-25",
                "provider_team_id": i,
                "canonical_team_id": f"club{i}",
                "reviewed": True,
            }
            for i in (1, 3)
        ],
        "eligibility": [
            provenance(provider_player_id=i, club=1 if i == 1 else 3, position=3, eligible=True)
            for i in (1, 2)
        ],
        "fixture_versions": [
            provenance(fixture_id=i, event=2, home_club=1, away_club=2) for i in (11, 12)
        ],
        "deadlines": [provenance(event=2, deadline=cutoff)],
        "observations": [
            {
                "season": "2024-25",
                "provider_player_id": 1,
                "club": 1,
                "fixture_id": 9,
                "available_at": "2024-08-08T00:00:00Z",
                "completed_at": "2024-08-07T00:00:00Z",
                "source_ref": "past",
                "timing_verified": True,
                "minutes": 90,
                "points": 5,
                "goals": 1,
                "assists": None,
            },
            {
                "season": "2024-25",
                "provider_player_id": 1,
                "club": 1,
                "fixture_id": 11,
                "available_at": "2024-08-11T00:00:00Z",
                "completed_at": "2024-08-10T15:00:00Z",
                "source_ref": "first-double",
                "timing_verified": True,
                "minutes": 90,
                "points": 20,
                "goals": 3,
                "assists": 0,
            },
        ],
    }


def test_double_blank_and_missing_statistics(tmp_path: Path):
    state = bundle()
    result = ingest_bundle(json.dumps(state).encode(), tmp_path)
    frame = build_features(Path(result["directory"]), "2024-08-10T10:00:00Z", 2, "2024-25")
    first = frame[frame.canonical_player_id == "person1"]
    assert len(first) == 2 and first.mean_points_5.tolist() == [5, 5]
    assert first.assists_per90.isna().all() and first.assists_missing.eq(1).all()
    assert first.outcome_state.tolist() == ["appeared", "missing_record"]
    blank = frame[frame.canonical_player_id == "person2"].iloc[0]
    assert blank.outcome_state == "blank" and blank.target_points == 0
    assert blank.history_missing == 1


def test_revised_future_and_unverified_versions_excluded(tmp_path: Path):
    state = bundle()
    revised = dict(state["observations"][0], points=100, available_at="2024-08-12T00:00:00Z")
    unverified = dict(state["observations"][0], fixture_id=8, points=77, timing_verified=False)
    state["observations"] += [revised, unverified]
    state["fixture_versions"].append(
        dict(state["fixture_versions"][0], event=3, available_at="2024-08-12T00:00:00Z")
    )
    result = ingest_bundle(json.dumps(state).encode(), tmp_path)
    frame = build_features(Path(result["directory"]), "2024-08-10T10:00:00Z", 2, "2024-25")
    assert frame[frame.canonical_player_id == "person1"].mean_points_5.tolist() == [5, 5]
    assert "xP" not in frame and "points" not in frame


def test_mapping_duplicates_deadline_and_timezone_reject(tmp_path: Path):
    state = bundle()
    state["mappings"][0]["reviewed"] = False
    with pytest.raises(ValueError, match="mapping"):
        ingest_bundle(json.dumps(state).encode(), tmp_path)
    state = bundle()
    state["observations"].append(state["observations"][0])
    with pytest.raises(ValueError, match="duplicate"):
        ingest_bundle(json.dumps(state).encode(), tmp_path)
    result = ingest_bundle(json.dumps(bundle()).encode(), tmp_path)
    with pytest.raises(ValueError, match="deadline"):
        build_features(Path(result["directory"]), "2024-08-10T09:00:00Z", 2, "2024-25")
    with pytest.raises(ValueError, match="timezone"):
        utc("2024-01-01")


def test_missing_attacks_not_zero():
    summary = lagged_summary([{"minutes": 90, "points": 2, "goals": None, "assists": None}])
    assert pd.isna(summary["goals_per90"]) and summary["goals_missing"] == 1


def test_nan_statistics_stay_missing():
    summary = lagged_summary(
        [
            {"minutes": float("nan"), "points": 2, "goals": 1, "assists": 1},
            {"minutes": 90, "points": 2, "goals": float("nan"), "assists": float("nan")},
        ]
    )
    assert summary["history_count"] == 1
    assert summary["goals_missing"] == 1 and summary["assists_missing"] == 1
    assert pd.isna(summary["goals_per90"]) and pd.isna(summary["assists_per90"])


def test_missing_minutes_are_not_appearances(tmp_path: Path):
    state = bundle()
    state["observations"].append(
        {
            "season": "2024-25",
            "provider_player_id": 1,
            "club": 1,
            "fixture_id": 12,
            "available_at": "2024-08-11T00:00:00Z",
            "completed_at": "2024-08-10T18:00:00Z",
            "source_ref": "missing-stat",
            "timing_verified": True,
            "minutes": None,
            "points": None,
            "goals": None,
            "assists": None,
        }
    )
    result = ingest_bundle(json.dumps(state).encode(), tmp_path)
    frame = build_features(Path(result["directory"]), "2024-08-10T10:00:00Z", 2, "2024-25")
    first = frame[frame.canonical_player_id == "person1"].sort_values("fixture_id")
    assert first.outcome_state.tolist() == ["appeared", "missing_statistic"]
    assert first.assists_missing.eq(1).all()
    assert pd.isna(first.target_minutes.iloc[1])
