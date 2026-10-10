"""Run with python -m fpl_app.jobs; queued work survives process restarts."""

import time

from fpl_app.jobs import Queue, Worker
from fpl_app.storage import Store


def main() -> None:
    worker = Worker(Queue(Store()))
    while True:
        if not worker.run_once():
            time.sleep(0.5)


if __name__ == "__main__":
    main()
