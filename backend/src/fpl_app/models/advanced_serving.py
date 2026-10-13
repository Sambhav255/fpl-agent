"""Local audited shadow bundles; never infer qualification from a research fit.

Audit records are operator-reviewed local evidence, not external attestations.
No provider requests, account writes or optional model imports during registration.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from fpl_app.contracts import Fixture, ManagerState, Player, ProjectionRun
from fpl_app.domain.rules import RULES
from fpl_app.storage import Store, fingerprint

from .training import data_dir

FAMILIES = {"bayesian", "tft", "tft_multilead", "ensemble"}


class SourceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class InputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    review_status: Literal["reviewed_local"]
    snapshot_id: str
    artifact_id: str
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    family: Literal["bayesian", "tft", "tft_multilead", "ensemble"]
    rules_version: str
    source_cutoff: str
    available_at: str
    prediction_origin: str
    next_event: int = Field(ge=1, le=38)
    horizon_events: int = Field(ge=1, le=8)
    schedule_complete_events: list[int]
    player_map: dict[str, StrictInt]
    club_map: dict[int, int]
    sources: list[SourceReceipt] = Field(min_length=2)
    files: dict[str, str]
    fixture_times: dict[int, float] = Field(default_factory=dict)
    member_bundle_ids: dict[str, str] = Field(default_factory=dict)
    seed: int = 42
    samples: int = Field(default=500, ge=2, le=10000)


def input_path(identifier: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", identifier):
        raise ValueError("Invalid serving input ID")
    path = data_dir() / "serving_inputs" / identifier
    if any(p.is_symlink() for p in (path, path.parent, path.parent.parent)):
        raise ValueError("Serving input symlinks are not allowed")
    return path


def _sources(store: Store, receipts: list[SourceReceipt], cutoff: str) -> set[str]:
    from .router import instant

    identifiers = set()
    for receipt in receipts:
        source = store.snapshot(receipt.snapshot_id)
        if (
            receipt.snapshot_id in identifiers
            or source["provider"] != "official_fpl"
            or source["data_mode"] != "live"
            or source["validation_status"] != "valid"
            or source["payload_sha256"] != receipt.sha256
            or hashlib.sha256(source["raw"]).hexdigest() != receipt.sha256
            or instant(source["captured_at"]) > instant(source["available_at"])
            or instant(source["available_at"]) > instant(cutoff)
        ):
            raise ValueError("Missing, changed or future retained source evidence")
        identifiers.add(receipt.snapshot_id)
    return identifiers


def _release(store: Store, reference: dict[str, Any], origin: str) -> dict[str, Any]:
    from .router import artifact_path, verify_artifact

    metadata = verify_artifact(reference)
    family = reference["provider"]
    directory = artifact_path(family, reference["artifact_id"])
    validate_release(store, directory, metadata, family, origin)
    return metadata


def validate_release(
    store: Store, directory: Path, metadata: dict[str, Any], family: str, origin: str
) -> None:
    from .router import _checked_file, instant

    hashes = metadata.get("artifacts", {})
    if "release_audit.json" not in hashes:
        raise ValueError("Advanced shadow requires a retained local release audit")
    audit = json.loads(
        _checked_file(directory, "release_audit.json", hashes["release_audit.json"]).read_text()
    )
    if (
        not isinstance(audit, dict)
        or audit.get("status") != "approved_shadow"
        or audit.get("model_family") != family
        or audit.get("rules_version") != RULES.version
        or audit.get("model_payloads")
        != {k: v for k, v in hashes.items() if k != "release_audit.json"}
        or metadata.get("data_mode") != "live"
        or (
            metadata.get("replay_timing") != "verified"
            and not (
                family == "ensemble"
                and metadata.get("replay_timing") == "historical_assumed_shadow"
                and metadata.get("data_evidence_mode") == "retrospective_assumed"
                and metadata.get("serving_mode") == "shadow_only"
                and audit.get("evaluation_evidence") == "retrospective_assumed"
                and {"training_manifest.json", "training_receipts.json"} <= hashes.keys()
            )
        )
        or metadata.get("rules_version") != RULES.version
        or metadata.get("model_family") != family
        or (family != "ensemble" and metadata.get("model_status") != "trained")
    ):
        raise ValueError("Local release audit does not bind verified live model payloads")
    cutoff = metadata.get("training_cutoff", metadata.get("fitting_labels_available_at"))
    available = metadata.get("available_at")
    if not cutoff or not available or not instant(cutoff) <= instant(available) <= instant(origin):
        raise ValueError("Advanced artifact timing is incompatible")
    receipts = [SourceReceipt.model_validate(r) for r in audit.get("training_sources", [])]
    if not receipts:
        raise ValueError("Training source evidence required")
    _sources(store, receipts, cutoff)
    if audit.get("input_provenance_reviewed") is not True:
        raise ValueError("Training and serving feature provenance needs local review")
    evaluation_name = audit.get("evaluation_file")
    if not isinstance(evaluation_name, str) or evaluation_name not in hashes:
        raise ValueError("Checksum-bound held-out evaluation required")
    evaluation = json.loads(
        _checked_file(directory, evaluation_name, hashes[evaluation_name]).read_text()
    )
    if not isinstance(evaluation, dict) or evaluation.get("partition") != "test":
        raise ValueError("Untouched test evaluation required")
    fingerprint(evaluation)  # Reject non-finite diagnostic values.
    if family == "tft_multilead":
        if (
            "training_manifest.json" not in hashes
            or evaluation.get("manifest_sha256") != hashes["training_manifest.json"]
            or not isinstance(evaluation.get("lead_metrics"), dict)
            or not any(
                isinstance(m, dict) and m.get("n", 0) > 0
                for m in evaluation["lead_metrics"].values()
            )
        ):
            raise ValueError("TFT evaluation must bind the retained original training manifest")
    elif family == "tft" and (
        evaluation.get("run_id") != metadata.get("run_id")
        or not metadata.get("dataset_sha256")
        or evaluation.get("dataset_sha256") != metadata["dataset_sha256"]
        or evaluation.get("metrics", {}).get("n", 0) <= 0
    ):
        raise ValueError("TFT held-out evaluation identity or coverage mismatch")
    elif family == "bayesian" and (
        evaluation.get("run_id") != metadata.get("run_id")
        or not metadata.get("dataset_sha256")
        or evaluation.get("dataset_sha256") != metadata["dataset_sha256"]
        or evaluation.get("metrics", {}).get("n", 0) <= 0
    ):
        raise ValueError("Bayesian held-out evaluation identity or coverage mismatch")
    elif family == "ensemble" and (
        evaluation.get("blend", {}).get("n", 0) <= 0
        or evaluation.get("test_origin_count", 0) <= 0
        or evaluation.get("validation", {}).get("weights")
        != json.loads((directory / "weights.json").read_text())
    ):
        raise ValueError("Ensemble weights or held-out coverage differ from evaluation")
    if family == "bayesian" and "scoring_profiles.json" not in hashes:
        raise ValueError("Partial Bayesian points are unavailable for serving")
    required = (
        {"posterior.nc", "diagnostics.json"}
        if family == "bayesian"
        else {"weights.json"}
        if family == "ensemble"
        else {"mean.ckpt", "quantiles.ckpt", "dataset.pt"}
    )
    if not required <= hashes.keys():
        raise ValueError("Incomplete trained model payloads")


def checked_inputs(
    store: Store, state: ManagerState, data: dict[str, Any], reference: dict[str, Any]
) -> tuple[InputManifest, Path, dict[str, Any]]:
    from .router import _checked_file, instant, utcnow

    bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
    if reference.get("implementation_sha256"):
        from fpl_app.evaluation.provenance import implementation_sha256

        if reference["implementation_sha256"] != implementation_sha256():
            raise ValueError("Queued advanced forecast implementation changed")
    if fingerprint(bundle) != reference["bundle_fingerprint"]:
        raise ValueError("Selected advanced serving bundle changed")
    directory = input_path(bundle["input_bundle_id"])
    raw = _checked_file(directory, "manifest.json", bundle["input_manifest_sha256"]).read_bytes()
    manifest = InputManifest.model_validate_json(raw)
    if (
        manifest.family != reference["provider"]
        or manifest.artifact_id != reference["artifact_id"]
        or manifest.manifest_sha256 != reference["manifest_sha256"]
        or manifest.prediction_origin != reference["prediction_origin"]
        or manifest.snapshot_id != state.snapshot_id
        or manifest.source_cutoff != data["source_cutoff"]
        or manifest.next_event != state.next_event
        or manifest.horizon_events != reference["horizon_events"]
        or manifest.rules_version != RULES.version
        or bundle.get("team_id") != state.team_id
        or state.data_mode != "live"
        or state.season != "2026/27"
        or store.get("current", "live")["snapshot_id"] != state.snapshot_id
    ):
        raise ValueError("Advanced input snapshot, artifact, origin, rules or horizon mismatch")
    origin = instant(manifest.prediction_origin)
    if (
        not instant(manifest.source_cutoff)
        <= instant(manifest.available_at)
        <= origin
        <= instant(utcnow())
    ):
        raise ValueError("Future or inconsistent input publication timing")
    events = list(range(state.next_event, state.next_event + manifest.horizon_events))
    if events[-1] > 38 or manifest.schedule_complete_events != events:
        raise ValueError("Complete frozen schedule required for every supported lead")
    deadline = next(
        (e.get("deadline_time") for e in data["events"] if e["id"] == state.next_event), None
    )
    if not deadline or instant(deadline) <= instant(utcnow()) or origin >= instant(deadline):
        raise ValueError("Advanced forecast deadline has passed or is unavailable")
    for fixture in data["fixtures"]:
        if fixture.get("event") in events and (
            not fixture.get("kickoff") or instant(fixture["kickoff"]) <= origin
        ):
            raise ValueError("Covered fixtures need known future kickoff times at origin")
    identifiers = _sources(store, manifest.sources, manifest.source_cutoff)
    if not {data["bootstrap_snapshot_id"], data["fixture_snapshot_id"]} <= identifiers:
        raise ValueError("Inputs must bind the exact retained bootstrap and fixture sources")
    universe = set(manifest.player_map.values())
    owned = {p.player_id for p in [*state.picks, *(state.persistent_picks or [])]}
    catalog = {p["player_id"]: p for p in data["players"]}
    if (
        not universe
        or len(universe) != len(manifest.player_map)
        or any(
            not key or type(value) is not int or value <= 0
            for key, value in manifest.player_map.items()
        )
        or not owned <= universe <= catalog.keys()
    ):
        raise ValueError("Explicit unambiguous universe must include every owned player")
    metadata = _release(store, reference, manifest.prediction_origin)
    if manifest.family == "tft" and manifest.horizon_events != 1:
        raise ValueError("Legacy TFT supports one lead only")
    if (
        manifest.family == "tft_multilead"
        and metadata.get("horizon_events") != manifest.horizon_events
    ):
        raise ValueError("Multilead horizon differs from evaluated model")
    for name, digest in manifest.files.items():
        if name == "manifest.json":
            raise ValueError("Input manifest cannot checksum itself")
        _checked_file(directory, name, digest)
    required = (
        {"exposures.parquet"}
        if manifest.family == "bayesian"
        else {"panel.parquet", "minutes.parquet"}
        if manifest.family.startswith("tft")
        else set()
    )
    if not required <= manifest.files.keys():
        raise ValueError("Incomplete advanced serving input frames")
    if manifest.family != "ensemble" and manifest.member_bundle_ids:
        raise ValueError("Only ensemble inputs accept member bundles")
    if manifest.family == "ensemble":
        _checked_members(store, state, data, bundle, manifest)
    return manifest, directory, metadata


def register_bundle(
    store: Store, state: ManagerState, family: str, artifact_id: str, input_id: str
) -> dict[str, Any]:
    from .router import artifact_path

    if family not in FAMILIES:
        raise ValueError("Unsupported advanced shadow provider")
    if store.get("state", state.team_id) != state.model_dump(mode="json"):
        raise ValueError("Manager state differs from retained current state")
    directory = input_path(input_id)
    if (directory / "manifest.json").is_symlink():
        raise ValueError("Input manifest symlinks are not allowed")
    raw = (directory / "manifest.json").read_bytes()
    manifest = InputManifest.model_validate_json(raw)
    model_path = artifact_path(family, artifact_id) / "manifest.json"
    if model_path.is_symlink():
        raise ValueError("Model manifest symlinks are not allowed")
    bundle = {
        "provider": family,
        "artifact_id": artifact_id,
        "manifest_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "snapshot_id": state.snapshot_id,
        "team_id": state.team_id,
        "input_bundle_id": input_id,
        "input_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "prediction_origin": manifest.prediction_origin,
        "horizon_events": manifest.horizon_events,
        "player_ids": sorted(manifest.player_map.values()),
    }
    if family == "ensemble":
        weights = json.loads((artifact_path(family, artifact_id) / "weights.json").read_text())
        if not isinstance(weights, dict):
            raise TypeError("Ensemble weights must be an object")
        bundle["member_bindings"] = {
            name: fingerprint(store.get("forecast_bundle", manifest.member_bundle_ids[name]))
            for name, weight in weights.items()
            if weight > 0
        }
    identifier = "advanced-" + fingerprint(bundle)[:32]
    bundle["serving_bundle_id"] = identifier
    reference = {
        **bundle,
        "serving_bundle_id": identifier,
        "bundle_fingerprint": fingerprint(bundle),
    }

    class CandidateStore:
        def get(self, kind, key):
            return (
                bundle if kind == "forecast_bundle" and key == identifier else store.get(kind, key)
            )

        def snapshot(self, key):
            return store.snapshot(key)

    checked_inputs(CandidateStore(), state, store.get("dataset", state.snapshot_id), reference)  # type: ignore[arg-type]
    try:
        existing = store.get("forecast_bundle", identifier)
    except KeyError:
        store.put("forecast_bundle", identifier, bundle, expected=0)
    else:
        if existing != bundle:
            raise ValueError("Immutable advanced bundle conflicts")
    return {**bundle, "serving_bundle_id": identifier, "mode": "shadow"}


def advanced_provider(
    store: Store, state: ManagerState, data: dict[str, Any], reference: dict[str, Any]
) -> ProjectionRun:
    import pandas as pd

    from .router import artifact_path

    manifest, directory, metadata = checked_inputs(store, state, data, reference)
    catalog = [
        Player.model_validate(p)
        for p in data["players"]
        if p["player_id"] in manifest.player_map.values()
    ]
    fixtures = [Fixture.model_validate(f) for f in data["fixtures"]]
    args: dict[str, Any] = {
        "artifact": artifact_path(manifest.family, manifest.artifact_id),
        "players": catalog,
        "fixtures": fixtures,
        "snapshot_id": state.snapshot_id,
        "cutoff": manifest.prediction_origin,
        "next_event": state.next_event,
        "horizon": manifest.horizon_events,
        "player_map": manifest.player_map,
        "club_map": manifest.club_map,
    }
    if manifest.family == "bayesian":
        from .strategy_adapters import bayesian_run

        result = bayesian_run(
            **args,
            exposures=pd.read_parquet(directory / "exposures.parquet"),
            fixture_times=manifest.fixture_times,
            samples=manifest.samples,
            seed=manifest.seed,
        )
    elif manifest.family.startswith("tft"):
        from .strategy_adapters import tft_run

        result = tft_run(
            **args,
            panel=pd.read_parquet(directory / "panel.parquet"),
            minutes=pd.read_parquet(directory / "minutes.parquet"),
        )
    else:
        result = _ensemble_provider(store, state, data, reference, manifest)
    from fpl_app.jobs import projection_players

    result = result.model_copy(
        update={
            "source_cutoff": data["source_cutoff"],
            "prediction_origin": manifest.prediction_origin,
            "model_family": manifest.family,
            "player_universe_ids": sorted(manifest.player_map.values()),
            "evaluation_reference": metadata["artifacts"]["release_audit.json"],
            "model_status": "experimental",
        }
    )
    projection_players(state, data, result)
    return result


def _ensemble_provider(store, state, data, reference, manifest):
    from .ensemble import ensemble_run
    from .router import artifact_path, forecast_job

    directory = artifact_path("ensemble", reference["artifact_id"])
    weights = json.loads((directory / "weights.json").read_text())
    runs = {}
    for name, weight in weights.items():
        if weight == 0:
            continue
        identifier = manifest.member_bundle_ids.get(name)
        if not identifier:
            raise ValueError("Positive ensemble weight requires a frozen member bundle")
        bundle = store.get("forecast_bundle", identifier)
        if bundle.get("provider") == "baseline":
            from .release_packets import checked_baseline_member

            runs[name] = checked_baseline_member(store, state, data, bundle)
        else:
            if bundle.get("provider") not in FAMILIES - {"ensemble"} | {"football_catboost"}:
                raise ValueError("Unsupported non-ensemble member provider")
            runs[name] = forecast_job(
                store,
                state,
                data,
                {
                    "provider": bundle["provider"],
                    "mode": "shadow",
                    "artifact_id": bundle["artifact_id"],
                    "serving_bundle_id": identifier,
                    "horizon_events": manifest.horizon_events,
                },
            )
        if runs[name].prediction_origin != manifest.prediction_origin:
            raise ValueError("Ensemble member origin differs from frozen origin")
    return ensemble_run(directory, runs)


def _checked_members(store, state, data, bundle, manifest):
    from math import isclose, isfinite

    from .router import artifact_path

    weights = json.loads(
        (artifact_path("ensemble", manifest.artifact_id) / "weights.json").read_text()
    )
    if (
        not isinstance(weights, dict)
        or not weights
        or any(type(w) not in (int, float) or not isfinite(w) or w < 0 for w in weights.values())
        or not isclose(sum(weights.values()), 1, abs_tol=1e-8)
    ):
        raise ValueError("Invalid normalized ensemble weights")
    for name, weight in weights.items():
        if weight == 0:
            continue
        identifier = manifest.member_bundle_ids.get(name)
        if not identifier:
            raise ValueError("Positive ensemble weight requires a frozen member bundle")
        member = store.get("forecast_bundle", identifier)
        if (
            member.get("provider")
            not in FAMILIES - {"ensemble"} | {"baseline", "football_catboost"}
            or fingerprint(member) != bundle.get("member_bindings", {}).get(name)
            or member.get("prediction_origin") != manifest.prediction_origin
            or member.get("horizon_events") != manifest.horizon_events
            or member.get("player_ids") != sorted(manifest.player_map.values())
        ):
            raise ValueError("Frozen ensemble member changed or has incompatible origin/coverage")
        if member["provider"] == "baseline":
            from .release_packets import checked_baseline_member

            checked_baseline_member(store, state, data, member)
        elif member["provider"] == "football_catboost":
            from .router import _football_bundle, verify_artifact

            reference = {**member, "bundle_fingerprint": fingerprint(member)}
            _football_bundle(store, state, data, reference, verify_artifact(reference))
        else:
            checked_inputs(
                store, state, data, {**member, "bundle_fingerprint": fingerprint(member)}
            )
