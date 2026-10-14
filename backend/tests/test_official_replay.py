"""Authored finalized payloads validate integrity, never real prospective accuracy."""

import json
from copy import deepcopy

import pytest
from sqlalchemy import update
from test_journal_replay import prepare, seal

from fpl_app.contracts import Settings
from fpl_app.evaluation.strategy import keep_policy, replay_policy
from fpl_app.learning.official_replay import official_replay_inputs
from fpl_app.learning.outcomes import SCORING_VERSION, build_finalized_outcomes
from fpl_app.storage import fingerprint, snapshots


def payloads(journal):
    fixtures = [
        {
            "id": row["fixture_id"],
            "event": row["event"],
            "team_h": row["home_club"],
            "team_a": row["away_club"],
            "finished": True,
        }
        for row in journal["fixtures"]
    ]
    live = {"elements": []}
    for player in journal["players"]:
        fixture = next(f for f in fixtures if player["club"] in (f["team_h"], f["team_a"]))
        live["elements"].append(
            {
                "id": player["player_id"],
                "stats": {"total_points": 2, "minutes": 90, "yellow_cards": 0, "red_cards": 0},
                "explain": [
                    {
                        "fixture": fixture["id"],
                        "stats": [{"identifier": "minutes", "value": 90, "points": 2}],
                    }
                ],
            }
        )
    return fixtures, live


def setup(tmp_path, monkeypatch):
    store, journal, origin, _manifest = prepare(tmp_path, monkeypatch)
    journal["fixtures"] = [f.model_dump(mode="json") for f in origin.forecasts.fixtures]
    store.put("decision_journal", journal["decision_id"], journal)
    seal(store, journal, origin)
    return store, journal, origin


def persist(store, journal, fixtures, live, *, finalized=True):
    bootstrap = {
        "events": [{"id": journal["event"], "finished": finalized, "data_checked": finalized}]
    }
    refs = [
        store.snapshot(store.archive(json.dumps(payload).encode(), resource))
        for payload, resource in (
            (bootstrap, "bootstrap-static/"),
            (fixtures, "fixtures/"),
            (live, f"event/{journal['event']}/live/"),
        )
    ]
    rows, scores = build_finalized_outcomes(
        journal, {"event": journal["event"], "ready": True}, fixtures, live
    )
    digest = fingerprint(
        {
            "decision_id": journal["decision_id"],
            "finalization_sha256": refs[0]["payload_sha256"],
            "fixture_sha256": refs[1]["payload_sha256"],
            "live_sha256": refs[2]["payload_sha256"],
            "outcomes": rows,
            "scoring_version": SCORING_VERSION,
        }
    )
    revision = {
        "decision_id": journal["decision_id"],
        "event": journal["event"],
        "revision": digest,
        "finalization_source": {
            "finalization_snapshot_id": refs[0]["id"],
            "finalization_sha256": refs[0]["payload_sha256"],
            "source_captured_at": refs[0]["captured_at"],
        },
        "fixture_source_snapshot_id": refs[1]["id"],
        "fixture_source_sha256": refs[1]["payload_sha256"],
        "live_source_snapshot_id": refs[2]["id"],
        "live_source_sha256": refs[2]["payload_sha256"],
        "captured_at": refs[2]["captured_at"],
        "scoring_version": SCORING_VERSION,
        "outcomes": rows,
        "scores": scores,
    }
    key = f"{journal['decision_id']}:{digest}"
    store.put("learning_outcome", key, revision, expected=0)
    return key, revision


def test_official_revision_positive_replay_and_correction_are_explicit(tmp_path, monkeypatch):
    store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    first, _ = persist(store, journal, fixtures, live)
    private_before = store.get("state", journal["team_id"])
    state, origin = official_replay_inputs(store, journal["decision_id"], keep_policy, first)
    assert origin.outcomes == {}
    assert set(origin.official_outcomes) == set(journal["player_universe_ids"])
    report = replay_policy(state, [origin], keep_policy, Settings(horizon_events=1))
    assert report["realised_net_points"] == 24
    assert report["rows"][0]["provenance"]["journal_reference"]["outcome_revision_id"] == first
    live["elements"][0]["stats"]["total_points"] = 3
    live["elements"][0]["explain"][0]["stats"][0]["points"] = 3
    second, _ = persist(store, journal, fixtures, live)
    assert second != first
    assert (
        official_replay_inputs(store, journal["decision_id"], keep_policy, first)[1]
        .official_outcomes[1]
        .points
        == 2
    )
    assert (
        official_replay_inputs(store, journal["decision_id"], keep_policy, second)[1]
        .official_outcomes[1]
        .points
        == 3
    )
    assert store.get("state", journal["team_id"]) == private_before


@pytest.mark.parametrize(
    "mutation",
    ["raw", "revision", "scores", "finalization", "early_capture", "source_mode", "missing_seal"],
)
def test_official_replay_mutations_fail_closed(tmp_path, monkeypatch, mutation):
    store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    key, revision = persist(store, journal, fixtures, live, finalized=mutation != "finalization")
    if mutation == "revision":
        revision["outcomes"][0]["points"] += 1
        store.put("learning_outcome", key, revision)
    elif mutation == "scores":
        revision["scores"][0]["actual_points"] += 1
        store.put("learning_outcome", key, revision)
    elif mutation in {"raw", "early_capture", "source_mode"}:
        values = (
            {"raw": b"{}"}
            if mutation == "raw"
            else {"captured_at": "2026-10-08T01:00:00Z"}
            if mutation == "early_capture"
            else {"data_mode": "demo"}
        )
        identifier = revision["finalization_source"]["finalization_snapshot_id"]
        with store.engine.begin() as connection:
            connection.execute(
                update(snapshots).where(snapshots.c.id == identifier).values(**values)
            )
    elif mutation == "missing_seal":
        from sqlalchemy import delete

        from fpl_app.learning.replay import _seal_id
        from fpl_app.storage import entities

        with store.engine.begin() as connection:
            connection.execute(
                delete(entities).where(
                    entities.c.kind == "decision_replay_seal",
                    entities.c.id == _seal_id(journal["decision_id"], keep_policy),
                )
            )
    with pytest.raises((ValueError, KeyError)):
        official_replay_inputs(store, journal["decision_id"], keep_policy, key)


@pytest.mark.parametrize("case", ["missing_cards", "card_only", "zero_minute_points"])
def test_zero_minute_participation_is_visible_and_gated(tmp_path, monkeypatch, case):
    store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    row = live["elements"][0]
    row["stats"].update(total_points=0, minutes=0)
    row["explain"] = []
    if case == "missing_cards":
        del row["stats"]["yellow_cards"]
    elif case == "card_only":
        row["stats"].update(yellow_cards=1, total_points=-1)
        row["explain"] = [
            {
                "fixture": fixtures[0]["id"],
                "stats": [{"identifier": "yellow_cards", "value": 1, "points": -1}],
            }
        ]
    else:
        row["stats"]["total_points"] = 1
        row["explain"] = [
            {
                "fixture": fixtures[0]["id"],
                "stats": [{"identifier": "bonus", "value": 1, "points": 1}],
            }
        ]
    key, revision = persist(store, journal, fixtures, live)
    assert revision["outcomes"][0]["appearance"] == (1 if case == "card_only" else None)
    with pytest.raises(ValueError, match="participation"):
        official_replay_inputs(store, journal["decision_id"], keep_policy, key)


def test_explicit_absence_and_double_reconcile_without_fabricated_fixture_minutes(
    tmp_path, monkeypatch
):
    _store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    double = dict(fixtures[0], id=999)
    fixtures.append(double)
    journal["fixtures"].append(dict(journal["fixtures"][0], fixture_id=999))
    for projection in list(journal["forecast"]["projections"]):
        if projection["fixture_id"] == fixtures[0]["id"]:
            journal["forecast"]["projections"].append(dict(projection, fixture_id=999))
    for element in live["elements"]:
        if element["explain"][0]["fixture"] == fixtures[0]["id"]:
            element["stats"].update(total_points=4, minutes=180)
            element["explain"].append(dict(element["explain"][0], fixture=999))
    rows, _ = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["points"] == 4 and rows[0]["minutes"] == 180
    live["elements"][0]["stats"].update(total_points=0, minutes=0)
    live["elements"][0]["explain"] = []
    rows, _ = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["appearance"] == 0
    assert all(row["status"] == "final_nonappearance" for row in rows[0]["fixtures"])
    live["elements"][0]["stats"].update(total_points=2, minutes=90)
    live["elements"][0]["explain"] = [
        {
            "fixture": fixtures[0]["id"],
            "stats": [{"identifier": "minutes", "value": 90, "points": 2}],
        }
    ]
    rows, _ = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["fixtures"][1]["status"] == "missing_fixture_explanation"
    assert rows[0]["fixtures"][1]["minutes"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_player",
        "duplicate_fixture",
        "duplicate_explain",
        "duplicate_stat",
        "boolean_points",
        "negative_minutes",
        "wrong_minutes",
        "wrong_points",
        "outside_fixture",
    ],
)
def test_malformed_official_rows_reject(tmp_path, monkeypatch, mutation):
    _, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    element = live["elements"][0]
    if mutation == "duplicate_player":
        live["elements"].append(deepcopy(element))
    elif mutation == "duplicate_fixture":
        fixtures.append(deepcopy(fixtures[0]))
    elif mutation == "duplicate_explain":
        element["explain"].append(deepcopy(element["explain"][0]))
    elif mutation == "duplicate_stat":
        element["explain"][0]["stats"].append(deepcopy(element["explain"][0]["stats"][0]))
    elif mutation == "boolean_points":
        element["stats"]["total_points"] = True
    elif mutation == "negative_minutes":
        element["stats"]["minutes"] = -1
    elif mutation == "wrong_minutes":
        element["stats"]["minutes"] = 89
    elif mutation == "wrong_points":
        element["stats"]["total_points"] = 3
    else:
        element["explain"][0]["fixture"] = 999
    with pytest.raises(ValueError):
        build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)


def test_original_blank_and_reassigned_club_are_not_scored_as_zero(tmp_path, monkeypatch):
    _, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    original = fixtures[0]
    journal["fixtures"] = [f for f in journal["fixtures"] if f["fixture_id"] != original["id"]]
    journal["forecast"]["projections"] = [
        p for p in journal["forecast"]["projections"] if p["fixture_id"] != original["id"]
    ]
    rows, scores = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["status"] == "fixture_reassigned_or_schedule_unknown"
    assert rows[0]["points"] is None
    assert all(row["player_id"] != 1 for row in scores)
    # A genuine explicit final blank requires checked zero participation evidence.
    fixtures.pop(0)
    for element in live["elements"]:
        if element["explain"][0]["fixture"] == original["id"]:
            element["stats"].update(total_points=0, minutes=0)
            element["explain"] = []
    rows, _ = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["status"] == "blank_event" and rows[0]["appearance"] == 0


@pytest.mark.parametrize(
    "mutation", ["added_fixture", "changed_clubs", "pending", "missing_player", "missing_cards"]
)
def test_incomplete_schedule_or_participation_never_enters_replay(tmp_path, monkeypatch, mutation):
    store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    if mutation == "added_fixture":
        fixtures.append(dict(fixtures[0], id=999))
    elif mutation == "changed_clubs":
        fixtures[0]["team_a"] = 199
    elif mutation == "pending":
        fixtures[0]["finished"] = False
    elif mutation == "missing_player":
        live["elements"].pop()
        with pytest.raises(ValueError, match="miss forecast-universe"):
            persist(store, journal, fixtures, live)
        return
    else:
        live["elements"][0]["stats"].update(total_points=0, minutes=0)
        live["elements"][0]["explain"] = []
        del live["elements"][0]["stats"]["red_cards"]
    key, revision = persist(store, journal, fixtures, live)
    if mutation != "missing_cards":
        assert revision["outcomes"][0]["points"] is None
        assert revision["outcomes"][0]["fixtures"][0]["points"] is None
    with pytest.raises(ValueError, match="coverage"):
        official_replay_inputs(store, journal["decision_id"], keep_policy, key)


def test_missing_fixture_minutes_remain_unknown_and_card_reconciliation_rejects(
    tmp_path, monkeypatch
):
    _, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    live["elements"][0]["explain"][0]["stats"] = [{"identifier": "bonus", "points": 2, "value": 2}]
    rows, _ = build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)
    assert rows[0]["minutes"] == 90
    assert rows[0]["fixtures"][0]["minutes"] is None
    live["elements"][0]["explain"][0]["stats"].append(
        {"identifier": "yellow_cards", "points": 0, "value": 1}
    )
    with pytest.raises(ValueError, match="cards do not reconcile"):
        build_finalized_outcomes(journal, {"event": 8, "ready": True}, fixtures, live)


def test_legacy_revision_requires_new_checked_capture_without_mutation(tmp_path, monkeypatch):
    store, journal, _ = setup(tmp_path, monkeypatch)
    fixtures, live = payloads(journal)
    key, revision = persist(store, journal, fixtures, live)
    revision["scoring_version"] = "official-fpl-live-total-points-v1"
    store.put("learning_outcome", key, revision)
    before = deepcopy(revision)
    with pytest.raises(ValueError, match="collect a new checked v2 revision"):
        official_replay_inputs(store, journal["decision_id"], keep_policy, key)
    assert store.get("learning_outcome", key) == before
