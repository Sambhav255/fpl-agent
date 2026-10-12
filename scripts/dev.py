"""Launch local services and stop their entire process groups on exit."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
commands = [
    (
        ROOT / "backend",
        [
            "uv",
            "run",
            "uvicorn",
            "fpl_app.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--timeout-keep-alive",
            "65",
        ],
    ),
    (ROOT / "backend", ["uv", "run", "python", "-m", "fpl_app.jobs.worker"]),
    (ROOT / "apps/web", ["npm", "run", "dev"]),
]
processes = []
stopping = False


def stop(signum=None, frame=None):
    global stopping
    if stopping:
        return
    stopping = True
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
try:
    for cwd, command in commands:
        processes.append(subprocess.Popen(command, cwd=cwd, start_new_session=True))
    print(
        "Frontend http://127.0.0.1:3000; API http://127.0.0.1:8000/docs. Ctrl-C stops all three.",
        flush=True,
    )
    while not stopping:
        for process in processes:
            if process.poll() is not None:
                print("A local service exited; stopping all services.", file=sys.stderr)
                stop()
                break
        time.sleep(0.25)
finally:
    stop()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
