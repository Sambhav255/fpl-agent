"""Bounded official football capture; stdout contains only public capture/coverage metadata."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from fpl_app.providers import Provider
from fpl_app.providers.collection import (
    MAX_PLAYERS,
    collect_football,
    export_collection_parquet,
    load_collection,
)
from fpl_app.storage import Store, entities


def positive_id(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 2_147_483_647:
        raise argparse.ArgumentTypeError("Use positive numeric player IDs, not URLs")
    return int(value)


def guard_versions(store: Store) -> list[tuple[Any, ...]]:
    """Inspect row metadata only, never manager finances or pointer payloads."""
    with store.engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                select(
                    entities.c.kind,
                    entities.c.id,
                    entities.c.version,
                    entities.c.updated_at,
                )
                .where(entities.c.kind.in_(["state", "current"]))
                .order_by(entities.c.kind, entities.c.id)
            )
        ]


def owned_ids(store: Store) -> list[int]:
    with store.engine.connect() as connection:
        values = list(
            connection.execute(
                text(
                    "SELECT json_extract(p.value, '$.player_id') "
                    "FROM entities e, json_each(e.payload, '$.picks') p "
                    "WHERE e.kind='state' AND json_extract(e.payload, '$.data_mode')='live'"
                )
            ).scalars()
        )
    if any(type(value) is not int or not 1 <= value <= 2_147_483_647 for value in values):
        raise ValueError("Stored live ownership contains invalid player IDs")
    return sorted(set(values))


def summarize(store: Store, collection: dict[str, Any]) -> dict[str, Any]:
    source = next(s for s in collection["sources"] if s["resource"] == "bootstrap-static/")
    bootstrap = json.loads(store.snapshot(source["id"])["raw"])
    current = next((e["id"] for e in bootstrap["events"] if e.get("is_current")), None)
    next_event = next((e["id"] for e in bootstrap["events"] if e.get("is_next")), None)
    by_event: dict[int, Counter[str]] = {}
    for row in collection["coverage"]:
        by_event.setdefault(row["event"], Counter())[row["status"]] += 1
    return {
        "collection_id": collection["collection_id"],
        "captured_at": collection["captured_at"],
        "season": collection["season"],
        "player_universe": collection["player_universe"],
        "event_origin": {
            "current_event": current,
            "next_event": next_event,
            "actual_next_deadline": collection["actual_deadline"],
            "before_deadline": collection["before_deadline"],
            "evidence_mode": collection["evidence_mode"],
        },
        "coverage": {
            "player_count": len(collection["player_ids"]),
            "source_count": len(collection["sources"]),
            "label_count": len(collection["labels"]),
            "labels_by_event": dict(
                sorted(Counter(r["event"] for r in collection["labels"]).items())
            ),
            "labels_by_status": dict(Counter(r["label_status"] for r in collection["labels"])),
            "schedule_rows_by_event": {
                event: dict(counts) for event, counts in sorted(by_event.items())
            },
        },
    }


def main(
    argv: list[str] | None = None,
    *,
    store: Store | None = None,
    provider: Provider | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-ids", nargs="+", type=positive_id, default=[])
    parser.add_argument(
        "--include-owned",
        action="store_true",
        help="Read only stored live owned player IDs",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Freeze and collect every player in the captured official bootstrap universe",
    )
    parser.add_argument("--from-collection", help="Union IDs from a verified previous collection")
    parser.add_argument(
        "--coverage",
        metavar="COLLECTION_ID",
        help="Read-only coverage of an existing collection",
    )
    parser.add_argument(
        "--parquet",
        action="store_true",
        help="Export labels/schedule/coverage under ignored data",
    )
    args = parser.parse_args(argv)
    if args.coverage and (
        args.player_ids or args.include_owned or args.from_collection or args.include_all
    ):
        parser.error("--coverage cannot be combined with capture selectors")
    if args.include_all and (args.player_ids or args.include_owned or args.from_collection):
        parser.error("--include-all cannot be combined with other player selectors")
    if len(set(args.player_ids)) > MAX_PLAYERS:
        parser.error(f"At most {MAX_PLAYERS} distinct players per collection")
    try:
        store = store or Store()
        before = guard_versions(store)
        if args.coverage:
            collection = load_collection(store, args.coverage)
        else:
            ids = set(args.player_ids)
            if args.include_owned:
                ids.update(owned_ids(store))
            if args.from_collection:
                ids.update(load_collection(store, args.from_collection)["player_ids"])
            if len(ids) > MAX_PLAYERS:
                raise ValueError(f"Union exceeds {MAX_PLAYERS} distinct players")
            provider = provider or Provider(store)
            provider.minimum_interval = max(provider.minimum_interval, 0.25)
            collection = collect_football(
                store, provider, sorted(ids), force=True, include_all=args.include_all
            )
        output = summarize(store, collection)
        if args.parquet:
            export_collection_parquet(store, collection["collection_id"])
        if guard_versions(store) != before:
            raise RuntimeError(
                "Manager/current row versions changed during capture; concurrent activity requires review"
            )
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0
    except (
        httpx.HTTPError,
        SQLAlchemyError,
        OSError,
        ImportError,
        RuntimeError,
        ValueError,
        KeyError,
    ) as exc:
        # Provider/database exception strings can contain payloads/connection details.
        print(
            json.dumps({"error": "COLLECTION_FAILED", "error_type": type(exc).__name__}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
