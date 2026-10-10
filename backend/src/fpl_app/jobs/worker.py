"""Compatibility worker entry point: uv run python -m fpl_app.jobs.worker."""

from fpl_app.jobs import Worker
from fpl_app.jobs.__main__ import main

__all__ = ["Worker", "main"]

if __name__ == "__main__":
    main()
