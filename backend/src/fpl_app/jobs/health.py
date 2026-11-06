"""Process heartbeat independent of whether a worker currently owns a job."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import Event, Thread

from sqlalchemy import select

from fpl_app.storage import Store, entities, fingerprint, jobs


def _instant(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("Worker health receipts require timezone-aware timestamps")
    return stamp


def heartbeat(store: Store, owner: str, *, stopped: bool = False) -> None:
    store.put(
        "worker_heartbeat",
        owner,
        {
            "owner": owner,
            "pid": os.getpid(),
            "database_sha256": fingerprint(str(store.engine.url)),
            "observed_at": datetime.now(UTC).isoformat(),
            "stopped": stopped,
        },
    )


def worker_health(store: Store, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("Worker health clock requires a timezone")
    workers = []
    for row in store.list("worker_heartbeat"):
        age = (now - _instant(row["observed_at"])).total_seconds()
        workers.append({**row, "age_seconds": age, "healthy": not row["stopped"] and 0 <= age < 90})
    healthy = any(w["healthy"] for w in workers)
    activity = learning_activity(store, now=now, worker_available=healthy)
    return {
        "status": "healthy" if healthy else "unavailable_or_stale",
        "workers": workers,
        "learning": activity,
        "recovery": "Restart python -m fpl_app.jobs with the intended exported DATA_DIR; expired job leases recover automatically",
    }


def learning_activity(store: Store, *, now: datetime, worker_available: bool) -> dict:
    """Read actual receipts and job state; never infer a fit from a schedule.

    Publication and observation timestamps are labelled by their real meaning.
    Missing legacy receipts remain unknown. Job payloads and private team state
    are deliberately absent from this operator health response.
    """
    with store.engine.connect() as connection:
        job_rows = [dict(row) for row in connection.execute(select(jobs)).mappings()]
        fits = [
            dict(row)
            for row in connection.execute(
                select(entities.c.kind, entities.c.id, entities.c.updated_at).where(
                    entities.c.kind == "learning_refit"
                )
            ).mappings()
        ]
    counts = Counter(row["status"] for row in job_rows)
    pending = [
        {key: row[key] for key in ("id", "kind", "status", "progress", "attempts", "updated_at")}
        | {
            "lease_expired": row["status"] == "running"
            and row["lease_until"] is not None
            and row["lease_until"] < now.timestamp()
        }
        for row in job_rows
        if row["status"] in {"queued", "running"}
    ]
    failed = sorted(
        (row for row in job_rows if row["status"] == "failed"),
        key=lambda row: _instant(row["updated_at"]),
    )
    finality = None
    source = store.latest("bootstrap-static/")
    if (
        source is not None
        and source["provider"] == "official_fpl"
        and source["data_mode"] == "live"
        and source["validation_status"] == "valid"
    ):
        try:
            if hashlib.sha256(source["raw"]).hexdigest() != source["payload_sha256"]:
                raise ValueError("Source checksum mismatch")
            events = json.loads(source["raw"])["events"]
            _instant(source["captured_at"])
            finality = {
                "observed_at": source["captured_at"],
                "snapshot_id": source["id"],
                "season": source["season"],
                "finalized_events": [
                    row["id"]
                    for row in events
                    if row.get("finished") is True and row.get("data_checked") is True
                ],
                "time_basis": "official_bootstrap_capture",
            }
        except (ValueError, TypeError, KeyError):
            # A corrupted receipt must not be presented as a successful check.
            finality = None
    scores = [
        row["scored_at"]
        for row in store.list("forecast_benchmark_outcome")
        if row.get("status") == "final" and row.get("scored_at")
    ] + [row["created_at"] for row in store.list("learning_scorecard") if row.get("created_at")]
    fit_receipts = [
        {
            "observed_at": row["updated_at"],
            "time_basis": "successful_refit_publication",
            "artifact_id": row["id"],
        }
        for row in fits
    ]
    for row in job_rows:
        result = row.get("result") or {}
        if (
            row["status"] == "succeeded"
            and row["kind"]
            in {
                "deadline_experiment",
                "rolling_experiment",
                "simple_experiment",
                "multilead_experiment",
            }
            and result.get("status") in {"evaluated", "evaluated_research", "trained"}
        ):
            fit_receipts.append(
                {
                    "observed_at": row["updated_at"],
                    "time_basis": "successful_training_job_completion",
                    "artifact_id": row["id"],
                }
            )
    fit = max(fit_receipts, key=lambda row: _instant(row["observed_at"]), default=None)
    benchmarks = store.list("forecast_benchmark")
    scored_ids = {
        row["benchmark_id"]
        for row in store.list("forecast_benchmark_outcome")
        if row.get("status") == "final"
    }
    awaiting = [row for row in benchmarks if row["benchmark_id"] not in scored_ids]
    finalized_events = set(finality["finalized_events"]) if finality else set()
    ready = (
        [
            row
            for row in awaiting
            if row["event"] in finalized_events
            and str(row.get("season")).replace("-", "/")
            == str(finality["season"]).replace("-", "/")
        ]
        if finality
        else []
    )
    if not worker_available:
        action = "restart_worker"
    elif any(row["lease_expired"] for row in pending):
        action = "recover_expired_lease"
    elif pending:
        action = "process_pending_jobs"
    elif ready:
        action = "score_finalized_benchmarks"
    elif awaiting:
        action = "check_official_finality" if finality is None else "await_official_finality"
    elif failed:
        action = "inspect_failed_jobs"
    elif any(row.get("enabled") for row in store.list("review_schedule")):
        action = "await_next_enabled_review"
    elif benchmarks:
        action = "await_next_benchmark_revision_check"
    else:
        action = "idle_no_enabled_work"
    return {
        "last_finality_check": finality,
        "last_final_scoring_at": max(scores, key=_instant, default=None),
        "last_successful_model_fit": fit,
        "job_counts": dict(counts),
        "pending_jobs": pending,
        "latest_failed_job": None
        if not failed
        else {
            "id": failed[-1]["id"],
            "kind": failed[-1]["kind"],
            "updated_at": failed[-1]["updated_at"],
            "code": (failed[-1].get("error") or {}).get("code"),
        },
        "unscored_benchmark_count": len(awaiting),
        "next_action": action,
        "limitations": "Local observations only; a configured schedule does not establish uptime or a successful fit",
    }


@contextmanager
def process_heartbeat(store: Store, owner: str, interval: float = 20) -> Iterator[None]:
    stop = Event()
    heartbeat(store, owner)

    def pulse() -> None:
        while not stop.wait(interval):
            try:
                heartbeat(store, owner)
            except Exception as exc:  # noqa: BLE001 - retry a transient database failure
                logging.getLogger(__name__).warning(
                    "Worker heartbeat failed (%s)", type(exc).__name__
                )

    thread = Thread(target=pulse, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)
        heartbeat(store, owner, stopped=True)
