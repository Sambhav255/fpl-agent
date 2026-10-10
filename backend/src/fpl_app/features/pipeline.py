from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

FEATURE_VERSION = "deadline-v1"


def known_number(value: Any) -> bool:
    """True only for a finite real. None, NaN, and missing sentinels stay unknown."""
    if isinstance(value, bool):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if not isinstance(missing, (bool, np.bool_)):
        return False
    if bool(missing):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def optional_number(value: Any) -> float | None:
    if not known_number(value):
        return None
    return float(value)


NUMERIC_FEATURES = [
    "history_count",
    "mean_points_5",
    "mean_minutes_5",
    "appearance_5",
    "minutes_60_5",
    "goals_per90",
    "assists_per90",
    "history_missing",
    "goals_missing",
    "assists_missing",
]


def utc(value: str | datetime) -> datetime:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(UTC)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def immutable_json(path: Path, value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"immutable artifact already exists: {path}")
        return
    with path.open("xb") as stream:
        stream.write(encoded)


def ingest_bundle(payload: bytes, output: Path) -> dict[str, Any]:
    """Local JSON bundle; no inferred timestamps, name matching, or silent zero filling.

    Tables: mappings, observations, fixture_versions, eligibility, deadlines.
    Each timed row has available_at, source_ref and timing_verified. Mappings use
    provider/season/provider_player_id and explicit canonical_player_id; team mappings
    use provider_team_id/canonical_team_id. Original revised statistics stay excluded
    unless their version's availability is verified.
    """
    bundle = json.loads(payload)
    required = {
        "season",
        "provider",
        "data_mode",
        "mappings",
        "team_mappings",
        "observations",
        "fixture_versions",
        "eligibility",
        "deadlines",
    }
    if not required <= bundle.keys():
        raise ValueError(f"missing bundle fields: {sorted(required - bundle.keys())}")
    if bundle["data_mode"] not in ("demo", "live"):
        raise ValueError("invalid data_mode")
    mapping: dict[tuple[str, int], str] = {}
    for row in bundle["mappings"]:
        key = (row["season"], int(row["provider_player_id"]))
        if key in mapping or not row.get("reviewed") or not row.get("canonical_player_id"):
            raise ValueError("duplicate/unreviewed player season mapping")
        mapping[key] = str(row["canonical_player_id"])
    teams: dict[tuple[str, int], str] = {}
    for row in bundle["team_mappings"]:
        key = (row["season"], int(row["provider_team_id"]))
        if key in teams or not row.get("reviewed"):
            raise ValueError("duplicate/unreviewed team season mapping")
        teams[key] = str(row["canonical_team_id"])
    seen: set[tuple[str, str, int, str]] = set()
    for table in ("observations", "fixture_versions", "eligibility", "deadlines"):
        for row in bundle[table]:
            utc(row["available_at"])
            if not row.get("source_ref") or "timing_verified" not in row:
                raise ValueError(f"missing provenance in {table}")
            if table in ("observations", "eligibility"):
                key = (row["season"], int(row["provider_player_id"]))
                if key not in mapping:
                    raise ValueError("unmapped season/player")
                row["canonical_player_id"] = mapping[key]
                team_key = (row["season"], int(row["club"]))
                if team_key not in teams:
                    raise ValueError("unmapped season/team")
                row["canonical_team_id"] = teams[team_key]
            if table == "observations":
                key4 = (
                    row["season"],
                    row["canonical_player_id"],
                    int(row["fixture_id"]),
                    row["available_at"],
                )
                if key4 in seen:
                    raise ValueError("duplicate observation version")
                seen.add(key4)
                utc(row["completed_at"])
                if utc(row["available_at"]) < utc(row["completed_at"]):
                    raise ValueError("outcome available before match completion")
                minutes = row.get("minutes")
                if minutes is not None and not (
                    known_number(minutes) and 0 <= float(minutes) <= 130
                ):
                    raise ValueError("invalid minutes")
                if row.get("points") is not None and not known_number(row.get("points")):
                    raise ValueError("nonfinite points")
                for field in ("goals", "assists"):
                    value = row.get(field)
                    if value is not None and not known_number(value):
                        raise ValueError(f"invalid {field}")
    digest = hashlib.sha256(payload).hexdigest()
    dest = output / bundle["data_mode"] / digest
    dest.mkdir(parents=True, exist_ok=True)
    raw = dest / "source.json"
    if not raw.exists():
        with raw.open("xb") as stream:
            stream.write(payload)
    for table in (
        "mappings",
        "team_mappings",
        "observations",
        "fixture_versions",
        "eligibility",
        "deadlines",
    ):
        path = dest / f"{table}.parquet"
        if not path.exists():
            pd.DataFrame(bundle[table]).to_parquet(path, index=False)
    envelope = {
        "snapshot_id": digest,
        "provider": bundle["provider"],
        "resource": "historical_bundle",
        "captured_at": datetime.now(UTC).isoformat(),
        "source_published_at": None,
        "available_at": datetime.now(UTC).isoformat(),
        "payload_sha256": digest,
        "schema_version": 1,
        "season": bundle["season"],
        "storage_path": str(raw),
        "validation_status": "validated",
        "data_mode": bundle["data_mode"],
    }
    if not (dest / "envelope.json").exists():
        immutable_json(dest / "envelope.json", envelope)
    return {**envelope, "directory": str(dest)}


def lagged_summary(history: list[dict[str, Any]]) -> dict[str, float]:
    valid = [r for r in history if known_number(r.get("minutes")) and known_number(r.get("points"))]
    recent = valid[-5:]
    exposure = sum(float(r["minutes"]) for r in valid)

    def mean(field: str) -> float:
        values = [float(r[field]) for r in recent if known_number(r.get(field))]
        return sum(values) / len(values) if values else float("nan")

    def known_field(field: str) -> bool:
        return bool(valid) and all(known_number(r.get(field)) for r in valid)

    goals_known = known_field("goals")
    assists_known = known_field("assists")
    return {
        "history_count": float(len(valid)),
        "mean_points_5": mean("points"),
        "mean_minutes_5": mean("minutes"),
        "appearance_5": sum(float(r["minutes"]) > 0 for r in recent) / len(recent)
        if recent
        else float("nan"),
        "minutes_60_5": sum(float(r["minutes"]) >= 60 for r in recent) / len(recent)
        if recent
        else float("nan"),
        "goals_per90": 90 * (sum(float(r["goals"]) for r in valid) + 0.2) / (exposure + 900)
        if goals_known
        else float("nan"),
        "assists_per90": 90 * (sum(float(r["assists"]) for r in valid) + 0.2) / (exposure + 900)
        if assists_known
        else float("nan"),
        "history_missing": float(not recent),
        "goals_missing": float(not goals_known),
        "assists_missing": float(not assists_known),
    }


def build_features(directory: Path, cutoff: str, event: int, season: str) -> pd.DataFrame:
    """Strict deadline replay: every input version verified and available by cutoff.

    Targets are joined separately, never inputs. Unknown outcomes remain null.
    A fixture-free event emits one explicit blank row; an ineligible/absent player
    emits no row. All fixtures of a double share the identical history cutoff.
    """
    limit = utc(cutoff)

    def rows(table: str) -> list[dict[str, Any]]:
        frame = pd.read_parquet(directory / f"{table}.parquet")
        return cast(list[dict[str, Any]], frame.to_dict("records"))

    def available(row: dict[str, Any]) -> bool:
        return (
            row.get("season") == season
            and row.get("timing_verified") is True
            and utc(row["available_at"]) <= limit
        )

    deadlines = [r for r in rows("deadlines") if available(r) and r["event"] == event]
    if (
        not deadlines
        or utc(max(deadlines, key=lambda r: utc(r["available_at"]))["deadline"]) != limit
    ):
        raise ValueError("verified event deadline matching cutoff unavailable")
    fixtures: dict[int, dict[str, Any]] = {}
    for row in sorted(rows("fixture_versions"), key=lambda r: utc(r["available_at"])):
        if available(row):
            fixtures[int(row["fixture_id"])] = row
    eligible: dict[str, dict[str, Any]] = {}
    for row in sorted(rows("eligibility"), key=lambda r: utc(r["available_at"])):
        if available(row):
            eligible[row["canonical_player_id"]] = row
    all_obs = rows("observations")
    records = []
    for player, state in eligible.items():
        if not state["eligible"]:
            continue
        scheduled = [
            f
            for f in fixtures.values()
            if f["event"] == event and state["club"] in (f["home_club"], f["away_club"])
        ]
        target_ids = {f["fixture_id"] for f in scheduled}
        hist_versions: dict[int, dict[str, Any]] = {}
        for obs in sorted(all_obs, key=lambda r: utc(r["available_at"])):
            if (
                obs["canonical_player_id"] == player
                and available(obs)
                and utc(obs["completed_at"]) < limit
                and obs["fixture_id"] not in target_ids
            ):
                hist_versions[obs["fixture_id"]] = obs
        history = sorted(hist_versions.values(), key=lambda r: utc(r["completed_at"]))
        summary = lagged_summary(history)
        fixture_rows: list[dict[str, Any] | None] = list(scheduled) if scheduled else [None]
        for fixture in fixture_rows:
            fid = fixture["fixture_id"] if fixture else 0
            targets = [
                o
                for o in all_obs
                if o["season"] == season
                and o["canonical_player_id"] == player
                and o["fixture_id"] == fid
            ]
            target = max(targets, key=lambda r: utc(r["available_at"])) if targets else {}
            blank = fixture is None
            records.append(
                {
                    **summary,
                    "season": season,
                    "canonical_player_id": player,
                    "event": event,
                    "fixture_id": fid,
                    "decision_cutoff": cutoff,
                    "position": state["position"],
                    "club": state["club"],
                    "opponent": (
                        fixture["away_club"]
                        if fixture["home_club"] == state["club"]
                        else fixture["home_club"]
                    )
                    if fixture
                    else 0,
                    "was_home": int(bool(fixture and fixture["home_club"] == state["club"])),
                    "outcome_state": (
                        "blank"
                        if blank
                        else "missing_record"
                        if not target
                        else "missing_statistic"
                        if not known_number(target.get("minutes"))
                        else "no_appearance"
                        if float(target["minutes"]) == 0
                        else "appeared"
                    ),
                    "target_points": 0.0 if blank else optional_number(target.get("points")),
                    "target_minutes": 0.0 if blank else optional_number(target.get("minutes")),
                    "target_start": None if blank else optional_number(target.get("start")),
                    "target_end": cutoff if blank else target.get("completed_at"),
                    "target_available_at": cutoff if blank else target.get("available_at"),
                    "source_refs": json.dumps(
                        sorted(
                            {
                                state["source_ref"],
                                *[h["source_ref"] for h in history],
                                *([fixture["source_ref"]] if fixture else []),
                            }
                        )
                    ),
                    "feature_version": FEATURE_VERSION,
                    "replay_timing": "verified",
                    "timing_verified": True,
                }
            )
    return pd.DataFrame(records)


def write_panel_audit(dataset: Path, audit: dict[str, Any]) -> dict[str, Any]:
    """Bind audit.json to the exact feature parquet. Checksum and row count are computed here."""
    if not dataset.is_file():
        raise ValueError("feature panel is missing")
    frame = pd.read_parquet(dataset)
    payload = {
        **audit,
        "panel_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "rows": len(frame),
    }
    immutable_json(dataset.parent / "audit.json", payload)
    return payload
