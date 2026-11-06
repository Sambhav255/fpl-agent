"""Opt in/out of future tournaments; existing frozen benchmarks continue scoring."""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))
from fpl_app.storage import Store, entities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--disable", action="store_true")
    parser.add_argument("--study-id")
    args = parser.parse_args()
    if args.enable and (not args.study_id or len(args.study_id) > 100):
        parser.error("Enabling requires a study ID of 1–100 characters")
    store = Store()
    with store.engine.connect() as connection:
        row = connection.execute(
            select(entities.c.version, entities.c.payload).where(
                entities.c.kind == "weekly_tournament_settings",
                entities.c.id == "default",
            )
        ).first()
    old = {} if row is None else dict(row.payload)
    config = {**old, "enabled": args.enable}
    if args.study_id:
        config["study_id"] = args.study_id
    store.put(
        "weekly_tournament_settings",
        "default",
        config,
        expected=0 if row is None else row.version,
    )
    print(
        json.dumps(
            {
                "enabled": config["enabled"],
                "study_id": config.get("study_id"),
                "requires": "Existing full-universe collect/refit review and matching local worker",
                "automatic_promotion": False,
            }
        )
    )


if __name__ == "__main__":
    main()
