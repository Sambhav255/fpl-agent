"""Local reviewed imports into existing deletable social records; no live collector."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from fpl_app.storage import fingerprint

from .records import Action, Capability, Record, SocialPost, SourceProfile, Topic
from .reliability import factual_reliability
from .semantic import StructuredExtractor
from .store import SocialStore


class ManualClaim(Record):
    player_id: str | None
    topic: Topic
    action: Action = "unclear"
    span_start: int = Field(ge=0)
    span_end: int = Field(gt=0)
    horizon: str = "unspecified"
    condition: str | None = None
    quoted: bool = False
    attribution: str | None = None
    question: bool = False
    negated: bool = False
    abstention: str | None = None
    funding_player_id: str | None = None
    kind: Literal["opinion", "report"] = "opinion"
    assertion: Literal["out", "available", "starts", "trained", "uncertain"] | None = None


class ManualPost(Record):
    post_id: str
    author_id: str
    text: str = Field(min_length=1, max_length=20000)
    created_at: AwareDatetime
    source_reference: str | None = None
    edited_at: AwareDatetime | None = None
    evidence_family: str | None = None
    context_ids: tuple[str, ...] = ()
    claims: tuple[ManualClaim, ...] = ()


class ManualImport(Record):
    schema_version: Literal[1] = 1
    capability: Capability
    material: Literal["self_authored", "permissioned", "synthetic_fixture"]
    permission_evidence: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    entity_reference: str = Field(min_length=1)
    player_ids: tuple[str, ...]
    profiles: tuple[SourceProfile, ...] = ()
    posts: tuple[ManualPost, ...] = Field(min_length=1, max_length=500)


def import_manual(store: SocialStore, bundle: ManualImport, now: datetime) -> dict[str, Any]:
    """Actual first observation is import time; original publication is separate.

    The original text lives only in social_posts, subject to deletion/retention.
    Receipts retain hashes and IDs rather than a second undeletable text archive.
    """
    if now.tzinfo is None:
        raise ValueError("Aware import time required")
    cap = bundle.capability
    expected_provider = "synthetic" if bundle.material == "synthetic_fixture" else "permissioned"
    if cap.provider != expected_provider:
        raise PermissionError(
            "Manual import requires authored/permissioned material or labelled synthetic fixtures"
        )
    if (
        not bundle.permission_evidence.strip()
        or not bundle.reviewer.strip()
        or not bundle.entity_reference.strip()
    ):
        raise ValueError("Permission, reviewer and entity mapping evidence required")
    if (
        not (cap.allow_store and cap.allow_inference and cap.allow_derived_features)
        or cap.retention_days is None
    ):
        raise PermissionError("Finite local storage, inference and derived-claim rights required")
    if cap.allow_external_processing or cap.allow_training:
        raise PermissionError(
            "Manual importer does not enable external processing or model training"
        )
    if len(set(bundle.player_ids)) != len(bundle.player_ids) or any(
        not p.strip() for p in bundle.player_ids
    ):
        raise ValueError("Unique explicitly resolved player IDs required")
    digest = fingerprint(bundle.model_dump(mode="json"))
    store.claims(now)  # retention also applies on retries
    old = store.db.execute(
        "SELECT payload FROM social_manual_receipts WHERE digest=?", (digest,)
    ).fetchone()
    if old:
        receipt = json.loads(old[0])
        active = {
            post.post_id
            for row in store.db.execute("SELECT payload FROM social_posts")
            if (post := SocialPost.model_validate_json(row[0])).query == "manual-reviewed:" + digest
        }
        return {
            **receipt,
            "replayed": True,
            "active_posts": len(active.intersection(receipt["post_ids"])),
        }
    ids = [post.post_id for post in bundle.posts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate post IDs in import")
    prepared = []
    for row in bundle.posts:
        if row.created_at > now or row.edited_at and row.edited_at > now:
            raise ValueError("Future publication or edit time")
        post = SocialPost(
            post_id=row.post_id,
            author_id=row.author_id,
            provider=cap.provider,
            text=row.text,
            source_reference=row.source_reference,
            created_at=row.created_at,
            observed_at=now,
            edited_at=row.edited_at,
            evidence_family=row.evidence_family,
            context_ids=row.context_ids,
            query="manual-reviewed:" + digest,
            capability_reference=cap.reference,
            synthetic=bundle.material == "synthetic_fixture",
        )
        claim_rows = []
        for claim in row.claims:
            if claim.assertion and (claim.topic != "availability" or claim.kind != "report"):
                raise ValueError("Availability assertions require factual availability report type")
            if not 0 <= claim.span_start < claim.span_end <= len(row.text):
                raise ValueError("Unsupported manual evidence span")
            claim_rows.append(
                {
                    **claim.model_dump(mode="json"),
                    "evidence_span": row.text[claim.span_start : claim.span_end],
                    "reviewed_by": bundle.reviewer,
                    "reviewed_at": now,
                }
            )

        def reviewed_rows(
            text: str, rows: list[dict[str, Any]] = claim_rows
        ) -> list[dict[str, Any]]:
            return rows

        extractor = StructuredExtractor(
            reviewed_rows, set(bundle.player_ids), version="manual-reviewed-v1"
        )
        extractor.extract(post, cap)  # validate all records before any writes
        prepared.append((post, extractor))
    for profile in bundle.profiles:
        if profile.reviewed_at > now or profile.effective_at > now:
            raise ValueError("Future source review")
    with store.transaction():
        for profile in bundle.profiles:
            existing = store.db.execute(
                "SELECT payload FROM social_reviews WHERE author=? AND version=?",
                (profile.author_id, profile.version),
            ).fetchone()
            if existing:
                if SourceProfile.model_validate_json(existing[0]) != profile:
                    raise ValueError("Source review version already exists with different content")
            else:
                store.review(profile)
        count = 0
        for post, extractor in prepared:
            count += len(store.ingest(post, cap, extractor, now))
        receipt = {
            "schema_version": 1,
            "digest": digest,
            "observed_at": now.isoformat(),
            "post_ids": ids,
            "posts": len(ids),
            "claims": count,
            "synthetic": bundle.material == "synthetic_fixture",
            "points_adjustment": 0,
            "capability_reference": cap.reference,
            "capability": cap.model_dump(mode="json"),
            "entity_reference": bundle.entity_reference,
            "permission_evidence_sha256": fingerprint(bundle.permission_evidence),
            "replayed": False,
            "active_posts": len(ids),
        }
        store.db.execute(
            "INSERT INTO social_manual_receipts VALUES (?, ?)", (digest, json.dumps(receipt))
        )
    return receipt


def availability_scenarios(store: SocialStore, as_of: datetime, horizon: str) -> dict[str, Any]:
    """Review-only branches preserve contradictions without invented probabilities."""
    if as_of.tzinfo is None or not horizon.strip():
        raise ValueError("Aware cutoff and explicit horizon required")
    groups: dict[str, dict[str, Any]] = {}
    for claim in store.claims(as_of):
        if (
            claim.topic != "availability"
            or claim.horizon != horizon
            or claim.kind != "report"
            or not claim.assertion
            or claim.player_id is None
            or not claim.reviewed_by
            or claim.reviewed_at is None
            or claim.reviewed_at > as_of
        ):
            continue
        group = groups.setdefault(claim.player_id, {"claims": [], "seen": set()})
        key = (
            claim.author_id,
            claim.evidence_family,
            claim.assertion,
            claim.condition,
            claim.negated,
            claim.quoted,
            claim.question,
            claim.abstention,
            claim.attribution,
        )
        if key in group["seen"]:
            continue
        group["seen"].add(key)
        group["claims"].append(
            {
                "claim_id": claim.claim_id,
                "post_id": claim.post_id,
                "assertion": claim.assertion,
                "condition": claim.condition,
                "evidence_family": claim.evidence_family,
                "source_group": store.group(claim.author_id, "availability", claim.observed_at),
                "review_required": bool(
                    claim.abstention
                    or claim.condition
                    or claim.quoted
                    or claim.question
                    or claim.negated
                    or claim.assertion == "uncertain"
                ),
                "reliability": factual_reliability(
                    [], claim.author_id, "availability", as_of.isoformat()
                ),
                "observed_at": claim.observed_at.isoformat(),
            }
        )
    players = []
    for player_id, group in sorted(groups.items()):
        assertions = {c["assertion"] for c in group["claims"] if not c["review_required"]}
        players.append(
            {
                "player_id": player_id,
                "branches": group["claims"],
                "contradictory": "out" in assertions and bool(assertions & {"available", "starts"}),
                "forecast_change_applied": False,
                "points_adjustment": 0,
            }
        )
    return {
        "as_of": as_of.isoformat(),
        "horizon": horizon,
        "status": "review_only" if players else "unavailable",
        "players": players,
        "points_adjustment": 0,
        "limitations": [
            "Manual sample, not live coverage or a calibrated availability probability",
            "Reliability remains prior-only without separately verified resolutions",
            "No social-derived model training or automatic forecast changes",
        ],
    }
