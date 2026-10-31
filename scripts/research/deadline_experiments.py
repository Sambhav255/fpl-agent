"""Queue fixed deadline ablations and freeze their next-event predictions."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.jobs import Queue, Worker
from fpl_app.models.deadline_experiments import protocol
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument(
        "--work-once", action="store_true", help="Process one durable job locally"
    )
    args = parser.parse_args()
    store = Store()
    specification = protocol(args.collection_id)
    store.put(
        "deadline_experiment_protocol",
        fingerprint(specification),
        specification,
        expected=0,
    )
    queue = Queue(store)
    job = queue.enqueue("deadline_experiment", {"protocol": specification})
    print(json.dumps({"job_id": job["id"], "status": job["status"]}), flush=True)
    if args.work_once:
        Worker(queue).run_once()
        result = queue.get(job["id"])
        print(
            json.dumps(
                {
                    "job_id": job["id"],
                    "status": result["status"],
                    "error": result.get("error"),
                    "result": result.get("result"),
                }
            ),
            flush=True,
        )
        if result["status"] == "failed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
