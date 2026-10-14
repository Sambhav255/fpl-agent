"""Capture, queue, freeze and seal a baseline paper journal through a local worker.

Uses the existing reviewed state in DATA_DIR, never imports an account or submits
FPL actions. API port must point at that same isolated store. All policies share
one fresh forecast and decision; actual execution remains unknown.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.jobs import input_state
from fpl_app.learning.packets import (
    capture_replay_evidence,
    produce_journal_replay_packet,
)
from fpl_app.storage import Store, fingerprint
from prepare_journal_replay import POLICIES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-id", type=int, required=True)
    parser.add_argument("--api-port", type=int, required=True)
    parser.add_argument("--horizon", type=int, choices=range(1, 9), default=6)
    parser.add_argument("--policy", choices=[*POLICIES, "all"], default="all")
    parser.add_argument("--solver-time-limit", type=float, default=3)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if (
        not 1 <= args.api_port <= 65535
        or not 0 < args.timeout <= 600
        or not 0.1 <= args.solver_time_limit <= 30
    ):
        parser.error("Use a valid local port, timeout <=600s and solver limit 0.1..30s")
    store = Store()
    state, _ = input_state(store, args.team_id)
    state_sha = fingerprint(state.model_dump(mode="json"))
    policies = (
        POLICIES if args.policy == "all" else {args.policy: POLICIES[args.policy]}
    )
    with httpx.Client(
        base_url=f"http://127.0.0.1:{args.api_port}/api/v1", timeout=30, trust_env=False
    ) as client:

        def request(path: str, body: dict | None = None) -> dict:
            response = (
                client.get(path) if body is None else client.post(path, json=body)
            )
            response.raise_for_status()
            return response.json()

        if fingerprint(request(f"/teams/{args.team_id}/state")) != state_sha:
            raise ValueError(
                "Local API and DATA_DIR do not share the same reviewed manager state"
            )
        captures = {
            name: capture_replay_evidence(store, args.team_id, args.horizon, policy)
            for name, policy in policies.items()
        }
        stop = time.monotonic() + args.timeout

        def wait(job: dict) -> dict:
            while time.monotonic() < stop:
                result = request("/jobs/" + job["job_id"])
                if result["status"] == "succeeded":
                    return result["result"]
                if result["status"] in {"failed", "cancelled"}:
                    raise ValueError(
                        "Recoverable worker job failed; inspect its persisted job status"
                    )
                time.sleep(0.5)
            raise TimeoutError(
                "Worker wait expired; queued work and captures are preserved"
            )

        forecast_job = request(
            "/projections/runs",
            {
                "team_id": args.team_id,
                "provider": "baseline",
                "horizon_events": args.horizon,
                "replay_capture_id": next(iter(captures.values()))["capture_id"],
            },
        )
        forecast = wait(forecast_job)
        analysis_job = request(
            "/recommendations",
            {
                "team_id": args.team_id,
                "expected_state_version": state.state_version,
                "projection_run_id": forecast["projection_run_id"],
                "settings": {
                    "horizon_events": args.horizon,
                    "max_transfers_this_event": 2,
                    "solver_time_limit_seconds": args.solver_time_limit,
                },
            },
        )
        recommendation = wait(analysis_job)
        journal = request(
            "/learning/decisions",
            {
                "recommendation_id": recommendation["recommendation_id"],
                "idempotency_key": "prospective-" + forecast["projection_run_id"],
            },
        )
        seals = {
            name: produce_journal_replay_packet(
                store, journal["decision_id"], captures[name]["capture_id"], policy
            )
            for name, policy in policies.items()
        }
        if fingerprint(request(f"/teams/{args.team_id}/state")) != state_sha:
            raise ValueError(
                "Manager state changed during prospective journal production"
            )
        print(
            json.dumps(
                {
                    "decision_id": journal["decision_id"],
                    "deadline": journal["deadline"],
                    "prediction_origin": forecast["prediction_origin"],
                    "decision_origin": journal["decision_origin"],
                    "projection_job_id": forecast_job["job_id"],
                    "analysis_job_id": analysis_job["job_id"],
                    "projection_run_id": forecast["projection_run_id"],
                    "players": len(journal["players"]),
                    "fixture_forecasts": len(forecast["projections"]),
                    "horizon_events": forecast["horizon_events"],
                    "execution_status": journal["execution_status"],
                    "seals": seals,
                    "manager_state_unchanged": True,
                    "completed_prospective_evaluation": False,
                },
                sort_keys=True,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
