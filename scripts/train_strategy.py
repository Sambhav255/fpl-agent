"""Real optional RL fit/evaluation; authored smoke is explicit and never promoted."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic-smoke", action="store_true")
    source.add_argument(
        "--episodes", type=Path, help="Frozen local train/test research episodes JSON"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timesteps", type=int, default=256)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument(
        "--direct-smoke",
        action="store_true",
        help="Run a small synthetic installation check directly; normal training uses the worker",
    )
    args = parser.parse_args()
    from fpl_app.contracts import Settings
    from fpl_app.models.training import data_dir

    if not args.direct_smoke:
        if args.output:
            parser.error("Queued artifacts use a managed output directory")
        from fpl_app.jobs import Queue
        from fpl_app.storage import Store

        payload = {
            "synthetic_smoke": args.synthetic_smoke,
            "timesteps": args.timesteps,
            "seeds": args.seeds,
            "settings": Settings(horizon_events=2, max_additional_hit_points=4).model_dump(),
        }
        if args.episodes:
            if args.episodes.is_symlink() or args.episodes.stat().st_size > 50_000_000:
                parser.error("Invalid bounded episode file")
            payload["episodes_data"] = json.loads(args.episodes.read_text())
        job = Queue(Store()).enqueue("strategy_training", payload)
        print(
            json.dumps(
                {"job_id": job["id"], "status": job["status"], "worker_required": True}, indent=2
            )
        )
        return
    if not args.synthetic_smoke or not 64 <= args.timesteps <= 256 or args.seeds != 5:
        parser.error(
            "Direct installation checks require synthetic smoke, five seeds and 64–256 timesteps"
        )
    from fpl_app.strategy.training import train_challenger

    if args.synthetic_smoke:
        from fpl_app.strategy.fixtures import synthetic_episode

        train = [synthetic_episode(i, "train") for i in range(100, 103)]
        test = [synthetic_episode(i, "test") for i in range(200, 203)]
    else:
        from fpl_app.strategy.datasets import load_episodes

        episodes = load_episodes(args.episodes)
        train = [e for e in episodes if e.partition == "train"]
        test = [e for e in episodes if e.partition == "test"]
    output = args.output or data_dir() / "models" / "strategy" / datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S-%f"
    )
    meta, report = train_challenger(
        train,
        test,
        Settings(horizon_events=2, max_additional_hit_points=4),
        output,
        seeds=tuple(range(args.seeds)),
        timesteps=args.timesteps,
    )
    print(
        json.dumps(
            {
                "artifact_id": meta["artifact_id"],
                "output": str(output),
                "status": meta["status"],
                "evidence_modes": meta["evidence_modes"],
                "seeds": meta["seeds"],
                "distinct_test_paths": report["distinct_test_paths"],
                "promotion": report["promotion"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
