from dataclasses import replace

import pytest

from fpl_app.social.benchmark import BenchmarkExample, benchmark_manifest, evaluate_semantics
from fpl_app.social.records import Claim
from fpl_app.social.reliability import ResolvedClaim, factual_reliability


def resolved():
    return ResolvedClaim(
        "c",
        "a",
        "availability",
        "family",
        "2026-10-01T00:00:00Z",
        "2026-10-01T00:01:00Z",
        "2026-10-02T00:00:00Z",
        "starts",
        True,
        True,
        1,
        "2026-09-01T00:00:00Z",
    )


def test_reliability_uses_only_resolved_asof_independent_families_and_shrinkage():
    row = resolved()
    before = factual_reliability([row], "a", "availability", "2026-10-01T12:00:00Z")
    assert before["status"] == "prior_only" and before["posterior_mean"] == 0.5
    after = factual_reliability(
        [
            row,
            replace(row, claim_id="repeat"),
            replace(row, claim_id="maybe", evidence_family="other", uncertain=True),
        ],
        "a",
        "availability",
        "2026-10-03T00:00:00Z",
    )
    assert after["qualified_families"] == 1 and after["posterior_mean"] == 0.6
    assert after["central_90_interval"][0] < 0.6 < after["central_90_interval"][1]
    assert after["forecast_points_adjustment"] == 0
    with pytest.raises(ValueError, match="timing"):
        factual_reliability(
            [replace(row, profile_effective_at="2026-10-02T00:00:00Z")],
            "a",
            "availability",
            "2026-10-03T00:00:00Z",
        )


def test_benchmark_never_fabricates_human_labels_or_leaks_source_families():
    text = "Buy Salah."
    label = (
        {
            "player_id": "salah",
            "action": "buy",
            "span_start": 0,
            "span_end": len(text),
            "evidence_span": text,
        },
    )
    dev = BenchmarkExample(
        "d", text, "dev-author", "dev-family", "2026-10-01T00:00:00Z", "development", label
    )
    test = BenchmarkExample(
        "t", text, "test-author", "test-family", "2026-10-02T00:00:00Z", "test", label
    )
    meta = benchmark_manifest([dev, test])
    assert meta["independently_double_reviewed"] == 0
    with pytest.raises(ValueError, match="overlap"):
        benchmark_manifest([dev, replace(test, author_id="dev-author")])
    with pytest.raises(ValueError, match="double review"):
        benchmark_manifest(
            [replace(test, label_origin="human_reviewed", independent_reviewer_ids=("agent",))]
        )


def test_exact_semantic_metrics_penalize_extra_duplicate_claims():
    text = "Buy Salah."
    expected = {
        "player_id": "salah",
        "action": "buy",
        "span_start": 0,
        "span_end": len(text),
        "evidence_span": text,
    }
    example = BenchmarkExample("t", text, "a", "f", "2026-10-02T00:00:00Z", "test", (expected,))
    claim = Claim(
        claim_id="c",
        post_id="p",
        author_id="a",
        player_id="salah",
        topic="strategy",
        action="buy",
        evidence_span=text,
        span_start=0,
        span_end=len(text),
        evidence_family="f",
        observed_at="2026-10-02T00:00:00Z",
    )
    report = evaluate_semantics(
        [example], {"t": [claim, claim.model_copy(update={"claim_id": "duplicate"})]}
    )
    assert report["field_accuracy"]["action"] == 1
    assert report["exact_claim_counts"] == {"tp": 1, "fp": 1, "fn": 0}
    assert report["exact_claim_precision"] == 0.5
    assert report["exact_claim_f1"] == pytest.approx(2 / 3)
