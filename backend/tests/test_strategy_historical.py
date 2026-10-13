"""Authored adapter fixtures prove timing/coverage mechanics, not football performance."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("gymnasium")

from fpl_app.contracts import Settings
from fpl_app.domain.rules import RULES
from fpl_app.storage import fingerprint
from fpl_app.strategy.environment import FPLEnv
from fpl_app.strategy.historical import _outcome, reconstruct_collection
from fpl_app.strategy.training import _split_check


def test_zero_minute_participation_is_not_inferred_from_missing_or_card_only_statistics():
    mapping = {"provider_club_id": 1}
    fixtures = {1: {"id": 1, "event": 4, "team_h": 1, "team_a": 2}}
    row = {
        "event": 4,
        "fixture_id": 1,
        "label_status": "final_revision",
        "minutes": 0,
        "total_points": 0,
        "statistics": {"was_home": True},
    }
    with pytest.raises(ValueError, match="Missing official participation"):
        _outcome(1, mapping, [row], fixtures, 4)
    row["statistics"].update(yellow_cards=1, red_cards=0)
    with pytest.raises(ValueError, match="reconciled participation"):
        _outcome(1, mapping, [row], fixtures, 4)
    row["statistics"]["yellow_cards"] = 0
    assert _outcome(1, mapping, [row], fixtures, 4).participated is False


def collection():
    positions = [1] * 4 + [2] * 12 + [3] * 12 + [4] * 8
    mappings = [
        {"provider_player_id": i + 1, "provider_club_id": i % 20 + 1, "position": p}
        for i, p in enumerate(positions)
    ]
    fixtures, labels, evidence = [], [], []
    start = datetime(2026, 8, 1, tzinfo=UTC)
    for event in range(1, 7):
        kickoff = start + timedelta(days=event * 7)
        evidence.append(
            {"event": event, "actual_deadline": (kickoff - timedelta(days=1)).isoformat()}
        )
        for home in range(1, 21, 2):
            fixtures.append(
                {
                    "id": event * 100 + home,
                    "event": event,
                    "team_h": home,
                    "team_a": home + 1,
                    "kickoff_time": kickoff.isoformat(),
                    "finished_provisional": event <= 5,
                }
            )
        for m in mappings:
            club, identifier = m["provider_club_id"], m["provider_player_id"]
            labels.append(
                {
                    "provider_player_id": identifier,
                    "fixture_id": event * 100 + (club if club % 2 else club - 1),
                    "event": event,
                    "label_status": "final_revision" if event <= 5 else "pending_fixture",
                    "minutes": 90 if event <= 5 else None,
                    "total_points": identifier % 7 if event <= 5 else None,
                    "statistics": {
                        "value": 50,
                        "was_home": bool(club % 2),
                        "goals_scored": 0,
                        "assists": 0,
                        "clean_sheets": 0,
                    },
                }
            )
    result = {
        "collection_id": "authored-adapter-fixture",
        "season": RULES.season,
        "player_mappings": mappings,
        "fixture_versions": fixtures,
        "labels": labels,
        "event_evidence": evidence,
        "sources": [],
    }
    result["envelope_sha256"] = fingerprint(result)
    return result


def seal(value):
    value["envelope_sha256"] = fingerprint(
        {k: v for k, v in value.items() if k != "envelope_sha256"}
    )
    return value


def build(value):
    return reconstruct_collection(value, train_events=[2, 3], test_events=[4, 5], universe_size=20)


def test_official_adapter_and_environment_score_without_unknown_component_defaults():
    train, test, audit = build(collection())
    assert audit["independent_actual_seasons"] == 1
    assert audit["forecast_horizon"] == 1
    assert train[0].bootstrap_origin.official_outcomes is not None
    env = FPLEnv(test, Settings(horizon_events=1, max_transfers_this_event=1), k=4)
    _, info = env.reset(seed=7)
    assert info["evidence_mode"] == "historical_reconstructed"
    _, reward, terminated, truncated, result = env.step(0)
    assert reward == result["scoring"]["points"] - result["total_hits"]
    assert not terminated and not truncated
    _, _, terminated, truncated, result = env.step(0)
    assert truncated and not terminated
    assert result["bootstrap_forecast_supported"]
    _split_check(train, test)


def test_target_points_price_and_statistics_do_not_enter_the_same_origin():
    baseline = collection()
    changed = deepcopy(baseline)
    for row in changed["labels"]:
        if row["event"] == 4:
            row["total_points"] = 99
            row["statistics"]["value"] = 99
            row["statistics"]["goals_scored"] = 9
    _, original, audit = build(baseline)
    _, mutated, revised = build(seal(changed))
    assert audit["selected_player_ids"] == revised["selected_player_ids"]
    assert original[0].origins[0].players == mutated[0].origins[0].players
    assert [p.model_dump() for p in original[0].origins[0].forecasts.projections] == [
        p.model_dump() for p in mutated[0].origins[0].forecasts.projections
    ]
    assert original[0].origins[0].official_outcomes != mutated[0].origins[0].official_outcomes


def test_pending_targets_and_invalid_chronology_are_rejected():
    value = collection()
    for row in value["labels"]:
        if row["event"] == 5:
            row["label_status"] = "preliminary"
    with pytest.raises(ValueError, match="provider-finalized"):
        build(seal(value))
    with pytest.raises(ValueError, match="Chronological"):
        reconstruct_collection(
            collection(), train_events=[3, 4], test_events=[4, 5], universe_size=20
        )


def test_missing_prices_and_rows_are_coverage_rejections_not_zero_outcomes():
    value = collection()
    value["labels"] = [
        r for r in value["labels"] if not (r["provider_player_id"] == 5 and r["event"] == 4)
    ]
    for row in value["labels"]:
        if row["provider_player_id"] == 6:
            row["statistics"].pop("value")
    _, _, audit = build(seal(value))
    assert audit["coverage_rejections"]["Missing or mismatched historical fixture coverage"] == 1
    assert audit["coverage_rejections"]["Missing historical price"] == 1
    assert 5 not in audit["selected_player_ids"] and 6 not in audit["selected_player_ids"]


def test_historical_training_guard_does_not_accept_overlapping_event_blocks():
    train, test, _ = build(collection())
    overlapping = replace(
        test[0], origins=train[0].origins, path_id="different-label-same-outcomes"
    )
    with pytest.raises(ValueError, match="Shared train/test outcomes|chronological"):
        _split_check(train, [overlapping])


def test_generated_episode_packets_roundtrip_with_outcome_free_bootstrap():
    from fpl_app.strategy.datasets import episodes_from_payload
    from fpl_app.strategy.training import _episode_payload

    train, test, _ = build(collection())
    payload = {"episodes": [_episode_payload(e) for e in [*train, *test]]}
    loaded = episodes_from_payload(payload)
    assert loaded[0].origins[0].official_outcomes == train[0].origins[0].official_outcomes
    assert loaded[0].bootstrap_origin.official_outcomes == {}
    payload["episodes"][0]["bootstrap_origin"]["official_outcomes"] = {
        "1": {"points": 0, "minutes": 0, "participated": False}
    }
    with pytest.raises(ValueError, match="outcome-free"):
        episodes_from_payload(payload)
