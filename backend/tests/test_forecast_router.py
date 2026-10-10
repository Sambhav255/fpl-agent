"""Synthetic routing contracts; no model training or accuracy evidence."""

import hashlib
import json

import pytest

from fpl_app.contracts import Fixture, Player
from fpl_app.jobs import Queue, Worker, input_state
from fpl_app.models.baseline import baseline_run
from fpl_app.models.router import forecast_job, resolve_forecast
from fpl_app.providers import demo
from fpl_app.storage import Store


@pytest.fixture
def configured(tmp_path, monkeypatch):
    from fpl_app.models import router

    monkeypatch.setattr(router, "data_dir", lambda: tmp_path)
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    state = demo(store)
    data = store.get("dataset", state.snapshot_id)
    state.data_mode = "live"
    data["data_mode"] = "live"
    store.put("dataset", state.snapshot_id, data)
    store.put("current", "live", {"snapshot_id": state.snapshot_id})
    store.put("state", state.team_id, state.model_dump(mode="json"))
    directory = tmp_path / "models" / "football_catboost" / "contract_fixture"
    directory.mkdir(parents=True)
    (directory / "fixture.bin").write_bytes(b"synthetic provider contract")
    manifest = {
        "model_family": "football_catboost",
        "data_mode": "live",
        "training_cutoff": "2026-01-01T00:00:00Z",
        "artifact_available_at": "2026-01-02T00:00:00Z",
        "rules_version": "2026-27-v1",
        "supported_horizon": 1,
        "feature_version": "synthetic-v1",
        "mapping_version": "synthetic-v1",
        "artifacts": {
            "fixture.bin": hashlib.sha256((directory / "fixture.bin").read_bytes()).hexdigest()
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    store.put(
        "forecast_bundle",
        "fixture_bundle",
        {"snapshot_id": state.snapshot_id, "fixture": "synthetic"},
    )
    payload = {
        "team_id": 0,
        "horizon_events": 1,
        "provider": "football_catboost",
        "mode": "experimental",
        "artifact_id": "contract_fixture",
        "serving_bundle_id": "fixture_bundle",
    }
    return store, state, directory, manifest, payload


def fixture_provider(store, state, data, reference):
    run = baseline_run(
        [Player.model_validate(p) for p in data["players"]],
        [Fixture.model_validate(f) for f in data["fixtures"]],
        state.snapshot_id,
        data["source_cutoff"],
        state.data_mode,
        state.next_event,
        reference["horizon_events"],
    )
    return run.model_copy(
        update={
            "model_family": "football_catboost",
            "projection_run_id": "synthetic-challenger",
            "projections": [
                p.model_copy(update={"expected_points": p.expected_points + 1})
                for p in run.projections
            ],
        }
    )


def test_two_providers_produce_distinct_worker_results(configured):
    store, _state, _, _, payload = configured
    queue = Queue(store)
    first = queue.enqueue("projection", {"team_id": 0, "horizon_events": 1})
    assert Worker(queue).run_once()
    baseline = queue.get(first["id"])["result"]
    second = queue.enqueue("projection", payload)

    def compute(frozen):
        manager, data = input_state(store, frozen["team_id"])
        return forecast_job(
            store, manager, data, frozen, {"football_catboost": fixture_provider}
        ).model_dump(mode="json")

    assert Worker(queue, handlers={"projection": compute}).run_once()
    challenger = queue.get(second["id"])["result"]
    assert baseline["resolved_provider"] == "baseline"
    assert challenger["resolved_provider"] == "football_catboost"
    assert challenger["evidence_mode"] == "experimental_live"
    assert challenger["artifact_id"] == "contract_fixture"
    assert (
        challenger["projections"][0]["expected_points"]
        == baseline["projections"][0]["expected_points"] + 1
    )
    assert queue.get(second["id"])["payload"]["_forecast"]["manifest_sha256"]


def test_changed_manifest_after_enqueue_fails_instead_of_switching(configured):
    store, _, directory, metadata, payload = configured
    queue = Queue(store)
    job = queue.enqueue("projection", payload)
    metadata["mapping_version"] = "changed"
    (directory / "manifest.json").write_text(json.dumps(metadata))
    assert Worker(queue).run_once()
    assert queue.get(job["id"])["status"] == "failed"


def test_default_advanced_provider_needs_explicit_promotion(configured):
    store, state, _, _, payload = configured
    with pytest.raises(ValueError, match="promotion"):
        resolve_forecast(store, {**payload, "mode": "default"}, state)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_available_at", "2099-01-01T00:00:00Z"),
        ("rules_version", "2024-25-v1"),
        ("supported_horizon", 0),
    ],
)
def test_incompatible_artifacts_fail_clearly(configured, field, value):
    store, state, directory, metadata, payload = configured
    metadata[field] = value
    (directory / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        resolve_forecast(store, payload, state)


def test_unavailable_provider_never_silently_falls_back(configured):
    store, state, _, _, payload = configured
    reference = resolve_forecast(store, payload, state)
    with pytest.raises(ValueError, match="no silent"):
        forecast_job(store, state, input_state(store, 0)[1], {**payload, "_forecast": reference})
