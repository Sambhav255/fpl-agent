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
    parser.add_argument("--work-once", action="store_true")
    parser.add_argument(
        "--export", type=Path, help="Export retained scorecards as JSON"
    )
    args = parser.parse_args()
    store = Store()
    queue = Queue(store)
    jobs = (
        [
            queue.enqueue(
                "forecast_benchmark_score",
                {
                    "benchmark_id": args.benchmark_id,
                    "check_slot": int(time.time()) // (6 * 3600),
                },
            )
        ]
        if args.benchmark_id
        else enqueue_due_benchmarks(store)
    )
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
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(json.dumps({"scorecards": scorecards}, indent=2) + "\n")
        print(
            json.dumps(
                {"exported_scorecards": len(scorecards), "output": str(args.export)}
            )
        )


if __name__ == "__main__":
    main()
