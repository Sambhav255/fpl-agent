"""Opted-in weekly experiments use fresh review collections and existing worker leases."""

from __future__ import annotations

import json
from typing import Any

from fpl_app.storage import Store, fingerprint, utcnow


def enqueue_tournament(store: Store, collection: dict[str, Any]) -> dict[str, Any] | None:
    settings = next((s for s in store.list("weekly_tournament_settings") if s.get("enabled")), None)
    if settings is None:
        return None
    from fpl_app.features.pipeline import utc
    from fpl_app.jobs import Queue
    from fpl_app.models.weekly_tournament import protocol

    future = [
        e
        for e in collection["event_evidence"]
        if utc(e["actual_deadline"]) > utc(collection["captured_at"])
    ]
    if not future:
        return {"status": "no_future_event"}
    event = min(e["event"] for e in future)
    deadline = next(e["actual_deadline"] for e in future if e["event"] == event)
    if utc(deadline) <= utc(utcnow()):
        return {"status": "missed_deadline_refresh_collection"}
    source = next(s for s in collection["sources"] if s["resource"] == "bootstrap-static/")
    bootstrap = json.loads(store.snapshot(source["id"])["raw"])
    previous = next((e for e in bootstrap["events"] if e["id"] == event - 1), None)
    if previous is not None and (
        previous.get("finished") is not True or previous.get("data_checked") is not True
    ):
        return {"status": "await_previous_event_finalization"}
    key = f"{settings['study_id']}:{collection['season']}:{event}"
    existing = next(
        (
            b
            for b in store.list("forecast_benchmark")
            if b["event"] == event
            and b["season"] == collection["season"]
            and b["protocol"].get("study_id") == settings["study_id"]
        ),
        None,
    )
    if existing:
        return {"status": "already_frozen", "benchmark_id": existing["benchmark_id"]}
    retained = next(
        (r for r in store.list("weekly_tournament_registration") if r["key"] == key), None
    )
    if retained is not None:
        if "job_id" in retained:
            return {"status": "registered", "job_id": retained["job_id"]}
        job = Queue(store).enqueue("weekly_tournament", {"protocol": retained["protocol"]})
        store.put(
            "weekly_tournament_registration", key, {**retained, "job_id": job["id"]}, expected=1
        )
        return {"status": job["status"], "job_id": job["id"]}
    spec = protocol(collection["collection_id"], settings["study_id"])
    # Persist the canonical protocol first; recovery reuses it even if a crash
    # occurs between queue insertion and registration of its job identifier.
    store.put("weekly_tournament_protocol", fingerprint(spec), spec, expected=0)
    registration = {"key": key, "protocol": spec}
    store.put("weekly_tournament_registration", key, registration, expected=0)
    job = Queue(store).enqueue("weekly_tournament", {"protocol": spec})
    store.put(
        "weekly_tournament_registration", key, {**registration, "job_id": job["id"]}, expected=1
    )
    return {"status": job["status"], "job_id": job["id"]}
