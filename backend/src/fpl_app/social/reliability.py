"""As-of factual reliability with author/family caps and Beta shrinkage.

Only explicit binary factual claims with verifiable resolutions qualify. Opinion,
uncertain wording and conditional assertions do not become invented targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from scipy.stats import beta


@dataclass(frozen=True)
class ResolvedClaim:
    claim_id: str
    author_id: str
    topic: str
    evidence_family: str
    claimed_at: str
    observed_at: str
    resolved_at: str
    assertion: str
    verified_value: bool
    predicted_value: bool
    source_profile_version: int
    profile_effective_at: str
    condition: str | None = None
    uncertain: bool = False
    kind: str = "report"


def factual_reliability(
    claims: list[ResolvedClaim],
    author_id: str,
    topic: str,
    as_of: str,
    *,
    prior_alpha=2.0,
    prior_beta=2.0,
):
    cutoff = datetime.fromisoformat(as_of)
    if cutoff.tzinfo is None or prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("Aware cutoff and positive topic prior required")
    by_family: dict[str, ResolvedClaim | None] = {}
    for row in claims:
        times = [
            datetime.fromisoformat(t)
            for t in (row.claimed_at, row.observed_at, row.resolved_at, row.profile_effective_at)
        ]
        if (
            any(t.tzinfo is None for t in times)
            or times[1] < times[0]
            or times[2] < times[0]
            or times[3] > times[0]
        ):
            raise ValueError("Invalid claim/profile/resolution timing")
        if (
            row.author_id != author_id
            or row.topic != topic
            or row.kind != "report"
            or row.uncertain
            or row.condition is not None
            or max(times) > cutoff
        ):
            continue
        if (
            row.assertion not in {"available", "out", "starts", "trained"}
            or type(row.predicted_value) is not bool
            or type(row.verified_value) is not bool
        ):
            continue
        # Repeated amplification of one factual family is one observation.
        previous = by_family.get(row.evidence_family)
        if previous is not None and previous.predicted_value != row.predicted_value:
            # Conflicting same-source repeats do not become a confident target.
            by_family[row.evidence_family] = None
        elif row.evidence_family not in by_family:
            by_family[row.evidence_family] = row
    qualified = [r for r in by_family.values() if r is not None]
    successes = sum(r.predicted_value == r.verified_value for r in qualified)
    alpha, b = prior_alpha + successes, prior_beta + len(qualified) - successes
    return {
        "author_id": author_id,
        "topic": topic,
        "as_of": as_of,
        "qualified_families": len(qualified),
        "posterior_mean": alpha / (alpha + b),
        "central_90_interval": [float(beta.ppf(0.05, alpha, b)), float(beta.ppf(0.95, alpha, b))],
        "prior_alpha": prior_alpha,
        "prior_beta": prior_beta,
        "version": "asof-author-family-beta-v1",
        "status": "prior_only" if not qualified else "estimated",
        "forecast_points_adjustment": 0,
    }
