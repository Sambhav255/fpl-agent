"""Publish a new reviewed shadow artifact; never edit the original research run."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from typing import Any

from fpl_app.storage import Store, fingerprint, utcnow

from .advanced_serving import FAMILIES, SourceReceipt, _release, _sources
from .publication import open_model_run, publish_model_run
from .router import _checked_file, artifact_path, instant, verify_artifact
from .training import data_dir


def qualify_shadow(store: Store, family: str, artifact_id: str, review_id: str) -> dict[str, Any]:
    if family not in FAMILIES or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", review_id):
        raise ValueError("Valid advanced family and local review ID required")
    review_path = data_dir() / "model_reviews" / f"{review_id}.json"
    if any(p.is_symlink() for p in (review_path, review_path.parent, review_path.parent.parent)):
        raise ValueError("Review symlinks are not allowed")
    review = json.loads(review_path.read_text())
    original = artifact_path(family, artifact_id)
    if (original / "manifest.json").is_symlink():
        raise ValueError("Model manifest symlinks are not allowed")
    raw = (original / "manifest.json").read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    metadata = verify_artifact(
        {"provider": family, "artifact_id": artifact_id, "manifest_sha256": sha}
    )
    if (
        not isinstance(review, dict)
        or review.get("status") != "approved_shadow"
        or review.get("source_manifest_sha256") != sha
        or review.get("input_provenance_reviewed") is not True
        or metadata.get("data_mode") != "live"
        or metadata.get("replay_timing") != "verified"
    ):
        raise ValueError("Explicit bound review and verified live training evidence required")
    cutoff = metadata.get("training_cutoff", metadata.get("fitting_labels_available_at"))
    if not cutoff or instant(cutoff) > instant(utcnow()):
        raise ValueError("Known actual training information cutoff required")
    receipts = [SourceReceipt.model_validate(r) for r in review.get("training_sources", [])]
    if not receipts:
        raise ValueError("Retained training sources required")
    _sources(store, receipts, cutoff)
    identifier = "qualified-" + fingerprint({"manifest": sha, "review": review})[:32]
    destination = artifact_path(family, identifier)
    if (destination / "manifest.json").is_file():
        digest = hashlib.sha256((destination / "manifest.json").read_bytes()).hexdigest()
        _release(
            store,
            {"provider": family, "artifact_id": identifier, "manifest_sha256": digest},
            utcnow(),
        )
        return {"provider": family, "artifact_id": identifier, "active": False, "mode": "shadow"}
    staging, _ = open_model_run(destination)
    try:
        hashes = metadata["artifacts"]
        for name in hashes:
            if name in {"release_audit.json", "training_manifest.json"}:
                raise ValueError(
                    "Qualify the original training artifact, not an already reviewed copy"
                )
            shutil.copyfile(original / name, staging / name)
        evaluation_name = review.get("evaluation_file")
        evaluation_sha = review.get("evaluation_sha256")
        if not isinstance(evaluation_name, str) or not isinstance(evaluation_sha, str):
            raise TypeError("Bound evaluation file and checksum required in review")
        evaluation_path = _checked_file(original, evaluation_name, evaluation_sha)
        shutil.copyfile(evaluation_path, staging / evaluation_name)
        (staging / "training_manifest.json").write_bytes(raw)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in staging.iterdir()}
        audit = {
            "status": "approved_shadow",
            "model_family": family,
            "rules_version": metadata.get("rules_version"),
            "model_payloads": hashes,
            "input_provenance_reviewed": True,
            "training_sources": review["training_sources"],
            "evaluation_file": review.get("evaluation_file"),
            "review_sha256": fingerprint(review),
            "source_manifest_sha256": sha,
        }
        (staging / "release_audit.json").write_text(json.dumps(audit, sort_keys=True, indent=2))
        hashes = {
            **hashes,
            "release_audit.json": hashlib.sha256(
                (staging / "release_audit.json").read_bytes()
            ).hexdigest(),
        }
        qualified = {
            **metadata,
            "artifact_id": identifier,
            "available_at": utcnow(),
            "artifacts": hashes,
            "active": False,
            "source_artifact_id": artifact_id,
            "source_manifest_sha256": sha,
            "limitations": [
                *metadata.get("limitations", []),
                "Locally reviewed shadow copy; no default promotion or external timing attestation",
            ],
        }
        # A manifest with two checksum dialects must agree after copying.
        if "files" in qualified:
            qualified["files"] = hashes
        (staging / "manifest.json").write_text(json.dumps(qualified, sort_keys=True, indent=2))
        # Full release validation uses the candidate path before atomic publication.
        candidate_reference = {
            "provider": family,
            "artifact_id": identifier,
            "manifest_sha256": hashlib.sha256((staging / "manifest.json").read_bytes()).hexdigest(),
        }
        validate_release_directory(store, staging, candidate_reference)
        publish_model_run(staging, destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {"provider": family, "artifact_id": identifier, "active": False, "mode": "shadow"}


def validate_release_directory(store, staging, reference):
    """Validate before publishing without changing any global path resolver."""
    from .advanced_serving import validate_release
    from .publication import verify_model_run

    validate_release(store, staging, verify_model_run(staging), reference["provider"], utcnow())
