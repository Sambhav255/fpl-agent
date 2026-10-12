"""Finalized official points joins and immutable scorecard revisions."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from fpl_app.contracts import Fixture, Player, ProjectionRun
from fpl_app.providers import Provider
from fpl_app.storage import Store, fingerprint

SCORING_VERSION = "official-fpl-live-total-points-v1"


def event_status(provider: Provider, event: int) -> dict[str, Any]:
    snapshot = provider.fetch("bootstrap-static/", force=True)
    payload = json.loads(snapshot["raw"])
    selected = next((row for row in payload["events"] if row.get("id") == event), None)
    if selected is None:
        raise ValueError("Event missing from official status snapshot")
    return {
        "event": event,
        "finished": selected.get("finished") is True,
        "data_checked": selected.get("data_checked") is True,
        "finalization_snapshot_id": snapshot["id"],
        "finalization_sha256": snapshot["payload_sha256"],
        "source_captured_at": snapshot["captured_at"],
        "ready": selected.get("finished") is True and selected.get("data_checked") is True,
    }


def collect_finalized_outcomes(
    store: Store,
    provider: Provider,
    decision_id: str,
    expected_finalization_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    journal = store.get("decision_journal", decision_id)
    if journal["data_mode"] != "live":
        raise ValueError("Synthetic decisions cannot ingest official outcomes")
    current = event_status(provider, journal["event"])
    if current["finalization_sha256"] != expected_finalization_sha256:
        raise ValueError("Official finalization status changed; refresh review inputs")
    if not current["ready"]:
        raise ValueError("Official event is not finalized and checked")

    fixture_snapshot = provider.fetch("fixtures/", force=True)
    fixture_payload = json.loads(fixture_snapshot["raw"])
    final_fixtures = {
        row["id"]: row
        for row in fixture_payload
        if row.get("id") is not None and row.get("event") == journal["event"]
    }
    live_snapshot = provider.fetch(f"event/{journal['event']}/live/", force=True)
    live_payload = json.loads(live_snapshot["raw"])
    result_by_player: dict[int, dict[str, Any]] = {}
    for element in live_payload["elements"]:
        points_by_fixture: dict[int, int] = {}
        minutes_by_fixture: dict[int, int] = {}
        for match in element["explain"]:
            fixture_id = match["fixture"]
            points_by_fixture[fixture_id] = sum(line["points"] for line in match["stats"])
            minutes = [
                line["value"]
                for line in match["stats"]
                if line.get("identifier") == "minutes" and type(line.get("value")) is int
            ]
            minutes_by_fixture[fixture_id] = minutes[-1] if minutes else 0
        if sum(points_by_fixture.values()) != element["stats"]["total_points"]:
            raise ValueError("Official fixture explanations do not reconcile to event points")
        if points_by_fixture and sum(minutes_by_fixture.values()) != element["stats"]["minutes"]:
            raise ValueError("Official fixture minutes do not reconcile to event minutes")
        result_by_player[element["id"]] = {
            "total_points": element["stats"]["total_points"],
            "minutes": element["stats"]["minutes"],
            "points_by_fixture": points_by_fixture,
            "minutes_by_fixture": minutes_by_fixture,
        }

    run = ProjectionRun.model_validate(journal["forecast"])
    players = [Player.model_validate(row) for row in journal["players"]]
    live_ids = set(result_by_player)
    universe = set(journal["player_universe_ids"])
    if not universe <= live_ids:
        raise ValueError("Official event results miss forecast-universe players")
    player_by_id = {player.player_id: player for player in players}
    frozen_fixtures = {
        fixture.fixture_id: fixture
        for fixture in (Fixture.model_validate(row) for row in journal["fixtures"])
        if fixture.event == journal["event"]
    }
    forecasts: dict[int, float] = defaultdict(float)
    forecast_fixtures: dict[int, set[int]] = defaultdict(set)
    for projection in run.projections:
        if projection.event == journal["event"]:
            forecasts[projection.player_id] += projection.expected_points
            forecast_fixtures[projection.player_id].add(projection.fixture_id)

    outcome_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    for player_id in sorted(universe):
        player = player_by_id[player_id]
        scheduled = {
            fixture.fixture_id
            for fixture in frozen_fixtures.values()
            if player.club in (fixture.home_club, fixture.away_club)
        }
        coverage = forecast_fixtures.get(player_id, set())
        if coverage != scheduled:
            raise ValueError("Frozen forecast coverage differs from its event fixture schedule")
        if not scheduled:
            outcome_rows.append(
                {
                    "player_id": player_id,
                    "event": journal["event"],
                    "fixture_ids": [],
                    "status": "blank_event",
                    "points": 0,
                    "minutes": 0,
                    "appearance": 0,
                    "forecast_points": 0.0,
                }
            )
            score_rows.append(
                {
                    "player_id": player_id,
                    "event": journal["event"],
                    "forecast_points": 0.0,
                    "actual_points": 0,
                    "forecast_appearance": None,
                    "actual_appearance": 0,
                    "minutes": 0,
                }
            )
            continue
        points_total = 0
        minutes_total = 0
        row_status = "final"
        fixture_rows = []
        for fixture_id in sorted(scheduled):
            final_fixture = final_fixtures.get(fixture_id)
            if final_fixture is None:
                row_status = "fixture_reassigned_or_schedule_unknown"
                fixture_rows.append({"fixture_id": fixture_id, "status": row_status})
                continue
            if final_fixture.get("finished") is not True:
                row_status = "fixture_pending"
                fixture_rows.append({"fixture_id": fixture_id, "status": row_status})
                continue
            points = result_by_player[player_id]["points_by_fixture"].get(fixture_id, 0)
            minutes = result_by_player[player_id]["minutes_by_fixture"].get(fixture_id, 0)
            points_total += points
            minutes_total += minutes
            fixture_rows.append(
                {
                    "fixture_id": fixture_id,
                    "status": "final" if minutes > 0 else "final_nonappearance",
                    "points": points,
                    "minutes": minutes,
                }
            )
        outcome = {
            "player_id": player_id,
            "event": journal["event"],
            "fixture_ids": sorted(scheduled),
            "status": row_status,
            "points": points_total if row_status == "final" else None,
            "minutes": minutes_total if row_status == "final" else None,
            "appearance": int(minutes_total > 0) if row_status == "final" else None,
            "forecast_points": forecasts.get(player_id),
            "fixtures": fixture_rows,
        }
        outcome_rows.append(outcome)
        if row_status == "final" and outcome["forecast_points"] is not None:
            score_rows.append(
                {
                    "player_id": player_id,
                    "event": journal["event"],
                    "forecast_points": outcome["forecast_points"],
                    "actual_points": points_total,
                    "forecast_appearance": _forecast_appearance(run, player_id, journal["event"]),
                    "actual_appearance": int(minutes_total > 0),
                    "minutes": minutes_total,
                }
            )
    revision_digest = fingerprint(
        {
            "decision_id": decision_id,
            "finalization_sha256": current["finalization_sha256"],
            "fixture_sha256": fixture_snapshot["payload_sha256"],
            "live_sha256": live_snapshot["payload_sha256"],
            "outcomes": outcome_rows,
            "scoring_version": SCORING_VERSION,
        }
    )
    if not score_rows:
        raise ValueError("No finalized outcomes overlap frozen forecast coverage")
    errors = [row["forecast_points"] - row["actual_points"] for row in score_rows]
    appearance_pairs = [
        (row["forecast_appearance"], row["actual_appearance"])
        for row in score_rows
        if row["forecast_appearance"] is not None
    ]
    metrics = {
        "n": len(score_rows),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": (sum(error * error for error in errors) / len(errors)) ** 0.5,
        "bias_forecast_minus_actual": sum(errors) / len(errors),
        "appearance_brier": (
            sum((probability - actual) ** 2 for probability, actual in appearance_pairs)
            / len(appearance_pairs)
            if appearance_pairs
            else None
        ),
        "appearance_n": len(appearance_pairs),
        "realized_player_event_points": sum(row["actual_points"] for row in score_rows),
        "coverage_status_counts": _status_counts(outcome_rows),
        "claim": "frozen forecast scorecard; one finalized event, not a model promotion test",
    }
    outcome_revision = {
        "decision_id": decision_id,
        "event": journal["event"],
        "revision": revision_digest,
        "finalization_source": {
            key: current[key]
            for key in ("finalization_snapshot_id", "finalization_sha256", "source_captured_at")
        },
        "fixture_source_snapshot_id": fixture_snapshot["id"],
        "fixture_source_sha256": fixture_snapshot["payload_sha256"],
        "live_source_snapshot_id": live_snapshot["id"],
        "live_source_sha256": live_snapshot["payload_sha256"],
        "scoring_version": SCORING_VERSION,
        "outcomes": outcome_rows,
        "scores": score_rows,
        "captured_at": live_snapshot["captured_at"],
    }
    scorecard = {
        "decision_id": decision_id,
        "event": journal["event"],
        "revision": revision_digest,
        "outcome_revision": revision_digest,
        "created_at": live_snapshot["captured_at"],
        "metrics": metrics,
        "frozen_forecast_sha256": journal["forecast_sha256"],
        "policy_reference": journal["policy_reference"],
        "evidence_mode": journal["evidence_mode"],
    }
    return outcome_revision, scorecard


def _forecast_appearance(run: ProjectionRun, player_id: int, event: int) -> float | None:
    rows = [
        projection
        for projection in run.projections
        if projection.player_id == player_id and projection.event == event
    ]
    values = [row.appearance_probability for row in rows]
    if not values or any(value is None for value in values):
        return None
    # Fixture appearance probabilities do not combine into an event probability.
    if len(values) == 1:
        return float(values[0]) if values[0] is not None else None
    return None


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts
