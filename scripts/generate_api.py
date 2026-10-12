"""Generate public runtime OpenAPI offline, without opening private app state."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.api import create_app
from fpl_app.storage import Store


def main() -> None:
    store = Store("sqlite://")
    try:
        schema = create_app(store).openapi()
        destination = ROOT / "apps" / "web" / "openapi.json"
        destination.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        print(
            "Generated apps/web/openapi.json from the runtime API using an in-memory store"
        )
    finally:
        store.engine.dispose()


if __name__ == "__main__":
    main()
