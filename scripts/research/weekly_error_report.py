"""Read retained sources and freeze weekly point/opportunity/execution diagnostics."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.learning.error_report import weekly_error_report
from fpl_app.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=int, required=True, choices=range(1, 39))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark-id", action="append", default=[])
    parser.add_argument("--previous-report", type=Path, action="append", default=[])
    args = parser.parse_args()
    store = Store()
    ids = args.benchmark_id or [
        b["benchmark_id"]
        for b in store.list("forecast_benchmark")
        if b["event"] == args.event
    ]
    sources = [
        store.latest(resource)
        for resource in ("bootstrap-static/", "fixtures/", f"event/{args.event}/live/")
    ]
    if any(source is None for source in sources):
        parser.error(
            "Retained official bootstrap, fixtures and event-live snapshots required"
        )
    report = weekly_error_report(
        store,
        ids,
        *(source["id"] for source in sources),
        previous_reports=[
            json.loads(path.read_text()) for path in args.previous_report
        ],
    )
    if report["event"] != args.event:
        parser.error("Benchmark event differs from --event")
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / ("weekly-errors-" + report["report_id"] + ".json")
    with path.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(
        json.dumps(
            {
                "status": report["status"],
                "event": report["event"],
                "streams": len(report["models"]),
                "report": str(path),
                "promotion": False,
            }
        )
    )


if __name__ == "__main__":
    main()
