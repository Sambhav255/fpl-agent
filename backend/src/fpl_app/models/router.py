"""Immutable forecast selection; an experiment is never a default promotion."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fpl_app.contracts import Fixture, ManagerState, Player, ProjectionRun
from fpl_app.storage import Store, fingerprint, utcnow

from .baseline import baseline_run
from .training import data_dir


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Forecast timestamps require an explicit timezone")
    return parsed.astimezone(UTC)


def artifact_path(family: str, identifier: str) -> Path:
    if family not in {"football_catboost", "catboost", "bayesian", "tft"}:
        raise ValueError("Unknown forecast provider")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", identifier):
        raise ValueError("Invalid artifact ID")
    path = data_dir() / "models" / family / identifier
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Artifact symlinks are not allowed")
    return path


def verify_artifact(reference: dict[str, Any]) -> dict[str, Any]:
    path = artifact_path(reference["provider"], reference["artifact_id"])
    if not (path / "manifest.json").is_file():
        raise ValueError("Selected model artifact is unavailable")
    raw = (path / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["manifest_sha256"]:
        raise ValueError("Selected artifact manifest changed; create a new job")
    metadata: dict[str, Any] = json.loads(raw)
    hashes = metadata.get("artifacts", {})
    if not hashes:
        raise ValueError("Artifact has no immutable files")
    for name, checksum in hashes.items():
        target = path / name
        if Path(name).name != name or target.is_symlink() or not target.is_file():
            raise ValueError("Unsafe or missing artifact file")
        if hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
            raise ValueError("Forecast artifact checksum mismatch")
    return metadata


def resolve_forecast(store: Store, payload: dict[str, Any], state: ManagerState) -> dict[str, Any]:
    provider = payload.get("provider", "baseline")
    mode = payload.get("mode", "default")
    if mode not in {"default", "experimental", "shadow"}:
        raise ValueError("Unknown forecast selection mode")
    reference: dict[str, Any] = {
        "requested_provider": provider,
        "provider": provider,
        "mode": mode,
        "prediction_origin": utcnow(),
        "artifact_id": None,
        "manifest_sha256": None,
        "serving_bundle_id": payload.get("serving_bundle_id"),
    }
    if provider == "baseline":
        if payload.get("artifact_id") or payload.get("serving_bundle_id"):
            raise ValueError("Baseline does not accept advanced artifacts")
        return reference
    if state.data_mode != "live":
        raise ValueError("Real model artifacts cannot serve synthetic demo squads")
    identifier = payload.get("artifact_id")
    if not isinstance(identifier, str):
        raise ValueError("Advanced selection requires an explicit artifact ID")  # noqa: TRY004
    path = artifact_path(provider, identifier)
    if not (path / "manifest.json").is_file():
        raise ValueError("Selected model artifact is unavailable")
    reference.update(
        artifact_id=identifier,
        manifest_sha256=hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest(),
    )
    metadata = verify_artifact(reference)
    if metadata.get("model_family") != provider or metadata.get("data_mode") != "live":
        raise ValueError("Artifact family or real-data evidence is incompatible")
    available = metadata.get("artifact_available_at", metadata.get("available_at"))
    cutoff = metadata.get("training_cutoff", metadata.get("information_cutoff"))
    if not available or not cutoff:
        raise ValueError("Artifact training and actual availability timestamps required")
    if not instant(cutoff) <= instant(available) <= instant(reference["prediction_origin"]):
        raise ValueError("Artifact information or availability is in the future")
    horizon = metadata.get("supported_horizon", metadata.get("horizon_events", 1))
    if payload["horizon_events"] > horizon:
        raise ValueError("Requested horizon exceeds evaluated provider support")
    if metadata.get("rules_version") != "2026-27-v1":
        raise ValueError("Artifact scoring regime does not support the current season")
    if not metadata.get("feature_version") or not metadata.get("mapping_version"):
        raise ValueError("Explicit feature and mapping versions required")
    if mode == "default":
        try:
            promotion = store.get("model_promotion", identifier)
        except KeyError as exc:
            raise ValueError(
                "No recorded default promotion; select experimental or shadow mode"
            ) from exc
        if (
            not promotion.get("eligible")
            or promotion.get("manifest_sha256") != reference["manifest_sha256"]
        ):
            raise ValueError("Promotion evidence does not bind this artifact")
    if not reference["serving_bundle_id"]:
        raise ValueError("Advanced provider requires an immutable serving feature bundle")
    bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
    if bundle.get("snapshot_id") != state.snapshot_id:
        raise ValueError("Serving bundle snapshot is stale")
    reference["bundle_fingerprint"] = fingerprint(bundle)
    return reference


ForecastRunner = Callable[[Store, ManagerState, dict[str, Any], dict[str, Any]], ProjectionRun]


def baseline_provider(
    store: Store, state: ManagerState, data: dict[str, Any], reference: dict[str, Any]
) -> ProjectionRun:
    return baseline_run(
        [Player.model_validate(p) for p in data["players"]],
        [Fixture.model_validate(f) for f in data["fixtures"]],
        state.snapshot_id,
        data["source_cutoff"],
        state.data_mode,
        state.next_event,
        reference["horizon_events"],
    )


def forecast_job(
    store: Store,
    state: ManagerState,
    data: dict[str, Any],
    payload: dict[str, Any],
    runners: dict[str, ForecastRunner] | None = None,
) -> ProjectionRun:
    reference = payload.get("_forecast")
    if reference is None:
        reference = resolve_forecast(store, payload, state)
    reference = {**reference, "horizon_events": payload["horizon_events"]}
    if reference["provider"] != "baseline":
        verify_artifact(reference)
        from fpl_app.storage import fingerprint

        bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
        if fingerprint(bundle) != reference["bundle_fingerprint"]:
            raise ValueError("Selected serving feature bundle changed")
    providers: dict[str, ForecastRunner] = {"baseline": baseline_provider}
    if runners:
        providers.update(runners)
    if reference["provider"] not in providers:
        raise ValueError("Selected provider adapter is unavailable; no silent baseline fallback")
    run = providers[reference["provider"]](store, state, data, reference)
    if (
        run.snapshot_id != state.snapshot_id
        or run.data_mode != state.data_mode
        or run.horizon_events != payload["horizon_events"]
    ):
        raise ValueError("Provider output does not match frozen job inputs")
    return run.model_copy(
        update={
            "requested_provider": reference["requested_provider"],
            "resolved_provider": reference["provider"],
            "artifact_id": reference["artifact_id"],
            "artifact_manifest_sha256": reference["manifest_sha256"],
            "prediction_origin": reference["prediction_origin"],
            "evidence_mode": "synthetic"
            if state.data_mode == "demo"
            else (
                "deployed"
                if reference["mode"] == "default"
                else "prospective_shadow"
                if reference["mode"] == "shadow"
                else "experimental_live"
            ),
            "lifecycle_state": "active"
            if reference["provider"] == "baseline"
            else reference["mode"],
        }
    )
