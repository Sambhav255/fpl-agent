"""Fixture-slot panels. Timestamped rows use one encoder per forecast deadline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from fpl_app.features.pipeline import known_number, utc

ENCODER_LENGTH = 6


def _point_versions(row: dict[str, Any] | None) -> list[tuple[datetime, float]]:
    if row is None:
        return []
    versions: list[tuple[datetime, float]] = []
    raw = row.get("point_versions")
    if isinstance(raw, (list, tuple)):
        for item in raw:
            if not isinstance(item, dict):
                continue
            if known_number(item.get("points")) and pd.notna(item.get("available_at")):
                versions.append((utc(item["available_at"]), float(item["points"])))
    if known_number(row.get("target_points")) and pd.notna(row.get("target_available_at")):
        versions.append((utc(row["target_available_at"]), float(row["target_points"])))
    return versions


def _asof(versions: list[tuple[datetime, float]], cutoff: datetime) -> tuple[float, float]:
    eligible = [item for item in versions if item[0] <= cutoff]
    if not eligible:
        return 0.0, 0.0
    published = max(eligible, key=lambda item: item[0])
    return published[1], 1.0


def _player_slots(frame: pd.DataFrame, max_slots: int) -> list[dict[str, Any]]:
    required = {
        "season",
        "canonical_player_id",
        "event",
        "fixture_id",
        "decision_cutoff",
        "target_points",
        "opponent",
        "was_home",
        "outcome_state",
    }
    if (
        not required <= set(frame)
        or frame.duplicated(["season", "canonical_player_id", "event", "fixture_id"]).any()
    ):
        raise ValueError("distinct dated player/event/fixture rows and verified schedule required")
    if max_slots < 1:
        raise ValueError("max_slots must be positive")
    prepared: list[dict[str, Any]] = []
    for (season, player), group in frame.groupby(["season", "canonical_player_id"]):
        dates = sorted(int(str(value)) for value in group["event"].unique())
        if dates != list(range(dates[0], dates[-1] + 1)):
            raise ValueError(
                "missing player events must be explicitly blank/missing; cannot auto-zero"
            )
        for event, event_rows in group.groupby("event"):
            if event_rows["decision_cutoff"].nunique() != 1:
                raise ValueError("all event fixtures require same deadline")
            rows = event_rows.sort_values("fixture_id").to_dict("records")
            if len(rows) > max_slots:
                raise ValueError("fixture slots overflow; do not average opponents")
            event_id = int(str(event))
            for slot in range(max_slots):
                prepared.append(
                    {
                        "season": str(season),
                        "player": str(player),
                        "event": event_id,
                        "slot": slot,
                        "row": rows[slot] if slot < len(rows) else None,
                        "decision_cutoff": event_rows["decision_cutoff"].iloc[0],
                    }
                )
    return prepared


def _legacy_row(item: dict[str, Any]) -> dict[str, Any]:
    row = item["row"]
    exists = row is not None and row["outcome_state"] != "blank"
    observed = row is not None and pd.notna(row["target_points"])
    return {
        "series": f"{item['season']}:{item['player']}:slot{item['slot']}",
        "player": item["player"],
        "season": item["season"],
        "time_idx": item["event"],
        "slot": float(item["slot"]),
        "fixture_id": int(row["fixture_id"]) if row else -1,
        "fixture_exists": float(exists),
        "opponent": float(row["opponent"]) if row else 0.0,
        "was_home": float(row["was_home"]) if row else 0.0,
        "points": float(row["target_points"]) if row is not None and observed else 0.0,
        "observation_mask": float(observed),
        "weight": float(observed),
        "decision_cutoff": item["decision_cutoff"],
    }


def _deadline_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    ordered = sorted(events, key=lambda item: int(item["event"]))
    season, player, slot = ordered[0]["season"], ordered[0]["player"], ordered[0]["slot"]
    for origin in ordered:
        origin_cutoff = utc(origin["decision_cutoff"])
        priors = [item for item in ordered if item["event"] < origin["event"]][-ENCODER_LENGTH:]
        steps: list[dict[str, Any] | None] = [None] * (ENCODER_LENGTH - len(priors)) + priors
        steps.append(origin)
        series = f"{season}:{player}:slot{slot}:origin{origin['event']}"
        for time_idx, step in enumerate(steps):
            is_target = step is origin
            source = None if step is None else step["row"]
            if step is None:
                encoder_points, mask, points, weight = 0.0, 0.0, 0.0, 0.0
                source_event, exists, fixture_id = -1, False, -1
                opponent = was_home = 0.0
            else:
                if is_target:
                    encoder_points, mask = 0.0, 0.0
                    if source is not None and known_number(source.get("target_points")):
                        points, weight = float(source["target_points"]), 1.0
                    else:
                        points, weight = 0.0, 0.0
                else:
                    encoder_points, mask = _asof(_point_versions(source), origin_cutoff)
                    points, weight = encoder_points, 0.0
                source_event = int(step["event"])
                exists = source is not None and source["outcome_state"] != "blank"
                opponent = float(source["opponent"]) if source else 0.0
                was_home = float(source["was_home"]) if source else 0.0
                fixture_id = int(source["fixture_id"]) if source else -1
            result.append(
                {
                    "series": series,
                    "player": player,
                    "season": season,
                    "time_idx": time_idx,
                    "slot": float(slot),
                    "fixture_id": fixture_id,
                    "fixture_exists": float(exists),
                    "opponent": opponent,
                    "was_home": was_home,
                    "points": points,
                    "encoder_points": encoder_points,
                    "observation_mask": mask,
                    "weight": weight,
                    "decision_cutoff": origin_cutoff.isoformat(),
                    "forecast_origin": int(origin["event"]),
                    "source_event": source_event,
                }
            )
    return result


def slot_panel(frame: pd.DataFrame, max_slots: int = 3) -> pd.DataFrame:
    prepared = _player_slots(frame, max_slots)
    if "target_available_at" not in frame.columns:
        return pd.DataFrame([_legacy_row(item) for item in prepared])
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for item in prepared:
        grouped.setdefault((item["season"], item["player"], item["slot"]), []).append(item)
    rows: list[dict[str, Any]] = []
    for events in grouped.values():
        rows.extend(_deadline_rows(events))
    return pd.DataFrame(rows)


def forecast_windows(panel: pd.DataFrame, train_end: int) -> dict[str, Any]:
    if "forecast_origin" in panel.columns:
        training_rows = panel[panel["forecast_origin"] <= train_end]
        future_rows = panel[panel["forecast_origin"] > train_end]
        if training_rows.empty or future_rows.empty:
            raise ValueError("training and later validation events required")
        return {
            "asof": True,
            "training_rows": training_rows,
            "future_rows": future_rows,
            "min_encoder_length": ENCODER_LENGTH,
            "max_encoder_length": ENCODER_LENGTH,
            "unknown_reals": ["encoder_points", "observation_mask"],
        }
    training_rows = panel[panel["time_idx"] <= train_end]
    if training_rows.empty or int(panel["time_idx"].max()) <= train_end:
        raise ValueError("training and later validation events required")
    return {
        "asof": False,
        "training_rows": training_rows,
        "future_rows": panel,
        "min_encoder_length": 2,
        "max_encoder_length": 6,
        "unknown_reals": ["points", "observation_mask"],
    }
