"""Fit an immutable current-era challenger; register only after current-state validation.

Run with backend/.venv/bin/python scripts/prepare_football_forecast.py
--collection-id ID --team-id ID [--register]. No fetching, state edits or promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.contracts import ManagerState
from fpl_app.models.football_catboost import train_collection_experiment
from fpl_app.models.router import artifact_path, create_serving_bundle
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store


def prepare_forecast(
    store: Store,
    collection_id: str,
    team_id: int,
    register: bool = False,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    collection = load_collection(store, collection_id)
    bootstrap_source = next(
        s for s in collection["sources"] if s["resource"] == "bootstrap-static/"
    )
    bootstrap = json.loads(store.snapshot(bootstrap_source["id"])["raw"])
    before = store.get("state", team_id)
    rules_version = "fpl-" + collection["season"].replace("/", "-")
    if artifact_id is None:
        run = train_collection_experiment(
            collection,
            artifact_path("football_catboost", "placeholder").parent,
            rules_version,
            bootstrap,
        )
    else:
        run = artifact_path("football_catboost", artifact_id)
    manifest = json.loads((run / "manifest.json").read_text())
    origin = json.loads((run / "forecast_origin.json").read_text())
    if (
        manifest["provenance"]["collection_id"] != collection_id
        or origin["artifact_manifest_sha256"]
        != hashlib.sha256((run / "manifest.json").read_bytes()).hexdigest()
    ):
        raise ValueError("Prepared artifact does not bind this collection/manifest")
    for filename, checksum in origin["files"].items():
        if (
            Path(filename).name != filename
            or (run / filename).is_symlink()
            or hashlib.sha256((run / filename).read_bytes()).hexdigest() != checksum
        ):
            raise ValueError("Prepared forecast file checksum mismatch")
    summary: dict[str, Any] = {
        "artifact_id": run.name,
        "artifact_path": str(run),
        "collection_id": collection_id,
        "rules_version": manifest["rules_version"],
        "mode": "experimental",
        "promoted": False,
        "prediction_origin": origin["prediction_origin"],
        "target_event": origin["event"],
        "forecast_files": origin["files"],
        "artifact_manifest_sha256": origin["artifact_manifest_sha256"],
        "partitions": manifest["partitions"],
        "label_states": dict(
            Counter(label["label_status"] for label in collection["labels"])
        ),
        "evaluation": json.loads((run / manifest["evaluation_reference"]).read_text()),
        "limitations": [
            "Only final_revision labels enter fitting and diagnostic evaluation; preliminary GW6 is excluded",
            "Future lag features currently also use final_revision rows only; pending observed event statistics are not treated as finals or zeros",
            "Selected-player limited experimental benchmark; no champion promotion",
            "Artifact preparation does not advance manager event or confirm finances/chips",
        ],
        "serving_bundle_id": None,
        "serving_status": "not_requested",
    }
    if register:
        try:
            bundle = create_serving_bundle(
                store, ManagerState.model_validate(before), collection_id, run.name
            )
        except (ValueError, KeyError) as exc:
            summary["serving_status"] = "blocked_pending_state_or_source_review"
            summary["serving_blocker"] = str(exc)
        else:
            summary["serving_bundle_id"] = bundle["serving_bundle_id"]
            summary["serving_status"] = "registered_experimental_only"
    if store.get("state", team_id) != before:
        raise ValueError(
            "Manager state changed during preparation; review concurrent edits"
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--team-id", type=int, required=True)
    parser.add_argument(
        "--artifact-id",
        help="Reuse an existing frozen artifact instead of fitting again",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Validate and register serving bundle; stale private state remains blocked",
    )
    args = parser.parse_args()
    if args.team_id <= 0:
        parser.error("team-id must be a positive integer")
    summary = prepare_forecast(
        Store(), args.collection_id, args.team_id, args.register, args.artifact_id
    )
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
