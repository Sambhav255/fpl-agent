"""Evaluate retained finalized official labels, then publish a separate serving refit.

No manager state, network collection, promotion or manual JSON inputs required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.models.football_catboost import train_collection_experiment
from fpl_app.models.release_packets import digest
from fpl_app.models.router import artifact_path
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    store = Store()
    collection = load_collection(store, args.collection_id)
    source = next(
        s for s in collection["sources"] if s["resource"] == "bootstrap-static/"
    )
    bootstrap = json.loads(store.snapshot(source["id"])["raw"])
    directory = train_collection_experiment(
        collection,
        artifact_path("football_catboost", "placeholder").parent,
        "fpl-" + collection["season"].replace("/", "-"),
        bootstrap,
    )
    metadata = json.loads((directory / "manifest.json").read_text())
    report = {
        "artifact_id": directory.name,
        "artifact_manifest_sha256": digest(directory / "manifest.json"),
        "evaluation_reference": metadata["evaluation_artifact_reference"],
        "evaluation_sha256": digest(directory / "evaluation.json"),
        "collection_id": args.collection_id,
        "collection_sha256": collection["envelope_sha256"],
        "actual_source_available_at": collection["available_at"],
        "actual_capture_completed_at": collection["captured_at"],
        "historical_evaluation_timing": "retrospective_assumed",
        "champion_promoted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        json.dump(report, file, sort_keys=True, indent=2)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
