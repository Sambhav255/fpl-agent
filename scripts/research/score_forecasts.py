"""Queue immutable forecast scoring; preliminary results remain pending."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.jobs import Queue, Worker
from fpl_app.learning.forecast_benchmark import enqueue_due_benchmarks
from fpl_app.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-id", help="Check one explicit benchmark, even before its due time"
    )
    parser.add_argument(
        "--collection-id",
        help="Score all finalized benchmarks consumed by this collection",
    )
    parser.add_argument("--work-once", action="store_true")
    parser.add_argument(
        "--export", type=Path, help="Export retained scorecards as JSON"
    )
    args = parser.parse_args()
    if args.collection_id and (args.benchmark_id or not args.work_once):
        parser.error("--collection-id requires --work-once and excludes --benchmark-id")
    store = Store()
    queue = Queue(store)
    if args.collection_id:
        from fpl_app.learning.review import score_collection_benchmarks
        from fpl_app.providers import Provider
        from fpl_app.providers.collection import load_collection

        results = score_collection_benchmarks(
            store, Provider(store), load_collection(store, args.collection_id)
        )
        print(
            json.dumps(
                {"collection_id": args.collection_id, "benchmark_scores": results}
            ),
            flush=True,
        )
    if args.collection_id:
        jobs = []
    elif args.benchmark_id:
        jobs = [
            queue.enqueue(
                "forecast_benchmark_score",
                {
                    "benchmark_id": args.benchmark_id,
                    "check_slot": int(time.time()) // (6 * 3600),
                },
            )
        ]
    else:
        jobs = enqueue_due_benchmarks(store)
    print(
        json.dumps({"jobs": [{"id": j["id"], "status": j["status"]} for j in jobs]}),
        flush=True,
    )
    if args.work_once and jobs:
        Worker(queue).run_once()
        print(
            json.dumps(
                {
                    "jobs": [
                        {"id": j["id"], "status": queue.get(j["id"])["status"]}
                        for j in jobs
                    ]
                }
            ),
            flush=True,
        )
    scorecards = [
        r
        for r in store.list("forecast_benchmark_outcome")
        if args.benchmark_id is None or r["benchmark_id"] == args.benchmark_id
    ]
    if args.export:
        event_reviews = [
            r
            for r in store.list("forecast_event_review")
            if args.benchmark_id is None or args.benchmark_id in r["benchmarks"]
        ]
        args.export.parent.mkdir(parents=True, exist_ok=True)
        selection_reviews = [
            r
            for r in store.list("forecast_selection_review")
            if args.benchmark_id is None
            or args.benchmark_id
            in store.get("forecast_selection_plan", r["plan_id"])["benchmark_hashes"]
        ]
        args.export.write_text(
            json.dumps(
                {
                    "scorecards": scorecards,
                    "event_reviews": event_reviews,
                    "selection_reviews": selection_reviews,
                },
                indent=2,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    "exported_scorecards": len(scorecards),
                    "exported_event_reviews": len(event_reviews),
                    "exported_selection_reviews": len(selection_reviews),
                    "output": str(args.export),
                }
            )
        )


if __name__ == "__main__":
    main()
