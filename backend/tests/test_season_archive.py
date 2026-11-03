import json

import pandas as pd
import pytest

from fpl_app.features.season_archive import ingest_season, league_table_prefix


def sources(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    pd.DataFrame(
        [
            {
                "element": 1,
                "fixture": 1,
                "GW": 1,
                "minutes": 90,
                "total_points": 8,
                "kickoff_time": "2024-08-01T12:00:00Z",
                "was_home": True,
                "position": "MID",
            },
            {
                "element": 1,
                "fixture": 2,
                "GW": 2,
                "minutes": 0,
                "total_points": -1,
                "kickoff_time": "2024-08-15T12:00:00Z",
                "was_home": True,
                "position": "MID",
            },
            {
                "element": 2,
                "fixture": 1,
                "GW": 1,
                "minutes": 0,
                "total_points": 0,
                "kickoff_time": "2024-08-01T12:00:00Z",
                "was_home": False,
                "position": "DEF",
            },
        ]
    ).to_csv(source / "gws_merged_gw.csv", index=False)
    pd.DataFrame(
        [
            {
                "id": 1,
                "team_h": 1,
                "team_a": 2,
                "team_h_score": 2,
                "team_a_score": 0,
                "finished": True,
                "kickoff_time": "2024-08-01T12:00:00Z",
            },
            {
                "id": 2,
                "team_h": 2,
                "team_a": 1,
                "team_h_score": 0,
                "team_a_score": 5,
                "finished": True,
                "kickoff_time": "2024-08-15T12:00:00Z",
            },
        ]
    ).to_csv(source / "fixtures.csv", index=False)
    pd.DataFrame(
        [
            {"id": 1, "code": 11, "name": "A", "position": 2},
            {"id": 2, "code": 22, "name": "B", "position": 1},
        ]
    ).to_csv(source / "teams.csv", index=False)
    # Player 2 left the final roster, but must survive the historical panel.
    pd.DataFrame([{"id": 1, "code": 100, "team": 1}]).to_csv(
        source / "players_raw.csv", index=False
    )
    return source


def run(source, output):
    return ingest_season(
        source,
        output,
        season="2024-25",
        revision="a" * 40,
        retrieved_at="2026-11-03T00:00:00+00:00",
    )


def test_normalization_preserves_departed_players_signed_outcomes_and_missingness(tmp_path):
    dest = run(sources(tmp_path), tmp_path / "output")
    frame = pd.read_parquet(dest / "player_fixture_outcome.parquet")
    quality = json.loads((dest / "quality.json").read_text())
    assert len(frame) == 3
    assert frame.loc[frame.minutes == 0, "total_points"].tolist() == [-1, 0]
    assert frame.defensive_contribution.isna().all()
    assert quality["players_absent_from_final_metadata"] == 1
    memberships = json.loads((dest / "player_club_interval.json").read_text())
    assert len([r for r in memberships if r["player_identity"].endswith(":1")]) == 2
    assert "xP" not in frame


def test_prefix_is_unchanged_by_later_scores_final_table_and_current_membership(tmp_path):
    source = sources(tmp_path)
    first = run(source, tmp_path / "first")
    f = pd.read_csv(source / "fixtures.csv")
    f.loc[f.id == 2, "team_h_score"] = 99
    f.to_csv(source / "fixtures.csv", index=False)
    p = pd.read_csv(source / "players_raw.csv")
    p["team"] = 2
    p.to_csv(source / "players_raw.csv", index=False)
    teams = pd.read_csv(source / "teams.csv")
    teams["position"] = [1, 2]
    teams.to_csv(source / "teams.csv", index=False)
    second = run(source, tmp_path / "second")
    a = pd.read_parquet(first / "league_table_snapshot.parquet")
    b = pd.read_parquet(second / "league_table_snapshot.parquet")
    pd.testing.assert_frame_equal(a, b)
    earlier = pd.read_parquet(first / "player_fixture_outcome.parquet")
    later = pd.read_parquet(second / "player_fixture_outcome.parquet")
    pd.testing.assert_frame_equal(earlier, later)
    assert a.loc[(a.event == 2) & (a.club_id == 1), "points"].item() == 3


def test_delayed_results_not_visible_and_retry_verifies_artifacts(tmp_path):
    source = sources(tmp_path)
    dest = run(source, tmp_path / "output")
    frame = pd.read_parquet(dest / "fixture_revision.parquet")
    assert league_table_prefix(frame, "2024-08-05T12:00:00Z", [1, 2]).played.sum() == 0
    assert league_table_prefix(frame, "2024-08-08T12:00:00Z", [1, 2]).played.sum() == 2
    before = (dest / "manifest.json").read_bytes()
    assert run(source, tmp_path / "output") == dest
    assert (dest / "manifest.json").read_bytes() == before
    (dest / "raw" / "teams.csv").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        run(source, tmp_path / "output")


def test_duplicate_and_unpinned_sources_rejected(tmp_path):
    source = sources(tmp_path)
    with pytest.raises(ValueError, match="commit"):
        ingest_season(
            source,
            tmp_path / "o",
            season="2024-25",
            revision="master",
            retrieved_at="2026-11-03T00:00:00Z",
        )
    frame = pd.read_csv(source / "gws_merged_gw.csv")
    pd.concat([frame, frame.iloc[:1]]).to_csv(source / "gws_merged_gw.csv", index=False)
    with pytest.raises(ValueError, match="duplicate"):
        run(source, tmp_path / "o")
