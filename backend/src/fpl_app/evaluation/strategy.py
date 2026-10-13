"""Bounded offline policy replay. Outcomes are never supplied to a policy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fpl_app.contracts import ManagerState, Player, ProjectionRun, Settings
from fpl_app.domain.plans import _check_inputs, validate_plan
from fpl_app.domain.rules import (
    MatchStats,
    OfficialEventPoints,
    advance_event,
    apply_transfers,
    readiness,
    score_lineup,
    score_official_lineup,
)
from fpl_app.evaluation.provenance import replay_time, verify_replay_manifest
from fpl_app.optimisation.planner import recommend


@dataclass
class ReplayOrigin:
    deadline: str
    information_available_at: str
    players: list[Player]
    forecasts: ProjectionRun
    outcomes: dict[int, list[MatchStats]]
    evidence_mode: str = "retrospective_assumed"
    financial_coverage: str = "assumed_frozen_prices"
    manifest_path: Path | None = None
    manifest_sha256: str | None = None
    # Simulated label availability, not today's artifact publication time.
    fitting_labels_available_at: str | None = None
    # Set by the journal bridge from immutable retained references.
    journal_reference: dict[str, str] | None = None
    # Official totals are an alternative to complete reconstructed components.
    # Neither form is exposed to a policy; missing coverage remains an error.
    official_outcomes: dict[int, OfficialEventPoints] | None = None


Policy = Callable[[ManagerState, list[Player], ProjectionRun, Settings], Any]


def keep_policy(state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings):
    return recommend(state, players, run, settings, lineup_only=True).baseline_plan


def planner_policy(
    state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings
):
    result = recommend(state, players, run, settings)
    return max([result.baseline_plan] + result.alternatives, key=lambda p: p.net_points)


def proxy_planner_policy(
    state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings
):
    """Original squad objective comparator, on identical forecasts and replay rules."""
    result = recommend(state, players, run, settings, candidate_mode="squad_proxy")
    return max([result.baseline_plan] + result.alternatives, key=lambda p: p.net_points)


def greedy_policy(
    state: ManagerState, players: list[Player], run: ProjectionRun, settings: Settings
):
    return planner_policy(
        state,
        players,
        run,
        settings.model_copy(update={"horizon_events": 1, "max_transfers_this_event": 1}),
    )


def replay_policy(
    initial: ManagerState, origins: list[ReplayOrigin], policy: Policy, settings: Settings
) -> dict[str, Any]:
    if not origins or len(origins) > 38:
        raise ValueError("Replay requires between one and 38 origins")
    current = initial.model_copy(deep=True)
    rows = []
    previous_deadline: datetime | None = None
    for offset, origin in enumerate(origins):
        deadline = replay_time(origin.deadline)
        available = replay_time(origin.information_available_at)
        cutoff = replay_time(origin.forecasts.source_cutoff)
        if (
            available > deadline
            or cutoff > available
            or previous_deadline
            and deadline <= previous_deadline
        ):
            raise ValueError("Future or noncontiguous information origin")
        previous_deadline = deadline
        current.snapshot_id = origin.forecasts.snapshot_id
        horizon = min(
            settings.horizon_events, origin.forecasts.horizon_events, 39 - current.next_event
        )
        # Greedy is deliberately myopic; other policies get the full supported path.
        local_settings = settings.model_copy(
            update={
                "horizon_events": 1 if policy is greedy_policy else horizon,
                **({"max_transfers_this_event": 1} if policy is greedy_policy else {}),
            }
        )
        provenance = _check_provenance(origin, current.next_event, local_settings, policy)
        _check_inputs(current, origin.players, origin.forecasts, local_settings)
        if not readiness(current, origin.players)["transfers_ready"]:
            raise ValueError("Unknown finances: financial replay unavailable")
        # Pass isolated inputs, without target outcomes or subsequent origin snapshots.
        plan = policy(
            current.model_copy(deep=True),
            [p.model_copy(deep=True) for p in origin.players],
            origin.forecasts.model_copy(deep=True),
            local_settings.model_copy(deep=True),
        )
        # Policies must return a plan bound to these exact settings and origin.
        validation_settings = local_settings
        baseline = keep_policy(current, origin.players, origin.forecasts, validation_settings)
        errors = validate_plan(
            plan, current, origin.players, origin.forecasts, validation_settings, baseline
        )
        if errors:
            raise ValueError("Invalid policy plan: " + "; ".join(errors))
        week = plan.weeks[0]
        changed, _ = apply_transfers(current, origin.players, week["actions"], week["chip"])
        ids = {p.player_id for p in changed.picks}
        outcomes = (
            origin.official_outcomes if origin.official_outcomes is not None else origin.outcomes
        )
        if not ids <= outcomes.keys():
            raise ValueError("Missing outcome coverage; absence cannot be assumed")
        scored = (
            score_official_lineup(
                week["lineup"], changed, origin.players, origin.official_outcomes, week["chip"]
            )
            if origin.official_outcomes is not None
            else score_lineup(
                week["lineup"], changed, origin.players, origin.outcomes, week["chip"]
            )
        )
        rows.append(
            {
                "event": current.next_event,
                "forecast_net_points": week["net_points"],
                "realised_net_points": scored["points"] - week["total_hits"],
                "hits": week["total_hits"],
                "transfers": len(week["actions"]),
                "actions": week["actions"],
                "bank_units": changed.bank_units,
                "scoring": scored,
                "deadline": origin.deadline,
                "information_available_at": origin.information_available_at,
                "evidence_mode": origin.evidence_mode,
                "financial_coverage": origin.financial_coverage,
                "planning_horizon_events": local_settings.horizon_events,
                "forecast_path_net_points": plan.net_points,
                "plan_input_fingerprint": plan.input_fingerprint,
                "provenance": provenance,
            }
        )
        current = advance_event(changed) if offset + 1 < len(origins) else changed
    return {
        "rows": rows,
        "realised_net_points": sum(r["realised_net_points"] for r in rows),
        "forecast_net_points": sum(r["forecast_net_points"] for r in rows),
        "legal": True,
        "final_state": current.model_dump(),
        "limitations": [
            "Only the first planned event executes; subsequent events replan from their own origins",
            "Retained strict timestamps are local capture evidence, not external timestamp attestation",
            "Reconstructed, synthetic and legacy assumed origins are not prospective evidence",
            "Full supplied MatchStats required; missing statistics are not reconstructed",
            "No rank or realistic historical financial coverage claim",
        ],
    }


def _check_provenance(
    origin: ReplayOrigin, event: int, settings: Settings, policy: Policy
) -> dict[str, Any]:
    mode = origin.evidence_mode
    if mode == "prospective_strict":
        if origin.manifest_path is None or origin.manifest_sha256 is None:
            raise ValueError("Strict replay requires a frozen manifest reference")
        hashes = verify_replay_manifest(
            origin.manifest_path,
            origin.manifest_sha256,
            origin.forecasts,
            origin.players,
            origin.deadline,
            origin.information_available_at,
            list(range(event, event + settings.horizon_events)),
            policy,
        )
        return {
            "verified": True,
            "manifest_sha256": origin.manifest_sha256,
            "artifacts": hashes,
            **({"journal_reference": origin.journal_reference} if origin.journal_reference else {}),
        }
    if mode == "historical_reconstructed":
        if origin.fitting_labels_available_at is None:
            raise ValueError("Reconstructed replay requires simulated fitting label cutoff")
        if replay_time(origin.fitting_labels_available_at) > replay_time(
            origin.information_available_at
        ):
            raise ValueError("Future reconstructed fitting labels")
        if origin.forecasts.prediction_origin is None:
            raise ValueError("Reconstructed replay requires actual prediction origin")
        replay_time(origin.forecasts.prediction_origin)
        return {
            "verified": False,
            "actual_prediction_origin": origin.forecasts.prediction_origin,
            "simulated_information_origin": origin.information_available_at,
            "simulated_fitting_labels_available_at": origin.fitting_labels_available_at,
        }
    if mode not in {"retrospective_assumed", "synthetic_mechanics"}:
        raise ValueError("Unsupported replay evidence mode")
    return {"verified": False, "timing": "caller_asserted"}


def compare_policies(
    starts: list[ManagerState],
    origins: list[ReplayOrigin],
    policies: dict[str, Policy],
    settings: Settings,
) -> dict[str, Any]:
    if "keep" not in policies or not starts:
        raise ValueError("Comparison requires starts and named keep comparator")
    results = []
    for index, start in enumerate(starts):
        reports = {
            name: replay_policy(start, origins, policy, settings)
            for name, policy in policies.items()
        }
        base = reports["keep"]["realised_net_points"]
        results.append(
            {
                "start_index": index,
                "reports": reports,
                "paired_incremental_points": {
                    name: report["realised_net_points"] - base for name, report in reports.items()
                },
            }
        )
    return {"comparator": "keep", "starts": results}
