"""Freeze ranking selections before outcomes; optionally score a retained past event."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.evaluation.selection import make_selection_plan
from fpl_app.learning.forecast_benchmark import checked_benchmark
from fpl_app.learning.selection_review import (
    collection_eligibility,
    register_plan,
    review_selection,
    verified_evidence,
)
from fpl_app.providers import Provider
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-plan", required=True, type=Path)
    parser.add_argument("--comparator", required=True)
    parser.add_argument("--method-manifest", required=True, type=Path)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--challenger", default="points_hurdle_news_zero")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    store = Store()
    analysis_plan = json.loads(args.analysis_plan.read_text())
    benchmarks = [checked_benchmark(store, i) for i in analysis_plan["benchmark_ids"]]
    if any(b["event"] != analysis_plan["event"] for b in benchmarks):
        raise ValueError("Analysis plan and benchmarks differ")
    collections = {b["protocol"].get("collection_id") for b in benchmarks} - {None}
    if len(collections) != 1:
        raise ValueError("One frozen collection reference required for eligibility")
    eligibility, source = collection_eligibility(store, collections.pop(), analysis_plan["event"])
    manifest = json.loads(args.method_manifest.read_text())
    if manifest["benchmark_id"] not in analysis_plan["benchmark_ids"]:
        raise ValueError("Method manifest is not one of the selected forecast artifacts")
    method = fingerprint(
        {
            "implementation": manifest.get(
                "implementation_sha256",
                {
                    "retained_report_sha256": hashlib.sha256(
                        args.method_manifest.read_bytes()
                    ).hexdigest()
                },
            ),
            "configurations": [
                {
                    k: v
                    for k, v in c.items()
                    if k not in ("selected_iterations", "validation", "exploratory_test")
                }
                for c in manifest["variants"]
            ],
            "baseline_sha256": hashlib.sha256(
                (ROOT / "backend/src/fpl_app/models/baseline.py").read_bytes()
            ).hexdigest(),
            "fit_procedure": next(
                b["protocol"]["version"] for b in benchmarks if "version" in b["protocol"]
            ),
        }
    )
    plan = make_selection_plan(
        benchmarks,
        eligibility,
        source,
        comparator=args.comparator,
        study_id=args.study_id,
        method_regime=method,
        challenger=args.challenger,
    )
    register_plan(store, plan)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / ("selection-plan-" + plan["plan_id"] + ".json")).write_text(
        json.dumps(plan, indent=2, allow_nan=False) + "\n"
    )
    report = None
    if args.score:
        provider = Provider(store)
        sources = []
        for resource in (
            "bootstrap-static/",
            "fixtures/",
            f"event/{plan['event']}/live/",
        ):
            source_record = (
                store.latest(resource) if args.offline else provider.fetch(resource, force=True)
            )
            if source_record is None:
                raise ValueError("Outcome source absent")
            sources.append(source_record["id"])
        report = review_selection(store, plan["plan_id"], *sources)
        store.put_checked("forecast_selection_review", report["revision"], report, lambda: None)
        (args.output / ("selection-review-" + report["revision"] + ".json")).write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
    evidence = verified_evidence(store, study_id=args.study_id, challenger=args.challenger)
    (args.output / "selection-evidence.json").write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                "event": plan["event"],
                "plan_id": plan["plan_id"],
                "evidence_mode": plan["evidence_mode"],
                "eligible_players": len(plan["eligible_ids"]),
                "scored_status": report["status"] if report else None,
                "readiness": evidence["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
