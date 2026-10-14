"""Finalized official points joins and immutable scorecard revisions."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from fpl_app.contracts import Fixture, Player, ProjectionRun
from fpl_app.providers import Provider
from fpl_app.storage import Store, fingerprint

SCORING_VERSION = "official-fpl-live-total-points-v2"


def event_status(provider: Provider, event: int) -> dict[str, Any]:
    snapshot = provider.fetch("bootstrap-static/", force=True)
    payload = json.loads(snapshot["raw"])
    _integer(event, "event", minimum=1)
    matching = [row for row in payload["events"] if row.get("id") == event]
    if len(matching) != 1 or type(matching[0].get("id")) is not int:
        raise ValueError("Event missing or duplicated in official status snapshot")
    selected = matching[0]
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
    live_snapshot = provider.fetch(f"event/{journal['event']}/live/", force=True)
    live_payload = json.loads(live_snapshot["raw"])
    outcome_rows, score_rows = build_finalized_outcomes(
        journal, current, fixture_payload, live_payload
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
        if row["forecast_appearance"] is not None and row["actual_appearance"] is not None
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


def _integer(value: Any, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int or minimum is not None and value < minimum:
        raise ValueError(f"Invalid official {name}")
    return value


def build_finalized_outcomes(
    journal: dict[str, Any],
    status: dict[str, Any],
    fixture_payload: list[dict[str, Any]],
    live_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reconcile retained official totals; missing fixture statistics stay missing.

    Event totals can be scored when fixture explanations reconcile but participation
    is unknown. Such rows never invent absence and are gated by the replay adapter.
    A changed schedule is excluded even when a previously blank club now plays.
    """
    event = _integer(journal["event"], "event", minimum=1)
    if status.get("event") != event or status.get("ready") is not True:
        raise ValueError("Official event is not finalized and checked")
    final_fixtures: dict[int, dict[str, Any]] = {}
    seen_fixtures: set[int] = set()
    for row in fixture_payload:
        identifier = _integer(row.get("id"), "fixture ID", minimum=1)
        if identifier in seen_fixtures:
            raise ValueError("Duplicate official fixture")
        seen_fixtures.add(identifier)
        if row.get("event") == event:
            _integer(row.get("event"), "fixture event", minimum=1)
            _integer(row.get("team_h"), "home club", minimum=1)
            _integer(row.get("team_a"), "away club", minimum=1)
            if row["team_h"] == row["team_a"]:
                raise ValueError("Invalid official fixture clubs")
            final_fixtures[identifier] = row
    result_by_player: dict[int, dict[str, Any]] = {}
    for element in live_payload["elements"]:
        identifier = _integer(element.get("id"), "player ID", minimum=1)
        if identifier in result_by_player:
            raise ValueError("Duplicate official player result")
        stats = element["stats"]
        total_points = _integer(stats.get("total_points"), "event points")
        total_minutes = _integer(stats.get("minutes"), "event minutes", minimum=0)
        cards: dict[str, int | None] = {}
        for key in ("yellow_cards", "red_cards"):
            cards[key] = (
                _integer(stats[key], key, minimum=0) if stats.get(key) is not None else None
            )
        explained_cards = {key: 0 for key in cards}
        points_by_fixture: dict[int, int] = {}
        minutes_by_fixture: dict[int, int | None] = {}
        for match in element["explain"]:
            fixture_id = _integer(match.get("fixture"), "explanation fixture ID", minimum=1)
            if fixture_id in points_by_fixture:
                raise ValueError("Duplicate official fixture explanation")
            if fixture_id not in final_fixtures:
                raise ValueError("Official explanation refers to a different event fixture")
            points = 0
            minutes: int | None = None
            identifiers: set[str] = set()
            for line in match["stats"]:
                name = line.get("identifier")
                if not isinstance(name, str) or name in identifiers:
                    raise ValueError("Duplicate or invalid official statistic identifier")
                identifiers.add(name)
                points += _integer(line.get("points"), "fixture points")
                if name == "minutes":
                    minutes = _integer(line.get("value"), "fixture minutes", minimum=0)
                elif name in cards:
                    explained_cards[name] += _integer(line.get("value"), name, minimum=0)
            points_by_fixture[fixture_id] = points
            minutes_by_fixture[fixture_id] = minutes
        for key, explained in explained_cards.items():
            total_cards = cards[key]
            if total_cards is not None and explained > total_cards:
                raise ValueError("Official fixture cards do not reconcile to event cards")
        if sum(points_by_fixture.values()) != total_points:
            raise ValueError("Official fixture explanations do not reconcile to event points")
        known_minutes = [v for v in minutes_by_fixture.values() if v is not None]
        if (
            sum(known_minutes) > total_minutes
            or (
                minutes_by_fixture
                and len(known_minutes) == len(minutes_by_fixture)
                and sum(known_minutes) != total_minutes
            )
            or not points_by_fixture
            and total_minutes != 0
        ):
            raise ValueError("Official fixture minutes do not reconcile to event minutes")
        participation = (
            1
            if total_minutes > 0 or any(value for value in cards.values())
            else 0
            if all(value == 0 for value in cards.values()) and total_points == 0
            else None
        )
        result_by_player[identifier] = {
            "total_points": total_points,
            "minutes": total_minutes,
            "cards": cards,
            "appearance": participation,
            "points_by_fixture": points_by_fixture,
            "minutes_by_fixture": minutes_by_fixture,
        }
    universe = {
        _integer(identifier, "frozen player ID", minimum=1)
        for identifier in journal["player_universe_ids"]
    }
    if len(universe) != len(journal["player_universe_ids"]):
        raise ValueError("Duplicate frozen universe player")
    if not universe <= result_by_player.keys():
        raise ValueError("Official event results miss forecast-universe players")
    run = ProjectionRun.model_validate(journal["forecast"])
    players = [Player.model_validate(row) for row in journal["players"]]
    player_by_id = {player.player_id: player for player in players}
    if len(player_by_id) != len(players) or set(player_by_id) != universe:
        raise ValueError("Frozen player mapping differs from forecast universe")
    frozen = [Fixture.model_validate(row) for row in journal["fixtures"]]
    if len({f.fixture_id for f in frozen}) != len(frozen):
        raise ValueError("Duplicate frozen fixture")
    forecasts: dict[int, float] = defaultdict(float)
    coverage: dict[int, set[int]] = defaultdict(set)
    for projection in run.projections:
        if projection.event == event:
            if projection.fixture_id in coverage[projection.player_id]:
                raise ValueError("Duplicate frozen forecast fixture")
            forecasts[projection.player_id] += projection.expected_points
            coverage[projection.player_id].add(projection.fixture_id)
    outcome_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    for player_id in sorted(universe):
        player = player_by_id[player_id]
        scheduled = {
            f.fixture_id
            for f in frozen
            if f.event == event and player.club in (f.home_club, f.away_club)
        }
        actual = {
            identifier
            for identifier, f in final_fixtures.items()
            if player.club in (f["team_h"], f["team_a"])
        }
        if coverage.get(player_id, set()) != scheduled:
            raise ValueError("Frozen forecast coverage differs from its event fixture schedule")
        result = result_by_player[player_id]
        row_status = "final" if scheduled else "blank_event"
        if scheduled != actual or any(
            (f.home_club, f.away_club)
            != (final_fixtures[f.fixture_id]["team_h"], final_fixtures[f.fixture_id]["team_a"])
            for f in frozen
            if f.fixture_id in scheduled & actual
        ):
            row_status = "fixture_reassigned_or_schedule_unknown"
        elif any(final_fixtures[i].get("finished") is not True for i in actual):
            row_status = "fixture_pending"
        elif not set(result["points_by_fixture"]) <= actual:
            row_status = "player_fixture_membership_unknown"
        elif not scheduled and (
            result["total_points"] != 0 or result["minutes"] != 0 or result["appearance"] != 0
        ):
            row_status = "blank_participation_unknown"
        fixture_rows = []
        for fixture_id in sorted(scheduled):
            reported = fixture_id in result["points_by_fixture"]
            known_absence = result["appearance"] == 0
            fixture_rows.append(
                {
                    "fixture_id": fixture_id,
                    "status": "final_nonappearance"
                    if known_absence
                    else "final"
                    if reported
                    else "missing_fixture_explanation",
                    "points": result["points_by_fixture"].get(
                        fixture_id, 0 if known_absence else None
                    ),
                    "minutes": result["minutes_by_fixture"].get(
                        fixture_id, 0 if known_absence else None
                    ),
                }
            )
        scoreable = row_status in {"final", "blank_event"}
        outcome = {
            "player_id": player_id,
            "event": event,
            "fixture_ids": sorted(scheduled),
            "actual_fixture_ids": sorted(actual),
            "status": row_status,
            "points": result["total_points"] if scoreable else None,
            "minutes": result["minutes"] if scoreable else None,
            "appearance": result["appearance"] if scoreable else None,
            "participation_status": "verified"
            if result["appearance"] is not None
            else "missing_cards_or_ambiguous_zero_minutes",
            "yellow_cards": result["cards"]["yellow_cards"],
            "red_cards": result["cards"]["red_cards"],
            "forecast_points": forecasts.get(player_id, 0.0 if not scheduled else None),
            "fixtures": fixture_rows,
        }
        if not scoreable:
            outcome["fixtures"] = [
                {"fixture_id": identifier, "status": row_status, "points": None, "minutes": None}
                for identifier in sorted(scheduled)
            ]
        outcome_rows.append(outcome)
        if scoreable and outcome["forecast_points"] is not None:
            score_rows.append(
                {
                    "player_id": player_id,
                    "event": event,
                    "forecast_points": outcome["forecast_points"],
                    "actual_points": result["total_points"],
                    "forecast_appearance": _forecast_appearance(run, player_id, event),
                    "actual_appearance": result["appearance"],
                    "minutes": result["minutes"],
                }
            )
    return outcome_rows, score_rows


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
