"""Import reviewed local social evidence, show review-only scenarios, or delete a post."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.social.manual import ManualImport, availability_scenarios, import_manual
from fpl_app.social.store import SocialStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Dedicated deletable social SQLite file",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    ingest = actions.add_parser(
        "import", help="Validate and atomically import reviewed JSON"
    )
    ingest.add_argument("manifest", type=Path)
    scenarios = actions.add_parser(
        "scenarios", help="Review availability evidence without changing forecasts"
    )
    scenarios.add_argument("--horizon", required=True)
    scenarios.add_argument(
        "--as-of", help="Aware ISO timestamp; defaults to actual now"
    )
    delete = actions.add_parser(
        "delete", help="Delete text, claims and context descendants; retain tombstone"
    )
    delete.add_argument("post_id")
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    store = SocialStore(args.database)
    try:
        if args.action == "import":
            if args.manifest.stat().st_size > 5_000_000:
                raise ValueError("Manual import exceeds 5 MB")
            result = import_manual(
                store,
                ManualImport.model_validate_json(args.manifest.read_bytes()),
                datetime.now(UTC),
            )
        elif args.action == "scenarios":
            cutoff = (
                datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
            )
            if cutoff.tzinfo is None or cutoff > datetime.now(UTC):
                raise ValueError("Scenario cutoff cannot be in the future")
            result = availability_scenarios(store, cutoff, args.horizon)
        else:
            store.delete(args.post_id)
            result = {
                "deleted_post": args.post_id,
                "context_descendants_deleted": True,
                "points_adjustment": 0,
            }
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
