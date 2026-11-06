"""Direct-lead research rows frozen at a common origin, never at target deadlines.

Historical schedule, universe and membership come from the captured collection;
their pre-origin availability is NOT established by this reconstruction.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import pandas as pd

from fpl_app.features.deadline import lag_features, opportunity_features
from fpl_app.features.football import frozen_features
from fpl_app.features.pipeline import known_number, utc

EXTRA = [
    "xg_5",
    "xa_5",
    "xg90_shrunk",
    "xa90_shrunk",
    "xg_missing",
    "xa_missing",
    "defcon_5",
    "defcon_missing",
    "minutes_std5",
    "minutes_last",
    "starts_last",
    "days_since_last_fixture",
    "appearance_3",
    "sixty_3",
    "minutes_ewm",
    "points_10",
    "xg_10",
    "xa_10",
    "lead",
    "days_to_fixture",
]


def direct_panel(collection: dict[str, Any], leads: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return fixture rows and an explicit origin/player/event coverage ledger.

    Missing rows/stats and unfinalized targets stay missing. Explicit captured
    blanks have zero event points only after the event is otherwise finalized;
    they never become fabricated fixture observations. All fixtures of a double
    share one origin and one unchanged player-history boundary.
    """
    if (
        not leads
        or len(set(leads)) != len(leads)
        or any(type(lead) is not int or not 1 <= lead <= 8 for lead in leads)
    ):
        raise ValueError("Distinct integer leads in 1..8 required")
    deadlines = {e["event"]: utc(e["actual_deadline"]) for e in collection["event_evidence"]}
    mappings = {m["provider_player_id"]: m for m in collection["player_mappings"]}
    labels = {(r["provider_player_id"], r["fixture_id"]): r for r in collection["labels"]}
    if len(labels) != len(collection["labels"]):
        raise ValueError("Duplicate player-fixture labels")
    exposures: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    exposure_keys = set()
    for exposure in collection["schedule_exposures"]:
        key = (exposure["provider_player_id"], exposure["fixture_id"])
        if key in exposure_keys:
            raise ValueError("Duplicate player-fixture exposures")
        exposure_keys.add(key)
        exposures[(exposure["provider_player_id"], exposure["event"])].append(exposure)
    final_events = {
        r["event"] for r in collection["labels"] if r["label_status"] == "final_revision"
    } - {r["event"] for r in collection["labels"] if r["label_status"] != "final_revision"}
    history_rows = []
    history_stats: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for label in collection["labels"]:
        if label["label_status"] != "final_revision" or not all(
            known_number(label.get(field)) for field in ("minutes", "total_points")
        ):
            continue
        kickoff = utc(label["statistics"]["kickoff_time"])
        available = kickoff + timedelta(days=1)
        history_rows.append(
            {
                "player_key": label["canonical_player_id"],
                "fixture_id": label["fixture_id"],
                "event": label["event"],
                "points": label["total_points"],
                "minutes": label["minutes"],
                "starts": label["statistics"].get("starts"),
                "kickoff": pd.Timestamp(kickoff),
                "available_at": pd.Timestamp(available),
            }
        )
        history_stats[label["provider_player_id"]].append(
            {
                "event": label["event"],
                "stats": label["statistics"],
                "kickoff": kickoff.isoformat(),
                "available_at": available.isoformat(),
            }
        )
    if not history_rows:
        raise ValueError("Final signed points and minutes history required")
    history = pd.DataFrame(history_rows)
    by_player = {str(key): rows for key, rows in history.groupby("player_key")}
    coverage = {(c["provider_player_id"], c["event"]): c for c in collection["coverage"]}
    rows, ledger = [], []
    captured = utc(collection["captured_at"])
    positions = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    for lead in leads:
        for event, target_deadline in sorted(deadlines.items()):
            origin_event = event - lead + 1
            if origin_event not in deadlines or deadlines[origin_event] > captured:
                continue
            cutoff = deadlines[origin_event]
            for player_id, mapping in sorted(mappings.items()):
                scheduled = exposures.get((player_id, event), [])
                evidence = coverage.get((player_id, event))
                blank = (
                    not scheduled and evidence is not None and evidence["status"] == "blank_event"
                )
                valid_points, missing = [], 0
                for exposure in scheduled:
                    label = labels.get((player_id, exposure["fixture_id"]), {})
                    observed = (
                        label.get("label_status") == "final_revision"
                        and label["event"] == event
                        and known_number(label.get("total_points"))
                        and known_number(label.get("minutes"))
                    )
                    if observed:
                        valid_points.append(float(label["total_points"]))
                    else:
                        missing += 1
                    # History event guard is the ORIGIN event, not target event.
                    context = {
                        "player_key": mapping["canonical_player_id"],
                        "fixture_id": exposure["fixture_id"],
                        "event": origin_event,
                        "position": positions[mapping["position"]],
                        "club": exposure["canonical_club_id"],
                        "opponent": f"official_fpl:{collection['season']}:team:{exposure['opponent_provider_club_id']}",
                        "home": str(exposure["is_home"]),
                        "rule_era": "fpl-" + collection["season"].replace("/", "-"),
                    }
                    player_history = by_player.get(mapping["canonical_player_id"], history.iloc[:0])
                    features = frozen_features(player_history, context, pd.Timestamp(cutoff))
                    features.update(
                        lag_features(history_stats[player_id], cutoff.isoformat(), origin_event)
                    )
                    features.update(
                        opportunity_features(
                            history_stats[player_id], cutoff.isoformat(), origin_event
                        )
                    )
                    future_kickoff = exposure.get("kickoff")
                    features.update(
                        {
                            "lead": lead,
                            "days_to_fixture": (utc(future_kickoff) - cutoff).total_seconds()
                            / 86400
                            if future_kickoff
                            else float("nan"),
                        }
                    )
                    rows.append(
                        {
                            **features,
                            "player_id": player_id,
                            "player_key": mapping["canonical_player_id"],
                            "fixture_id": exposure["fixture_id"],
                            "event": event,
                            "origin_event": origin_event,
                            "target_deadline": target_deadline.isoformat(),
                            "target_points": float(label["total_points"])
                            if observed
                            else float("nan"),
                            "target_minutes": float(label["minutes"]) if observed else float("nan"),
                            "target_available_at": (
                                utc(label["statistics"]["kickoff_time"]) + timedelta(days=1)
                            ).isoformat()
                            if observed
                            else None,
                            "actual_label_available_at": label["available_at"]
                            if observed
                            else None,
                            "outcome_status": "final_observed"
                            if observed
                            else "missing_or_unfinalized",
                            "schedule_snapshot_id": exposure.get("snapshot_id"),
                            "schedule_available_at": exposure.get("available_at"),
                            "schedule_basis": "captured_reconstructed_not_verified_at_origin",
                            "source_sha256": collection["envelope_sha256"],
                        }
                    )
                status = (
                    "blank_event"
                    if blank
                    else "complete"
                    if scheduled and not missing
                    else "missing_or_unfinalized"
                )
                ledger.append(
                    {
                        "lead": lead,
                        "origin_event": origin_event,
                        "event": event,
                        "player_id": player_id,
                        "decision_cutoff": cutoff.isoformat(),
                        "scheduled_fixture_ids": [e["fixture_id"] for e in scheduled],
                        "scheduled_fixtures": len(scheduled),
                        "observed_fixtures": len(valid_points),
                        "missing_fixtures": missing,
                        "coverage_status": status,
                        "target_points": 0.0
                        if blank and event in final_events
                        else sum(valid_points)
                        if status == "complete"
                        else None,
                        "event_finalized": event in final_events,
                        "schedule_basis": "captured_reconstructed_not_verified_at_origin",
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(ledger)
