import pytest

from fpl_app.learning.promotion import CandidateGate, assess_candidate


def evidence(kind):
    return {
        **{
            key: "bound"
            for key in [
                "method_id",
                "artifact_sha256",
                "feature_schema_sha256",
                "dataset_sha256",
                "evaluation_sha256",
                "protocol_sha256",
                "comparator_method_id",
                "rules_version",
                "candidate_version",
                "forecast_reference",
                "observation_version",
                "simulator_sha256",
            ]
        },
        "registered_gate_version": "candidate-evidence-gate-v2",
        "candidate_kind": kind,
        "primary_metric": "point_mae" if kind == "forecast" else "net_points_per_event",
        "metric_units": "FPL_points" if kind == "forecast" else "FPL_points/event",
        "metric_window": "per_event",
        "evidence_mode": "prospective_strict",
        "event_ids": [f"2026/27:{i}" for i in range(1, 9)],
        "matched_coverage": True,
        "invalid_accepted_actions": 0,
        "paired_gain_lower_bound": 1.2,
        "downside_loss": 2.0,
        "latency_seconds": 1.0,
    }


def gate(kind):
    return CandidateGate(
        kind,
        "point_mae" if kind == "forecast" else "net_points_per_event",
        "FPL_points" if kind == "forecast" else "FPL_points/event",
    )


@pytest.mark.parametrize("kind", ["forecast", "planner"])
def test_deterministic_candidates_need_no_policy_seeds(kind):
    result = assess_candidate(evidence(kind), gate(kind))
    assert result["decision"] == "eligible_for_review"
    assert result["automatic_activation"] is False


def test_stochastic_policy_needs_distinct_seeds_and_simulator():
    data = evidence("stochastic_policy")
    data["training_seeds"] = [1] * 5
    assert assess_candidate(data, gate("stochastic_policy"))["decision"] == "retain_champion"
    data["training_seeds"] = list(range(5))
    assert assess_candidate(data, gate("stochastic_policy"))["decision"] == "eligible_for_review"
    del data["simulator_sha256"]
    assert assess_candidate(data, gate("stochastic_policy"))["decision"] == "retain_champion"


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_kind": "planner"},
        {"metric_units": "rank_score"},
        {"metric_window": "cumulative"},
        {"paired_gain_lower_bound": float("nan")},
        {"downside_loss": -1},
        {"matched_coverage": False},
        {"event_ids": ["2026/27:1"] * 8},
        {"evidence_mode": "historical_reconstructed"},
        {"event_ids": [True] * 8},
        {"paired_gain_lower_bound": True},
    ],
)
def test_invalid_or_mismatched_evidence_cannot_pass(change):
    assert (
        assess_candidate(evidence("forecast") | change, gate("forecast"))["decision"]
        == "retain_champion"
    )


def test_policy_illegality_and_weakened_gate_rejected():
    assert (
        assess_candidate(evidence("planner") | {"invalid_accepted_actions": 1}, gate("planner"))[
            "decision"
        ]
        == "retain_champion"
    )
    with pytest.raises(ValueError):
        CandidateGate("planner", "point_mae", "FPL_points")
    with pytest.raises(ValueError):
        CandidateGate("forecast", "point_mae", "FPL_points", minimum_distinct_events=1)
