"""Offline authored synthetic tests, not an adjudicated extraction benchmark."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fpl_app.social import (
    Capability,
    Coverage,
    Extractor,
    RedditAdapter,
    SocialPost,
    SocialStore,
    SourceProfile,
    XAdapter,
    aggregate,
)
from fpl_app.social.fixtures import ALIASES, SYNTHETIC_CASES

NOW = datetime(2026, 10, 10, tzinfo=UTC)
CAP = Capability(
    provider="synthetic",
    reference="authored-test-v1",
    allow_store=True,
    allow_inference=True,
    allow_derived_features=True,
    retention_days=7,
)
EXTRACTOR = Extractor(ALIASES)


def post(text: str, key: str = "synthetic:1", author: str = "author", **kwargs):
    return SocialPost(
        post_id=key,
        author_id=author,
        provider="synthetic",
        text=text,
        created_at=NOW,
        observed_at=NOW,
        query="authored fixture",
        capability_reference=CAP.reference,
        synthetic=True,
        **kwargs,
    )


def review(store, author, group="expert", **kwargs):
    store.review(
        SourceProfile(
            author_id=author,
            group=group,
            topics=("strategy", "captaincy"),
            evidence="Authored synthetic reviewer evidence",
            reviewer="test reviewer",
            reviewed_at=NOW,
            effective_at=NOW,
            expires_at=NOW + timedelta(days=2),
            version=1,
            **kwargs,
        )
    )


def coverage(status="available"):
    return Coverage(status=status, query="authored fixture", start=NOW, end=NOW, synthetic=True)


@pytest.mark.parametrize("text,player,action,abstention", SYNTHETIC_CASES)
def test_authored_extraction(text, player, action, abstention):
    claims = EXTRACTOR.extract(post(text), CAP)
    claim = next(c for c in claims if c.player_id == player)
    assert (claim.action, claim.abstention) == (action, abstention)
    assert text[claim.span_start : claim.span_end] == claim.evidence_span


def test_funding_and_condition():
    claims = EXTRACTOR.extract(post("Palmer is brilliant, but sell him to fund Salah."), CAP)
    assert {(c.player_id, c.action, c.funding_player_id) for c in claims} == {
        ("palmer", "sell", "salah"),
        ("salah", "buy", "palmer"),
    }
    claim = EXTRACTOR.extract(post("I would captain Haaland only if he starts."), CAP)[0]
    assert claim.condition == "if he starts."
    quoted = EXTRACTOR.extract(
        post("The reporter says Haaland trained. That does not mean he starts."), CAP
    )
    assert all(c.action == "unclear" and c.abstention for c in quoted)
    assert quoted[0].attribution == "The reporter"


def test_disabled_adapters_and_separate_rights():
    for adapter in (RedditAdapter(), XAdapter()):
        assert adapter.status().status == "unavailable"
        assert not adapter.capability.allow_read
        with pytest.raises(PermissionError):
            adapter.fetch()
    assert not CAP.allow_training and not CAP.allow_external_processing
    with pytest.raises(PermissionError):
        EXTRACTOR.extract(post("Buy Salah"), CAP.model_copy(update={"allow_inference": False}))


def test_registry_asof_and_topic(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    review(store, "author")
    assert store.group("author", "strategy", NOW) == "expert"
    assert store.group("author", "availability", NOW) == "unknown"
    assert store.group("author", "strategy", NOW - timedelta(seconds=1)) == "unknown"
    assert store.group("author", "strategy", NOW + timedelta(days=3)) == "unknown"
    store.close()


def test_dedup_and_missing_coverage(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    for author in ("a", "b"):
        review(store, author)
    review(store, "c", "crowd")
    for i in range(10):
        store.ingest(
            post("Buy Salah.", f"synthetic:{i}", "a", evidence_family="report"), CAP, EXTRACTOR, NOW
        )
    store.ingest(
        post("Buy Salah.", "synthetic:b", "b", evidence_family="report"), CAP, EXTRACTOR, NOW
    )
    store.ingest(post("Sell Salah.", "synthetic:c", "c"), CAP, EXTRACTOR, NOW)

    def summary(group="expert", cov=None):
        return aggregate(store, "salah", "strategy", "unspecified", group, cov or coverage(), NOW)

    result = summary()
    assert result.distribution == {"buy": 1.0}
    assert result.distinct_authors == 2 and result.evidence_families == 1
    assert result.effective_sample_size == 2  # Author ESS, not independent-family ESS.
    assert summary("crowd").distribution == {"sell": 1.0}
    assert summary(cov=coverage("unavailable")).distribution is None
    assert summary(cov=coverage("stale")).status == "stale"
    assert result.points_adjustment == 0
    store.delete("synthetic:c")
    assert summary("crowd").status == "unavailable"
    store.close()


def test_edit_delete_context_retention_and_reopen(tmp_path: Path):
    path = tmp_path / "social.sqlite"
    store = SocialStore(path)
    store.ingest(post("Buy Salah."), CAP, EXTRACTOR, NOW)
    store.ingest(post("Sell Salah."), CAP, EXTRACTOR, NOW)
    assert [c.action for c in store.claims(NOW)] == ["sell"]
    store.ingest(
        post("Buy Salah.", "synthetic:child", context_ids=("synthetic:1",)), CAP, EXTRACTOR, NOW
    )
    store.delete("synthetic:1")
    assert not store.claims(NOW)
    with pytest.raises(ValueError, match="Deleted"):
        store.ingest(post("Buy Salah."), CAP, EXTRACTOR, NOW)
    store.ingest(post("Buy Salah.", "synthetic:new"), CAP, EXTRACTOR, NOW)
    store.close()
    store = SocialStore(path)
    assert len(store.claims(NOW)) == 1
    store.purge_expired(CAP, NOW + timedelta(days=7))
    assert not store.claims(NOW)
    store.close()


def test_conditional_quotes_negation_not_votes(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    review(store, "author")
    for i, text in enumerate(
        ("Buy Salah if he starts.", "Do not buy Salah.", 'Reporter says "buy Salah".', "Buy Salah?")
    ):
        store.ingest(post(text, f"synthetic:{i}"), CAP, EXTRACTOR, NOW)
    result = aggregate(store, "salah", "strategy", "unspecified", "expert", coverage(), NOW)
    assert result.status == "unavailable" and result.distribution is None
    store.close()


def test_funding_negation_and_exact_copy_families(tmp_path: Path):
    claims = EXTRACTOR.extract(post("Do not sell Palmer to fund Salah."), CAP)
    assert {c.action for c in claims} == {"buy", "sell"}
    assert all(c.negated and c.abstention == "negated_action" for c in claims)
    store = SocialStore(tmp_path / "social.sqlite")
    for author in ("a", "b"):
        review(store, author)
        store.ingest(post("Buy Salah.", f"synthetic:{author}", author), CAP, EXTRACTOR, NOW)
    result = aggregate(store, "salah", "strategy", "unspecified", "expert", coverage(), NOW)
    assert result.distinct_authors == 2 and result.evidence_families == 1
    store.close()


def test_same_author_conflict_and_future_coverage(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    review(store, "author")
    for i, text in enumerate(("Buy Salah.", "Sell Salah.")):
        store.ingest(
            post(text, f"synthetic:{i}", evidence_family="same-report"), CAP, EXTRACTOR, NOW
        )
    result = aggregate(store, "salah", "strategy", "unspecified", "expert", coverage(), NOW)
    assert result.distribution == {"unclear": 1.0}
    assert result.distinct_authors == 1 and result.effective_sample_size == 1
    future = coverage().model_copy(update={"end": NOW + timedelta(hours=1)})
    assert (
        aggregate(store, "salah", "strategy", "unspecified", "expert", future, NOW).distribution
        is None
    )
    store.close()


def test_timing_and_retention_fail_closed(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    with pytest.raises(PermissionError):
        store.ingest(
            post("Buy Salah."), CAP.model_copy(update={"allow_store": False}), EXTRACTOR, NOW
        )
    with pytest.raises(ValueError, match="timing"):
        store.ingest(
            post("Buy Salah.").model_copy(update={"observed_at": NOW + timedelta(days=1)}),
            CAP,
            EXTRACTOR,
            NOW,
        )
    with pytest.raises(PermissionError):
        EXTRACTOR.extract(post("Buy Salah."), CAP.model_copy(update={"reference": "wrong"}))
    store.ingest(post("Buy Salah."), CAP, EXTRACTOR, NOW)
    assert store.claims(NOW + timedelta(days=7)) == []
    assert store.db.execute("SELECT COUNT(*) FROM social_posts").fetchone()[0] == 0
    store.close()


def test_later_review_cannot_upgrade_earlier_claim(tmp_path: Path):
    store = SocialStore(tmp_path / "social.sqlite")
    store.ingest(post("Buy Salah."), CAP, EXTRACTOR, NOW)
    later = NOW + timedelta(hours=1)
    store.review(
        SourceProfile(
            author_id="author",
            group="expert",
            topics=("strategy",),
            evidence="Authored synthetic evidence",
            reviewer="reviewer",
            reviewed_at=later,
            effective_at=NOW,
            expires_at=NOW + timedelta(days=2),
            version=1,
        )
    )
    result = aggregate(store, "salah", "strategy", "unspecified", "expert", coverage(), later)
    assert result.distribution is None
    unknown = aggregate(store, "salah", "strategy", "unspecified", "unknown", coverage(), later)
    assert unknown.distribution == {"buy": 1.0}
    store.close()
