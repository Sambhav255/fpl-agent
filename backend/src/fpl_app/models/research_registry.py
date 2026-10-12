"""Discover genuine D12 artifacts without loading checkpoints or activating them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fpl_app.storage import fingerprint

from .publication import verify_model_run


def research_entries(root: Path) -> list[dict[str, Any]]:
    entries = []
    for family in ("tft_multilead", "ensemble"):
        entry: dict[str, Any] = {
            "model_family": family,
            "name": "Multilead TFT" if family == "tft_multilead" else "Mean ensemble",
            "status": "not_trained",
            "active": False,
            "strict_release_eligible": False,
            "evaluation_kind": "research_unqualified",
            "metrics": None,
            "reason": ["No retained research artifact; baseline remains default"],
            "artifacts": [],
        }
        # Stable directory ordering, never select a winner using held-out scores.
        for path in sorted(root.glob(f"{family}/*/manifest.json")):
            record: dict[str, Any] = {"artifact_id": path.parent.name, "status": "disabled"}
            try:
                if any(p.is_symlink() for p in (root, path.parent.parent, path.parent, path)):
                    raise ValueError("Artifact symlinks are not allowed")
                meta = verify_model_run(path.parent)
                if meta.get("model_family") != family:
                    raise ValueError("Research artifact family mismatch")
                manifest_sha = hashlib.sha256(path.read_bytes()).hexdigest()
                evaluations = []
                if family == "tft_multilead":
                    horizon = meta.get("horizon_events")
                    if type(horizon) is not int or not 1 <= horizon <= 8:
                        raise ValueError("Invalid multilead horizon")
                    if (
                        not {"mean.ckpt", "quantiles.ckpt", "dataset.pt"}
                        <= meta["artifacts"].keys()
                    ):
                        raise ValueError("Incomplete multilead checkpoints")
                    for report_path in sorted(path.parent.glob("evaluation-*.json")):
                        if report_path.is_symlink():
                            raise ValueError("Evaluation symlinks are not allowed")
                        report = json.loads(report_path.read_text())
                        if not isinstance(report, dict):
                            raise TypeError("Evaluation must be an object")
                        if (
                            report_path.name != f"evaluation-{fingerprint(report)}.json"
                            or report.get("manifest_sha256") != manifest_sha
                            or report.get("model_family") != family
                            or report.get("partition") != "test"
                            or not report.get("panel_sha256")
                            or not isinstance(report.get("lead_metrics"), dict)
                            or set(report["lead_metrics"])
                            != {str(i) for i in range(1, horizon + 1)}
                        ):
                            raise ValueError("Unbound multilead evaluation")
                        evaluations.append(report)
                else:
                    if not {"weights.json", "evaluation.json"} <= meta["artifacts"].keys():
                        raise ValueError("Incomplete ensemble artifacts")
                    report = json.loads((path.parent / "evaluation.json").read_text())
                    if not isinstance(report, dict):
                        raise TypeError("Evaluation must be an object")
                    if report.get("partition") != "test" or not isinstance(
                        report.get("blend"), dict
                    ):
                        raise ValueError("Held-out ensemble evaluation required")
                    fingerprint(report)  # Reject non-finite metrics before API serialization.
                    evaluations.append(report)
                record.update(
                    status="evaluated_research" if evaluations else "trained_research",
                    manifest_sha256=manifest_sha,
                    available_at=meta.get("available_at"),
                    horizon_events=meta.get("horizon_events"),
                    evidence_mode=meta.get("data_evidence_mode", "unqualified_research"),
                    evaluations=evaluations,
                    limitations=meta.get("limitations", []),
                )
            except (OSError, ValueError, KeyError, TypeError):
                record["reason"] = "Invalid research artifact or evaluation; ignored for serving"
            entry["artifacts"].append(record)
        valid = [r for r in entry["artifacts"] if r["status"] != "disabled"]
        if valid:
            entry["status"] = (
                "evaluated_research"
                if any(r["status"] == "evaluated_research" for r in valid)
                else "trained_research"
            )
            entry["reason"] = [
                "Retained research artifacts only; no live serving or default promotion",
                "Integrity and held-out report bindings do not establish audited data or model advantage",
                "Per-artifact reports preserve lead-specific metrics; no winning-test artifact selected",
            ]
        elif entry["artifacts"]:
            entry.update(
                status="disabled", reason=["All retained research artifacts failed validation"]
            )
        entries.append(entry)
    return entries
