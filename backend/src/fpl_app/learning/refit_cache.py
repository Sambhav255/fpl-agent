"""Avoid fitting the same finalized labels on every scheduled capture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fpl_app.storage import Store, fingerprint


def refit_identity(collection: dict[str, Any], implementation: str) -> str:
    """Observation receipts change on polls; football inputs and revisions matter."""
    finals = [r for r in collection["labels"] if r["label_status"] == "final_revision"]
    keys = {(r["provider_player_id"], r["fixture_id"]) for r in finals}
    events = {r.get("event") for r in finals}
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
            "exposures": [
                {k: v for k, v in row.items() if k not in {"snapshot_id", "available_at"}}
                for row in collection.get("schedule_exposures", [])
                if (row["provider_player_id"], row["fixture_id"]) in keys
            ],
            "event_deadlines": [
                {k: row[k] for k in ("event", "actual_deadline")}
                for row in collection.get("event_evidence", [])
                if row["event"] in events
            ],
        }
    )


def cached_refit(store: Store, identity: str) -> dict[str, Any] | None:
    try:
        row = store.get("learning_refit", identity)
    except KeyError:
        return None
    try:
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
    except OSError as exc:
        raise ValueError("Cached refit artifact unavailable") from exc
    return {**row, "reused_unchanged_inputs": True}
