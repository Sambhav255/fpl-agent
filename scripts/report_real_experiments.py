"""Publish checksum-bound experiment evidence without exporting manager state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.models.release_packets import digest
from fpl_app.models.router import artifact_path, verify_artifact
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--current-artifact", required=True)
    parser.add_argument("--archive-experiment", type=Path, required=True)
    parser.add_argument("--rl-experiment", type=Path, required=True)
    parser.add_argument("--planning-report", type=Path, required=True)
    parser.add_argument("--current-planning-report", type=Path)
    parser.add_argument("--ensemble-artifact")
    parser.add_argument("--integration-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    current = artifact_path("football_catboost", args.current_artifact)
    metadata = verify_artifact(
        {
            "provider": "football_catboost",
            "artifact_id": args.current_artifact,
            "manifest_sha256": digest(current / "manifest.json"),
        }
    )
    collection = load_collection(Store(), args.collection_id)
    if metadata["provenance"]["collection_id"] != args.collection_id:
        raise ValueError("Current fit and capture differ")
    for directory, manifest_name, files_key in (
        (args.archive_experiment, "manifest.json", "files"),
        (args.rl_experiment, "football_experiment.json", "artifacts"),
    ):
        manifest = json.loads((directory / manifest_name).read_text())
        for name, checksum in manifest[files_key].items():
            path = directory / name
            if Path(name).name != name or path.is_symlink() or digest(path) != checksum:
                raise ValueError("Experiment evidence changed")
    receipts = [
        {
            key: source[key]
            for key in (
                "id",
                "resource",
                "provider",
                "season",
                "captured_at",
                "available_at",
                "source_published_at",
                "payload_sha256",
                "validation_status",
            )
        }
        for source in collection["sources"]
    ]
    report = {
        "schema_version": 1,
        "produced_at": utcnow(),
        "champions": {"football": "baseline", "strategy": "numerical_planner"},
        "collection_id": args.collection_id,
        "collection_sha256": collection["envelope_sha256"],
        "sources_sha256": hashlib.sha256(
            json.dumps(receipts, sort_keys=True).encode()
        ).hexdigest(),
        "real_vs_synthetic": {
            "football_labels": "retained actual official and pinned archive results",
            "historical_features": "explicit reconstructed assumptions",
            "future_serving": "actual pre-deadline shadow",
            "starting_squads_finances": "hypothetical paper portfolios; no actual manager inputs",
            "strict_prospective_performance": "unavailable until future finalized labels",
        },
        "actual_artifacts": {
            "current": {
                "artifact_id": args.current_artifact,
                "manifest_sha256": digest(current / "manifest.json"),
                "payloads": metadata["artifacts"],
            },
            "archive": {
                "artifact_id": json.loads(
                    (args.archive_experiment / "manifest.json").read_text()
                )["artifact_id"],
                "manifest_sha256": digest(args.archive_experiment / "manifest.json"),
            },
            "rl": {
                "artifact_id": json.loads(
                    (args.rl_experiment / "manifest.json").read_text()
                )["artifact_id"],
                "manifest_sha256": digest(args.rl_experiment / "manifest.json"),
            },
        },
        "timing": {
            "capture_completed_at": collection["captured_at"],
            "actual_sources_available_at": collection["available_at"],
            "current_fit_available_at": metadata["available_at"],
            "current_historical_labels": "kickoff+1day assumed; original publication unverified",
            "rl_historical_labels": "kickoff+27hours assumed",
            "archive_historical_labels": "kickoff+7days assumed",
            "archive_origins": "earliest event kickoff minus48hours assumed",
            "preliminary_targets_excluded": True,
        },
        "configuration": {
            "current": metadata["ablation_training_config"],
            "current_feature_version": metadata["feature_version"],
            "current_mapping_version": metadata["mapping_version"],
            "current_rules": metadata["rules_version"],
        },
    }
    policy_packet = json.loads(
        (args.rl_experiment / "football_experiment.json").read_text()
    )
    report["rl_training"] = {
        "audit": policy_packet["audit"],
        "configuration": policy_packet["configuration"],
        "packet_sha256": digest(args.rl_experiment / "football_experiment.json"),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    for name, source in (
        ("current-evaluation.json", current / "evaluation.json"),
        ("archive-evaluation.json", args.archive_experiment / "evaluation.json"),
        ("rl-evaluation.json", args.rl_experiment / "evaluation.json"),
        ("planning.json", args.planning_report),
        ("integration.json", args.integration_receipt),
        ("archive-protocol.json", args.archive_experiment / "registered_protocol.json"),
    ):
        with (args.output / name).open("xb") as file:
            file.write(source.read_bytes())
    with (args.output / "sources.json").open("x") as file:
        json.dump(receipts, file, sort_keys=True, indent=2)
    if args.current_planning_report:
        (args.output / "current-planning.json").write_bytes(
            args.current_planning_report.read_bytes()
        )
    if args.ensemble_artifact:
        ensemble = artifact_path("ensemble", args.ensemble_artifact)
        verify_artifact(
            {
                "provider": "ensemble",
                "artifact_id": args.ensemble_artifact,
                "manifest_sha256": digest(ensemble / "manifest.json"),
            }
        )
        (args.output / "serving-ensemble-evaluation.json").write_bytes(
            (ensemble / "evaluation.json").read_bytes()
        )
        (args.output / "serving-ensemble-weights.json").write_bytes(
            (ensemble / "weights.json").read_bytes()
        )
        report["actual_artifacts"]["ensemble"] = {
            "artifact_id": args.ensemble_artifact,
            "manifest_sha256": digest(ensemble / "manifest.json"),
        }
    report["files"] = {p.name: digest(p) for p in args.output.iterdir()}
    with (args.output / "manifest.json").open("x") as file:
        json.dump(report, file, sort_keys=True, indent=2)
    print(
        json.dumps(
            {
                "report": str(args.output),
                "manifest_sha256": digest(args.output / "manifest.json"),
                "contains_private_manager_state": False,
            }
        )
    )


if __name__ == "__main__":
    main()
