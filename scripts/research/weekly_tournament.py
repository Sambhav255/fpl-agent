"""Register a new fixed weekly model competition and run through the recoverable worker."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))
from fpl_app.features.pipeline import utc
from fpl_app.jobs import Queue, Worker
from fpl_app.models.weekly_tournament import protocol
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--work-once", action="store_true")
    args = parser.parse_args()
    store = Store()
    collection = load_collection(store, args.collection_id)
    event = min(
        e["event"]
        for e in collection["event_evidence"]
        if utc(e["actual_deadline"]) > utc(collection["captured_at"])
    )
    existing = next(
        (
            b
            for b in store.list("forecast_benchmark")
            if b["event"] == event
            and b["season"] == collection["season"]
            and b["protocol"].get("study_id") == args.study_id
        ),
        None,
    )
    if existing is not None:
        print(json.dumps({"status": "already_frozen", "benchmark_id": existing["benchmark_id"]}))
        return
    spec = protocol(args.collection_id, args.study_id)
    store.put("weekly_tournament_protocol", fingerprint(spec), spec, expected=0)
    queue = Queue(store)
    job = queue.enqueue("weekly_tournament", {"protocol": spec})
    print(json.dumps({"job_id": job["id"], "status": job["status"]}), flush=True)
    if args.work_once:
        Worker(queue).run_once(job["id"])
        result = queue.get(job["id"])
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "result": result.get("result"),
                    "error": result.get("error"),
                }
            ),
            flush=True,
        )
        if result["status"] != "succeeded":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
