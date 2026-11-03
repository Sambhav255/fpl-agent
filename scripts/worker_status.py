"""Read worker heartbeat for the same exported DATA_DIR used at startup."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/src"))

from fpl_app.jobs.health import worker_health
from fpl_app.storage import Store


if __name__ == "__main__":
    print(json.dumps(worker_health(Store()), indent=2))
