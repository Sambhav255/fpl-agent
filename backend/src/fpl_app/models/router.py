"""Immutable forecast selection; an experiment is never a default promotion."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fpl_app.contracts import Fixture, ManagerState, Player, Projection, ProjectionRun
from fpl_app.storage import Store, fingerprint, utcnow

from .baseline import baseline_run
from .training import data_dir


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Forecast timestamps require an explicit timezone")
    return parsed.astimezone(UTC)


def artifact_path(family: str, identifier: str) -> Path:
    if family not in {
        "football_catboost",
        "catboost",
        "bayesian",
        "tft",
        "tft_multilead",
        "ensemble",
    }:
        raise ValueError("Unknown forecast provider")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", identifier):
        raise ValueError("Invalid artifact ID")
    path = data_dir() / "models" / family / identifier
    if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink():
        raise ValueError("Artifact symlinks are not allowed")
    return path


def verify_artifact(reference: dict[str, Any]) -> dict[str, Any]:
    path = artifact_path(reference["provider"], reference["artifact_id"])
    if (path / "manifest.json").is_symlink() or not (path / "manifest.json").is_file():
        raise ValueError("Selected model artifact is unavailable")
    raw = (path / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["manifest_sha256"]:
        raise ValueError("Selected artifact manifest changed; create a new job")
    metadata: dict[str, Any] = json.loads(raw)
    if not isinstance(metadata, dict):
        raise TypeError("Model manifest must be an object")
    if (
        metadata.get("model_family")
        and metadata.get("family")
        and metadata["model_family"] != metadata["family"]
    ):
        raise ValueError("Conflicting artifact family aliases")
    if metadata.get("artifact_id") and metadata["artifact_id"] not in {
        reference["artifact_id"],
        f"{reference['provider']}/{reference['artifact_id']}",
    }:
        raise ValueError("Artifact identity mismatch")
    hashes = metadata.get("artifacts", metadata.get("files", {}))
    if (
        metadata.get("artifacts")
        and metadata.get("files")
        and metadata["artifacts"] != metadata["files"]
    ):
        raise ValueError("Conflicting artifact checksum aliases")
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
    from .advanced_serving import FAMILIES, checked_inputs

    if provider in FAMILIES:
        from fpl_app.evaluation.provenance import implementation_sha256

        if mode != "shadow":
            raise ValueError("Advanced research providers support explicit shadow mode only")
        identifier = payload.get("serving_bundle_id")
        if not identifier:
            raise ValueError("Advanced shadow requires a registered immutable input bundle")
        bundle = store.get("forecast_bundle", identifier)
        if payload.get("artifact_id") != bundle.get("artifact_id"):
            raise ValueError("Advanced selection artifact differs from frozen bundle")
        reference.update(
            artifact_id=bundle["artifact_id"],
            manifest_sha256=bundle["manifest_sha256"],
            prediction_origin=bundle["prediction_origin"],
            horizon_events=payload["horizon_events"],
            bundle_fingerprint=fingerprint(bundle),
            implementation_sha256=implementation_sha256(),
        )
        checked_inputs(store, state, store.get("dataset", state.snapshot_id), reference)
        return reference
    if state.data_mode != "live":
        raise ValueError("Real model artifacts cannot serve synthetic demo squads")
    identifier = payload.get("artifact_id")
    if not isinstance(identifier, str):
        raise ValueError("Advanced selection requires an explicit artifact ID")  # noqa: TRY004
    path = artifact_path(provider, identifier)
    if (path / "manifest.json").is_symlink() or not (path / "manifest.json").is_file():
        raise ValueError("Selected model artifact is unavailable")
    reference.update(
        artifact_id=identifier,
        manifest_sha256=hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest(),
    )
    metadata = verify_artifact(reference)
    legacy_live = (
        provider == "football_catboost"
        and metadata.get("data_evidence_mode") == "retrospective_assumed"
        and metadata.get("provenance", {}).get("provider") == "official_fpl"
        and metadata.get("provenance", {}).get("collection_id")
        and metadata.get(
            "current_training_data_available_at", metadata.get("current_training_available")
        )
    )
    if metadata.get("model_family", metadata.get("family")) != provider or not (
        metadata.get("data_mode") == "live" or legacy_live
    ):
        raise ValueError("Artifact family or real-data evidence is incompatible")
    available = metadata.get("artifact_available_at", metadata.get("available_at"))
    cutoff = metadata.get("training_cutoff", metadata.get("information_cutoff"))
    actual_training = metadata.get(
        "current_training_data_available_at", metadata.get("current_training_available")
    )
    if actual_training and cutoff:
        cutoff = max((cutoff, actual_training), key=instant)
    if not available or not cutoff:
        raise ValueError("Artifact training and actual availability timestamps required")
    if not instant(cutoff) <= instant(available) <= instant(reference["prediction_origin"]):
        raise ValueError("Artifact information or availability is in the future")
    horizon = metadata.get("supported_horizon", metadata.get("horizon_events", 1))
    if payload["horizon_events"] > horizon:
        raise ValueError("Requested horizon exceeds evaluated provider support")
    if (
        metadata.get("rules_version") not in {"2026-27-v1", "fpl-2026-27"}
        or state.season != "2026/27"
    ):
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
    if provider == "football_catboost":
        reference["prediction_origin"] = bundle.get("prediction_origin", "")
        reference["horizon_events"] = payload["horizon_events"]
        _football_bundle(store, state, store.get("dataset", state.snapshot_id), reference, metadata)
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

        bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
        if fingerprint(bundle) != reference["bundle_fingerprint"]:
            raise ValueError("Selected serving feature bundle changed")
    providers: dict[str, ForecastRunner] = {
        "baseline": baseline_provider,
        "football_catboost": football_provider,
    }
    from .advanced_serving import FAMILIES, advanced_provider

    if reference["provider"] in FAMILIES and reference.get("mode") != "shadow":
        raise ValueError("Advanced research providers support explicit shadow mode only")
    providers.update(dict.fromkeys(FAMILIES, advanced_provider))
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


def _checked_file(directory: Path, name: str, digest: str) -> Path:
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
    ):
        raise ValueError("Unsafe serving bundle filename")
    target = directory / name
    if target.is_symlink() or not target.is_file():
        raise ValueError("Unsafe or missing serving bundle file")
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise ValueError("Serving bundle file checksum mismatch")
    return target


def _football_bundle(
    store: Store,
    state: ManagerState,
    data: dict[str, Any],
    reference: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[Any, Any, dict[str, Any]]:
    """Bind local immutable frames to verified retained official source observations."""
    import pandas as pd

    from fpl_app.features.football import FEATURES, collection_frames
    from fpl_app.providers.collection import load_collection

    if store.get("current", "live")["snapshot_id"] != state.snapshot_id:
        raise ValueError("Manager snapshot is stale; review state before serving")
    bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
    if fingerprint(bundle) != reference["bundle_fingerprint"]:
        raise ValueError("Selected serving feature bundle changed")
    if any(
        bundle.get(key) != reference[key]
        for key in ["artifact_id", "manifest_sha256", "prediction_origin"]
    ):
        raise ValueError("Serving bundle artifact or origin mismatch")
    if (
        bundle.get("snapshot_id") != state.snapshot_id
        or bundle.get("source_cutoff") != data["source_cutoff"]
    ):
        raise ValueError("Serving bundle snapshot/cutoff is stale")
    if any(bundle.get(key) != metadata.get(key) for key in ["feature_version", "mapping_version"]):
        raise ValueError("Serving bundle feature/mapping version mismatch")
    origin = instant(reference["prediction_origin"])
    actual_training = metadata.get(
        "current_training_data_available_at", metadata.get("current_training_available")
    )
    available = metadata.get("artifact_available_at", metadata.get("available_at"))
    cutoff = metadata.get("training_cutoff", metadata.get("information_cutoff"))
    if (
        not available
        or not cutoff
        or max(instant(cutoff), instant(actual_training or cutoff)) > instant(available)
        or instant(available) > origin
        or origin > instant(utcnow())
    ):
        raise ValueError("Artifact/source did not exist at prediction origin")
    if (
        state.data_mode != "live"
        or metadata.get("rules_version") not in {"2026-27-v1", "fpl-2026-27"}
        or state.season != "2026/27"
        or reference["horizon_events"] != 1
    ):
        raise ValueError("Unsupported live football regime or horizon")
    directory = artifact_path("football_catboost", reference["artifact_id"])
    hashes = bundle.get("files", {})
    if not hashes:
        raise ValueError("Serving bundle file checksums required")
    for name, digest in hashes.items():
        _checked_file(directory, name, digest)
    names: list[str] = [bundle[key] for key in ["features_file", "mappings_file", "origin_file"]]
    if any(name not in hashes for name in names):
        raise ValueError("Serving bundle features, mappings and origin files required")
    origin_record = json.loads((directory / names[2]).read_text())
    if (
        origin_record.get("artifact_manifest_sha256") != reference["manifest_sha256"]
        or origin_record.get("prediction_origin") != reference["prediction_origin"]
        or origin_record.get("event") != state.next_event
        or origin_record.get("rules_version") != metadata["rules_version"]
    ):
        raise ValueError("Frozen forecast origin does not match selected event/artifact")
    if any(origin_record.get("files", {}).get(name) != hashes[name] for name in names[:2]):
        raise ValueError("Origin record does not bind serving features/mappings")
    collection = load_collection(store, bundle["collection_id"])
    if (
        collection["season"] != state.season
        or collection["data_mode"] != "live"
        or origin_record.get("input_captured_at") != collection["captured_at"]
    ):
        raise ValueError("Serving collection identity/capture mismatch")
    provenance = metadata.get("provenance", {})
    if (
        provenance.get("collection_id") != collection["collection_id"]
        or provenance.get("source_ref") != collection["envelope_sha256"]
        or provenance.get("sources") != collection["sources"]
    ):
        raise ValueError("Artifact does not bind serving collection/source evidence")
    if not actual_training or instant(actual_training) < max(
        max(instant(source["captured_at"]), instant(source["available_at"]))
        for source in collection["sources"]
    ):
        raise ValueError("Artifact training availability predates retained collection sources")
    if (
        any(
            max(instant(s["available_at"]), instant(s["captured_at"])) > origin
            for s in collection["sources"]
        )
        or instant(collection["available_at"]) > origin
        or instant(data["source_cutoff"]) > origin
    ):
        raise ValueError("Serving source was unavailable at prediction origin")
    deadlines = [
        e["actual_deadline"] for e in collection["event_evidence"] if e["event"] == state.next_event
    ]
    if (
        len(deadlines) != 1
        or not origin < instant(deadlines[0])
        or instant(utcnow()) >= instant(deadlines[0])
    ):
        raise ValueError("Target deadline has passed; live forecasts require the next open event")
    bootstrap_source = next(
        s for s in collection["sources"] if s["resource"] == "bootstrap-static/"
    )
    catalog_snapshot = store.snapshot(data["bootstrap_snapshot_id"])
    if (
        hashlib.sha256(catalog_snapshot["raw"]).hexdigest() != bootstrap_source["payload_sha256"]
        or catalog_snapshot["payload_sha256"] != bootstrap_source["payload_sha256"]
    ):
        raise ValueError(
            "Serving collection bootstrap differs from current catalogue; refresh/review state"
        )
    bootstrap = json.loads(store.snapshot(bootstrap_source["id"])["raw"])
    if "player_mappings" not in collection:
        elements = {p["id"]: p for p in bootstrap["elements"]}
        collection = {
            **collection,
            "player_mappings": [
                {
                    "provider_player_id": i,
                    "canonical_player_id": f"official_fpl:{collection['season']}:element:{i}",
                    "position": elements[i]["element_type"],
                }
                for i in collection["player_ids"]
            ],
        }
    _, expected, expected_mappings = collection_frames(collection, metadata["rules_version"])
    features = pd.read_parquet(directory / names[0])
    mappings = pd.read_parquet(directory / names[1])
    universe = bundle.get("player_ids")
    if (
        not isinstance(universe, list)
        or not universe
        or any(type(i) is not int or i <= 0 for i in universe)
        or len(set(universe)) != len(universe)
    ):
        raise ValueError("Explicit unique player universe required")
    catalog = {p["player_id"]: Player.model_validate(p) for p in data["players"]}
    owned = {p.player_id for p in state.picks}
    if state.persistent_picks:
        owned |= {p.player_id for p in state.persistent_picks}
    if not owned <= set(universe) or not set(universe) <= set(catalog):
        raise ValueError(
            "Partial player coverage: universe must include every owned and only known players"
        )
    if set(universe) != set(collection["player_ids"]) or set(features.player_id) != set(universe):
        raise ValueError("Partial player/exposure coverage; missing rows are not zero outcomes")
    expected = expected[expected.player_id.isin(universe)]
    columns = [
        "player_id",
        "fixture_id",
        "event",
        "player_key",
        "feature_version",
        "source_ref",
        "source_available_at",
        *FEATURES,
    ]
    try:
        pd.testing.assert_frame_equal(
            features[columns].sort_values(["player_id", "fixture_id"]).reset_index(drop=True),
            expected[columns].sort_values(["player_id", "fixture_id"]).reset_index(drop=True),
            check_dtype=False,
            check_exact=True,
        )
        pd.testing.assert_frame_equal(
            mappings.sort_values("current_player_id").reset_index(drop=True),
            expected_mappings.sort_values("current_player_id").reset_index(drop=True),
            check_dtype=False,
            check_exact=True,
        )
    except (AssertionError, KeyError) as exc:
        raise ValueError("Serving features/mappings disagree with retained collection") from exc
    if not pd.to_datetime(features.decision_cutoff, utc=True).eq(pd.Timestamp(origin)).all():
        raise ValueError("Serving feature origin mismatch")
    fixture_models = [
        Fixture.model_validate(f) for f in data["fixtures"] if f["event"] == state.next_event
    ]
    scheduled = {
        (i, f.fixture_id)
        for i in universe
        for f in fixture_models
        if catalog[i].club in [f.home_club, f.away_club]
    }
    actual = list(zip(features.player_id, features.fixture_id, strict=True))
    if (
        len(actual) != len(set(actual))
        or set(actual) != scheduled
        or not features.event.eq(state.next_event).all()
    ):
        raise ValueError("Incomplete or duplicate scheduled exposures; missing rows are not zeros")
    retained_fixtures = {
        f["id"]: f
        for f in json.loads(
            store.snapshot(
                next(s["id"] for s in collection["sources"] if s["resource"] == "fixtures/")
            )["raw"]
        )
    }
    positions = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    for row in features.to_dict("records"):
        player = catalog[row["player_id"]]
        fixture = next(f for f in fixture_models if f.fixture_id == row["fixture_id"])
        retained = retained_fixtures[fixture.fixture_id]
        if (
            (fixture.home_club, fixture.away_club, fixture.event, fixture.kickoff)
            != (
                retained["team_h"],
                retained["team_a"],
                retained["event"],
                retained.get("kickoff_time"),
            )
            or row["position"] != positions[player.position]
            or row["club"] != f"official_fpl:{state.season}:team:{player.club}"
        ):
            raise ValueError(
                "Current catalogue role or schedule differs from retained serving source"
            )
        if fixture.kickoff is None or instant(fixture.kickoff) <= origin:
            raise ValueError("Serving fixture kickoff is not in the future at origin")
    return features, mappings, bundle


def football_provider(
    store: Store, state: ManagerState, data: dict[str, Any], reference: dict[str, Any]
) -> ProjectionRun:
    from .football_catboost import forecast_frozen

    metadata = verify_artifact(reference)
    features, mappings, bundle = _football_bundle(store, state, data, reference, metadata)
    forecasts = forecast_frozen(
        artifact_path("football_catboost", reference["artifact_id"]),
        features,
        mappings,
        reference["prediction_origin"],
    )
    from fpl_app.providers.collection import load_collection

    collection = load_collection(store, bundle["collection_id"])
    bootstrap_source = next(
        s for s in collection["sources"] if s["resource"] == "bootstrap-static/"
    )
    elements = {
        p["id"]: p for p in json.loads(store.snapshot(bootstrap_source["id"])["raw"])["elements"]
    }
    projections = []
    for row in forecasts.to_dict("records"):
        values = [
            row[k]
            for k in [
                "points_mean",
                "minutes_mean",
                "appearance_probability",
                "sixty_probability",
                "q10",
                "q50",
                "q90",
            ]
        ]
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("Non-finite football forecast")
        start = row["start_probability"]
        raw_row = dict(row)
        element = elements[row["player_id"]]
        hard_absence = element.get("chance_of_playing_next_round") == 0 or element.get(
            "status"
        ) in {"u", "s"}
        override_assumptions = []
        if hard_absence:
            for key in [
                "points_mean",
                "minutes_mean",
                "appearance_probability",
                "sixty_probability",
                "start_probability",
                "q10",
                "q50",
                "q90",
            ]:
                row[key] = 0.0
            start = 0.0
            override_assumptions = [
                "Current-event confirmed nonappearance replaces the whole unconditional forecast with zero once; no availability multiplier",
                f"Absence source {bootstrap_source['id']} sha256:{bootstrap_source['payload_sha256']} available_at={bootstrap_source['available_at']}; status={element.get('status')} chance={element.get('chance_of_playing_next_round')} news={element.get('news', '')}",
            ]
        projections.append(
            Projection(
                player_id=row["player_id"],
                fixture_id=row["fixture_id"],
                event=row["event"],
                expected_points=row["points_mean"],
                expected_minutes=row["minutes_mean"],
                appearance_probability=row["appearance_probability"],
                start_probability=float(start) if math.isfinite(float(start)) else None,
                minutes_60_probability=row["sixty_probability"],
                point_quantiles={"0.1": row["q10"], "0.5": row["q50"], "0.9": row["q90"]},
                components={
                    "full_points_mean": row["points_mean"],
                    "raw_unconditional_points_mean": raw_row["points_mean"],
                    "raw_expected_minutes": raw_row["minutes_mean"],
                    "raw_appearance_probability": raw_row["appearance_probability"],
                    "raw_sixty_probability": raw_row["sixty_probability"],
                    "raw_start_probability": float(raw_row["start_probability"])
                    if math.isfinite(float(raw_row["start_probability"]))
                    else None,
                    "raw_q10": raw_row["q10"],
                    "raw_q50": raw_row["q50"],
                    "raw_q90": raw_row["q90"],
                    "confirmed_absence_override": float(hard_absence),
                },
                assumptions=[
                    "Full points mean is unconditional; availability is not applied again",
                    "Auxiliary probabilities and quantile intervals are experimental, not calibrated confidence",
                    *override_assumptions,
                ],
            )
        )
    return ProjectionRun(
        projection_run_id="football_catboost-"
        + fingerprint({"reference": reference, "bundle": bundle})[:24],
        snapshot_id=state.snapshot_id,
        source_cutoff=data["source_cutoff"],
        data_mode="live",
        model_family="football_catboost",
        model_status="experimental",
        horizon_events=1,
        feature_version=metadata["feature_version"],
        mapping_version=metadata["mapping_version"],
        evaluation_reference=metadata.get("evaluation_reference"),
        player_universe_ids=sorted(bundle["player_ids"]),
        projections=projections,
        fixtures=[
            Fixture.model_validate(f) for f in data["fixtures"] if f["event"] == state.next_event
        ],
        warnings=[
            "Limited selected-player experimental universe; no default promotion",
            "Historical evaluation assumptions and weak current-era benchmark remain visible",
            "Confirmed current-event hard absences replace whole forecasts once; uncertain/unknown availability remains unscaled",
        ],
    )


def create_serving_bundle(
    store: Store, state: ManagerState, collection_id: str, artifact_id: str
) -> dict[str, Any]:
    """Register only a fully validated immutable bundle; never edit manager state.

    Requires a current-state snapshot whose bootstrap bytes match the collection,
    an open target event, all owned players, and every selected scheduled exposure.
    Returns the stored bundle with its serving_bundle_id for experimental selection.
    """
    if store.get("state", state.team_id) != state.model_dump(mode="json"):
        raise ValueError(
            "Manager state differs from retained current state; review event and private state"
        )
    directory = artifact_path("football_catboost", artifact_id)
    if (directory / "manifest.json").is_symlink():
        raise ValueError("Artifact manifest symlinks are not allowed")
    manifest_sha = hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()
    metadata = verify_artifact(
        {
            "provider": "football_catboost",
            "artifact_id": artifact_id,
            "manifest_sha256": manifest_sha,
        }
    )
    origin_path = directory / "forecast_origin.json"
    if origin_path.is_symlink() or not origin_path.is_file():
        raise ValueError("Unsafe or missing serving origin file")
    origin_raw = origin_path.read_bytes()
    origin_record = json.loads(origin_raw)
    hashes = {
        **origin_record["files"],
        "forecast_origin.json": hashlib.sha256(origin_raw).hexdigest(),
    }
    from fpl_app.providers.collection import load_collection

    collection = load_collection(store, collection_id)
    data = store.get("dataset", state.snapshot_id)
    if store.get("current", "live")["snapshot_id"] != state.snapshot_id:
        raise ValueError(
            "Manager state is stale; review current event and private state before serving"
        )
    bundle = {
        "snapshot_id": state.snapshot_id,
        "artifact_id": artifact_id,
        "manifest_sha256": manifest_sha,
        "prediction_origin": origin_record["prediction_origin"],
        "source_cutoff": data["source_cutoff"],
        "feature_version": metadata["feature_version"],
        "mapping_version": metadata["mapping_version"],
        "collection_id": collection_id,
        "player_ids": sorted(collection["player_ids"]),
        "features_file": "future_features.parquet",
        "mappings_file": "current_mappings.parquet",
        "origin_file": "forecast_origin.json",
        "files": hashes,
    }
    identifier = "football-" + fingerprint(bundle)[:32]

    # Validation reads a bundle from Store. Use an in-memory overlay until it passes.
    class CandidateStore:
        def get(self, kind: str, key: Any) -> dict[str, Any]:
            return (
                bundle if kind == "forecast_bundle" and key == identifier else store.get(kind, key)
            )

        def snapshot(self, key: str) -> dict[str, Any]:
            return store.snapshot(key)

    reference = {
        "provider": "football_catboost",
        "artifact_id": artifact_id,
        "manifest_sha256": manifest_sha,
        "serving_bundle_id": identifier,
        "bundle_fingerprint": fingerprint(bundle),
        "prediction_origin": bundle["prediction_origin"],
        "horizon_events": 1,
    }
    _football_bundle(CandidateStore(), state, data, reference, metadata)  # type: ignore[arg-type]
    try:
        existing = store.get("forecast_bundle", identifier)
    except KeyError:
        store.put("forecast_bundle", identifier, bundle, expected=0)
    else:
        if existing != bundle:
            raise ValueError("Immutable serving bundle conflicts")
    return {**bundle, "serving_bundle_id": identifier}
