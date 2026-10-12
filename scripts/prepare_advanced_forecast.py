"""Register audited shadow inputs, optionally publishing a reviewed artifact copy.

No source fetching, manager edits, model promotion or account actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.jobs import Queue, input_state
from fpl_app.models.advanced_serving import register_bundle
from fpl_app.models.qualification import qualify_shadow
from fpl_app.storage import Store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=["bayesian", "tft", "tft_multilead", "ensemble"],
        required=True,
    )
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument(
        "--review-id",
        help="Publish a new immutable shadow copy from this approved local review",
    )
    parser.add_argument("--team-id", type=int)
    parser.add_argument("--input-bundle-id")
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="Queue an explicit shadow forecast for the normal worker",
    )
    args = parser.parse_args()
    if bool(args.team_id) != bool(args.input_bundle_id) or (
        args.enqueue and not args.team_id
    ):
        parser.error(
            "Registration needs both --team-id and --input-bundle-id; enqueue needs registration"
        )
    if not args.review_id and not args.input_bundle_id:
        parser.error("Select --review-id or --input-bundle-id")
    store = Store()
    artifact_id = args.artifact_id
    result = {"provider": args.provider, "artifact_id": artifact_id, "active": False}
    if args.review_id:
        result = qualify_shadow(store, args.provider, artifact_id, args.review_id)
        artifact_id = result["artifact_id"]
    if args.input_bundle_id:
        state, _ = input_state(store, args.team_id)
        result = register_bundle(
            store, state, args.provider, artifact_id, args.input_bundle_id
        )
        if args.enqueue:
            job = Queue(store).enqueue(
                "projection",
                {
                    "team_id": args.team_id,
                    "provider": args.provider,
                    "mode": "shadow",
                    "artifact_id": artifact_id,
                    "serving_bundle_id": result["serving_bundle_id"],
                    "horizon_events": result["horizon_events"],
                },
            )
            result["job_id"] = job["id"]
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
