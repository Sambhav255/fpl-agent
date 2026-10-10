"""Solver-independent input checks, points reconciliation and transfer replay."""

from __future__ import annotations

import json
from hashlib import sha256
from math import isclose, isfinite
from typing import Any

from fpl_app.contracts import ManagerState, Plan, Player, ProjectionRun, Settings
from fpl_app.domain.rules import (
    RULES,
    advance_event,
    apply_transfers,
    player_map,
    projection_points,
    readiness,
    select_lineup,
    transfer_accounting,
    validate_chip,
    validate_lineup,
)


def input_fingerprint(
    state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings
) -> str:
    payload = {
        "state": state.model_dump(),
        "players": [p.model_dump() for p in sorted(players, key=lambda p: p.player_id)],
        "run": run.model_dump(),
        "settings": settings.model_dump(),
    }
    return sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _check_inputs(
    state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings
) -> None:
    if (
        state.snapshot_id != run.snapshot_id
        or state.data_mode != run.data_mode
        or run.rules_version != RULES.version
    ):
        raise ValueError("Stale snapshot, mode or rules")
    if (
        state.season != RULES.season
        or settings.horizon_events > run.horizon_events
        or state.next_event + settings.horizon_events - 1 > 38
    ):
        raise ValueError("Unsupported season or forecast horizon")
    if not readiness(state, players)["lineup_ready"]:
        raise ValueError("Invalid squad")
    ids = set(player_map(players))
    locks, excluded = set(settings.locked_player_ids), set(settings.excluded_player_ids)
    if (
        locks & excluded
        or not (locks | excluded) <= ids
        or not locks <= {p.player_id for p in state.picks}
    ):
        raise ValueError("Invalid locks or exclusions")
    projection_points(run.projections, state.next_event)
    if any(p.player_id not in ids for p in run.projections):
        raise ValueError("Unknown projected player")
    by_id = player_map(players)
    coverage = {(p.player_id, p.fixture_id, p.event) for p in run.projections}
    schedules: dict[int, set[tuple[int, int]]] = {}
    if run.fixtures:
        fixtures = {f.fixture_id: f for f in run.fixtures}
        if len(fixtures) != len(run.fixtures):
            raise ValueError("Duplicate frozen fixture")
        for fixture in run.fixtures:
            if fixture.event is not None:
                for club in (fixture.home_club, fixture.away_club):
                    schedules.setdefault(club, set()).add((fixture.fixture_id, fixture.event))
        for projection in run.projections:
            projected_fixture = fixtures.get(projection.fixture_id)
            if (
                projected_fixture is None
                or projected_fixture.event != projection.event
                or by_id[projection.player_id].club
                not in (projected_fixture.home_club, projected_fixture.away_club)
            ):
                raise ValueError("Projection disagrees with frozen fixture schedule")
    else:
        for projection in run.projections:
            schedules.setdefault(by_id[projection.player_id].club, set()).add(
                (projection.fixture_id, projection.event)
            )
    for player in players:
        for fixture_id, event in schedules.get(player.club, set()):
            if (
                state.next_event <= event < state.next_event + settings.horizon_events
                and (player.player_id, fixture_id, event) not in coverage
            ):
                raise ValueError(
                    f"Missing scheduled projection for player {player.player_id}, fixture {fixture_id}"
                )


def _week(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    chip: str | None,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    chip_errors = validate_chip(state, chip)
    if chip_errors:
        raise ValueError("; ".join(chip_errors))
    lineup = select_lineup(state, players, run.projections, state.next_event, chip)
    accounting = None
    if (
        state.free_transfers_at_event_start is not None
        and state.transfers_made_this_event is not None
    ):
        accounting = transfer_accounting(
            state.free_transfers_at_event_start, state.transfers_made_this_event, chip=chip
        )
    hits = state.confirmed_hit_points or 0
    if chip in {"wildcard", "free_hit"}:
        hits = 0
    return {
        "event": state.next_event,
        "actions": actions,
        "chip": chip,
        "lineup": lineup,
        "squad_ids": [p.player_id for p in state.picks],
        "bank_units": state.bank_units,
        "free_transfers_at_event_start": state.free_transfers_at_event_start,
        "transfers_made": state.transfers_made_this_event,
        "free_transfers_next": accounting["free_transfers_next"] if accounting else None,
        "gross_points": lineup["expected_points"],
        "total_hits": hits,
        "net_points": lineup["expected_points"] - hits,
    }


def validate_plan(
    plan: Plan,
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    baseline: Plan | None = None,
    enforce_preferences: bool = True,
) -> list[str]:
    """Replay from original state without consulting any solver variables."""
    errors: list[str] = []
    if (
        plan.state_version != state.state_version
        or plan.projection_run_id != run.projection_run_id
        or plan.input_fingerprint != input_fingerprint(state, players, run, settings)
    ):
        errors.append("Stale plan fingerprint or version")
    if len(plan.weeks) != settings.horizon_events:
        return errors + ["Incomplete horizon"]
    current = state.model_copy(deep=True)
    gross, hits = 0.0, 0
    newly_incurred_hits = 0
    for offset, week in enumerate(plan.weeks):
        try:
            chip = week.get("chip")
            expected_chip = state.current_chip if offset == 0 else None
            if enforce_preferences and offset == 0 and settings.chip_policy != "none":
                expected_chip = settings.chip_policy
            if chip != expected_chip:
                raise ValueError("Unexpected chip or event")
            if week.get("event") != current.next_event:
                raise ValueError("Noncontiguous events")
            chip_errors = validate_chip(current, chip)
            if chip_errors:
                raise ValueError("; ".join(chip_errors))
            actions = week.get("actions", [])
            if actions or chip and chip != current.current_chip:
                current, ledger = apply_transfers(current, players, actions, chip)
                for actual, recorded in zip(ledger, actions, strict=True):
                    if any(recorded.get(k) != v for k, v in actual.items()):
                        raise ValueError("Transfer ledger mismatch")
            lineup_errors = validate_lineup(week["lineup"], current, players)
            if lineup_errors:
                raise ValueError("; ".join(lineup_errors))
            if enforce_preferences:
                ids = {p.player_id for p in current.picks}
                if not set(settings.locked_player_ids) <= ids or ids & set(
                    settings.excluded_player_ids
                ):
                    raise ValueError("Lock or exclusion violation")
            expected = _week(current, players, run, chip, actions)
            for key in (
                "squad_ids",
                "bank_units",
                "free_transfers_next",
                "free_transfers_at_event_start",
                "transfers_made",
                "total_hits",
            ):
                if week.get(key) != expected[key]:
                    raise ValueError(f"Replay mismatch: {key}")
            # Recompute supplied lineup objective directly, independent of its optimiser.
            xp = projection_points(run.projections, current.next_event)
            lineup = week["lineup"]
            score_ids = lineup["starters"] + (lineup["bench"] if chip == "bench_boost" else [])
            score = sum(xp.get(i, 0) for i in score_ids) + (
                2 if chip == "triple_captain" else 1
            ) * xp.get(lineup["captain"], 0)
            if (
                not isclose(score, week["gross_points"], abs_tol=1e-7)
                or not isclose(score - expected["total_hits"], week["net_points"], abs_tol=1e-7)
                or not isclose(score, lineup["expected_points"], abs_tol=1e-7)
            ):
                raise ValueError("Weekly points mismatch")
            gross += score
            hits += expected["total_hits"]
            prior_hits = (state.confirmed_hit_points or 0) if offset == 0 else 0
            newly_incurred_hits += max(0, expected["total_hits"] - prior_hits)
            if offset + 1 < settings.horizon_events:
                current = advance_event(current)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
            return errors
    if plan.actions != [a for week in plan.weeks for a in week["actions"]]:
        errors.append("Top-level actions mismatch")
    if (
        plan.lineup != plan.weeks[0]["lineup"]
        or plan.bank_units != plan.weeks[0]["bank_units"]
        or plan.free_transfers_next != plan.weeks[0]["free_transfers_next"]
        or plan.chip != plan.weeks[0]["chip"]
    ):
        errors.append("Top-level state mismatch")
    if (
        not all(isfinite(v) for v in (plan.gross_points, plan.net_points, plan.delta_to_baseline))
        or not isclose(gross, plan.gross_points, abs_tol=1e-7)
        or hits != plan.total_hits
        or not isclose(gross - hits, plan.net_points, abs_tol=1e-7)
    ):
        errors.append("Plan totals mismatch")
    reference_hits = baseline.total_hits if baseline else plan.total_hits
    if plan.incremental_hits != hits - reference_hits:
        errors.append("Incremental hits mismatch")
    if baseline and (
        newly_incurred_hits > settings.max_additional_hit_points
        or not isclose(plan.delta_to_baseline, plan.net_points - baseline.net_points, abs_tol=1e-7)
    ):
        errors.append("Hit budget or delta mismatch")
    if (
        plan.weeks
        and plan.this_week_net is not None
        and (
            not isfinite(plan.this_week_net)
            or not isclose(plan.this_week_net, float(plan.weeks[0]["net_points"]), abs_tol=1e-7)
        )
    ):
        errors.append("This week net mismatch")
    if plan.this_week_delta is not None:
        if baseline is None:
            expected_delta = 0.0
        else:
            expected_delta = float(plan.weeks[0]["net_points"]) - float(
                baseline.weeks[0]["net_points"]
            )
        if not isfinite(plan.this_week_delta) or not isclose(
            plan.this_week_delta, expected_delta, abs_tol=1e-7
        ):
            errors.append("This week delta mismatch")
    if (
        settings.max_transfers_this_event is not None
        and plan.weeks
        and len(plan.weeks[0].get("actions", [])) > settings.max_transfers_this_event
    ):
        errors.append("This week transfer cap exceeded")
    return errors
