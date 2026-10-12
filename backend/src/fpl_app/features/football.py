"""Origin-frozen football covariates; archive timing is explicitly assumed."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pandas as pd

FEATURE_VERSION = "football-asof-v1"
CATEGORICAL = ["position", "club", "opponent", "home", "rule_era"]
NUMERIC = [
    "history_count",
    "points_5",
    "minutes_5",
    "appearance_5",
    "sixty_5",
    "starts_5",
    "history_missing",
    "starts_missing",
]
FEATURES = CATEGORICAL + NUMERIC


def frozen_features(
    history: pd.DataFrame, exposure: dict[str, Any], origin: pd.Timestamp
) -> dict[str, Any]:
    """Only usable earlier events; every fixture of a double shares one origin."""
    origin = pd.Timestamp(origin)
    if origin.tzinfo is None:
        raise ValueError("origin must be timezone aware")
    usable = history[
        (history.player_key == exposure["player_key"])
        & (history.available_at <= origin)
        & (history.event < exposure["event"])
        & (history.fixture_id != exposure["fixture_id"])
    ].sort_values("kickoff")
    recent = usable.tail(5)
    return {
        **{k: str(exposure[k]) for k in CATEGORICAL},
        "history_count": len(usable),
        "history_missing": int(recent.empty),
        "points_5": float(recent.points.mean()) if len(recent) else 0.0,
        "minutes_5": float(recent.minutes.mean()) if len(recent) else 0.0,
        "appearance_5": float((recent.minutes > 0).mean()) if len(recent) else 0.0,
        "sixty_5": float((recent.minutes >= 60).mean()) if len(recent) else 0.0,
        "starts_5": float(recent.starts.mean()) if recent.starts.notna().any() else 0.0,
        "starts_missing": int(not recent.starts.notna().any()),
        "history_available_max": usable.available_at.max().isoformat() if len(usable) else None,
        "history_refs": json.dumps(usable[["player_key", "fixture_id"]].to_dict("records")),
        "feature_version": FEATURE_VERSION,
        "decision_cutoff": origin.isoformat(),
    }


def archive_panel(csv_path: str, max_events: int = 16) -> pd.DataFrame:
    raw = pd.read_csv(csv_path)
    raw = raw[raw.GW.between(1, max_events) & raw.position.isin(["GK", "DEF", "MID", "FWD"])].copy()
    raw = raw.rename(
        columns={
            "GW": "event",
            "element": "player_id",
            "fixture": "fixture_id",
            "total_points": "points",
            "kickoff_time": "kickoff",
        }
    )
    keys = ["player_id", "fixture_id"]
    if raw.duplicated(keys).any():
        duplicate = raw[raw.duplicated(keys, keep=False)]
        if (
            (
                duplicate.groupby(keys)[
                    [
                        "points",
                        "minutes",
                        "event",
                        "kickoff",
                        "position",
                        "team",
                        "opponent_team",
                        "was_home",
                    ]
                ].nunique(dropna=False)
                > 1
            )
            .any()
            .any()
        ):
            raise ValueError("conflicting duplicate outcomes")
        raw = raw.drop_duplicates(keys)
    raw["kickoff"] = pd.to_datetime(raw.kickoff, utc=True)
    raw["available_at"] = raw.kickoff + pd.Timedelta(days=7)
    raw["player_key"] = raw.player_id.map(lambda x: f"fpl:2024-25:{x}")
    if raw[["points", "minutes", "kickoff"]].isna().any().any():
        raise ValueError("missing outcome is not zero")
    origins = raw.groupby("event").kickoff.min() - pd.Timedelta(hours=48)
    rows = []
    for r in raw.to_dict("records"):
        exposure: dict[str, Any] = {
            **{str(k): v for k, v in r.items()},
            "club": f"vaastav:2024-25:{r['team']}",
            "opponent": f"fpl:2024-25:club:{r['opponent_team']}",
            "home": str(r["was_home"]),
            "rule_era": "fpl-2024-25",
        }
        rows.append(
            {
                **frozen_features(raw, exposure, origins[r["event"]]),
                "player_key": r["player_key"],
                "player_id": r["player_id"],
                "fixture_id": r["fixture_id"],
                "event": r["event"],
                "target_points": r["points"],
                "target_minutes": r["minutes"],
                "target_start": r["starts"],
                "target_available_at": r["available_at"].isoformat(),
            }
        )
    return pd.DataFrame(rows)


def collection_frames(
    envelope: dict[str, Any], rules_version: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Qualified same-season research plus actual-current frozen exposures.

    Historical lag and current role/schedule reconstruction are assumptions. Actual
    future features only use labels retained by the collection capture.
    """
    mappings = {m["provider_player_id"]: m for m in envelope["player_mappings"]}
    exposures = {
        (e["provider_player_id"], e["fixture_id"]): e for e in envelope["schedule_exposures"]
    }
    origins = {e["event"]: pd.Timestamp(e["actual_deadline"]) for e in envelope["event_evidence"]}
    positions = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    history_rows = []
    labels = []
    for label in envelope["labels"]:
        if (
            label["label_status"] != "final_revision"
            or label["minutes"] is None
            or label["total_points"] is None
        ):
            continue
        stats = label["statistics"]
        kickoff = pd.Timestamp(stats["kickoff_time"])
        if pd.isna(kickoff):
            raise ValueError("unknown kickoff")
        history_rows.append(
            {
                "player_key": label["canonical_player_id"],
                "fixture_id": label["fixture_id"],
                "event": label["event"],
                "points": label["total_points"],
                "minutes": label["minutes"],
                "starts": stats.get("starts"),
                "kickoff": kickoff,
                "available_at": kickoff + timedelta(days=1),
            }
        )
        labels.append(label)
    history = pd.DataFrame(history_rows)
    if history.empty:
        raise ValueError("no finalized current-era labels")

    def exposure_row(e: dict[str, Any]) -> dict[str, Any]:
        m = mappings[e["provider_player_id"]]
        return {
            "player_key": m["canonical_player_id"],
            "fixture_id": e["fixture_id"],
            "event": e["event"],
            "position": positions[m["position"]],
            "club": e["canonical_club_id"],
            "opponent": f"official_fpl:{envelope['season']}:team:{e['opponent_provider_club_id']}",
            "home": str(e["is_home"]),
            "rule_era": rules_version,
        }

    panel_rows = []
    for label in labels:
        e = exposures.get((label["provider_player_id"], label["fixture_id"]))
        if e is None:
            continue  # current club cannot establish missing historical membership
        row = frozen_features(history, exposure_row(e), origins[label["event"]])
        stats = label["statistics"]
        panel_rows.append(
            {
                **row,
                "player_key": label["canonical_player_id"],
                "player_id": label["provider_player_id"],
                "fixture_id": label["fixture_id"],
                "event": label["event"],
                "target_points": label["total_points"],
                "target_minutes": label["minutes"],
                "target_start": stats.get("starts"),
                "target_available_at": (
                    pd.Timestamp(stats["kickoff_time"]) + timedelta(days=1)
                ).isoformat(),
            }
        )
    origin = pd.Timestamp(envelope["captured_at"])
    actual_history = history.copy()
    actual_history["available_at"] = pd.Timestamp(envelope["available_at"])
    future_events = [event for event, deadline in origins.items() if deadline > origin]
    if not future_events:
        raise ValueError("no future event")
    next_event = min(future_events)
    future_rows = []
    for e in envelope["schedule_exposures"]:
        if e["event"] != next_event:
            continue
        future_rows.append(
            {
                **frozen_features(actual_history, exposure_row(e), origin),
                "player_key": e["canonical_player_id"],
                "player_id": e["provider_player_id"],
                "event": e["event"],
                "fixture_id": e["fixture_id"],
                "source_available_at": envelope["available_at"],
                "source_ref": envelope["envelope_sha256"],
            }
        )
    explicit = pd.DataFrame(
        [
            {
                "current_player_id": i,
                "player_key": m["canonical_player_id"],
                "season": envelope["season"],
                "source_ref": envelope["envelope_sha256"],
            }
            for i, m in mappings.items()
        ]
    )
    return pd.DataFrame(panel_rows), pd.DataFrame(future_rows), explicit
