"""Offline, descriptive social evidence. Live access and forecast influence are disabled."""

from .aggregation import aggregate
from .extraction import Extractor
from .providers import RedditAdapter, XAdapter
from .records import Capability, Claim, Consensus, Coverage, SocialPost, SourceProfile
from .store import SocialStore

__all__ = [
    "Capability",
    "Claim",
    "Consensus",
    "Coverage",
    "Extractor",
    "RedditAdapter",
    "SocialPost",
    "SocialStore",
    "SourceProfile",
    "XAdapter",
    "aggregate",
]
