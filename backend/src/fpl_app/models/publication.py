"""Stage model artifacts and publish them once. A completed manifest is reused."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def run_staging(dest: Path) -> Path:
    return dest.parent.parent / f".staging-{dest.parent.name}-{dest.name}"


def verify_model_run(dest: Path) -> dict[str, Any]:
    manifest_path = dest / "manifest.json"
    if dest.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("model manifest missing")
    meta = json.loads(manifest_path.read_text())
    if not isinstance(meta, dict):
        raise TypeError("model manifest must be an object")
    artifacts = meta.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("model manifest has no artifacts")
    for name, checksum in artifacts.items():
        if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
            raise ValueError("invalid artifact name")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("invalid artifact checksum")
        path = dest / name
        if path.is_symlink():
            raise ValueError("model artifact symlinks are not allowed")
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        if digest != checksum:
            raise ValueError("existing run artifact checksum mismatch")
    return meta


def open_model_run(dest: Path) -> tuple[Path, bool]:
    """Return a completed run, or a fresh staging directory. Never overwrite either."""
    if (dest / "manifest.json").is_file():
        verify_model_run(dest)
        return dest, True
    if dest.exists():
        raise ValueError("refusing to overwrite an incomplete model run")
    staging = run_staging(dest)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    return staging, False


def publish_model_run(staging: Path, dest: Path) -> Path:
    if staging.resolve() == dest.resolve():
        raise ValueError("cannot publish a run onto itself")
    verify_model_run(staging)
    if dest.exists():
        raise ValueError("refusing to overwrite an existing model run")
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.rename(staging, dest)
    return dest


def reuse_model_run(dest: Path, dataset_sha256: str) -> bool:
    if not (dest / "manifest.json").is_file():
        return False
    meta = verify_model_run(dest)
    if meta.get("dataset_sha256") != dataset_sha256:
        raise ValueError("existing run is not bound to this dataset")
    return True


def publication_timing(*partitions: pd.DataFrame) -> dict[str, str]:
    """Bound new artifacts to all information used for fitting/model selection.

    Availability is actual execution time, never an inferred historical deadline.
    Untouched test outcomes must not be passed as fitting partitions.
    """
    timestamps = []
    for partition in partitions:
        for field in ("decision_cutoff", "target_available_at"):
            if field not in partition:
                raise ValueError("training information timestamps missing")
            parsed = pd.to_datetime(partition[field], utc=True, errors="raise")
            if parsed.isna().any() or not len(parsed):
                raise ValueError("training information timestamps incomplete")
            timestamps.append(parsed.max())
    if not timestamps:
        raise ValueError("no fitting partitions")
    information = max(timestamps)
    available = datetime.now(UTC)
    if information.to_pydatetime() > available:
        raise ValueError("training uses future information")
    return {"training_cutoff": information.isoformat(), "available_at": available.isoformat()}
