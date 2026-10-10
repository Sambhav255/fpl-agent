"""Dedicated deletable SQLite store; never uses the application's private database."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .extraction import Extractor
from .records import Capability, Claim, Group, SocialPost, SourceProfile, Topic


class SocialStore:
    def __init__(self, path: Path) -> None:
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS social_posts (id TEXT PRIMARY KEY, payload TEXT NOT NULL, expires_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS social_claims
                (id TEXT PRIMARY KEY, post_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS social_reviews
                (author TEXT, version INTEGER, payload TEXT NOT NULL, PRIMARY KEY(author, version));
            CREATE TABLE IF NOT EXISTS social_tombstones (id TEXT PRIMARY KEY);
        """)

    def close(self) -> None:
        self.db.close()

    def review(self, profile: SourceProfile) -> None:
        if not profile.evidence.strip() or not profile.reviewer.strip():
            raise ValueError("Manual review requires evidence and reviewer")
        if profile.expires_at <= profile.effective_at:
            raise ValueError("Review window must be nonempty")
        with self.db:
            self.db.execute(
                "INSERT INTO social_reviews VALUES (?, ?, ?)",
                (profile.author_id, profile.version, profile.model_dump_json()),
            )

    def group(self, author: str, topic: Topic, as_of: datetime) -> Group:
        rows = self.db.execute("SELECT payload FROM social_reviews WHERE author=?", (author,))
        reviews = [SourceProfile.model_validate_json(r[0]) for r in rows]
        eligible = [
            r for r in reviews if r.reviewed_at <= as_of and r.effective_at <= as_of < r.expires_at
        ]
        if not eligible:
            return "unknown"
        review = max(eligible, key=lambda r: r.version)
        return review.group if topic in review.topics else "unknown"

    def ingest(
        self, post: SocialPost, capability: Capability, extractor: Extractor, now: datetime
    ) -> list[Claim]:
        if not post.post_id.startswith(post.provider + ":"):
            raise ValueError("Post IDs must be provider namespaced")
        if not capability.allow_store or capability.retention_days is None:
            raise PermissionError("Storage requires explicit finite retention")
        if post.created_at > post.observed_at or post.observed_at > now:
            raise ValueError("Invalid observation timing")
        if post.edited_at and post.edited_at > post.observed_at:
            raise ValueError("Edit cannot postdate observation")
        if now >= post.observed_at + timedelta(days=capability.retention_days):
            raise ValueError("Content retention expired")
        if self.db.execute(
            "SELECT 1 FROM social_tombstones WHERE id=?", (post.post_id,)
        ).fetchone():
            raise ValueError("Deleted post cannot be reingested")
        old = self.db.execute(
            "SELECT payload FROM social_posts WHERE id=?", (post.post_id,)
        ).fetchone()
        if old:
            previous = SocialPost.model_validate_json(old[0])
            if post.observed_at < previous.observed_at:
                raise ValueError("Stale post edit")
        claims = extractor.extract(post, capability)
        with self.db:
            self.db.execute("DELETE FROM social_claims WHERE post_id=?", (post.post_id,))
            self.db.execute(
                "INSERT OR REPLACE INTO social_posts VALUES (?, ?, ?)",
                (
                    post.post_id,
                    post.model_dump_json(),
                    (post.observed_at + timedelta(days=capability.retention_days)).isoformat(),
                ),
            )
            self.db.executemany(
                "INSERT INTO social_claims VALUES (?, ?, ?)",
                [(c.claim_id, c.post_id, c.model_dump_json()) for c in claims],
            )
        return claims

    def delete(self, post_id: str) -> None:
        # Context-dependent descendants must also disappear, not just the original text.
        doomed = {post_id}
        posts = [
            SocialPost.model_validate_json(r[0])
            for r in self.db.execute("SELECT payload FROM social_posts")
        ]
        while True:
            expanded = doomed | {p.post_id for p in posts if doomed.intersection(p.context_ids)}
            if expanded == doomed:
                break
            doomed = expanded
        with self.db:
            for key in doomed:
                self.db.execute("DELETE FROM social_claims WHERE post_id=?", (key,))
                self.db.execute("DELETE FROM social_posts WHERE id=?", (key,))
                self.db.execute("INSERT OR IGNORE INTO social_tombstones VALUES (?)", (key,))

    def purge_expired(self, capability: Capability, now: datetime) -> None:
        posts = [
            SocialPost.model_validate_json(r[0])
            for r in self.db.execute("SELECT payload FROM social_posts")
        ]
        for post in posts:
            if post.capability_reference == capability.reference and (
                capability.retention_days is None
                or not capability.allow_store
                or now >= post.observed_at + timedelta(days=capability.retention_days)
            ):
                self.delete(post.post_id)

    def claims(self, as_of: datetime) -> list[Claim]:
        expired = [
            r[0]
            for r in self.db.execute("SELECT id, expires_at FROM social_posts")
            if datetime.fromisoformat(r[1]) <= as_of
        ]
        for key in expired:
            self.delete(key)
        return [
            Claim.model_validate_json(r[0])
            for r in self.db.execute("SELECT payload FROM social_claims ORDER BY id")
        ]
