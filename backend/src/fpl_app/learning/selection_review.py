"""Source-verified ranking reviews and immutable prospective selection registration."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fpl_app.evaluation.selection import score_selection_plan, selection_evidence
from fpl_app.features.pipeline import utc
from fpl_app.learning.forecast_benchmark import checked_benchmark
from fpl_app.learning.post_event import verified_source
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow


def collection_eligibility(
    store: Store, collection_id: str, event: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct prior five fixture minutes from checksum-verified source bytes."""
    collection = load_collection(store, collection_id)
    origin = collection["captured_at"]
    future = min(
        e["event"] for e in collection["event_evidence"] if utc(e["actual_deadline"]) > utc(origin)
    )
    if future != event:
        raise ValueError("Eligibility collection belongs to a different forecast event")
    history: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in collection["labels"]:
        if (
            row["label_status"] == "final_revision"
            and row["event"] < event
            and utc(row["available_at"]) <= utc(origin)
        ):
            history[row["provider_player_id"]].append(row)
    positions = {m["provider_player_id"]: m["position"] for m in collection["player_mappings"]}
    ids = sorted(
        {e["provider_player_id"] for e in collection["schedule_exposures"] if e["event"] == event}
    )
    rows = []
    for player in ids:
        recent = sorted(history[player], key=lambda r: utc(r["statistics"]["kickoff_time"]))[-5:]
        minutes = [r["minutes"] for r in recent]
        if any(type(value) is not int or value < 0 for value in minutes):
            raise ValueError("Invalid finalized minutes coverage")
        rows.append(
            {
                "player_id": player,
                "position": positions[player],
                "prior_mean_minutes": sum(minutes) / len(minutes) if minutes else 0.0,
                "decision_cutoff": origin,
            }
        )
    return rows, {
        "collection_id": collection_id,
        "collection_sha256": collection["envelope_sha256"],
        "season": collection["season"],
        "event": event,
        "available_at": collection["available_at"],
        "verification": "retained_official_collection_reconstruction",
    }


def verify_eligibility(store: Store, plan: dict[str, Any]) -> None:
    source = plan["eligibility_source"]
    rows, expected = collection_eligibility(store, source["collection_id"], plan["event"])
    collections = {
        checked_benchmark(store, i)["protocol"].get("collection_id")
        for i in plan["benchmark_hashes"]
    }
    if (
        source != expected
        or source["season"] != plan["season"]
        or source["collection_id"] not in collections
        or fingerprint(rows) != plan["eligibility_sha256"]
    ):
        raise ValueError("Eligibility is not bound to this frozen forecast collection")


def checked_plan(store: Store, identifier: str) -> dict[str, Any]:
    plan = store.get("forecast_selection_plan", identifier)
    if fingerprint({k: v for k, v in plan.items() if k != "plan_id"}) != identifier:
        raise ValueError("Selection plan changed")
    for benchmark_id, digest in plan["benchmark_hashes"].items():
        if fingerprint(checked_benchmark(store, benchmark_id)) != digest:
            raise ValueError("Selection benchmark binding changed")
    verify_eligibility(store, plan)
    receipt = store.get("forecast_selection_registration", identifier)
    if (
        receipt["plan_id"] != identifier
        or plan["evidence_mode"] == "prospective_selection"
        and (
            not receipt["qualified_prospective"]
            or utc(receipt["received_at"]) >= utc(plan["deadline"])
        )
    ):
        raise ValueError("Actual predeadline selection registration required")
    return plan


def review_selection(
    store: Store,
    identifier: str,
    bootstrap_id: str,
    fixtures_id: str,
    live_id: str,
) -> dict[str, Any]:
    plan = checked_plan(store, identifier)
    pairs = [
        verified_source(store, i, resource)
        for i, resource in (
            (bootstrap_id, "bootstrap-static/"),
            (fixtures_id, "fixtures/"),
            (live_id, f"event/{plan['event']}/live/"),
        )
    ]
    if any(
        s["season"] != plan["season"] or utc(s["available_at"]) <= utc(plan["deadline"])
        for s, _ in pairs
    ):
        raise ValueError("Same-season post-deadline outcomes required")
    bootstrap, fixtures, live = [value for _, value in pairs]
    event = next(e for e in bootstrap["events"] if e["id"] == plan["event"])
    schedule = {f["id"]: f for f in fixtures if f.get("event") == plan["event"]}
    for benchmark_id in plan["benchmark_hashes"]:
        benchmark = checked_benchmark(store, benchmark_id)
        frozen = {f["id"]: f for f in benchmark["fixtures"]}
        if schedule.keys() != frozen.keys() or any(
            any(schedule[i].get(k) != row[k] for k in ("event", "team_h", "team_a"))
            for i, row in frozen.items()
        ):
            raise ValueError("Frozen selection schedule changed")
    if len({p["id"] for p in live["elements"]}) != len(live["elements"]):
        raise ValueError("Duplicate official outcome IDs")
    finalized = (
        event.get("finished") is True
        and event.get("data_checked") is True
        and bool(schedule)
        and all(
            f.get("finished") is True and f.get("finished_provisional") is True
            for f in schedule.values()
        )
    )
    report = score_selection_plan(
        plan,
        {p["id"]: p["stats"] for p in live["elements"]},
        finalized=finalized,
        source_refs=[
            {k: s[k] for k in ("id", "resource", "available_at", "payload_sha256")}
            for s, _ in pairs
        ],
    )
    receipt = store.get("forecast_selection_registration", identifier)
    body = {k: v for k, v in report.items() if k not in ("revision", "scored_at")}
    body["registration_sha256"] = fingerprint(receipt)
    return {**body, "revision": fingerprint(body), "scored_at": report["scored_at"]}


def registered_selection_reviews(
    store: Store, scorecard: dict[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    if scorecard.get("status") != "final":
        return []
    refs = {r["resource"]: r["id"] for r in scorecard["source_refs"]}
    artifacts = []
    for plan in store.list("forecast_selection_plan"):
        if scorecard["benchmark_id"] not in plan["benchmark_hashes"]:
            continue
        report = review_selection(
            store,
            plan["plan_id"],
            refs["bootstrap-static/"],
            refs["fixtures/"],
            refs[f"event/{plan['event']}/live/"],
        )
        artifacts.append(("forecast_selection_review", report["revision"], report))
    return artifacts


def register_plan(store: Store, plan: dict[str, Any]) -> None:
    if fingerprint({k: v for k, v in plan.items() if k != "plan_id"}) != plan["plan_id"]:
        raise ValueError("Selection plan identity invalid")
    for benchmark_id, digest in plan["benchmark_hashes"].items():
        if fingerprint(checked_benchmark(store, benchmark_id)) != digest:
            raise ValueError("Selection benchmark binding changed")
    verify_eligibility(store, plan)
    now = utcnow()
    try:
        receipt = store.get("forecast_selection_registration", plan["plan_id"])
    except KeyError:
        prospective = plan["evidence_mode"] == "prospective_selection"
        if (
            utc(plan["registered_at"]) > utc(now)
            or prospective
            and utc(now) >= utc(plan["deadline"])
        ):
            raise ValueError("Cannot backdate actual prospective registration")
        receipt = {
            "plan_id": plan["plan_id"],
            "received_at": now,
            "qualified_prospective": prospective,
        }
    if plan.get("study_id"):
        contract = {
            "study_id": plan["study_id"],
            "method_regime": plan["method_regime"],
            "protocol": plan["protocol"],
            "comparison_contract": plan["comparison_contract"],
        }
        store.put_checked("forecast_selection_study", plan["study_id"], contract, lambda: None)
    if plan.get("study_id") and plan["evidence_mode"] == "prospective_selection":
        # One canonical decision origin per study/event; corrections attach new
        # outcome revisions to this plan rather than selecting another origin.
        key = fingerprint(
            {"study": plan["study_id"], "season": plan["season"], "event": plan["event"]}
        )
        value = {
            "plan_id": plan["plan_id"],
            "study_id": plan["study_id"],
            "season": plan["season"],
            "event": plan["event"],
        }
        store.put_checked("selection_study_event", key, value, lambda: None)
    store.put_checked("forecast_selection_plan", plan["plan_id"], plan, lambda: None)
    store.put_checked("forecast_selection_registration", plan["plan_id"], receipt, lambda: None)
    checked_plan(store, plan["plan_id"])


def verified_evidence(store: Store, *, study_id: str, challenger: str) -> dict[str, Any]:
    study = store.get("forecast_selection_study", study_id)
    reports = []
    for report in store.list("forecast_selection_review"):
        if report.get("study_id") != study_id:
            continue
        plan = checked_plan(store, report["plan_id"])
        if report.get("registration_sha256") != fingerprint(
            store.get("forecast_selection_registration", plan["plan_id"])
        ):
            raise ValueError("Review registration receipt changed")
        refs = {r["resource"]: r for r in report["source_refs"]}
        for ref in refs.values():
            source, _ = verified_source(store, ref["id"], ref["resource"])
            if any(source[k] != ref[k] for k in ("available_at", "payload_sha256")):
                raise ValueError("Review outcome source changed")
        reports.append(report)
    return selection_evidence(
        reports, study_id=study_id, method_regime=study["method_regime"], challenger=challenger
    )
