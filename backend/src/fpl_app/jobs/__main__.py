"""Run with python -m fpl_app.jobs; queued work survives process restarts."""

import logging
import time

from fpl_app.jobs import Queue, Worker
from fpl_app.learning.forecast_benchmark import enqueue_due_benchmarks
from fpl_app.learning.review import enqueue_due_reviews
from fpl_app.storage import Store


def run_iteration(worker: Worker, next_review_at: float, now: float) -> tuple[bool, float]:
    """Poll opted-in durable reviews without starving ordinary queued work."""
    if now >= next_review_at:
        try:
            enqueue_due_benchmarks(worker.store)
            enqueue_due_reviews(worker.store)
        except Exception as exc:  # noqa: BLE001 - optional scheduling must not stop the worker
            logging.getLogger(__name__).warning(
                "Learning review scheduling failed (%s); retrying in one minute",
                type(exc).__name__,
            )
        next_review_at = now + 60
    return worker.run_once(), next_review_at


def main() -> None:
    worker = Worker(Queue(Store()))
    next_review_at = 0.0
    while True:
        worked, next_review_at = run_iteration(worker, next_review_at, time.monotonic())
        if not worked:
            time.sleep(0.5)


if __name__ == "__main__":
    main()
