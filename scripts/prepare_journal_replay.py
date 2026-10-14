"""Capture baseline replay evidence, then assemble and seal a fresh frozen journal."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.evaluation.strategy import (
    keep_policy,
    planner_policy,
    proxy_planner_policy,
)
from fpl_app.jobs import Queue
from fpl_app.learning.packets import (
    capture_replay_evidence,
    produce_journal_replay_packet,
)
from fpl_app.storage import Store

POLICIES = {
    "keep": keep_policy,
    "planner": planner_policy,
    "proxy": proxy_planner_policy,
}


def main(argv: list[str] | None = None, *, store: Store | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="Run before requesting the forecast")
    capture.add_argument("--team-id", type=int, required=True)
    capture.add_argument("--horizon", type=int, choices=range(1, 9), default=6)
    capture.add_argument("--policy", choices=[*POLICIES, "all"], default="all")
    capture.add_argument(
        "--enqueue",
        action="store_true",
        help="Queue the captured baseline forecast for the existing worker",
    )
    seal = commands.add_parser(
        "seal", help="Use a matching pre-origin capture, not manual JSON"
    )
    seal.add_argument("--decision-id", required=True)
    seal.add_argument("--capture-id", required=True)
    seal.add_argument("--policy", choices=POLICIES, required=True)
    args = parser.parse_args(argv)
    store = store or Store()
    try:
        if args.command == "capture":
            policies = (
                POLICIES
                if args.policy == "all"
                else {args.policy: POLICIES[args.policy]}
            )
            receipts = {
                name: capture_replay_evidence(store, args.team_id, args.horizon, policy)
                for name, policy in policies.items()
            }
            result = {
                "captures": receipts,
                "projection_request": {
                    "team_id": args.team_id,
                    "provider": "baseline",
                    "horizon_events": args.horizon,
                    "replay_capture_id": next(iter(receipts.values()))["capture_id"],
                },
                "next": "Queue projection_request at /api/v1/projections/runs (or use --enqueue); wait for its worker, request analysis, freeze the decision, then seal each captured policy",
            }
            if args.enqueue:
                from fpl_app.api import ProjectionRequest

                payload = ProjectionRequest.model_validate(
                    result["projection_request"]
                ).model_dump()
                job = Queue(store).enqueue("projection", payload)
                result["job"] = {"job_id": job["id"], "status": job["status"]}
        else:
            result = produce_journal_replay_packet(
                store, args.decision_id, args.capture_id, POLICIES[args.policy]
            )
    except (KeyError, ValueError, RuntimeError, OSError) as exc:
        print(
            json.dumps(
                {"error": "REPLAY_PREPARATION_FAILED", "error_type": type(exc).__name__}
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
