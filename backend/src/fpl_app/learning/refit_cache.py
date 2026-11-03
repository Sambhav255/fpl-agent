"""Avoid fitting the same finalized labels on every scheduled capture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fpl_app.storage import Store, fingerprint


def refit_identity(collection: dict[str, Any], implementation: str) -> str:
    """Observation receipts change on polls; football inputs and revisions matter."""
    return fingerprint(
        {
            "implementation": implementation,
            "season": collection["season"],
            "labels": [
                {k: r[k] for k in ("provider_player_id", "fixture_id", "revision_sha256")}
                for r in sorted(
                    (r for r in collection["labels"] if r["label_status"] == "final_revision"),
                    key=lambda r: (r["provider_player_id"], r["fixture_id"]),
                )
            ],
            "mappings": [
                {k: v for k, v in row.items() if k != "bootstrap_snapshot_id"}
                for row in collection.get("player_mappings", [])
            ],
            "fixtures": collection.get("fixture_versions", []),
            "event_deadlines": collection.get("event_evidence", []),
        }
    )


def cached_refit(store: Store, identity: str) -> dict[str, Any] | None:
    try:
        row = store.get("learning_refit", identity)
    except KeyError:
        return None
    directory = Path(row["artifact_directory"])
    manifest_path = directory / "manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != row["manifest_sha256"]:
        raise ValueError("Cached refit manifest changed")
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["files"].items():
        if (
            Path(name).name != name
            or hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Cached refit artifact changed")
    return {**row, "reused_unchanged_inputs": True}
