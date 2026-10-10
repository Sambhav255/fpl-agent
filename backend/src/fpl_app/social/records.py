"""Offline social contracts. No record confers provider access rights."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Action = Literal["buy", "sell", "hold", "captain", "avoid", "bench", "unclear"]
Topic = Literal["strategy", "captaincy", "availability"]
Group = Literal["expert", "crowd", "unknown"]


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Capability(Record):
    provider: Literal["reddit", "x", "synthetic", "permissioned"]
    reference: str
    allow_read: bool = False
    allow_store: bool = False
    allow_inference: bool = False
    allow_external_processing: bool = False
    allow_derived_features: bool = False
    allow_training: bool = False
    retention_days: int | None = Field(default=None, ge=1)


class SourceProfile(Record):
    author_id: str
    group: Group
    roles: tuple[str, ...] = ()
    topics: tuple[Topic, ...] = ()
    evidence: str
    reviewer: str
    reviewed_at: AwareDatetime
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    version: int = Field(ge=1)


class SocialPost(Record):
    post_id: str
    author_id: str
    provider: Literal["reddit", "x", "synthetic", "permissioned"]
    text: str
    created_at: AwareDatetime
    observed_at: AwareDatetime
    edited_at: AwareDatetime | None = None
    evidence_family: str | None = None
    context_ids: tuple[str, ...] = ()
    query: str
    language: str = "en"
    capability_reference: str
    synthetic: bool = False


class Claim(Record):
    claim_id: str
    post_id: str
    author_id: str
    player_id: str | None
    topic: Topic
    action: Action
    evidence_span: str
    span_start: int
    span_end: int
    evidence_family: str
    observed_at: AwareDatetime
    horizon: str = "unspecified"
    condition: str | None = None
    funding_player_id: str | None = None
    negated: bool = False
    quoted: bool = False
    attribution: str | None = None
    question: bool = False
    abstention: str | None = None
    extractor_version: str = "deterministic-v1"
    kind: Literal["opinion", "report"] = "opinion"


class Coverage(Record):
    status: Literal["available", "partial", "unavailable", "stale"]
    query: str
    start: AwareDatetime
    end: AwareDatetime
    reason: str | None = None
    synthetic: bool = False


class Consensus(Record):
    player_id: str
    topic: Topic
    horizon: str
    group: Group
    status: Literal["available", "partial", "unavailable", "stale"]
    distribution: dict[str, float] | None
    distinct_authors: int
    evidence_families: int
    effective_sample_size: float | None
    coverage: Coverage
    as_of: AwareDatetime
    aggregation_version: str = "author-family-bounded-v1"
    points_adjustment: Literal[0] = 0
