from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def registry() -> list[dict[str, Any]]:
    """Read genuine manifests dynamically; training never implies activation."""
    from .training import data_dir

    root = data_dir() / "models"
    entries: list[dict[str, Any]] = [
        {
            "model_family": "baseline",
            "name": "baseline",
            "status": "active",
            "reason": "Labelled approximate baseline, no trained parameters",
            "metrics": None,
        }
    ]
    football: dict[str, Any] = {
        "model_family": "football_catboost",
        "name": "Football CatBoost",
        "status": "not_trained",
        "active": False,
        "strict_release_eligible": False,
        "reason": "No football-specific artifact; baseline remains default",
        "metrics": None,
    }
    for path in sorted(root.glob("football_catboost/*/manifest.json")):
        try:
            if path.is_symlink() or path.parent.is_symlink():
                raise ValueError("artifact symlinks are not allowed")
            meta = json.loads(path.read_text())
            if meta.get("model_family", meta.get("family")) != "football_catboost":
                raise ValueError("artifact family mismatch")
            files = meta.get("artifacts", meta.get("files", {}))
            if not files or any(
                Path(name).name != name
                or (path.parent / name).is_symlink()
                or not (path.parent / name).is_file()
                or hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != sha
                for name, sha in files.items()
            ):
                raise ValueError("artifact integrity check failed")
            evaluation = json.loads((path.parent / "evaluation.json").read_text())
            football.update(
                status="evaluated_experimental",
                artifact_id=meta["artifact_id"],
                metrics=evaluation.get("comparators", {}).get("football_catboost"),
                comparators=evaluation.get("comparators"),
                evaluation_kind=evaluation.get("evaluation_kind", "retrospective_assumed"),
                reason=[
                    "Experimental only; not promoted to default recommendations",
                    "Historical availability is assumed; prospective validation remains required",
                    *meta.get("limitations", []),
                ],
            )
        except (OSError, ValueError, KeyError, TypeError):
            football.pop("artifact_id", None)
            football.update(
                status="disabled", reason="Invalid football model artifact", metrics=None
            )
    entries.append(football)
    for family, dependency in (
        ("catboost", "catboost"),
        ("bayesian", "pymc"),
        ("tft", "pytorch_forecasting"),
    ):
        try:
            installed = importlib.util.find_spec(dependency) is not None
        except (ImportError, ValueError):
            installed = False
        entry: dict[str, Any] = {
            "model_family": family,
            "name": family,
            "status": "not_trained" if installed else "not_installed",
            "reason": "No real audited training artifact"
            if installed
            else f"Optional dependency {dependency} unavailable",
            "metrics": None,
        }
        manifests = sorted(root.glob(f"{family}/*/manifest.json"), key=lambda p: p.stat().st_mtime)
        for path in manifests:
            try:
                meta = json.loads(path.read_text())
                if meta.get("data_mode") != "live" or meta.get("model_family") != family:
                    continue
                artifacts = meta.get("artifacts", {})
                if not artifacts or any(
                    not (path.parent / name).is_file()
                    or hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != checksum
                    for name, checksum in artifacts.items()
                ):
                    raise ValueError("artifact integrity check failed")
                evaluation_path = path.parent / "evaluation.json"
                metrics = None
                status = "trained"
                if evaluation_path.exists():
                    evaluation = json.loads(evaluation_path.read_text())
                    if (
                        evaluation.get("run_id") == meta["run_id"]
                        and evaluation.get("dataset_sha256") == meta["dataset_sha256"]
                        and evaluation.get("partition") == "test"
                    ):
                        status, metrics = "evaluated", evaluation["metrics"]
                entry.update(
                    active=False,
                    strict_release_eligible=False,
                    evaluation_kind="deadline_verified"
                    if meta.get("replay_timing") == "verified"
                    else "retrospective_unverified",
                    status=status if installed else "not_installed",
                    run_id=meta["run_id"],
                    reason=meta.get("limitations", []),
                    metrics=metrics,
                    artifact_directory=str(path.parent),
                    replay_timing=meta.get("replay_timing"),
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                entry.update(status="disabled", reason=f"Invalid artifact: {exc}", metrics=None)
        entries.append(entry)
    return entries
