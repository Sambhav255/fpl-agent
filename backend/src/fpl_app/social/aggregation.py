"""Descriptive samples only; conditions, quotations and unresolved claims are excluded."""

from collections import defaultdict
from datetime import datetime

from .records import Consensus, Coverage, Group, Topic
from .store import SocialStore


def aggregate(
    store: SocialStore,
    player_id: str,
    topic: Topic,
    horizon: str,
    group: Group,
    coverage: Coverage,
    as_of: datetime,
) -> Consensus:
    votes: dict[tuple[str, str], set[str]] = defaultdict(set)
    claims = store.claims(as_of)
    if coverage.status in ("available", "partial") and coverage.end <= as_of:
        for claim in claims:
            if (
                claim.player_id == player_id
                and claim.topic == topic
                and claim.horizon == horizon
                and claim.abstention is None
                and not claim.condition
                and not claim.negated
                and not claim.quoted
                and not claim.question
                and coverage.start <= claim.observed_at <= coverage.end
                and store.group(claim.author_id, topic, claim.observed_at) == group
            ):
                votes[(claim.author_id, claim.evidence_family)].add(claim.action)
    # Dedup per author/family. Contradictions retain an unclear vote, never cherry pick.
    authors_per_family: dict[str, set[str]] = defaultdict(set)
    families_per_author: dict[str, set[str]] = defaultdict(set)
    for author, family in votes:
        authors_per_family[family].add(author)
        families_per_author[author].add(family)
    distribution: dict[str, float] = defaultdict(float)
    weights_by_author: dict[str, float] = defaultdict(float)
    for (author, family), actions in votes.items():
        weight = 1 / (len(families_per_author[author]) * len(authors_per_family[family]))
        distribution[next(iter(actions)) if len(actions) == 1 else "unclear"] += weight
        weights_by_author[author] += weight
    total = sum(weights_by_author.values())
    status = coverage.status
    if coverage.end > as_of or (not votes and status in ("available", "partial")):
        status = "unavailable"
    return Consensus(
        player_id=player_id,
        topic=topic,
        horizon=horizon,
        group=group,
        status=status,
        distribution={a: w / total for a, w in distribution.items()} if total else None,
        distinct_authors=len(weights_by_author),
        evidence_families=len(authors_per_family),
        effective_sample_size=(total * total / sum(w * w for w in weights_by_author.values()))
        if total
        else None,
        coverage=coverage,
        as_of=as_of,
    )
