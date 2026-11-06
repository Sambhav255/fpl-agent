"""Register and run direct-lead research without changing live forecasts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.jobs import Queue, Worker
from fpl_app.models.multilead_experiments import protocol
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--work-once", action="store_true")
    args = parser.parse_args()
    store = Store()
    spec = protocol(load_collection(store, args.collection_id))
    store.put("multilead_experiment_protocol", fingerprint(spec), spec, expected=0)
    queue = Queue(store)
    job = queue.enqueue("multilead_experiment", {"protocol": spec})
    print(json.dumps({"job_id": job["id"], "status": job["status"]}), flush=True)
    if args.work_once:
        Worker(queue).run_once(job["id"])
        completed = queue.get(job["id"])
        print(
            json.dumps(
                {
                    "job_id": job["id"],
                    "status": completed["status"],
                    "error": completed.get("error"),
                    "result": completed.get("result"),
                }
            ),
            flush=True,
        )
        if completed["status"] == "failed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
