"""Predeclared evidence gates; a report never mutates a champion pointer."""

from __future__ import annotations

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
