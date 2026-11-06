"""Research ablations with lagged official statistics and explicit timing limits."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import numpy as np

from fpl_app.features.football import collection_frames
from fpl_app.features.pipeline import known_number, utc

ATTACK = ["xg_5", "xa_5", "xg90_shrunk", "xa90_shrunk", "xg_missing", "xa_missing"]
DEFENCE = ["defcon_5", "defcon_missing"]
CONTEXT = [
    "minutes_std5",
    "minutes_last",
    "starts_last",
    "days_since_last_fixture",
    "club_goals_prior",
    "opponent_conceded_prior",
]
OPPORTUNITY = ["appearance_3", "sixty_3", "minutes_ewm", "points_10", "xg_10", "xa_10"]


def lag_features(history: list[dict[str, Any]], cutoff: str, event: int) -> dict[str, float]:
    usable = sorted(
        [r for r in history if r["event"] < event and utc(r["available_at"]) <= utc(cutoff)],
        key=lambda r: utc(r["kickoff"]),
    )[-5:]
    result: dict[str, float] = {}
    for field, prefix in [
        ("expected_goals", "xg"),
        ("expected_assists", "xa"),
        ("defensive_contribution", "defcon"),
    ]:
        values = [float(r["stats"][field]) for r in usable if known_number(r["stats"].get(field))]
        result[prefix + "_5"] = float(np.mean(values)) if values else float("nan")
        result[prefix + "_missing"] = 1 - len(values) / len(usable) if usable else 1.0
        if prefix in {"xg", "xa"}:
            complete = [
                r
                for r in usable
                if known_number(r["stats"].get(field)) and known_number(r["stats"].get("minutes"))
            ]
            # Fixed 450-minute prior: 0.20 xG/90 and 0.10 xA/90, never fitted on test.
            prior = 0.2 if prefix == "xg" else 0.1
            result[prefix + "90_shrunk"] = (
                (sum(float(r["stats"][field]) for r in complete) + 5 * prior)
                / (sum(float(r["stats"]["minutes"]) for r in complete) + 450)
                * 90
                if complete
                else float("nan")
            )
    minutes = [
        float(r["stats"]["minutes"]) for r in usable if known_number(r["stats"].get("minutes"))
    ]
    result["minutes_std5"] = float(np.std(minutes)) if minutes else float("nan")
    result["minutes_last"] = (
        float(usable[-1]["stats"]["minutes"])
        if usable and known_number(usable[-1]["stats"].get("minutes"))
        else float("nan")
    )
    result["starts_last"] = (
        float(usable[-1]["stats"]["starts"])
        if usable and known_number(usable[-1]["stats"].get("starts"))
        else float("nan")
    )
    result["days_since_last_fixture"] = (
        min(60.0, (utc(cutoff) - utc(usable[-1]["kickoff"])).total_seconds() / 86400)
        if usable
        else float("nan")
    )
    # Read compatibility for old retained feature manifests; new fits use the explicit name.
    result["rest_days"] = result["days_since_last_fixture"]
    return result


def opportunity_features(
    history: list[dict[str, Any]], cutoff: str, event: int
) -> dict[str, float]:
    """Short opportunity and longer attacking history; no current/future outcomes."""
    usable = sorted(
        [r for r in history if r["event"] < event and utc(r["available_at"]) <= utc(cutoff)],
        key=lambda r: utc(r["kickoff"]),
    )[-10:]
    result = {}
    for field, name in (
        ("total_points", "points_10"),
        ("expected_goals", "xg_10"),
        ("expected_assists", "xa_10"),
    ):
        values = [float(r["stats"][field]) for r in usable if known_number(r["stats"].get(field))]
        result[name] = float(np.mean(values)) if values else float("nan")
    minutes = [
        float(r["stats"]["minutes"]) for r in usable if known_number(r["stats"].get("minutes"))
    ]
    result["appearance_3"] = float(np.mean(np.array(minutes[-3:]) > 0)) if minutes else float("nan")
    result["sixty_3"] = float(np.mean(np.array(minutes[-3:]) >= 60)) if minutes else float("nan")
    weights = 0.7 ** np.arange(len(minutes) - 1, -1, -1)
    result["minutes_ewm"] = float(np.average(minutes, weights=weights)) if minutes else float("nan")
    return result


def enriched_panels(collection: dict[str, Any], fixtures: list[dict[str, Any]]):
    rules = "fpl-" + collection["season"].replace("/", "-")
    historical, future, mappings = collection_frames(collection, rules)
    histories: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in collection["labels"]:
        if row["label_status"] != "final_revision":
            continue
        kickoff = row["statistics"]["kickoff_time"]
        histories[row["provider_player_id"]].append(
            {
                "event": row["event"],
                "stats": row["statistics"],
                "kickoff": kickoff,
                "available_at": (utc(kickoff) + timedelta(days=1)).isoformat(),
                "actual_available_at": row["available_at"],
            }
        )
    by_fixture = {f["id"]: f for f in fixtures}
    for frame, actual_origin in [(historical, False), (future, True)]:
        extras = []
        for row in frame.to_dict("records"):
            history = histories[row["player_id"]]
            if actual_origin:
                history = [{**h, "available_at": h["actual_available_at"]} for h in history]
            features = lag_features(history, row["decision_cutoff"], row["event"])
            features.update(opportunity_features(history, row["decision_cutoff"], row["event"]))
            fixture = by_fixture[row["fixture_id"]]
            home = row["home"] == "True"
            club, opponent = (
                (fixture["team_h"], fixture["team_a"])
                if home
                else (fixture["team_a"], fixture["team_h"])
            )
            observed = [
                f
                for f in fixtures
                if f.get("finished_provisional") is True
                and f.get("kickoff_time")
                and f.get("event", 99) < row["event"]
                and known_number(f.get("team_h_score"))
                and known_number(f.get("team_a_score"))
                and (
                    actual_origin
                    or utc(f["kickoff_time"]) + timedelta(days=1) < utc(row["decision_cutoff"])
                )
            ]
            for name, team, conceded in [
                ("club_goals_prior", club, False),
                ("opponent_conceded_prior", opponent, True),
            ]:
                recent = sorted(
                    [f for f in observed if team in (f["team_h"], f["team_a"])],
                    key=lambda f: f["kickoff_time"],
                )[-5:]
                values = [
                    f["team_a_score"] if (f["team_h"] == team) == conceded else f["team_h_score"]
                    for f in recent
                ]
                features[name] = (sum(values) + 3 * 1.3) / (len(values) + 3)
            extras.append(features)
        for column in ATTACK + DEFENCE + CONTEXT + OPPORTUNITY:
            frame[column] = [value[column] for value in extras]
    return historical, future, mappings
