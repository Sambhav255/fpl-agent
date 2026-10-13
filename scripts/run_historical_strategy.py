"""Reproducible bounded real-football shadow strategy experiment; no team reads."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.contracts import Settings
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store
from fpl_app.strategy.historical import reconstruct_collection
from fpl_app.strategy.training import _episode_payload, train_challenger


def events(value: str) -> list[int]:
    try:
        result = [int(v) for v in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Comma separated numeric events required"
        ) from exc
    if not result or any(not 1 <= n <= 38 for n in result):
        raise argparse.ArgumentTypeError("Events must be within 1..38")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", required=True, help="Isolated retained official-source SQLite URL"
    )
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--train-events", required=True, type=events)
    parser.add_argument("--test-events", required=True, type=events)
    parser.add_argument("--universe-size", type=int, default=40)
    parser.add_argument("--starting-squads", type=int, default=1)
    parser.add_argument("--timesteps", type=int, default=64)
    parser.add_argument("--candidates", type=int, default=8)
    args = parser.parse_args()
    if not 64 <= args.timesteps <= 512 or not 2 <= args.candidates <= 32:
        parser.error(
            "Bounded CPU experiment requires 64..512 steps and 2..32 candidates"
        )
    collection = load_collection(Store(args.database), args.collection_id)
    train, test, audit = reconstruct_collection(
        collection,
        train_events=args.train_events,
        test_events=args.test_events,
        universe_size=args.universe_size,
        starting_squads=args.starting_squads,
    )
    settings = Settings(
        horizon_events=1,
        max_additional_hit_points=4,
        max_transfers_this_event=2,
        solver_time_limit_seconds=1,
    )
    config = {
        "seeds": list(range(5)),
        "timesteps_per_seed": args.timesteps,
        "candidates": args.candidates,
        "settings": settings.model_dump(),
        "tuning": "fixed before test; none",
        "cpu_threads": 1,
        "producer_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    # This registration is written before fitting or inspecting test metrics.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    registration = args.output.with_suffix(".registration.json")
    with registration.open("x") as out:
        json.dump(
            {"audit": audit, "configuration": config}, out, sort_keys=True, indent=2
        )
    manifest, report = train_challenger(
        train,
        test,
        settings,
        args.output,
        seeds=tuple(range(5)),
        timesteps=args.timesteps,
        k=args.candidates,
    )
    with (args.output / "episodes.json").open("x") as out:
        json.dump(
            {"episodes": [_episode_payload(e) for e in [*train, *test]]},
            out,
            sort_keys=True,
            indent=2,
        )
    packet = {
        "audit": audit,
        "configuration": config,
        "artifact_id": manifest["artifact_id"],
        "artifacts": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in args.output.iterdir()
            if p.is_file()
        },
        "promotion": report["promotion"],
    }
    with (args.output / "football_experiment.json").open("x") as out:
        json.dump(packet, out, sort_keys=True, indent=2)
    print(
        json.dumps(
            {
                "artifact_directory": str(args.output),
                "artifact_id": manifest["artifact_id"],
                "independent_actual_seasons": audit["independent_actual_seasons"],
                "promotion": report["promotion"],
                "active": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
