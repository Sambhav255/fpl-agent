"""Conservative, explicitly approximate Vaastav completed-match replay.

No claim of original statistic publication times or final fixture version knowledge.
Only lagged minutes/points/goals/assists are inputs. Current position/team/price,
xP and injuries are never predictors. Same-season IDs are namespaced explicitly;
cross-season person linking is unresolved rather than joined by names.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from .pipeline import NUMERIC_FEATURES, immutable_json, lagged_summary

LIMITATIONS = [
    "Final archive match statistics may be revised; available_at is a conservative assumed kickoff+7 days, not verified publication",
    "Decision cutoff is earliest event kickoff minus 48 hours, an early-deadline proxy, not verified official deadline",
    "Final fixture assignments identify targets only; no future fixture, team, role, price, injury or xP inputs",
    "Panel covers archive-listed player fixture outcomes; absent rows are missing, not inferred zeros; no full policy replay",
    "Explicit same-season provider ID namespaces; cross-season canonical person mapping unresolved",
]


def ingest_archive(
    output: Path, season: str = "2024-25", max_events: int = 16, lag_days: int = 7
) -> Path:
    if (
        not re.fullmatch(r"20[0-9]{2}-[0-9]{2}", season)
        or not 8 <= max_events <= 38
        or lag_days < 3
    ):
        raise ValueError("invalid season/event/lag configuration")
    # Fixed provider origin and validated season; never arbitrary supplied URLs.
    url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{season}/gws/merged_gw.csv"
    response = httpx.get(url, timeout=45, follow_redirects=False)
    response.raise_for_status()
    raw = response.content
    sha = hashlib.sha256(raw).hexdigest()
    dest = output / "live" / f"vaastav-{season}-{sha[:16]}-e{max_events}-lag{lag_days}"
    dest.mkdir(parents=True, exist_ok=True)
    raw_path = dest / "merged_gw.csv"
    if not raw_path.exists():
        with raw_path.open("xb") as stream:
            stream.write(raw)
    frame = pd.read_csv(io.BytesIO(raw))
    required = {
        "element",
        "fixture",
        "GW",
        "kickoff_time",
        "minutes",
        "total_points",
        "goals_scored",
        "assists",
    }
    if not required <= set(frame):
        raise ValueError(f"historical schema missing {required - set(frame)}")
    frame = frame[frame["GW"].between(1, max_events)].copy()
    # Assistant Manager is not an ordinary player and uses a different scoring target.
    if "position" in frame:
        frame = frame[frame["position"].isin(["GK", "DEF", "MID", "FWD"])]
    if frame.duplicated(["element", "fixture"]).any():
        duplicates = frame[frame.duplicated(["element", "fixture"], keep=False)]
        keys = ["minutes", "total_points", "goals_scored", "assists", "kickoff_time", "GW"]
        if (duplicates.groupby(["element", "fixture"])[keys].nunique(dropna=False) > 1).any().any():
            raise ValueError("conflicting duplicate archive outcomes")
        frame = frame.drop_duplicates(["element", "fixture"])
    frame["kickoff_time"] = pd.to_datetime(frame["kickoff_time"], utc=True)
    if frame["kickoff_time"].isna().any() or not frame["minutes"].between(0, 130).all():
        raise ValueError("invalid kickoff/minutes coverage")
    source = f"sha256:{sha}"
    mappings = [
        {
            "provider": "vaastav/fpl",
            "season": season,
            "provider_player_id": int(i),
            "canonical_player_id": f"fpl:{season}:{int(i)}",
            "mapping_status": "season_scoped_identity_only",
            "cross_season_person_id": None,
            "source_ref": source,
        }
        for i in sorted(frame["element"].unique())
    ]
    observations: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        kickoff = row["kickoff_time"].to_pydatetime()
        observations.append(
            {
                "season": season,
                "canonical_player_id": f"fpl:{season}:{int(row['element'])}",
                "provider_player_id": int(row["element"]),
                "fixture_id": int(row["fixture"]),
                "event": int(row["GW"]),
                "kickoff": kickoff.isoformat(),
                "completed_at": (kickoff + timedelta(hours=3)).isoformat(),
                "available_at": (kickoff + timedelta(days=lag_days)).isoformat(),
                "points": float(row["total_points"]),
                "minutes": float(row["minutes"]),
                "goals": float(row["goals_scored"]) if pd.notna(row["goals_scored"]) else None,
                "assists": float(row["assists"]) if pd.notna(row["assists"]) else None,
                "start": float(row["starts"])
                if "starts" in row and pd.notna(row["starts"])
                else None,
                "source_ref": source,
                "timing_verified": False,
                "timing_basis": f"assumed kickoff+{lag_days}d",
            }
        )
    cutoffs = (frame.groupby("GW")["kickoff_time"].min() - pd.Timedelta(hours=48)).to_dict()
    features = []
    for target in observations:
        cutoff = cutoffs[target["event"]].to_pydatetime()
        history = [
            o
            for o in observations
            if o["canonical_player_id"] == target["canonical_player_id"]
            and datetime.fromisoformat(o["available_at"]) <= cutoff
            and o["event"] < target["event"]
            and o["fixture_id"] != target["fixture_id"]
        ]
        history.sort(key=lambda o: o["completed_at"])
        features.append(
            {
                **lagged_summary(history),
                "season": season,
                "canonical_player_id": target["canonical_player_id"],
                "fixture_id": target["fixture_id"],
                "event": target["event"],
                "decision_cutoff": cutoff.isoformat(),
                "target_points": target["points"],
                "target_minutes": target["minutes"],
                "target_start": target["start"],
                "target_end": target["completed_at"],
                "target_available_at": target["available_at"],
                "source_refs": json.dumps([source]),
                "outcome_state": "no_appearance" if target["minutes"] == 0 else "appeared",
                "replay_timing": "conservative_assumed",
                "timing_verified": False,
                "feature_version": "lagged-only-v1",
            }
        )
    for name, records in (
        ("mappings", mappings),
        ("observations", observations),
        ("features", features),
    ):
        path = dest / f"{name}.parquet"
        if not path.exists():
            pd.DataFrame(records).to_parquet(path, index=False)
    envelope = {
        "snapshot_id": sha,
        "provider": "vaastav",
        "resource": url,
        "captured_at": datetime.now(UTC).isoformat(),
        "source_published_at": None,
        "available_at": datetime.now(UTC).isoformat(),
        "payload_sha256": sha,
        "schema_version": 1,
        "season": season,
        "storage_path": str(raw_path),
        "validation_status": "conservative_approximate_audit",
        "data_mode": "live",
        "feature_columns": NUMERIC_FEATURES,
        "replay_timing": "conservative_assumed",
        "panel_sha256": hashlib.sha256((dest / "features.parquet").read_bytes()).hexdigest(),
        "lag_days": lag_days,
        "max_events": max_events,
        "limitations": LIMITATIONS,
        "rows": len(features),
        "players": len(mappings),
        "events": sorted(int(str(e)) for e in cutoffs),
    }
    if not (dest / "audit.json").exists():
        immutable_json(dest / "audit.json", envelope)
    return dest
