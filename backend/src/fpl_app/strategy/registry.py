"""Separate strategy registry. No heavy dependency imports or default replacement."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from fpl_app.domain.rules import RULES
from fpl_app.models.training import data_dir
from fpl_app.strategy.candidates import CANDIDATE_VERSION


def verify_policy(path: Path) -> dict[str, Any]:
    if path.is_symlink() or (path / "manifest.json").is_symlink():
        raise ValueError("Policy symlinks forbidden")
    meta = json.loads((path / "manifest.json").read_text())
    if (
        meta.get("rules_version") != RULES.version
        or meta.get("candidate_version") != CANDIDATE_VERSION
    ):
        raise ValueError("Policy versions differ")
    hashes = meta.get("artifacts", {})
    if not hashes or "evaluation.json" not in hashes or "fitted_q.npz" not in hashes:
        raise ValueError("Incomplete policy manifest")
    for name, digest in hashes.items():
        target = path / name
        if (
            Path(name).name != name
            or target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Policy checksum mismatch")
    return meta


def strategy_registry(root: Path | None = None) -> dict[str, Any]:
    root = root or data_dir() / "models" / "strategy"
    entries = []
    for path in sorted(root.glob("*/manifest.json")):
        try:
            meta = verify_policy(path.parent)
            if meta.get("publication_job_id"):
                from fpl_app.jobs import Queue
                from fpl_app.storage import Store

                job = Queue(Store()).get(meta["publication_job_id"])
                if (
                    job["status"] != "succeeded"
                    or job["result"]["artifact_id"] != meta["artifact_id"]
                ):
                    continue
            report = json.loads((path.parent / "evaluation.json").read_text())
            entries.append(
                {
                    "artifact_id": meta["artifact_id"],
                    "status": meta["status"],
                    "mode": "shadow",
                    "active": False,
                    "evidence_modes": meta["evidence_modes"],
                    "seed_count": len(meta["seeds"]),
                    "distinct_test_paths": report["distinct_test_paths"],
                    "promotion": report["promotion"],
                    "available_at": meta["available_at"],
                    "artifact_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        except (OSError, ValueError, KeyError, TypeError):
            entries.append(
                {
                    "artifact_id": path.parent.name,
                    "status": "disabled_invalid_artifact",
                    "active": False,
                }
            )
    try:
        installed = importlib.util.find_spec("sb3_contrib") is not None
    except (ValueError, ImportError):
        installed = False
    return {
        "champion": "numerical_planner",
        "rl_installed": installed,
        "policies": entries,
        "automatic_promotion": False,
        "reason": "Research/shadow policies require independent prospective evidence; numerical planner retained",
    }
