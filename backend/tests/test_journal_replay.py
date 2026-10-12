"""Authored retained contracts test the bridge, not real prospective evidence."""

from copy import deepcopy

import pytest
from test_replay_learning import strict_fixture, write_manifest

from fpl_app.contracts import Settings
from fpl_app.evaluation.strategy import keep_policy, planner_policy, replay_policy
from fpl_app.learning.replay import journal_replay_inputs, seal_journal_replay
from fpl_app.storage import Conflict, Store, fingerprint


def prepare(tmp_path, monkeypatch):
    packet = tmp_path / "replay_inputs" / "retained"
    packet.mkdir(parents=True)
    state, origin, manifest = strict_fixture(packet)
    origin.manifest_path = packet / "manifest.json"
    write_manifest(origin, manifest)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr("fpl_app.learning.replay.utcnow", lambda: "2026-10-09T02:00:00Z")
    store = Store(f"sqlite:///{tmp_path}/journal.sqlite")
    journal = {
        "decision_id": "retained-decision",
        "team_id": state.team_id,
        "event": state.next_event,
        "state_version": state.state_version,
        "data_mode": "live",
        "snapshot_id": origin.forecasts.snapshot_id,
        "decision_origin": origin.information_available_at,
        "deadline": origin.deadline,
        "manager_state": state.model_dump(mode="json"),
        "forecast": origin.forecasts.model_dump(mode="json"),
        "forecast_reference": origin.forecasts.projection_run_id,
        "forecast_sha256": fingerprint(origin.forecasts.model_dump(mode="json")),
        "players": [player.model_dump(mode="json") for player in origin.players],
        "player_universe_ids": sorted(player.player_id for player in origin.players),
        "execution_status": "execution_unknown",
    }
    store.put("decision_journal", journal["decision_id"], journal, expected=0)
    store.put("state", state.team_id, state.model_dump(mode="json"), expected=0)
    return store, journal, origin, manifest


def seal(store, journal, origin, policy=keep_policy):
    return seal_journal_replay(
        store, journal["decision_id"], "retained", origin.manifest_sha256, policy
    )


def test_retained_seal_builds_strict_paper_replay_and_is_idempotent(tmp_path, monkeypatch):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    before = deepcopy(journal)
    first = seal(store, journal, origin)
    assert seal(store, journal, origin) == first
    monkeypatch.setattr("fpl_app.learning.replay.utcnow", lambda: "2026-10-11T02:00:00Z")
    assert seal(store, journal, origin) == first  # Existing seal may be read after deadline.
    state, retained = journal_replay_inputs(
        store, journal["decision_id"], keep_policy, origin.outcomes
    )
    report = replay_policy(state, [retained], keep_policy, Settings(horizon_events=1))
    evidence = report["rows"][0]["provenance"]
    assert evidence["verified"] is True
    assert evidence["journal_reference"]["decision_sha256"] == fingerprint(before)
    assert evidence["journal_reference"]["seal_sha256"] == fingerprint(first)
    assert store.get("decision_journal", journal["decision_id"]) == before
    assert retained.financial_coverage == "journal_known_prices_only"


@pytest.mark.parametrize("at", ["2026-10-10T12:00:00Z", "2026-10-11T00:00:00Z"])
def test_old_unsealed_journal_cannot_be_upgraded(tmp_path, monkeypatch, at):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    monkeypatch.setattr("fpl_app.learning.replay.utcnow", lambda: at)
    with pytest.raises(ValueError, match="before the deadline"):
        seal(store, journal, origin)
    assert store.list("decision_replay_seal") == []


def test_missing_policy_specific_seal_and_unbound_policy_fail(tmp_path, monkeypatch):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    with pytest.raises(KeyError):
        journal_replay_inputs(store, journal["decision_id"], keep_policy, origin.outcomes)
    with pytest.raises(ValueError, match="Policy implementation"):
        seal(store, journal, origin, planner_policy)
    seal(store, journal, origin)
    with pytest.raises(KeyError):
        journal_replay_inputs(store, journal["decision_id"], planner_policy, origin.outcomes)


@pytest.mark.parametrize("mutation", ["manifest", "payload", "journal", "seal"])
def test_retained_mutations_fail_closed(tmp_path, monkeypatch, mutation):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    seal(store, journal, origin)
    if mutation == "manifest":
        origin.manifest_path.write_bytes(b"{}")
    elif mutation == "payload":
        (origin.manifest_path.parent / "source.bin").write_bytes(b"changed")
    elif mutation == "journal":
        journal["manager_state"]["bank_units"] += 1
        store.put("decision_journal", journal["decision_id"], journal)
    else:
        record = store.list("decision_replay_seal")[0]
        record["sealed_at"] = journal["deadline"]
        from fpl_app.learning.replay import _seal_id

        store.put("decision_replay_seal", _seal_id(journal["decision_id"], keep_policy), record)
    with pytest.raises(ValueError):
        journal_replay_inputs(store, journal["decision_id"], keep_policy, origin.outcomes)


def test_conflicting_reseal_and_symlink_paths_fail(tmp_path, monkeypatch):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    seal(store, journal, origin)
    with pytest.raises(Conflict):
        seal_journal_replay(store, journal["decision_id"], "other", "a" * 64, keep_policy)
    with pytest.raises(ValueError, match="Invalid replay packet"):
        seal_journal_replay(store, journal["decision_id"], "../retained", "a" * 64, planner_policy)
    origin.manifest_path.rename(origin.manifest_path.with_suffix(".saved"))
    origin.manifest_path.symlink_to(origin.manifest_path.with_suffix(".saved"))
    with pytest.raises(ValueError, match="symlinks"):
        journal_replay_inputs(store, journal["decision_id"], keep_policy, origin.outcomes)


def test_team_deletion_removes_private_replay_seal(tmp_path, monkeypatch):
    store, journal, origin, _ = prepare(tmp_path, monkeypatch)
    seal(store, journal, origin)
    store.delete_team(journal["team_id"])
    assert store.list("decision_replay_seal") == []
    assert store.list("decision_journal") == []


def test_actual_api_frozen_journal_seals_and_replays_without_state_edits(tmp_path, monkeypatch):
    import hashlib
    import inspect
    from pathlib import Path

    from fastapi.testclient import TestClient
    from test_learning_journal import make_recommendation, prepare_live

    from fpl_app.api import create_app
    from fpl_app.contracts import Player, ProjectionRun
    from fpl_app.domain.rules import MatchStats
    from fpl_app.evaluation.provenance import ReplayArtifact, ReplayManifest, implementation_sha256

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr("fpl_app.models.router.utcnow", lambda: "2026-10-09T08:00:00Z")
    monkeypatch.setattr("fpl_app.learning.replay.utcnow", lambda: "2026-10-09T08:01:00Z")
    store, state, _, _ = prepare_live(tmp_path, monkeypatch)
    client = TestClient(create_app(store))
    recommendation = make_recommendation(client)
    response = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": recommendation["recommendation_id"],
            "idempotency_key": "replay",
        },
    )
    assert response.status_code == 201, response.text
    journal = store.get("decision_journal", response.json()["decision_id"])
    before_state = store.get("state", state.team_id)
    packet = tmp_path / "replay_inputs" / "api-frozen"
    packet.mkdir(parents=True)
    artifacts = []
    for role in ("source", "model", "policy", "mapping"):
        raw = (
            Path(inspect.getsourcefile(keep_policy)).read_bytes()
            if role == "policy"
            else role.encode()
        )
        name = f"{role}.bin"
        (packet / name).write_bytes(raw)
        artifacts.append(
            ReplayArtifact(
                role=role,
                filename=name,
                sha256=hashlib.sha256(raw).hexdigest(),
                captured_at=journal["source_cutoff"],
                available_at=journal["source_cutoff"],
            )
        )
    run = ProjectionRun.model_validate(journal["forecast"])
    manifest = ReplayManifest(
        deadline=journal["deadline"],
        information_available_at=journal["decision_origin"],
        forecast=run,
        players=[Player.model_validate(player) for player in journal["players"]],
        schedule_complete_events=[journal["event"]],
        artifacts=artifacts,
        policy_identifier=f"{keep_policy.__module__}.{keep_policy.__qualname__}",
        implementation_sha256=implementation_sha256(),
    )
    raw = manifest.model_dump_json().encode()
    (packet / "manifest.json").write_bytes(raw)
    seal_journal_replay(
        store, journal["decision_id"], "api-frozen", hashlib.sha256(raw).hexdigest(), keep_policy
    )
    outcomes = {player["player_id"]: [MatchStats(minutes=90)] for player in journal["players"]}
    initial, origin = journal_replay_inputs(store, journal["decision_id"], keep_policy, outcomes)
    report = replay_policy(
        initial, [origin], keep_policy, Settings.model_validate(journal["settings"])
    )
    assert report["legal"] and report["rows"][0]["provenance"]["verified"]
    assert store.get("state", state.team_id) == before_state
    assert store.get("decision_journal", journal["decision_id"]) == journal
