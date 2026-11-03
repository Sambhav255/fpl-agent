"""Capture and review frozen event forecasts without editing the personal app state."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.learning.post_event import review_forecasts
from fpl_app.providers import Provider, team_id
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=int, required=True, choices=range(1, 39))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analysis-plan", type=Path)
    parser.add_argument(
        "--register-followup",
        action="store_true",
        help="Retain the plan for worker-generated final diagnostics after official finalization",
    )
    parser.add_argument("--team-from-main-store", action="store_true")
    parser.add_argument(
        "--offline", action="store_true", help="Use retained source snapshots"
    )
    args = parser.parse_args()
    store = Store()
    provider = Provider(store)
    resources = ("bootstrap-static/", "fixtures/", f"event/{args.event}/live/")
    sources = []
    for resource in resources:
        source = (
            store.latest(resource)
            if args.offline
            else provider.fetch(resource, force=True)
        )
        if source is None:
            raise ValueError("Required retained source absent")
        sources.append(source)
    benchmarks = [
        b["benchmark_id"]
        for b in store.list("forecast_benchmark")
        if b["event"] == args.event
    ]
    plan = json.loads(args.analysis_plan.read_text()) if args.analysis_plan else None
    if plan:
        if plan["event"] != args.event:
            parser.error("Analysis plan event differs from --event")
        benchmarks = plan["benchmark_ids"]
    if args.register_followup:
        if plan is None:
            parser.error("--register-followup requires --analysis-plan")
        digest = fingerprint(plan)
        record = {"plan": plan, "plan_sha256": digest}
        store.put_checked("forecast_analysis_plan", digest, record, lambda: None)
    review = review_forecasts(
        store, benchmarks, *(s["id"] for s in sources), analysis_plan=plan
    )
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / ("review-" + review["revision"] + ".json")
    if not path.exists():
        with path.open("x") as stream:
            json.dump(review, stream, indent=2, allow_nan=False)
    if args.team_from_main_store:
        personal = Store("sqlite:///" + str(ROOT / "data/app.sqlite"))
        states = [s for s in personal.list("state") if s.get("data_mode") == "live"]
        if len(states) != 1:
            raise ValueError("Exactly one saved personal live team required")
        identifier = team_id(states[0]["team_id"])
        before = fingerprint(states[0])
        refs = []
        for resource in (
            f"entry/{identifier}/event/{args.event}/picks/",
            f"entry/{identifier}/event/{max(1, args.event - 1)}/picks/",
            f"entry/{identifier}/history/",
            f"entry/{identifier}/transfers/",
        ):
            source = (
                store.latest(resource)
                if args.offline
                else provider.fetch(resource, force=True)
            )
            if source is None:
                raise ValueError("Retained public team source absent")
            refs.append(
                {
                    k: source[k]
                    for k in ("id", "resource", "payload_sha256", "available_at")
                }
            )
        if before != fingerprint(personal.get("state", identifier)):
            raise RuntimeError(
                "Personal state changed concurrently during read-only review"
            )
        private = {
            "event": args.event,
            "review_revision": review["revision"],
            "sources": refs,
            "state_unchanged": True,
        }
        private_path = args.output / (
            "private-team-sources-" + fingerprint(private) + ".json"
        )
        if not private_path.exists():
            with private_path.open("x") as stream:
                json.dump(private, stream, indent=2)
    print(
        json.dumps(
            {
                "status": review["status"],
                "event": args.event,
                "streams": len(review["comparisons"]),
                "common_players": len(review["common_player_ids"]),
                "report": str(path),
            }
        )
    )


if __name__ == "__main__":
    main()
