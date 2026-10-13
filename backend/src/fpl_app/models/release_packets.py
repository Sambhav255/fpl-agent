"""Reproducible real-football shadow producers; no timestamp qualification fiction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from fpl_app.contracts import ManagerState, ProjectionRun
from fpl_app.domain.rules import RULES
from fpl_app.storage import Store, fingerprint, utcnow


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    with path.open("x") as file:
        json.dump(value, file, sort_keys=True, indent=2, allow_nan=False)


def freeze_football_inputs(store: Store, collection_id: str, artifact_id: str, origin: str) -> str:
    """Build new inputs without changing a previously published model or packet."""
    from fpl_app.features.football import collection_frames
    from fpl_app.providers.collection import load_collection

    from .advanced_serving import input_path
    from .football_catboost import forecast_frozen
    from .router import artifact_path, instant, verify_artifact

    model = artifact_path("football_catboost", artifact_id)
    model_sha = digest(model / "manifest.json")
    metadata = verify_artifact(
        {"provider": "football_catboost", "artifact_id": artifact_id, "manifest_sha256": model_sha}
    )
    collection = load_collection(store, collection_id)
    if instant(metadata["available_at"]) > instant(origin) or instant(origin) > instant(utcnow()):
        raise ValueError("Model must actually exist before the frozen serving origin")
    _, features, mappings = collection_frames(
        collection, metadata["rules_version"], include_training=False
    )
    features["decision_cutoff"] = origin
    # Predict/reload now, retaining payload checksums independently from training.
    predictions = forecast_frozen(model, features, mappings, origin)
    identifier = "football-input-" + uuid4().hex
    directory = input_path(identifier)
    directory.mkdir(parents=True, exist_ok=False)
    for name, frame in (
        ("future_features.parquet", features),
        ("current_mappings.parquet", mappings),
        ("future_predictions.parquet", predictions),
    ):
        frame.to_parquet(directory / name, index=False)
    write(
        directory / "forecast_origin.json",
        {
            "prediction_origin": origin,
            "input_captured_at": collection["captured_at"],
            "input_produced_at": utcnow(),
            "event": int(features.event.iloc[0]),
            "artifact_manifest_sha256": model_sha,
            "rules_version": metadata["rules_version"],
            "files": {p.name: digest(p) for p in directory.iterdir()},
            "sources": collection["sources"],
            "historical_training_evidence": "retrospective_assumed",
            "serving_evidence": "actual_future_shadow",
        },
    )
    return identifier


def create_baseline_member(
    store: Store, state: ManagerState, football_bundle: dict[str, Any]
) -> dict[str, Any]:
    """Freeze the actual app baseline on exactly the football member's universe."""
    from fpl_app.contracts import Fixture, Player

    from .advanced_serving import input_path
    from .baseline import baseline_run

    data = store.get("dataset", state.snapshot_id)
    universe = football_bundle["player_ids"]
    run = baseline_run(
        [Player.model_validate(p) for p in data["players"] if p["player_id"] in universe],
        [
            Fixture.model_validate(f)
            for f in data["fixtures"]
            if f["event"] is not None
            and state.next_event
            <= f["event"]
            < state.next_event + football_bundle["horizon_events"]
        ],
        state.snapshot_id,
        data["source_cutoff"],
        "live",
        state.next_event,
        football_bundle["horizon_events"],
    ).model_copy(
        update={
            "prediction_origin": football_bundle["prediction_origin"],
            "player_universe_ids": universe,
        }
    )
    identifier = "baseline-input-" + uuid4().hex
    directory = input_path(identifier)
    directory.mkdir(parents=True, exist_ok=False)
    write(directory / "baseline.json", run.model_dump(mode="json"))
    bundle = {
        "provider": "baseline",
        "team_id": state.team_id,
        "snapshot_id": state.snapshot_id,
        "prediction_origin": run.prediction_origin,
        "source_cutoff": data["source_cutoff"],
        "horizon_events": run.horizon_events,
        "player_ids": universe,
        "input_bundle_id": identifier,
        "files": {"baseline.json": digest(directory / "baseline.json")},
        "source_receipts": [
            {"snapshot_id": data[key], "sha256": store.snapshot(data[key])["payload_sha256"]}
            for key in ("bootstrap_snapshot_id", "fixture_snapshot_id")
        ],
        "produced_at": utcnow(),
        "evidence_mode": "actual_future_shadow",
    }
    key = "baseline-member-" + fingerprint(bundle)[:32]
    bundle["serving_bundle_id"] = key
    store.put("forecast_bundle", key, bundle, expected=0)
    return bundle


def checked_baseline_member(store, state, data, bundle) -> ProjectionRun:
    from .advanced_serving import SourceReceipt, _sources, input_path
    from .router import _checked_file, instant

    if (
        bundle.get("provider") != "baseline"
        or bundle.get("team_id") != state.team_id
        or bundle.get("snapshot_id") != state.snapshot_id
        or bundle.get("source_cutoff") != data["source_cutoff"]
        or store.get("current", "live")["snapshot_id"] != state.snapshot_id
    ):
        raise ValueError("Frozen baseline member is stale")
    receipts = [SourceReceipt.model_validate(r) for r in bundle["source_receipts"]]
    sources = _sources(store, receipts, bundle["source_cutoff"])
    if not {data["bootstrap_snapshot_id"], data["fixture_snapshot_id"]} <= sources:
        raise ValueError("Baseline member source identity differs")
    if instant(bundle["source_cutoff"]) > instant(bundle["prediction_origin"]):
        raise ValueError("Baseline sources postdate origin")
    raw = _checked_file(
        input_path(bundle["input_bundle_id"]), "baseline.json", bundle["files"]["baseline.json"]
    ).read_bytes()
    run = ProjectionRun.model_validate_json(raw)
    if (
        run.model_family != "baseline"
        or run.snapshot_id != state.snapshot_id
        or run.source_cutoff != bundle["source_cutoff"]
        or run.prediction_origin != bundle["prediction_origin"]
        or run.player_universe_ids != bundle["player_ids"]
        or run.horizon_events != bundle["horizon_events"]
    ):
        raise ValueError("Baseline member payload identity differs")
    from fpl_app.jobs import projection_players

    projection_players(state, data, run)
    return run


def produce_football_ensemble(store: Store, collection_id: str, artifact_id: str) -> str:
    """Fit from checksummed chronological fold outputs, never hand-authored weights."""
    from fpl_app.providers.collection import load_collection

    from .ensemble import fit_mean_ensemble
    from .router import _checked_file, artifact_path, verify_artifact

    model = artifact_path("football_catboost", artifact_id)
    metadata = verify_artifact(
        {
            "provider": "football_catboost",
            "artifact_id": artifact_id,
            "manifest_sha256": digest(model / "manifest.json"),
        }
    )
    collection = load_collection(store, collection_id)
    if metadata["provenance"]["collection_id"] != collection_id:
        raise ValueError("Ensemble training collection differs from serving refit")
    evaluation = json.loads((model / metadata["evaluation_reference"]).read_text())
    if not evaluation.get("folds"):
        raise ValueError("Chronological held-out football folds are unavailable")
    # Fit on the earliest fold's genuine held-out calibration predictions, then
    # score every later out-of-fold test origin. Never refit weights on tests.
    folds = sorted(evaluation["folds"], key=lambda row: row["test_events"][0])
    fold = folds[0]
    relative = Path(fold["artifact_reference"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe evaluation fold reference")
    evaluation_root = Path(metadata["evaluation_artifact_reference"])
    if evaluation_root.is_absolute() or ".." in evaluation_root.parts:
        raise ValueError("Unsafe evaluation reference")
    directory = model.parent / evaluation_root / relative
    raw = (directory / "manifest.json").read_bytes()
    folded = json.loads(raw)
    frames = {}
    for name in ("ensemble_validation_predictions.parquet", "test_predictions.parquet"):
        frames[name] = pd.read_parquet(_checked_file(directory, name, folded["files"][name]))
    later_tests = [frames["test_predictions.parquet"]]
    later_receipts = []
    for later in folds[1:]:
        reference = Path(later["artifact_reference"])
        if reference.is_absolute() or ".." in reference.parts:
            raise ValueError("Unsafe later fold reference")
        folder = model.parent / evaluation_root / reference
        later_raw = (folder / "manifest.json").read_bytes()
        later_metadata = json.loads(later_raw)
        if later_metadata["provenance"]["collection_id"] != collection_id:
            raise ValueError("Later fold source collection differs")
        checksum = later_metadata["files"]["test_predictions.parquet"]
        later_tests.append(
            pd.read_parquet(_checked_file(folder, "test_predictions.parquet", checksum))
        )
        later_receipts.append(
            {
                "manifest_sha256": hashlib.sha256(later_raw).hexdigest(),
                "test_predictions_sha256": checksum,
                "test_events": later["test_events"],
            }
        )
    identifier = "football-blend-" + uuid4().hex
    output = artifact_path("ensemble", identifier)
    manifest, _report = fit_mean_ensemble(
        frames["ensemble_validation_predictions.parquet"],
        pd.concat(later_tests, ignore_index=True),
        ["app_baseline_reconstructed", "football_catboost"],
        output,
    )
    (output / "training_manifest.json").write_bytes(raw)
    write(
        output / "training_receipts.json",
        {
            "collection_id": collection_id,
            "collection_sha256": collection["envelope_sha256"],
            "source_hashes": collection["sources"],
            "evaluation_fold_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "evaluation_refit_manifest_sha256": digest(model / "manifest.json"),
            "heldout_files": {name: folded["files"][name] for name in frames},
            "later_untouched_fold_receipts": later_receipts,
        },
    )
    manifest["artifacts"] = {
        p.name: digest(p) for p in output.iterdir() if p.name != "manifest.json"
    }
    audit = {
        "status": "approved_shadow",
        "model_family": "ensemble",
        "rules_version": RULES.version,
        "model_payloads": dict(manifest["artifacts"]),
        "training_sources": [
            {"snapshot_id": s["id"], "sha256": s["payload_sha256"]} for s in collection["sources"]
        ],
        "input_provenance_reviewed": True,
        "evaluation_file": "evaluation.json",
        "evaluation_evidence": "retrospective_assumed",
        "review_basis": "deterministic producer checksums and chronological partition checks; no independent timing attestation",
    }
    write(output / "release_audit.json", audit)
    manifest["artifacts"]["release_audit.json"] = digest(output / "release_audit.json")
    manifest.update(
        artifact_id=identifier,
        data_mode="live",
        replay_timing="historical_assumed_shadow",
        data_evidence_mode="retrospective_assumed",
        training_cutoff=max(s["available_at"] for s in collection["sources"]),
        available_at=utcnow(),
        supported_horizon=1,
        serving_mode="shadow_only",
    )
    # fit_mean_ensemble created the manifest; this producer completes it before release.
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return identifier


def freeze_ensemble_inputs(store, state, artifact_id, football, baseline):
    from .advanced_serving import InputManifest, SourceReceipt, input_path
    from .router import artifact_path

    data = store.get("dataset", state.snapshot_id)
    identifier = "ensemble-input-" + uuid4().hex
    directory = input_path(identifier)
    directory.mkdir(parents=True, exist_ok=False)
    manifest = InputManifest(
        review_status="reviewed_local",
        family="ensemble",
        snapshot_id=state.snapshot_id,
        artifact_id=artifact_id,
        manifest_sha256=digest(artifact_path("ensemble", artifact_id) / "manifest.json"),
        rules_version=RULES.version,
        source_cutoff=data["source_cutoff"],
        available_at=data["source_cutoff"],
        prediction_origin=football["prediction_origin"],
        next_event=state.next_event,
        horizon_events=1,
        schedule_complete_events=[state.next_event],
        player_map={f"official_fpl:{state.season}:element:{i}": i for i in football["player_ids"]},
        club_map={p["club"]: p["club"] for p in data["players"]},
        sources=[SourceReceipt.model_validate(r) for r in baseline["source_receipts"]],
        files={},
        member_bundle_ids={
            "app_baseline_reconstructed": baseline["serving_bundle_id"],
            "football_catboost": football["serving_bundle_id"],
        },
    )
    write(directory / "manifest.json", manifest.model_dump(mode="json"))
    return identifier
