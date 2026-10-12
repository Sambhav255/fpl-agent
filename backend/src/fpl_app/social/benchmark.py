"""Frozen semantic benchmark contracts; authored labels are never human review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fpl_app.social.records import Claim
from fpl_app.storage import fingerprint


@dataclass(frozen=True)
class BenchmarkExample:
    example_id: str
    text: str
    author_id: str
    family_id: str
    created_at: str
    partition: str
    expected: tuple[dict[str, Any], ...]
    label_origin: str = "authored_synthetic"
    independent_reviewer_ids: tuple[str, ...] = ()


def benchmark_manifest(examples: list[BenchmarkExample]):
    if not examples or len({e.example_id for e in examples}) != len(examples):
        raise ValueError("Distinct benchmark examples required")
    allowed = {"development", "validation", "test"}
    for e in examples:
        if e.partition not in allowed or datetime.fromisoformat(e.created_at).tzinfo is None:
            raise ValueError("Explicit split and aware time required")
        if e.label_origin == "human_reviewed" and len(set(e.independent_reviewer_ids)) < 2:
            raise ValueError("Human reviewed labels require independent double review")
        for span in e.expected:
            if e.text[span["span_start"] : span["span_end"]] != span["evidence_span"]:
                raise ValueError("Label evidence span differs from text")
    for field in ("author_id", "family_id"):
        groups = {
            split: {getattr(e, field) for e in examples if e.partition == split}
            for split in allowed
        }
        if (
            groups["test"] & (groups["development"] | groups["validation"])
            or groups["validation"] & groups["development"]
        ):
            raise ValueError("Source/family partition overlap")
    dev = [datetime.fromisoformat(e.created_at) for e in examples if e.partition == "development"]
    val = [datetime.fromisoformat(e.created_at) for e in examples if e.partition == "validation"]
    test = [datetime.fromisoformat(e.created_at) for e in examples if e.partition == "test"]
    if (
        dev
        and val
        and max(dev) >= min(val)
        or val
        and test
        and max(val) >= min(test)
        or dev
        and test
        and max(dev) >= min(test)
    ):
        raise ValueError("Chronological partition overlap")
    from dataclasses import asdict

    return {
        "benchmark_sha256": fingerprint([asdict(e) for e in examples]),
        "counts": {s: sum(e.partition == s for e in examples) for s in sorted(allowed)},
        "independently_double_reviewed": sum(
            len(set(e.independent_reviewer_ids)) >= 2 and e.label_origin == "human_reviewed"
            for e in examples
        ),
        "label_origins": sorted({e.label_origin for e in examples}),
    }


def evaluate_semantics(
    examples: list[BenchmarkExample], predictions: dict[str, list[Claim]], *, partition="test"
):
    manifest = benchmark_manifest(examples)
    keys = (
        "player_id",
        "action",
        "topic",
        "horizon",
        "condition",
        "funding_player_id",
        "attribution",
        "question",
        "kind",
    )
    counts = {key: {"correct": 0, "total": 0} for key in keys}
    span_good = span_total = 0
    abstained = accepted = 0
    true_positives = false_positives = false_negatives = 0
    for example in examples:
        if example.partition != partition:
            continue
        actual = predictions.get(example.example_id, [])
        unmatched = list(example.expected)
        for claim in actual:
            # Extra and duplicate claims are false positives, even when field
            # accuracy on expected claims alone would look perfect.
            match = next(
                (e for e in unmatched if all(getattr(claim, k, None) == v for k, v in e.items())),
                None,
            )
            if match is None:
                false_positives += 1
            else:
                true_positives += 1
                unmatched.remove(match)
        false_negatives += len(unmatched)
        for claim in actual:
            span_total += 1
            span_good += example.text[claim.span_start : claim.span_end] == claim.evidence_span
            if claim.abstention:
                abstained += 1
            else:
                accepted += 1
        # Entity and evidence span identify a claim; no hindsight fuzzy matching.
        by_key = {(c.player_id, c.span_start, c.span_end): c for c in actual}
        for expected in example.expected:
            matched = by_key.get(
                (expected.get("player_id"), expected["span_start"], expected["span_end"])
            )
            for key in keys:
                if key in expected:
                    counts[key]["total"] += 1
                    counts[key]["correct"] += (
                        matched is not None and getattr(matched, key) == expected[key]
                    )
    return {
        "manifest": manifest,
        "partition": partition,
        "field_accuracy": {
            k: None if not v["total"] else v["correct"] / v["total"] for k, v in counts.items()
        },
        "evidence_span_fidelity": None if not span_total else span_good / span_total,
        "accepted_claims": accepted,
        "abstentions": abstained,
        "exact_claim_counts": {"tp": true_positives, "fp": false_positives, "fn": false_negatives},
        "exact_claim_precision": None
        if true_positives + false_positives == 0
        else true_positives / (true_positives + false_positives),
        "exact_claim_recall": None
        if true_positives + false_negatives == 0
        else true_positives / (true_positives + false_negatives),
        "exact_claim_f1": None
        if 2 * true_positives + false_positives + false_negatives == 0
        else 2 * true_positives / (2 * true_positives + false_positives + false_negatives),
        "calibrated_confidence": None,
        "limitation": "Authored engineering labels and independent human benchmark remain distinct; no live accuracy claim",
    }
