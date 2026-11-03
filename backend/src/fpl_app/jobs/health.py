"""Process heartbeat independent of whether a worker currently owns a job."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import Event, Thread

from fpl_app.storage import Store, fingerprint


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
    workers = []
    for row in store.list("worker_heartbeat"):
        age = (now - datetime.fromisoformat(row["observed_at"])).total_seconds()
        workers.append({**row, "age_seconds": age, "healthy": not row["stopped"] and 0 <= age < 90})
    return {
        "status": "healthy" if any(w["healthy"] for w in workers) else "unavailable_or_stale",
        "workers": workers,
        "recovery": "Restart python -m fpl_app.jobs with the intended exported DATA_DIR; expired job leases recover automatically",
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
