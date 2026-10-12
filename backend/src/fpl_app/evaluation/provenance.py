"""Verify retained replay inputs; reconstructed timing is never prospective evidence."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fpl_app.contracts import Player, ProjectionRun


def replay_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Replay times require timezone")
    return parsed


def implementation_sha256() -> str:
    """Bind the policy's domain/planner dependencies as well as its own module."""
    root = Path(__file__).resolve().parents[1]
    entries = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.py"))
    }
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


class ReplayArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["source", "model", "policy", "mapping"]
    filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    captured_at: str
    available_at: str


class ReplayManifest(BaseModel):
    """Locally retained envelope, whose digest must come from a frozen reference.

    Timestamps are recorded capture evidence, not an external timestamp authority.
    The model entry covers its manifest; model payloads must also be listed so every
    byte used by a run is checked. Baseline entries can bind the implementation.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    deadline: str
    information_available_at: str
    forecast: ProjectionRun
    players: list[Player]
    schedule_complete_events: list[int]
    artifacts: list[ReplayArtifact]
    policy_identifier: str
    implementation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def verify_replay_manifest(
    path: Path,
    expected_sha256: str,
    run: ProjectionRun,
    players: list[Player],
    deadline: str,
    information_available_at: str,
    events: list[int],
    policy: Callable,
) -> dict[str, str]:
    """Fail closed on missing, changed, future or unbound prospective inputs."""
    if path.is_symlink():
        raise ValueError("Replay evidence symlinks are not allowed")
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Replay manifest checksum mismatch")
        manifest = ReplayManifest.model_validate_json(raw)
        if (
            manifest.forecast != run
            or sorted(manifest.players, key=lambda p: p.player_id)
            != sorted(players, key=lambda p: p.player_id)
            or replay_time(manifest.deadline) != replay_time(deadline)
            or replay_time(manifest.information_available_at)
            != replay_time(information_available_at)
        ):
            raise ValueError("Replay evidence does not bind these forecast/catalogue inputs")
        if not set(events) <= set(manifest.schedule_complete_events):
            raise ValueError("Missing complete frozen fixture schedule")
        # A declared complete schedule is required even for wholly blank events.
        if any(p.event in events for p in run.projections) and not run.fixtures:
            raise ValueError("Missing frozen fixture schedule")
        if run.data_mode != "live" or run.prediction_origin is None:
            raise ValueError("Strict replay requires live inputs and prediction origin")
        prediction = replay_time(run.prediction_origin)
        if not (
            replay_time(run.source_cutoff)
            <= prediction
            <= replay_time(information_available_at)
            <= replay_time(deadline)
        ):
            raise ValueError("Future strict prediction origin or source cutoff")
        roles = {entry.role for entry in manifest.artifacts}
        if roles != {"source", "model", "policy", "mapping"}:
            raise ValueError("Missing source/model/policy/mapping artifact evidence")
        names: set[str] = set()
        hashes: dict[str, str] = {}
        for entry in manifest.artifacts:
            if (
                Path(entry.filename).name != entry.filename
                or entry.filename in {"", ".", ".."}
                or entry.filename in names
                or (path.parent / entry.filename).resolve() == path.resolve()
            ):
                raise ValueError("Invalid replay artifact filename")
            names.add(entry.filename)
            artifact = path.parent / entry.filename
            if artifact.is_symlink():
                raise ValueError("Replay evidence symlinks are not allowed")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if digest != entry.sha256:
                raise ValueError("Replay artifact checksum mismatch")
            captured, available = replay_time(entry.captured_at), replay_time(entry.available_at)
            if captured > available or available > prediction:
                raise ValueError("Future source/model/policy/mapping artifact availability")
            if entry.role == "source" and available > replay_time(run.source_cutoff):
                raise ValueError("Source artifact available after forecast source cutoff")
            hashes[entry.filename] = digest
        identifier = f"{policy.__module__}.{policy.__qualname__}"
        code_path = inspect.getsourcefile(policy)
        if (
            identifier != manifest.policy_identifier
            or manifest.implementation_sha256 != implementation_sha256()
            or "<locals>" in identifier
            or code_path is None
            or not any(
                entry.role == "policy"
                and entry.sha256 == hashlib.sha256(Path(code_path).read_bytes()).hexdigest()
                for entry in manifest.artifacts
            )
        ):
            raise ValueError("Policy implementation is not bound to replay evidence")
        if run.model_family != "baseline" and (
            run.artifact_id is None or run.artifact_manifest_sha256 is None
        ):
            raise ValueError("Strict model replay requires bound model manifest identity")
        if run.artifact_manifest_sha256 is not None and not any(
            entry.role == "model" and entry.sha256 == run.artifact_manifest_sha256
            for entry in manifest.artifacts
        ):
            raise ValueError("Model manifest is not bound to replay evidence")
        if run.artifact_manifest_sha256 is not None:
            model_entry = next(
                entry
                for entry in manifest.artifacts
                if entry.role == "model" and entry.sha256 == run.artifact_manifest_sha256
            )
            model_meta = json.loads((path.parent / model_entry.filename).read_bytes())
            if not isinstance(model_meta, dict):
                raise ValueError("Invalid replay model manifest")
            if model_meta.get("artifact_id") != run.artifact_id:
                raise ValueError("Replay model identity mismatch")
            for key in ("available_at", "training_cutoff"):
                if key not in model_meta or replay_time(model_meta[key]) > prediction:
                    raise ValueError("Missing or future replay model timing")
            files = model_meta.get("artifacts", model_meta.get("files", {}))
            if (
                not isinstance(files, dict)
                or not files
                or any(hashes.get(name) != checksum for name, checksum in files.items())
            ):
                raise ValueError("Missing bound model payloads")
        return hashes
    except OSError as exc:
        raise ValueError("Missing retained replay evidence") from exc
