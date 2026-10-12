"""Authored source/audit contracts; mocked checkpoint inference is mechanics only."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from fpl_app.api import create_app
from fpl_app.contracts import ManagerState, Pick, Player
from fpl_app.jobs import Queue, Worker
from fpl_app.models.advanced_serving import register_bundle
from fpl_app.models.router import resolve_forecast
from fpl_app.storage import Store


def seal(path, values):
    path.write_text(json.dumps(values))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def configured(tmp_path, monkeypatch):
    from fpl_app import storage
    from fpl_app.models import router, strategy_adapters

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(router, "utcnow", lambda: "2026-10-12T14:00:00Z")
    store = Store(f"sqlite:///{tmp_path / 'app.sqlite'}")
    monkeypatch.setattr(storage, "utcnow", lambda: "2026-09-01T00:00:00Z")
    training = store.archive(b'{"authored_training_contract": true}', "element-summary/7/")
    monkeypatch.setattr(storage, "utcnow", lambda: "2026-10-12T10:00:00Z")
    bootstrap = store.archive(b'{"authored_bootstrap_contract": true}', "bootstrap-static/")
    fixtures = store.archive(b'{"authored_fixtures_contract": true}', "fixtures/")
    state = ManagerState(
        team_id=1, data_mode="live", snapshot_id=bootstrap, next_event=8, picks=[Pick(player_id=7)]
    )
    data = {
        "data_mode": "live",
        "snapshot_id": bootstrap,
        "bootstrap_snapshot_id": bootstrap,
        "fixture_snapshot_id": fixtures,
        "source_cutoff": "2026-10-12T10:00:00Z",
        "next_event": 8,
        "players": [
            Player(
                player_id=7,
                name="Authored",
                club=1,
                position=3,
                market_price_units=50,
                availability=0.1,
            ).model_dump(mode="json")
        ],
        "fixtures": [
            {
                "fixture_id": i,
                "event": 8,
                "home_club": 1,
                "away_club": 2,
                "kickoff": "2026-10-18T10:00:00Z",
            }
            for i in (11, 12)
        ],
        "events": [{"id": 8, "deadline_time": "2026-10-17T10:00:00Z"}],
    }
    store.put("dataset", bootstrap, data)
    store.put("state", 1, state.model_dump(mode="json"))
    store.put("current", "live", {"snapshot_id": bootstrap})
    model = tmp_path / "models/tft/contract"
    model.mkdir(parents=True)
    hashes = {}
    for name in ("mean.ckpt", "quantiles.ckpt", "dataset.pt"):
        (model / name).write_bytes(b"authored dummy checkpoint, not a trained model")
        hashes[name] = hashlib.sha256((model / name).read_bytes()).hexdigest()
    hashes["training_manifest.json"] = seal(model / "training_manifest.json", {"authored": True})
    hashes["evaluation.json"] = seal(
        model / "evaluation.json",
        {
            "partition": "test",
            "run_id": "authored-contract",
            "dataset_sha256": "authored-only",
            "metrics": {"n": 2, "mae": 1.0},
        },
    )
    hashes["release_audit.json"] = seal(
        model / "release_audit.json",
        {
            "status": "approved_shadow",
            "model_family": "tft",
            "rules_version": "2026-27-v1",
            "model_payloads": dict(hashes),
            "input_provenance_reviewed": True,
            "evaluation_file": "evaluation.json",
            "training_sources": [
                {"snapshot_id": training, "sha256": store.snapshot(training)["payload_sha256"]}
            ],
        },
    )
    meta = {
        "model_family": "tft",
        "model_status": "trained",
        "data_mode": "live",
        "replay_timing": "verified",
        "rules_version": "2026-27-v1",
        "training_cutoff": "2026-09-02T00:00:00Z",
        "available_at": "2026-09-03T00:00:00Z",
        "run_id": "authored-contract",
        "dataset_sha256": "authored-only",
        "artifacts": hashes,
    }
    model_sha = seal(model / "manifest.json", meta)
    directory = tmp_path / "serving_inputs/contract"
    directory.mkdir(parents=True)
    panel = pd.DataFrame(
        [
            {
                "series": f"s{i}",
                "player": "person",
                "time_idx": t,
                "forecast_origin": 8,
                "source_event": 7 if t == 0 else 8,
                "fixture_id": i,
                "fixture_exists": 1,
                "opponent": 20,
                "was_home": 1,
                "decision_cutoff": "2026-10-12T12:00:00Z",
                "points": 0,
                "encoder_points": 0,
                "observation_mask": 0,
                "weight": 0,
            }
            for i in (11, 12)
            for t in (0, 1)
        ]
    )
    panel.to_parquet(directory / "panel.parquet", index=False)
    pd.DataFrame(
        [
            {
                "player_id": 7,
                "fixture_id": i,
                "expected_minutes": 60,
                "available_at": data["source_cutoff"],
            }
            for i in (11, 12)
        ]
    ).to_parquet(directory / "minutes.parquet", index=False)
    manifest = {
        "review_status": "reviewed_local",
        "snapshot_id": bootstrap,
        "artifact_id": "contract",
        "manifest_sha256": model_sha,
        "family": "tft",
        "rules_version": "2026-27-v1",
        "source_cutoff": data["source_cutoff"],
        "available_at": "2026-10-12T11:00:00Z",
        "prediction_origin": "2026-10-12T12:00:00Z",
        "next_event": 8,
        "horizon_events": 1,
        "schedule_complete_events": [8],
        "player_map": {"person": 7},
        "club_map": {1: 10, 2: 20},
        "sources": [
            {"snapshot_id": i, "sha256": store.snapshot(i)["payload_sha256"]}
            for i in (bootstrap, fixtures)
        ],
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()},
    }
    seal(directory / "manifest.json", manifest)
    monkeypatch.setattr(
        strategy_adapters,
        "predict_tft",
        lambda *args: {
            "mean": np.array([[4.0], [5.0]]),
            "quantiles": np.array([[[1.0, 3.0, 7.0]], [[2.0, 4.0, 8.0]]]),
            "index": pd.DataFrame([{"series": f"s{i}", "time_idx": 1} for i in (11, 12)]),
        },
    )
    return store, state, data, model, directory, manifest


def payload(bundle):
    return {
        "team_id": 1,
        "provider": "tft",
        "mode": "shadow",
        "artifact_id": "contract",
        "serving_bundle_id": bundle["serving_bundle_id"],
        "horizon_events": 1,
    }


def test_api_registration_queue_real_adapter_and_idempotency(configured):
    store, state, _, _, _, _ = configured
    before = store.get("state", 1)
    client = TestClient(create_app(store))
    body = {
        "team_id": 1,
        "provider": "tft",
        "artifact_id": "contract",
        "input_bundle_id": "contract",
    }
    response = client.post("/api/v1/projections/bundles", json=body)
    assert response.status_code == 201, response.text
    bundle = response.json()
    assert client.post("/api/v1/projections/bundles", json=body).json() == bundle
    listed = client.get("/api/v1/projections/bundles?team_id=1").json()["bundles"]
    assert listed[0]["serving_bundle_id"] == bundle["serving_bundle_id"]
    response = client.post("/api/v1/projections/runs", json=payload(bundle))
    assert response.status_code == 202, response.text
    queue = Queue(store)
    assert Worker(queue).run_once()
    job = queue.get(response.json()["job_id"])
    assert job["status"] == "succeeded", job.get("error")
    run = job["result"]
    assert run["resolved_provider"] == run["model_family"] == "tft"
    assert run["evidence_mode"] == "prospective_shadow"
    assert run["source_cutoff"] != run["prediction_origin"]
    assert [p["expected_points"] for p in run["projections"]] == [4, 5]  # No 10% scaling.
    assert run["player_universe_ids"] == [7]
    assert store.get("state", state.team_id) == before


@pytest.mark.parametrize("mode", ["default", "experimental"])
def test_no_implicit_advanced_activation(configured, mode):
    store, state, *_ = configured
    bundle = register_bundle(store, state, "tft", "contract", "contract")
    with pytest.raises(ValueError, match="shadow mode"):
        resolve_forecast(store, {**payload(bundle), "mode": mode}, state)


@pytest.mark.parametrize(
    "field,value",
    [
        ("prediction_origin", "2099-01-01T00:00:00Z"),
        ("available_at", "2026-10-12T13:00:00Z"),
        ("source_cutoff", "2026-10-11T10:00:00Z"),
        ("schedule_complete_events", []),
        ("player_map", {"someone": 99}),
        ("horizon_events", 2),
    ],
)
def test_resealed_invalid_inputs_do_not_register(configured, field, value):
    store, state, _, _, directory, manifest = configured
    seal(directory / "manifest.json", {**manifest, field: value})
    with pytest.raises(ValueError):
        register_bundle(store, state, "tft", "contract", "contract")
    store.put("current", "live", {"snapshot_id": "new"})
    with pytest.raises(ValueError):
        register_bundle(store, state, "tft", "contract", "contract")
    assert store.list("forecast_bundle") == []


@pytest.mark.parametrize("filename", ["panel.parquet", "minutes.parquet", "manifest.json"])
def test_input_mutation_after_enqueue_prevents_publication(configured, filename):
    store, state, _, _, directory, _ = configured
    bundle = register_bundle(store, state, "tft", "contract", "contract")
    queue = Queue(store)
    job = queue.enqueue("projection", payload(bundle))
    with (directory / filename).open("ab") as handle:
        handle.write(b"corrupt")
    assert Worker(queue).run_once()
    assert queue.get(job["id"])["status"] == "failed"
    assert store.list("projection") == []


def test_changes_during_inference_and_code_changes_block_worker_publication(
    configured, monkeypatch
):
    from fpl_app.evaluation import provenance
    from fpl_app.models import strategy_adapters

    store, state, _, _, directory, _ = configured
    bundle = register_bundle(store, state, "tft", "contract", "contract")
    queue = Queue(store)
    job = queue.enqueue("projection", payload(bundle))
    original = strategy_adapters.predict_tft

    def mutate(*args):
        result = original(*args)
        with (directory / "minutes.parquet").open("ab") as handle:
            handle.write(b"changed while computing")
        return result

    monkeypatch.setattr(strategy_adapters, "predict_tft", mutate)
    assert Worker(queue).run_once()
    assert queue.get(job["id"])["status"] == "failed"
    assert store.list("projection") == []
    # A second frozen reference rejects an implementation digest change as well.
    raw = (directory / "minutes.parquet").read_bytes()
    (directory / "minutes.parquet").write_bytes(raw.removesuffix(b"changed while computing"))
    monkeypatch.setattr(strategy_adapters, "predict_tft", original)
    second = queue.enqueue("projection", payload(bundle))
    monkeypatch.setattr(provenance, "implementation_sha256", lambda: "0" * 64)
    assert Worker(queue).run_once()
    assert queue.get(second["id"])["status"] == "failed"
    assert store.list("projection") == []


def test_missing_release_audit_and_stale_manager_fail_closed(configured):
    store, state, _, model, _, _ = configured
    (model / "release_audit.json").unlink()
    with pytest.raises(ValueError):
        register_bundle(store, state, "tft", "contract", "contract")


def test_qualification_publishes_new_copy_and_keeps_original_bytes(configured, monkeypatch):
    from fpl_app.models import qualification

    store, _, _, model, _, _ = configured
    audit = json.loads((model / "release_audit.json").read_text())
    original = json.loads((model / "manifest.json").read_text())
    for name in ("release_audit.json", "training_manifest.json"):
        original["artifacts"].pop(name)
        (model / name).unlink()
    sha = seal(model / "manifest.json", original)
    retained = {p.name: p.read_bytes() for p in model.iterdir()}
    reviews = model.parents[2] / "model_reviews"
    reviews.mkdir()
    review = {
        "status": "approved_shadow",
        "source_manifest_sha256": sha,
        "input_provenance_reviewed": True,
        "training_sources": audit["training_sources"],
        "evaluation_file": "evaluation.json",
        "evaluation_sha256": original["artifacts"]["evaluation.json"],
    }
    seal(reviews / "review.json", review)
    monkeypatch.setattr(qualification, "utcnow", lambda: "2026-10-12T13:00:00Z")
    result = qualification.qualify_shadow(store, "tft", "contract", "review")
    assert result["active"] is False and result["mode"] == "shadow"
    assert result == qualification.qualify_shadow(store, "tft", "contract", "review")
    destination = model.parent / result["artifact_id"]
    meta = json.loads((destination / "manifest.json").read_text())
    assert meta["available_at"] == "2026-10-12T13:00:00Z"
    assert hashlib.sha256((destination / "training_manifest.json").read_bytes()).hexdigest() == sha
    assert {p.name: p.read_bytes() for p in model.iterdir()} == retained
    seal(reviews / "review.json", {**review, "status": "pending"})
    with pytest.raises(ValueError, match="bound review"):
        qualification.qualify_shadow(store, "tft", "contract", "review")


def reviewed_artifact(store, path, metadata, training_sources):
    """Seal an authored local audit contract, not a real release approval."""
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.iterdir()
        if p.name != "manifest.json"
    }
    hashes["release_audit.json"] = seal(
        path / "release_audit.json",
        {
            "status": "approved_shadow",
            "model_family": metadata["model_family"],
            "rules_version": "2026-27-v1",
            "model_payloads": dict(hashes),
            "input_provenance_reviewed": True,
            "evaluation_file": "evaluation.json",
            "training_sources": training_sources,
        },
    )
    return seal(path / "manifest.json", {**metadata, "artifacts": hashes})


def test_bayesian_worker_reads_real_netcdf_and_complete_fitted_scoring_profiles(
    configured, monkeypatch
):
    from dataclasses import asdict

    cache = configured[3].parents[2] / "library-cache"
    platformdirs = pytest.importorskip("platformdirs")
    monkeypatch.setattr(platformdirs, "user_cache_dir", lambda *args, **kwargs: str(cache))
    monkeypatch.setenv("MPLCONFIGDIR", str(cache / "matplotlib"))
    az = pytest.importorskip("arviz")
    from fpl_app.domain.rules import MatchStats
    from fpl_app.models.bayesian_scoring import fit_scoring_profiles

    store, state, _, tft, directory, manifest = configured
    path = tft.parent.parent / "bayesian/contract"
    path.mkdir(parents=True)
    az.from_dict(
        posterior={
            **{name: np.zeros((2, 8)) for name in ("base", "venue", "trend")},
            "dispersion": np.ones((2, 8)),
            "attack": np.zeros((2, 8, 2)),
            "defence": np.zeros((2, 8, 2)),
        }
    ).to_netcdf(path / "posterior.nc")
    seal(
        path / "diagnostics.json",
        {
            "clubs": [10, 20],
            "converged": True,
            "time_center": 0,
            "time_scale": 1,
            "limitations": ["authored posterior contract"],
        },
    )
    rows = [
        {
            "player_id": "person" if position == 3 else f"helper-{position}",
            "position": position,
            "started": True,
            "bps": 20,
            "available_at": "2026-09-01T00:00:00Z",
            **asdict(MatchStats(minutes=90, goals=int(position == 3))),
        }
        for position in (1, 2, 3, 4)
    ]
    seal(
        path / "scoring_profiles.json",
        fit_scoring_profiles(pd.DataFrame(rows), "2026-09-02T00:00:00Z"),
    )
    seal(
        path / "evaluation.json",
        {
            "partition": "test",
            "run_id": "bayes-authored",
            "dataset_sha256": "authored-only",
            "metrics": {"n": 4, "mae": 1.0},
        },
    )
    meta = json.loads((tft / "manifest.json").read_text())
    meta.update(model_family="bayesian", run_id="bayes-authored")
    receipts = json.loads((tft / "release_audit.json").read_text())["training_sources"]
    sha = reviewed_artifact(store, path, meta, receipts)
    pd.DataFrame(
        [
            {
                "canonical_player_id": "person",
                "club": 1,
                "position": 3,
                "available_at": manifest["source_cutoff"],
                "appearances": 6,
                "total_matches": 8,
                "minutes_per_appearance": 70,
                "goals": 2,
                "assists": 1,
                "total_minutes": 420,
            }
        ]
    ).to_parquet(directory / "exposures.parquet", index=False)
    manifest.update(
        family="bayesian", manifest_sha256=sha, fixture_times={11: 8.0, 12: 9.0}, samples=100
    )
    manifest["files"] = {
        "exposures.parquet": hashlib.sha256(
            (directory / "exposures.parquet").read_bytes()
        ).hexdigest()
    }
    seal(directory / "manifest.json", manifest)
    bundle = register_bundle(store, state, "bayesian", "contract", "contract")
    queue = Queue(store)
    job = queue.enqueue("projection", {**payload(bundle), "provider": "bayesian"})
    assert Worker(queue).run_once()
    result = queue.get(job["id"])
    assert result["status"] == "succeeded", result.get("error")
    assert len(result["result"]["projections"]) == 2
    assert all(p["start_probability"] is not None for p in result["result"]["projections"])
    assert result["result"]["evidence_mode"] == "prospective_shadow"


def test_genuine_fitted_ensemble_worker_and_member_fences(configured, monkeypatch):
    from fpl_app.models import ensemble
    from fpl_app.models.router import forecast_job

    store, state, data, tft, directory, manifest = configured
    member = register_bundle(store, state, "tft", "contract", "contract")
    path = tft.parent.parent / "ensemble/contract"
    frame = pd.DataFrame(
        [
            {
                "event": e,
                "partition": "validation" if e < 3 else "test",
                "decision_cutoff": f"2026-09-{e * 5:02d}T00:00:00Z",
                "target_available_at": f"2026-09-{e * 5 + 1:02d}T00:00:00Z",
                "train_target_end": "2026-09-01T00:00:00Z",
                "target_points": float(e),
                "tft": float(e) + 1,
            }
            for e in range(1, 5)
        ]
    )
    monkeypatch.setattr(ensemble, "utcnow", lambda: "2026-09-22T00:00:00Z")
    meta, _ = ensemble.fit_mean_ensemble(
        frame[frame.partition == "validation"], frame[frame.partition == "test"], ["tft"], path
    )
    meta.update(artifact_id="contract", data_mode="live", replay_timing="verified")
    receipts = json.loads((tft / "release_audit.json").read_text())["training_sources"]
    sha = reviewed_artifact(store, path, meta, receipts)
    packet = directory.parent / "ensemble"
    packet.mkdir()
    manifest.update(
        family="ensemble",
        manifest_sha256=sha,
        files={},
        member_bundle_ids={"tft": member["serving_bundle_id"]},
    )
    seal(packet / "manifest.json", manifest)
    bundle = register_bundle(store, state, "ensemble", "contract", "ensemble")
    request = {**payload(bundle), "provider": "ensemble"}
    queue = Queue(store)
    job = queue.enqueue("projection", request)
    assert Worker(queue).run_once()
    result = queue.get(job["id"])
    assert result["status"] == "succeeded", result.get("error")
    assert [p["expected_points"] for p in result["result"]["projections"]] == [4, 5]
    assert all(p["point_quantiles"] is None for p in result["result"]["projections"])
    assert (
        forecast_job(store, state, data, result["payload"]).projection_run_id
        == result["result"]["projection_run_id"]
    )
    changed = store.get("forecast_bundle", member["serving_bundle_id"])
    store.put("forecast_bundle", member["serving_bundle_id"], {**changed, "horizon_events": 2})
    with pytest.raises(ValueError, match="member changed"):
        resolve_forecast(store, request, state)
