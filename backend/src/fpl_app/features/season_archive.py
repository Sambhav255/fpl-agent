"""Pinned archive normalization; no claim of verified historical publication timing.

Extends the approximate archive adapter with reusable season tables. This is a
research data foundation, never authority for current rules or strict replay.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pandas as pd

FILES = ("gws_merged_gw.csv", "fixtures.csv", "teams.csv", "players_raw.csv")
VERSION = "season-archive-v1"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def league_table_prefix(fixtures: pd.DataFrame, cutoff: str, club_ids: list[int]) -> pd.DataFrame:
    """Results known under the declared lag, excluding later or unfinished games.

    available_at is mandatory: kickoff alone never establishes source availability.
    No final table/position fields from teams.csv are consumed.
    """
    origin = pd.Timestamp(cutoff)
    if origin.tzinfo is None:
        raise ValueError("cutoff must have timezone")
    table = {i: {"club_id": i, "played": 0, "points": 0, "gf": 0, "ga": 0} for i in club_ids}
    available = pd.to_datetime(fixtures["available_at"], utc=True)
    for row in fixtures.loc[available <= origin].to_dict("records"):
        if not row["finished"] or pd.isna(row["team_h_score"]) or pd.isna(row["team_a_score"]):
            continue
        home, away = int(row["team_h"]), int(row["team_a"])
        hs, aws = int(row["team_h_score"]), int(row["team_a_score"])
        for club, gf, ga in ((home, hs, aws), (away, aws, hs)):
            record = table[club]
            record["played"] += 1
            record["gf"] += gf
            record["ga"] += ga
            record["points"] += 3 if gf > ga else int(gf == ga)
    result = pd.DataFrame(table.values())
    result["goal_difference"] = result["gf"] - result["ga"]
    # Stable numeric tie order is a research convention, not official tie resolution.
    result = result.sort_values(
        ["points", "goal_difference", "gf", "club_id"], ascending=[False, False, False, True]
    )
    result["position"] = range(1, len(result) + 1)
    result["decision_cutoff"] = cutoff
    return result.reset_index(drop=True)


def ingest_season(
    source: Path,
    output: Path,
    *,
    season: str,
    revision: str,
    retrieved_at: str,
    lag_days: int = 7,
) -> Path:
    """Normalize four pinned files, preserving all archive-listed ordinary players.

    Caller retrieves files from the fixed vaastav repository at a full Git SHA.
    Original bytes are retained and each retry verifies all raw and derived hashes.
    Historical availability is an explicit conservative assumption, not backdating.
    """
    if not re.fullmatch(r"20\d{2}-\d{2}", season) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("season and full source commit required")
    if datetime.fromisoformat(retrieved_at).tzinfo is None or lag_days < 3:
        raise ValueError("timezone-aware retrieval and conservative lag required")
    hashes = {name: _hash(source / name) for name in FILES}
    identity = hashlib.sha256(
        json.dumps([VERSION, season, revision, hashes, lag_days], sort_keys=True).encode()
    ).hexdigest()
    dest = output / f"{season}-{identity[:16]}"
    manifest_path = dest / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, expected in manifest["artifact_sha256"].items():
            if _hash(dest / name) != expected:
                raise ValueError(f"archive artifact checksum mismatch: {name}")
        return dest
    if dest.exists():
        raise ValueError("incomplete archive destination; preserve and retry in clean output")

    outcomes = pd.read_csv(source / FILES[0])
    fixtures = pd.read_csv(source / "fixtures.csv")
    teams = pd.read_csv(source / "teams.csv")
    players = pd.read_csv(source / "players_raw.csv")
    required = {
        "element",
        "fixture",
        "GW",
        "minutes",
        "total_points",
        "kickoff_time",
        "was_home",
        "position",
    }
    if not required <= set(outcomes):
        raise ValueError(f"missing archive columns: {sorted(required - set(outcomes))}")
    outcomes = outcomes[outcomes["position"].isin(["GK", "DEF", "MID", "FWD"])].copy()
    duplicates = int(outcomes.duplicated(["element", "fixture"]).sum())
    if duplicates:
        raise ValueError(
            "duplicate player fixture observations require explicit revision resolution"
        )
    if (
        fixtures["id"].duplicated().any()
        or teams["id"].duplicated().any()
        or players["id"].duplicated().any()
    ):
        raise ValueError("duplicate source identities")
    if not outcomes["minutes"].between(0, 130).all() or outcomes["total_points"].isna().any():
        raise ValueError("invalid minutes or missing point outcomes")
    if not set(outcomes["fixture"]) <= set(fixtures["id"]):
        raise ValueError("unmapped fixture identity")
    fixtures = fixtures.copy()
    fixtures["kickoff_time"] = pd.to_datetime(fixtures["kickoff_time"], utc=True)
    if fixtures["kickoff_time"].isna().any():
        raise ValueError("missing kickoff")
    fixtures["available_at"] = fixtures["kickoff_time"] + pd.Timedelta(days=lag_days)
    lookup = fixtures.set_index("id")
    outcomes["club_id"] = [
        int(cast(Any, lookup.loc[r["fixture"], "team_h" if r["was_home"] else "team_a"]))
        for r in outcomes.to_dict("records")
    ]
    outcomes["opponent_club_id"] = [
        int(cast(Any, lookup.loc[r["fixture"], "team_a" if r["was_home"] else "team_h"]))
        for r in outcomes.to_dict("records")
    ]
    if not set(outcomes["club_id"]) <= set(teams["id"]):
        raise ValueError("unmapped club identity")
    outcomes["kickoff_time"] = pd.to_datetime(outcomes["kickoff_time"], utc=True)
    if outcomes["kickoff_time"].isna().any():
        raise ValueError("missing player kickoff")
    outcomes["available_at"] = outcomes["kickoff_time"] + pd.Timedelta(days=lag_days)
    outcomes["season"] = season
    outcomes["player_identity"] = outcomes["element"].map(lambda i: f"fpl:{season}:{int(i)}")
    outcomes["scoring_rules_version"] = f"official-archive:{season}"
    outcomes["timing_verified"] = False
    outcomes["label_status"] = (
        outcomes["fixture"]
        .map(lookup["finished"])
        .map({True: "archive_finished_revision", False: "provisional"})
    )
    # Exclude xP and final metadata from the normalized outcome interface.
    label_columns = [
        "season",
        "player_identity",
        "element",
        "fixture",
        "GW",
        "club_id",
        "opponent_club_id",
        "position",
        "kickoff_time",
        "available_at",
        "minutes",
        "total_points",
        "scoring_rules_version",
        "timing_verified",
        "label_status",
    ]
    optional = [
        "starts",
        "goals_scored",
        "assists",
        "bps",
        "expected_goals",
        "expected_assists",
        "defensive_contribution",
    ]
    for name in optional:
        if name not in outcomes:
            outcomes[name] = float("nan")
    normalized = outcomes[label_columns + optional].copy()
    mappings = []
    player_lookup = players.set_index("id")
    for identifier in sorted(int(i) for i in outcomes["element"].unique()):
        code = (
            player_lookup.loc[identifier, "code"]
            if identifier in player_lookup.index and "code" in players
            else None
        )
        mappings.append(
            {
                "season": season,
                "provider_player_id": identifier,
                "canonical_player_id": f"fpl:{season}:{identifier}",
                "provider_code_clue": int(cast(Any, code)) if pd.notna(code) else None,
                "cross_season_person_id": None,
                "mapping_status": "season_scoped_unresolved_cross_season",
            }
        )
    clubs = [
        {
            "season": season,
            "provider_club_id": int(r["id"]),
            "provider_code": int(r["code"]),
            "canonical_club_id": f"fpl-club-code:{int(r['code'])}",
            "name": r["name"],
            "mapping_status": "provider_code_identity",
        }
        for r in teams.to_dict("records")
    ]
    # Observed membership spans only; gaps and exact transfer dates remain unknown.
    memberships = []
    for player_key, group in outcomes.sort_values("kickoff_time").groupby("element"):
        group = group.copy()
        group["spell"] = group["club_id"].ne(group["club_id"].shift()).cumsum()
        for _, spell in group.groupby("spell"):
            memberships.append(
                {
                    "player_identity": f"fpl:{season}:{int(cast(Any, player_key))}",
                    "club_id": int(spell.iloc[0]["club_id"]),
                    "first_observed": spell["kickoff_time"].min().isoformat(),
                    "last_observed": spell["kickoff_time"].max().isoformat(),
                    "boundary_status": "observed_fixture_span_not_transfer_date",
                }
            )
    prefixes = []
    for event, group in outcomes.groupby("GW"):
        cutoff = (group["kickoff_time"].min() - timedelta(hours=48)).isoformat()
        prefix = league_table_prefix(fixtures, cutoff, [int(i) for i in teams["id"]])
        prefix["event"] = int(cast(Any, event))
        prefixes.append(prefix)
    quality = {
        "rows": len(normalized),
        "players": len(mappings),
        "events": sorted(int(i) for i in outcomes["GW"].unique()),
        "fixtures_covered": int(outcomes["fixture"].nunique()),
        "fixtures_in_source": len(fixtures),
        "clubs": len(clubs),
        "duplicates": duplicates,
        "negative_point_rows": int((outcomes["total_points"] < 0).sum()),
        "zero_minute_negative_point_rows": int(
            ((outcomes["minutes"] == 0) & (outcomes["total_points"] < 0)).sum()
        ),
        "players_absent_from_final_metadata": len(set(outcomes["element"]) - set(players["id"])),
        "missing_statistic_rows": {name: int(normalized[name].isna().sum()) for name in optional},
        "membership_spans": len(memberships),
        "missing_archive_rows": "unknown; never filled with zero",
        "source_coverage": "all archive-listed ordinary player fixture rows; includes departed players where retained",
    }
    dest.mkdir(parents=True)
    raw = dest / "raw"
    raw.mkdir()
    for name in FILES:
        (raw / name).write_bytes((source / name).read_bytes())
    normalized.to_parquet(dest / "player_fixture_outcome.parquet", index=False)
    pd.concat(prefixes, ignore_index=True).to_parquet(
        dest / "league_table_snapshot.parquet", index=False
    )
    fixtures.to_parquet(dest / "fixture_revision.parquet", index=False)
    _write_json(dest / "player_identity.json", mappings)
    _write_json(dest / "club_identity.json", clubs)
    _write_json(dest / "player_club_interval.json", memberships)
    _write_json(dest / "quality.json", quality)
    paths = sorted(p for p in dest.rglob("*") if p.is_file())
    manifest = {
        "schema_version": VERSION,
        "season": season,
        "source_revision": revision,
        "retrieved_at": retrieved_at,
        "source_published_at": None,
        "available_at": retrieved_at,
        "provider": "vaastav/Fantasy-Premier-League",
        "sources": [
            {
                "url": f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{revision}/data/{season}/{name.replace('gws_', 'gws/')}",
                "sha256": hashes[name],
            }
            for name in FILES
        ],
        "allowed_use": "research audit only; source licence must be reviewed before redistribution",
        "scoring_rules_version": f"official-archive:{season}",
        "scoring_reconstruction": False,
        "timing": {
            "verified": False,
            "statistics_available_at": f"assumed kickoff+{lag_days} days",
            "deadline": "assumed earliest event kickoff-48 hours",
            "fixture_schedule": "final revision; targets only, not historical future schedule",
        },
        "feature_contract": {
            "table_inputs": ["earlier finished scores available under declared lag"],
            "excluded": [
                "final league position",
                "xP",
                "current club",
                "current price",
                "injuries",
                "unverified role",
            ],
            "strict_replay_eligible": False,
        },
        "artifact_sha256": {str(p.relative_to(dest)): _hash(p) for p in paths},
        "quality": quality,
    }
    _write_json(manifest_path, manifest)
    return dest
