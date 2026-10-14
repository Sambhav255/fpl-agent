"""Offline actual queue/worker capture ordering, not football performance evidence."""

from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient
from test_learning_journal import live_bootstrap, prepare_live

from fpl_app.api import create_app
from fpl_app.evaluation.strategy import keep_policy, planner_policy, proxy_planner_policy
from fpl_app.jobs import Worker
from fpl_app.learning.packets import capture_replay_evidence, produce_journal_replay_packet
from fpl_app.providers import Provider


def prepared(tmp_path, monkeypatch):
    store, state, data, fixtures = prepare_live(tmp_path, monkeypatch)
    bootstrap = live_bootstrap(data["players"])
    bootstrap["events"][0]["is_next"] = True
    monkeypatch.setattr("fpl_app.storage.utcnow", lambda: "2026-10-09T07:00:00Z")

    def respond(request):
        return httpx.Response(
            200, json=bootstrap if request.url.path.endswith("bootstrap-static/") else fixtures
        )

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    normalized = provider.refresh(force=True)
    state.snapshot_id = normalized["snapshot_id"]
    store.put("state", state.team_id, state.model_dump(mode="json"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr("fpl_app.learning.packets.utcnow", lambda: "2026-10-09T08:01:00Z")
    monkeypatch.setattr("fpl_app.models.router.utcnow", lambda: "2026-10-09T08:02:00Z")
    monkeypatch.setattr("fpl_app.learning.journal.utcnow", lambda: "2026-10-09T08:04:00Z")
    monkeypatch.setattr("fpl_app.learning.replay.utcnow", lambda: "2026-10-09T08:05:00Z")
    client = TestClient(create_app(store, provider))
    return store, state, client


def freeze(client, capture_id=None):
    request = {"team_id": 0, "horizon_events": 1}
    if capture_id:
        request["replay_capture_id"] = capture_id
    job = client.post("/api/v1/projections/runs", json=request)
    assert job.status_code == 202, job.text
    assert Worker(client.app.state.queue).run_once()
    complete = client.get("/api/v1/jobs/" + job.json()["job_id"]).json()
    assert complete["status"] == "succeeded", complete
    run = complete["result"]
    job = client.post(
        "/api/v1/recommendations",
        json={
            "team_id": 0,
            "expected_state_version": client.get("/api/v1/teams/0/state").json()["state_version"],
            "projection_run_id": run["projection_run_id"],
            "settings": {"horizon_events": 1, "solver_time_limit_seconds": 0.2},
        },
    )
    assert job.status_code == 202, job.text
    assert Worker(client.app.state.queue).run_once()
    complete = client.get("/api/v1/jobs/" + job.json()["job_id"]).json()
    assert complete["status"] == "succeeded", complete
    frozen = client.post(
        "/api/v1/learning/decisions",
        json={
            "recommendation_id": complete["result"]["recommendation_id"],
            "idempotency_key": run["projection_run_id"],
        },
    )
    assert frozen.status_code == 201, frozen.text
    return frozen.json(), run


def test_producer_captures_three_policies_before_forecast_and_seals_without_state_edits(
    tmp_path, monkeypatch
):
    store, state, client = prepared(tmp_path, monkeypatch)
    before = deepcopy(store.get("state", state.team_id))
    policies = [keep_policy, planner_policy, proxy_planner_policy]
    captures = [capture_replay_evidence(store, state.team_id, 1, policy) for policy in policies]
    journal, run = freeze(client, captures[0]["capture_id"])
    assert run["projection_run_id"].startswith("baseline-replay-")
    for capture, policy in zip(captures, policies, strict=True):
        first = produce_journal_replay_packet(
            store, journal["decision_id"], capture["capture_id"], policy
        )
        assert first["evidence_mode"] == "prospective_strict"
        assert (
            produce_journal_replay_packet(
                store, journal["decision_id"], capture["capture_id"], policy
            )
            == first
        )
    assert len(store.list("decision_replay_seal")) == 3
    backup = client.get("/api/v1/backup").json()
    assert len(backup["learning_replay_captures"]) == 3
    assert len(backup["learning_replay_seals"]) == 3
    assert store.get("state", state.team_id) == before
    assert (
        store.get("decision_journal", journal["decision_id"])["execution_status"]
        == "execution_unknown"
    )
    assert store.list("learning_outcome") == []
    client.delete("/api/v1/teams/0/state")
    assert store.list("replay_capture") == []


def test_new_capture_never_qualifies_an_old_prediction_and_does_not_overwrite_it(
    tmp_path, monkeypatch
):
    store, state, client = prepared(tmp_path, monkeypatch)
    old, old_run = freeze(client)
    monkeypatch.setattr("fpl_app.learning.packets.utcnow", lambda: "2026-10-09T08:03:00Z")
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    with pytest.raises(ValueError, match="before the forecast origin"):
        produce_journal_replay_packet(store, old["decision_id"], capture["capture_id"], keep_policy)
    monkeypatch.setattr("fpl_app.models.router.utcnow", lambda: "2026-10-09T08:03:30Z")
    new, new_run = freeze(client, capture["capture_id"])
    assert old_run["projection_run_id"] != new_run["projection_run_id"]
    assert store.get("projection", old_run["projection_run_id"]) == old_run
    assert new["decision_id"] != old["decision_id"]


@pytest.mark.parametrize("changed", ["mapping", "policy", "receipt", "state", "catalogue", "code"])
def test_queue_fences_capture_mutations(tmp_path, monkeypatch, changed):
    store, state, client = prepared(tmp_path, monkeypatch)
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    folder = tmp_path / "replay_captures" / capture["capture_id"]
    if changed in {"mapping", "policy", "receipt"}:
        name = {"mapping": "mappings.json", "policy": "policy.py", "receipt": "capture.json"}[
            changed
        ]
        (folder / name).write_bytes(b"{}")
    elif changed == "state":
        current = store.get("state", state.team_id)
        current["bank_units"] += 1
        store.put("state", state.team_id, current)
    elif changed == "catalogue":
        data = store.get("dataset", state.snapshot_id)
        data["players"][0]["market_price_units"] += 1
        store.put("dataset", state.snapshot_id, data)
    else:
        monkeypatch.setattr("fpl_app.learning.packets.implementation_sha256", lambda: "a" * 64)
    response = client.post(
        "/api/v1/projections/runs",
        json={"team_id": 0, "horizon_events": 1, "replay_capture_id": capture["capture_id"]},
    )
    assert response.status_code in {409, 422}, response.text
    assert store.list("projection") == []


def test_worker_rejects_capture_mutation_after_queue(tmp_path, monkeypatch):
    store, state, client = prepared(tmp_path, monkeypatch)
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    response = client.post(
        "/api/v1/projections/runs",
        json={"team_id": 0, "horizon_events": 1, "replay_capture_id": capture["capture_id"]},
    )
    assert response.status_code == 202
    (tmp_path / "replay_captures" / capture["capture_id"] / "source-0.json").write_bytes(b"{}")
    assert Worker(client.app.state.queue).run_once()
    result = client.get("/api/v1/jobs/" + response.json()["job_id"]).json()
    assert result["status"] == "failed"
    assert store.list("projection") == []


def test_schedule_horizon_late_capture_and_policy_mismatch_reject(tmp_path, monkeypatch):
    store, state, client = prepared(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="schedule declaration"):
        capture_replay_evidence(store, state.team_id, 2, keep_policy)
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    journal, _ = freeze(client, capture["capture_id"])
    with pytest.raises(ValueError, match="policy/horizon"):
        produce_journal_replay_packet(
            store, journal["decision_id"], capture["capture_id"], planner_policy
        )
    monkeypatch.setattr("fpl_app.learning.packets.utcnow", lambda: "2026-10-10T10:00:00Z")
    with pytest.raises(ValueError, match="precede the deadline"):
        capture_replay_evidence(store, state.team_id, 1, keep_policy)
    with pytest.raises(ValueError, match="before the deadline"):
        produce_journal_replay_packet(
            store, journal["decision_id"], capture["capture_id"], keep_policy
        )


def test_capture_rejects_non_provider_catalogue_and_unsafe_ids(tmp_path, monkeypatch):
    store, state, _ = prepared(tmp_path, monkeypatch)
    data = store.get("dataset", state.snapshot_id)
    data["players"][0]["points_per_game"] += 1
    store.put("dataset", state.snapshot_id, data)
    with pytest.raises(ValueError, match="retained official source bytes"):
        capture_replay_evidence(store, state.team_id, 1, keep_policy)
    from fpl_app.learning.packets import checked_capture

    with pytest.raises(ValueError, match="Invalid replay capture"):
        checked_capture(store, "../escape", state, data)


def test_optional_capture_absence_preserves_existing_queue_fingerprints(tmp_path, monkeypatch):
    _, _, client = prepared(tmp_path, monkeypatch)
    existing = client.app.state.queue.enqueue(
        "projection",
        {
            "team_id": 0,
            "horizon_events": 1,
            "provider": "baseline",
            "mode": "default",
            "artifact_id": None,
            "serving_bundle_id": None,
        },
    )
    response = client.post("/api/v1/projections/runs", json={"team_id": 0, "horizon_events": 1})
    assert response.status_code == 202
    assert response.json()["job_id"] == existing["id"]


def test_capture_retains_package_and_records_completed_availability(tmp_path, monkeypatch):
    import hashlib
    import json
    import zipfile

    from fpl_app.evaluation.provenance import implementation_sha256

    store, state, _ = prepared(tmp_path, monkeypatch)
    times = iter(["2026-10-09T08:01:00Z", "2026-10-09T08:01:30Z"])
    monkeypatch.setattr("fpl_app.learning.packets.utcnow", lambda: next(times))
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    assert capture["available_at"] == "2026-10-09T08:01:30Z"
    path = tmp_path / "replay_captures" / capture["capture_id"]
    receipt = json.loads((path / "capture.json").read_bytes())
    with zipfile.ZipFile(path / "implementation.zip") as archive:
        hashes = {
            name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
        }
    assert (
        hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        == implementation_sha256()
    )
    assert all(
        row["available_at"] == capture["available_at"]
        for row in receipt["artifacts"]
        if row["role"] != "source"
    )


def test_interrupted_packet_publication_can_retry_without_partial_target(tmp_path, monkeypatch):
    from pathlib import Path

    store, state, client = prepared(tmp_path, monkeypatch)
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    journal, _ = freeze(client, capture["capture_id"])
    original = Path.rename

    def interrupted(path, target):
        if path.name.startswith(".staging-"):
            raise OSError("interrupted publication")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        produce_journal_replay_packet(
            store, journal["decision_id"], capture["capture_id"], keep_policy
        )
    assert store.list("decision_replay_seal") == []
    assert all(path.name.startswith(".staging-") for path in (tmp_path / "replay_inputs").iterdir())
    monkeypatch.setattr(Path, "rename", original)
    result = produce_journal_replay_packet(
        store, journal["decision_id"], capture["capture_id"], keep_policy
    )
    assert (tmp_path / "replay_inputs" / result["packet_id"] / "manifest.json").is_file()
    assert len(store.list("decision_replay_seal")) == 1


def test_completed_capture_after_prediction_cannot_be_queued(tmp_path, monkeypatch):
    store, state, client = prepared(tmp_path, monkeypatch)
    times = iter(["2026-10-09T08:01:00Z", "2026-10-09T08:03:00Z"])
    monkeypatch.setattr("fpl_app.learning.packets.utcnow", lambda: next(times))
    capture = capture_replay_evidence(store, state.team_id, 1, keep_policy)
    response = client.post(
        "/api/v1/projections/runs",
        json={"team_id": 0, "horizon_events": 1, "replay_capture_id": capture["capture_id"]},
    )
    assert response.status_code == 422
    assert store.list("projection") == []
