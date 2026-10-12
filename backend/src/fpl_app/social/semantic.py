"""Permission-fenced structured extractor boundary, including precise abstention.

A caller supplies a reviewed local semantic model. No account, network call or
unconfigured LLM fallback is introduced. The grammar extractor remains comparator.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fpl_app.social.records import Capability, Claim, SocialPost


class StructuredExtractor:
    def __init__(
        self,
        extract: Callable[[str], list[dict[str, Any]]],
        player_ids: set[str],
        *,
        version: str,
        external=False,
    ):
        if not version:
            raise ValueError("Versioned extractor required")
        self.extract_model = extract
        self.player_ids = player_ids
        self.version = version
        self.external = external

    def extract(self, post: SocialPost, capability: Capability) -> list[Claim]:
        if (
            capability.provider != post.provider
            or capability.reference != post.capability_reference
            or not capability.allow_inference
            or not capability.allow_derived_features
        ):
            raise PermissionError("Semantic inference and derived claims require rights")
        if self.external and not capability.allow_external_processing:
            raise PermissionError("External semantic processing forbidden")
        if post.provider == "synthetic" and not post.synthetic:
            raise ValueError("Synthetic source must be explicit")
        claims = []
        from fpl_app.storage import fingerprint

        for i, row in enumerate(self.extract_model(post.text)):
            claim = Claim.model_validate(
                {
                    **row,
                    "claim_id": f"{post.post_id}:semantic:{i}",
                    "post_id": post.post_id,
                    "author_id": post.author_id,
                    "observed_at": post.observed_at,
                    "evidence_family": post.evidence_family
                    or "semantic-text:" + fingerprint(post.text),
                    "extractor_version": self.version,
                }
            )
            if (
                not 0 <= claim.span_start < claim.span_end <= len(post.text)
                or post.text[claim.span_start : claim.span_end] != claim.evidence_span
            ):
                raise ValueError("Unsupported evidence span")
            if (
                claim.player_id is not None
                and claim.player_id not in self.player_ids
                or claim.funding_player_id is not None
                and claim.funding_player_id not in self.player_ids
            ):
                raise ValueError("Unlinked semantic entity")
            claims.append(claim)
        return claims
