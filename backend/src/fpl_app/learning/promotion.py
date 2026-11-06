"""Predeclared evidence gates; a report never mutates a champion pointer."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class PromotionGate:
    minimum_gain_points: float = 1.0
    maximum_downside_points: float = 5.0
    maximum_latency_seconds: float = 15.0
    minimum_distinct_events: int = 8
    minimum_seeds: int = 5
    version: str = "prospective-strategy-gate-v1"


def assess_promotion(evidence: dict[str, Any], gate: PromotionGate | None = None):
    gate = gate or PromotionGate()
    reasons = []
    if evidence.get("evidence_mode") != "prospective_strict":
        reasons.append("Qualified prospective evidence required")
    if evidence.get("invalid_accepted_actions") != 0:
        reasons.append("Zero invalid accepted actions required")
    if evidence.get("distinct_events", 0) < gate.minimum_distinct_events:
        reasons.append("Too few distinct football events")
    if evidence.get("training_seed_count", 0) < gate.minimum_seeds:
        reasons.append("Too few training seeds")
    required = [
        "policy_sha256",
        "candidate_version",
        "observation_version",
        "rules_version",
        "forecast_reference",
        "evaluation_sha256",
        "registered_gate_version",
    ]
    if (
        any(not evidence.get(field) for field in required)
        or evidence.get("registered_gate_version") != gate.version
    ):
        reasons.append("Exact artifact and predeclared gate bindings required")
    lower = evidence.get("paired_gain_lower_bound")
    downside = evidence.get("downside_loss_points")
    latency = evidence.get("latency_seconds")
    for value, name in [(lower, "gain"), (downside, "downside"), (latency, "latency")]:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            reasons.append(f"Unavailable {name} evidence")
    if (
        isinstance(lower, (int, float))
        and not isinstance(lower, bool)
        and isfinite(lower)
        and lower <= gate.minimum_gain_points
    ):
        reasons.append("Lower confidence bound does not clear registered gain")
    if (
        isinstance(downside, (int, float))
        and not isinstance(downside, bool)
        and isfinite(downside)
        and downside > gate.maximum_downside_points
    ):
        reasons.append("Downside exceeds tolerance")
    if (
        isinstance(latency, (int, float))
        and not isinstance(latency, bool)
        and isfinite(latency)
        and latency > gate.maximum_latency_seconds
    ):
        reasons.append("Latency exceeds tolerance")
    return {
        "decision": "retain_champion" if reasons else "eligible_for_review",
        "reasons": reasons,
        "gate": asdict(gate),
        "automatic_activation": False,
    }


@dataclass(frozen=True)
class CandidateGate:
    """New registrations only; legacy strategy receipts retain their v1 contract.

    Forecast gains are paired reductions in the registered loss, in that loss's
    units. Planner/policy gains are net FPL points per event. No automatic serving
    change follows a favourable assessment.
    """

    kind: str
    primary_metric: str
    metric_units: str
    minimum_gain: float = 0.0
    maximum_downside: float = 5.0
    maximum_latency_seconds: float = 15.0
    minimum_distinct_events: int = 8
    minimum_seeds: int = 5
    version: str = "candidate-evidence-gate-v2"

    def __post_init__(self):
        if self.kind not in {"forecast", "planner", "stochastic_policy"}:
            raise ValueError("Unknown candidate evidence kind")
        forecast_metrics = {
            "point_mae": "FPL_points",
            "point_rmse": "FPL_points",
            "minutes_mae": "minutes",
            "appearance_brier": "probability_squared",
            "sixty_brier": "probability_squared",
            "appearance_log_loss": "nats",
            "sixty_log_loss": "nats",
            "point_pinball": "FPL_points",
        }
        if (
            self.kind == "forecast"
            and forecast_metrics.get(self.primary_metric) != self.metric_units
        ):
            raise ValueError("Registered forecast loss and matching units required")
        if self.kind != "forecast" and (
            self.primary_metric != "net_points_per_event" or self.metric_units != "FPL_points/event"
        ):
            raise ValueError("Decision candidates require net points per event")
        for value in (self.minimum_gain, self.maximum_downside, self.maximum_latency_seconds):
            if isinstance(value, bool) or not isfinite(value) or value < 0:
                raise ValueError("Finite nonnegative thresholds required")
        if type(self.minimum_distinct_events) is not int or self.minimum_distinct_events < 8:
            raise ValueError("At least eight distinct prospective events required")
        if type(self.minimum_seeds) is not int or self.minimum_seeds < 5:
            raise ValueError("At least five seeds required for stochastic policy evidence")


def assess_candidate(evidence: dict[str, Any], gate: CandidateGate) -> dict[str, Any]:
    """Assess a predeclared, type-specific contract without changing a champion."""
    reasons = []
    bindings = [
        "method_id",
        "artifact_sha256",
        "feature_schema_sha256",
        "dataset_sha256",
        "evaluation_sha256",
        "protocol_sha256",
        "comparator_method_id",
    ]
    if gate.kind != "forecast":
        bindings += ["rules_version", "candidate_version", "forecast_reference"]
    if gate.kind == "stochastic_policy":
        bindings += ["observation_version", "simulator_sha256"]
    if any(not evidence.get(key) for key in bindings) or any(
        evidence.get(key) != expected
        for key, expected in {
            "registered_gate_version": gate.version,
            "candidate_kind": gate.kind,
            "primary_metric": gate.primary_metric,
            "metric_units": gate.metric_units,
            "metric_window": "per_event",
        }.items()
    ):
        reasons.append("Exact method, protocol, comparator and metric bindings required")
    if evidence.get("evidence_mode") != "prospective_strict":
        reasons.append("Qualified prospective evidence required")
    events = evidence.get("event_ids")
    if (
        not isinstance(events, list)
        or any(
            not isinstance(event, str) or not re.fullmatch(r"20\d{2}/\d{2}:[1-9]\d?", event)
            for event in events
        )
        or len(set(events)) != len(events)
        or len(events) < gate.minimum_distinct_events
    ):
        reasons.append("Too few distinct season-scoped football events")
    if evidence.get("matched_coverage") is not True:
        reasons.append("Matched comparator coverage required")
    if gate.kind != "forecast" and (
        type(evidence.get("invalid_accepted_actions")) is not int
        or evidence["invalid_accepted_actions"] != 0
    ):
        reasons.append("Zero invalid accepted actions required")
    if gate.kind == "stochastic_policy":
        seeds = evidence.get("training_seeds")
        if (
            not isinstance(seeds, list)
            or any(type(seed) is not int for seed in seeds)
            or len(set(seeds)) < gate.minimum_seeds
        ):
            reasons.append("Too few distinct training seeds")
    for key, threshold, direction in [
        ("paired_gain_lower_bound", gate.minimum_gain, "above"),
        ("downside_loss", gate.maximum_downside, "below"),
        ("latency_seconds", gate.maximum_latency_seconds, "below"),
    ]:
        value = evidence.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            reasons.append(f"Unavailable {key} evidence")
        elif (direction == "above" and value <= threshold) or (
            direction == "below" and (value < 0 or value > threshold)
        ):
            reasons.append(f"{key} fails registered threshold")
    return {
        "decision": "retain_champion" if reasons else "eligible_for_review",
        "reasons": reasons,
        "gate": asdict(gate),
        "automatic_activation": False,
    }
