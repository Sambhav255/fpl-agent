"""Authored synthetic CI examples: no real source or expert-accuracy assertions."""

from datetime import UTC, datetime, timedelta

import pytest

from fpl_app.social.manual import ManualImport, availability_scenarios, import_manual
from fpl_app.social.store import SocialStore

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def bundle(posts=None, **changes):
    text = "Synthetic Player is out for GW10."
    data = {
        "capability": {
            "provider": "synthetic",
            "reference": "authored-ci-only",
            "allow_store": True,
            "allow_inference": True,
            "allow_derived_features": True,
            "retention_days": 2,
        },
        "material": "synthetic_fixture",
        "permission_evidence": "Authored synthetic test text",
        "reviewer": "synthetic-fixture-author",
        "entity_reference": "synthetic-test-IDs-v1",
        "player_ids": ["player-1"],
        "posts": posts
        or [
            {
                "post_id": "synthetic:1",
                "author_id": "synthetic-author",
                "text": text,
                "created_at": NOW - timedelta(days=1),
                "claims": [
                    {
                        "player_id": "player-1",
                        "topic": "availability",
                        "span_start": 0,
                        "span_end": len(text),
                        "horizon": "GW10",
                        "kind": "report",
                        "assertion": "out",
                    }
                ],
            }
        ],
    }
    data.update(changes)
    return ManualImport.model_validate(data)


def test_import_observation_is_actual_time_retry_is_idempotent_and_delete_is_final(tmp_path):
    store = SocialStore(tmp_path / "social.sqlite")
    receipt = import_manual(store, bundle(), NOW)
    assert receipt["claims"] == 1 and receipt["synthetic"] and receipt["points_adjustment"] == 0
    assert store.claims(NOW - timedelta(seconds=1)) == []
    assert store.claims(NOW)[0].observed_at == NOW
    assert store.claims(NOW)[0].reviewed_by == "synthetic-fixture-author"
    repeat = import_manual(store, bundle(), NOW + timedelta(hours=1))
    assert repeat["replayed"] and repeat["observed_at"] == NOW.isoformat()
    assert len(store.claims(NOW + timedelta(hours=1))) == 1
    store.delete("synthetic:1")
    assert store.claims(NOW) == []
    repeat = import_manual(store, bundle(), NOW + timedelta(hours=1))
    assert repeat["active_posts"] == 0
    # Receipts carry lineage, never another copy of deletable source text.
    assert (
        "Synthetic Player is out"
        not in store.db.execute("SELECT payload FROM social_manual_receipts").fetchone()[0]
    )
    store.close()


def test_span_and_entity_validation_leave_no_partial_import(tmp_path):
    store = SocialStore(tmp_path / "social.sqlite")
    data = bundle().model_dump(mode="json")
    for bad in [{"span_end": 500}, {"player_id": "unresolved-player"}]:
        edited = bundle().model_dump(mode="json")
        edited["posts"][0]["claims"][0].update(bad)
        with pytest.raises(ValueError):
            import_manual(store, ManualImport.model_validate(edited), NOW)
    assert store.db.execute("SELECT count(*) FROM social_posts").fetchone()[0] == 0
    data["posts"][0]["created_at"] = (NOW + timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError, match="Future"):
        import_manual(store, ManualImport.model_validate(data), NOW)
    store.close()


def test_mid_import_failure_rolls_back_posts_and_profile_review(tmp_path):
    store = SocialStore(tmp_path / "social.sqlite")
    store.delete("synthetic:deleted")
    data = bundle().model_dump(mode="json")
    second = {**data["posts"][0], "post_id": "synthetic:deleted"}
    data["posts"].append(second)
    data["profiles"] = [
        {
            "author_id": "synthetic-author",
            "group": "expert",
            "topics": ["availability"],
            "evidence": "Synthetic role fixture only",
            "reviewer": "test",
            "reviewed_at": NOW,
            "effective_at": NOW,
            "expires_at": NOW + timedelta(days=1),
            "version": 1,
        }
    ]
    with pytest.raises(ValueError, match="Deleted"):
        import_manual(store, ManualImport.model_validate(data), NOW)
    assert store.db.execute("SELECT count(*) FROM social_posts").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM social_reviews").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM social_manual_receipts").fetchone()[0] == 0
    store.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"allow_training": True},
        {"allow_external_processing": True},
        {"allow_inference": False},
        {"retention_days": None},
        {"provider": "reddit"},
    ],
)
def test_manual_rights_do_not_enable_provider_collection_or_training(tmp_path, changes):
    store = SocialStore(tmp_path / "social.sqlite")
    data = bundle().model_dump(mode="json")
    data["capability"].update(changes)
    with pytest.raises(PermissionError):
        import_manual(store, ManualImport.model_validate(data), NOW)
    assert not store.claims(NOW)
    store.close()


def test_availability_scenarios_preserve_conflicts_groups_conditions_and_prior(tmp_path):
    store = SocialStore(tmp_path / "social.sqlite")
    data = bundle().model_dump(mode="json")
    out = data["posts"][0]
    available = {
        **out,
        "post_id": "synthetic:2",
        "author_id": "crowd-author",
        "text": "Synthetic Player is available.",
    }
    available["claims"] = [
        {**out["claims"][0], "assertion": "available", "span_end": len(available["text"])}
    ]
    duplicate = {**out, "post_id": "synthetic:3"}
    conditional = {**out, "post_id": "synthetic:4", "text": "Synthetic Player starts if fit."}
    conditional["claims"] = [
        {
            **out["claims"][0],
            "assertion": "starts",
            "condition": "if fit",
            "span_end": len(conditional["text"]),
        }
    ]
    data["posts"] = [out, available, duplicate, conditional]
    data["profiles"] = [
        {
            "author_id": author,
            "group": group,
            "topics": ["availability"],
            "evidence": "Authored synthetic role evidence",
            "reviewer": "test",
            "reviewed_at": NOW,
            "effective_at": NOW,
            "expires_at": NOW + timedelta(days=1),
            "version": 1,
        }
        for author, group in [("synthetic-author", "expert"), ("crowd-author", "crowd")]
    ]
    import_manual(store, ManualImport.model_validate(data), NOW)
    before = availability_scenarios(store, NOW - timedelta(seconds=1), "GW10")
    assert before["status"] == "unavailable"
    result = availability_scenarios(store, NOW, "GW10")
    player = result["players"][0]
    assert player["contradictory"] and not player["forecast_change_applied"]
    assert len(player["branches"]) == 3
    assert {b["source_group"] for b in player["branches"]} == {"expert", "crowd"}
    assert all(b["reliability"]["status"] == "prior_only" for b in player["branches"])
    assert next(b for b in player["branches"] if b["assertion"] == "starts")["review_required"]
    assert result["points_adjustment"] == 0
    assert availability_scenarios(store, NOW, "GW11")["status"] == "unavailable"
    assert availability_scenarios(store, NOW + timedelta(days=2), "GW10")["status"] == "unavailable"
    store.close()


def test_manual_import_permissioned_authored_text_preserves_context_deletion(tmp_path):
    store = SocialStore(tmp_path / "social.sqlite")
    data = bundle().model_dump(mode="json")
    data.update(
        material="self_authored",
        permission_evidence="Operator declares ownership of authored example",
    )
    data["capability"].update(provider="permissioned")
    data["posts"][0]["post_id"] = "permissioned:original"
    child = {
        **data["posts"][0],
        "post_id": "permissioned:child",
        "context_ids": ["permissioned:original"],
    }
    data["posts"].append(child)
    import_manual(store, ManualImport.model_validate(data), NOW)
    store.delete("permissioned:original")
    assert not store.claims(NOW)
    store.close()
