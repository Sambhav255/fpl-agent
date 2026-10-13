from pathlib import Path

import pandas as pd
import pytest

from fpl_app.models.football_experiment import (
    REGISTERED_ABLATIONS,
    build_archive_multilead,
    experiment_contract,
    partition_panel,
)


def archive(path: Path) -> pd.DataFrame:
    rows = []
    for event in range(1, 39):
        for player, club, opponent, home in [(1, "A", 2, True), (2, "B", 1, False)]:
            rows.append(
                {
                    "GW": event,
                    "element": player,
                    "fixture": event,
                    "kickoff_time": (
                        pd.Timestamp("2024-08-01T12:00Z") + pd.Timedelta(7 * event, "d")
                    ).isoformat(),
                    "team": club,
                    "position": "MID",
                    "minutes": 90,
                    "total_points": player + event % 3,
                    "opponent_team": opponent,
                    "was_home": home,
                    "team_h_score": 1,
                    "team_a_score": 0,
                    "starts": 1,
                    "goals_scored": int(home),
                    "assists": 0,
                    "clean_sheets": int(home),
                    "expected_goals": 0.1,
                    "expected_assists": 0.2,
                    "saves": 0,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(path, index=False)
    return result


def test_multilead_never_reveals_later_observed_statistics(tmp_path):
    path = tmp_path / "source.csv"
    raw = archive(path)
    before = build_archive_multilead(path, 3)
    raw.loc[raw.GW >= 10, ["total_points", "minutes", "expected_goals", "starts"]] = 99
    raw.to_csv(path, index=False)
    after = build_archive_multilead(path, 3)
    columns = sorted(
        {column for columns in REGISTERED_ABLATIONS.values() for column in columns}
        | {"app_baseline_reconstructed", "history_available_max"}
    )
    # Lead three at origin10 targets12, but every covariate remains frozen10.
    first = before[before.origin_event == 10]
    second = after[after.origin_event == 10]
    pd.testing.assert_frame_equal(first[columns], second[columns])
    assert set(first.lead) == {1, 2, 3}
    assert (
        pd.to_datetime(first.history_available_max) <= pd.to_datetime(first.decision_cutoff)
    ).all()
    assert not any(c.startswith("target") or "xP" in c for c in columns)


def test_partition_purge_uses_actual_origin_not_target_event(tmp_path):
    path = tmp_path / "source.csv"
    archive(path)
    panel = build_archive_multilead(path, 8)
    frames = partition_panel(panel)
    for earlier, later in [
        ("train", "validation"),
        ("validation", "calibration"),
        ("calibration", "test"),
    ]:
        assert (
            pd.to_datetime(frames[earlier].target_available_at).max()
            < pd.to_datetime(frames[later].decision_cutoff).min()
        )
    assert set(frames["test"].lead) == set(range(1, 9))
    assert experiment_contract()["hyperparameter_search"] is False
    assert experiment_contract()["selected_method"] == "role_permitted_advanced"


def test_missing_outcome_and_duplicate_are_not_zeros(tmp_path):
    path = tmp_path / "source.csv"
    raw = archive(path)
    raw.loc[0, "total_points"] = None
    raw.to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing outcomes"):
        build_archive_multilead(path)
    raw = archive(path)
    pd.concat([raw, raw.iloc[:1]]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        build_archive_multilead(path)
