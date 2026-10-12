"""Deadline-frozen decisions and append-only execution reports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fpl_app.contracts import ProjectionRun, Recommendation
from fpl_app.jobs import inputs
from fpl_app.storage import Conflict, Store, fingerprint, utcnow


def freeze_decision(
    store: Store,
    recommendation: Recommendation,
    recommendation_input: dict[str, Any],
    deadline: str,
    idempotency_key: str,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Persist the recommendation, coverage and all proposed actions as immutable."""
    if not 1 <= len(idempotency_key) <= 128:
        raise ValueError("Idempotency key must contain 1 to 128 characters")
    payload = recommendation_input["payload"]
    team_id = payload["team_id"]
    run = ProjectionRun.model_validate(store.get("projection", payload["projection_run_id"]))
    data = store.get("dataset", run.snapshot_id)
    event_id = payload.get("event", data["next_event"])
    decision_id = fingerprint(
        {"team_id": team_id, "event": event_id, "idempotency_key": idempotency_key}
    )
    try:
        existing = store.get("decision_journal", decision_id)
        if existing["input_fingerprint"] != recommendation_input["fingerprint"]:
            raise Conflict("Decision idempotency key already binds another recommendation")
        return existing
    except KeyError:
        pass
    frozen_at = captured_at or utcnow()
    origin = datetime.fromisoformat(frozen_at)
    cutoff = datetime.fromisoformat(run.source_cutoff)
    deadline_at = datetime.fromisoformat(deadline)
    if any(value.tzinfo is None for value in (origin, cutoff, deadline_at)):
        raise ValueError("Decision and source times require timezone")
    if cutoff > origin or origin >= deadline_at:
        raise ValueError("Decision must freeze after its sources and before its deadline")
    if recommendation.state_version != payload["expected_state_version"]:
        raise Conflict("Recommendation state version mismatch")
    if recommendation.projection_run_id != run.projection_run_id:
        raise Conflict("Recommendation forecast reference mismatch")
    candidates = [recommendation.baseline_plan, *recommendation.alternatives]
    if recommendation.gameweek_optimum is not None:
        candidates.append(recommendation.gameweek_optimum)
    # De-duplicate the same proposal while preserving the original candidate order.
    by_id = {candidate.plan_id: candidate for candidate in candidates}
    candidates = list(by_id.values())
    selected = max(candidates, key=lambda candidate: candidate.net_points)
    player_by_id = {player["player_id"]: player for player in data["players"]}
    covered_ids = run.player_universe_ids or sorted(player_by_id)
    if not set(covered_ids) <= player_by_id.keys():
        raise Conflict("Frozen forecast universe is absent from the source catalogue")
    if run.data_mode == "live" and not any(
        event.get("id") == event_id and event.get("deadline_time") == deadline
        for event in data.get("events", [])
    ):
        raise Conflict("Deadline is not bound to the forecast source snapshot")
    if run.data_mode == "live" and not run.fixtures:
        raise Conflict("Live decision freeze requires an explicit forecast fixture schedule")
    decision_id = fingerprint(
        {
            "team_id": team_id,
            "event": event_id,
            "idempotency_key": idempotency_key,
        }
    )
    journal = {
        "decision_id": decision_id,
        "season": data.get("season", "2026/27"),
        "event": event_id,
        "team_id": team_id,
        "decision_origin": frozen_at,
        "deadline": deadline,
        "state_version": recommendation.state_version,
        "input_fingerprint": recommendation_input["fingerprint"],
        "snapshot_id": run.snapshot_id,
        "forecast_reference": run.projection_run_id,
        "policy_reference": run.resolved_provider,
        "policy_artifact_id": run.artifact_id,
        "policy_artifact_manifest_sha256": run.artifact_manifest_sha256,
        "candidate_set_reference": fingerprint(
            [candidate.model_dump() for candidate in candidates]
        ),
        "candidate_plans": [candidate.model_dump() for candidate in candidates],
        "recommended_action_id": selected.plan_id,
        "recommendation_id": recommendation.recommendation_id,
        "execution_status": "execution_unknown",
        "execution_action_id": None,
        "paper_portfolio_action_id": None,
        "evidence_mode": "prospective_shadow" if run.data_mode == "live" else "synthetic_demo",
        "data_mode": run.data_mode,
        "source_cutoff": run.source_cutoff,
        "rules_version": run.rules_version,
        "forecast_sha256": fingerprint(run.model_dump(mode="json")),
        "player_universe_ids": covered_ids,
        "players": [player_by_id[player_id] for player_id in covered_ids],
        "forecast": run.model_dump(mode="json"),
        "fixtures": [
            fixture
            for fixture in data["fixtures"]
            if fixture.get("event") is not None
            and event_id <= fixture["event"] < event_id + run.horizon_events
        ],
        "manager_state": store.get("state", team_id),
        "settings": payload["settings"],
        "frozen_at": frozen_at,
    }
    store.put_checked(
        "decision_journal",
        decision_id,
        journal,
        lambda: _verify_freeze_inputs(
            store, recommendation.recommendation_id, recommendation_input
        ),
        same=lambda existing, proposed: (
            existing["recommendation_id"] == proposed["recommendation_id"]
        ),
    )
    return store.get("decision_journal", decision_id)


def _verify_freeze_inputs(store: Store, recommendation_id: str, reference: dict[str, Any]) -> None:
    current = store.get("recommendation_input", recommendation_id)
    if current != reference:
        raise Conflict("Recommendation input changed before decision freeze")
    if inputs(store, "recommendation", reference["payload"]) != reference["fingerprint"]:
        raise Conflict("Manager, source or forecast changed before decision freeze")


def record_decision_action(
    store: Store,
    decision_id: str,
    *,
    idempotency_key: str,
    execution_status: str,
    execution_action_id: str | None,
    paper_portfolio_action_id: str | None,
    expected_sequence: int,
) -> dict[str, Any]:
    journal = store.get("decision_journal", decision_id)
    known = {plan["plan_id"] for plan in journal["candidate_plans"]}
    if execution_status not in {"execution_unknown", "user_selected", "confirmed_executed"}:
        raise ValueError("Invalid execution status")
    if execution_status == "execution_unknown" and execution_action_id is not None:
        raise ValueError("Unknown execution cannot identify an executed plan")
    if execution_status != "execution_unknown" and execution_action_id not in known:
        raise ValueError("Selected action must be a frozen candidate")
    if paper_portfolio_action_id is not None and paper_portfolio_action_id not in known:
        raise ValueError("Paper portfolio action must be a frozen candidate")
    history: Sequence[dict[str, Any]] = store.decision_records(decision_id)
    prior_execution = next(
        (
            row["record"]
            for row in reversed(history)
            if row["record"]["execution_status"] != "execution_unknown"
        ),
        None,
    )
    if (
        prior_execution
        and prior_execution["execution_status"] == "confirmed_executed"
        and (execution_status, execution_action_id)
        != ("confirmed_executed", prior_execution["execution_action_id"])
    ):
        raise Conflict("Confirmed execution is immutable")
    if (
        execution_status == "confirmed_executed"
        and prior_execution
        and prior_execution["execution_action_id"] != execution_action_id
    ):
        raise Conflict("Confirmed execution differs from the selected action")
    record = {
        "kind": "manager_action_update",
        "execution_status": execution_status,
        "execution_action_id": execution_action_id,
        "paper_portfolio_action_id": paper_portfolio_action_id,
        "recorded_at": utcnow(),
    }
    previous = next((row for row in history if row["event_key"] == idempotency_key), None)
    if previous:
        old = previous["record"]
        if any(old[key] != record[key] for key in record if key != "recorded_at"):
            raise Conflict("Idempotency key was reused with different action data")
    else:
        store.append_decision_record(
            decision_id, idempotency_key, record, expected_sequence=expected_sequence
        )
    return decision_view(store, decision_id)


def decision_view(store: Store, decision_id: str) -> dict[str, Any]:
    journal = store.get("decision_journal", decision_id)
    updates = store.decision_records(decision_id)
    for update in updates:
        record = update["record"]
        journal["execution_status"] = (
            record["execution_status"]
            if record["execution_status"] != "execution_unknown"
            else journal["execution_status"]
        )
        if record["execution_action_id"] is not None:
            journal["execution_action_id"] = record["execution_action_id"]
        if record["paper_portfolio_action_id"] is not None:
            journal["paper_portfolio_action_id"] = record["paper_portfolio_action_id"]
    journal["action_history"] = updates
    journal["outcome_revisions"] = [
        record
        for record in store.list("learning_scorecard")
        if record["decision_id"] == decision_id
    ]
    return journal
