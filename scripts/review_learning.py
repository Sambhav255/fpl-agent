"""Enqueue due opt-in local learning reviews; run the normal recoverable worker."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--watch", action="store_true", help="Poll enabled schedules once per minute"
    )
    args = parser.parse_args()
    from fpl_app.learning.review import enqueue_due_reviews
    from fpl_app.storage import Store

    store = Store()
    while True:
        jobs = enqueue_due_reviews(store)
        print(
            json.dumps({"jobs": [{"job_id": j["id"], "status": j["status"]} for j in jobs]}),
            flush=True,
        )
        if not args.watch:
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
