"""Register and enqueue fixed linear and optional LightGBM comparisons."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))

from fpl_app.jobs import Queue, Worker
from fpl_app.models.simple_experiments import protocol
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-directory", type=Path, required=True)
    parser.add_argument("--work-once", action="store_true")
    args = parser.parse_args()
    store = Store()
    spec = protocol(args.reference_directory)
    store.put("simple_experiment_protocol", fingerprint(spec), spec, expected=0)
    queue = Queue(store)
    job = queue.enqueue("simple_experiment", {"protocol": spec})
    print(json.dumps({"job_id": job["id"], "status": job["status"]}), flush=True)
    if args.work_once:
        Worker(queue).run_once()
        result = queue.get(job["id"])
        print(json.dumps(result), flush=True)
        if result["status"] == "failed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
