"""Manual local pipeline commands; optional training never runs in an API request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fpl_app.features import build_features, ingest_bundle
from fpl_app.models.training import data_dir, evaluate_run, train_catboost


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--source", choices=["fpl", "bundle", "vaastav"], default="fpl")
    ingest.add_argument("--input", type=Path)
    ingest.add_argument("--season", default="2024-25")
    ingest.add_argument("--max-events", type=int, default=16)
    ingest.add_argument("--lag-days", type=int, default=7)
    sub.add_parser("demo")
    features = sub.add_parser("features")
    features.add_argument("--input", required=True, type=Path)
    features.add_argument("--cutoff", required=True)
    features.add_argument("--event", required=True, type=int)
    features.add_argument("--season", required=True)
    features.add_argument("--output", type=Path)
    train = sub.add_parser("train")
    train.add_argument("--model", choices=["catboost", "bayesian", "tft"], required=True)
    train.add_argument("--dataset", type=Path)
    train.add_argument("--allow-approximate", action="store_true")
    train.add_argument("--iterations", type=int, default=120)
    train.add_argument("--seed", type=int, default=42)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        result: Any
        if args.command == "demo":
            from fpl_app.providers import demo
            from fpl_app.storage import Store

            result = demo(Store()).model_dump()
        elif args.command == "ingest":
            if args.source == "fpl":
                from fpl_app.providers import Provider
                from fpl_app.storage import Store

                result = Provider(Store()).refresh(force=True)
            elif args.source == "bundle":
                if args.input is None:
                    raise ValueError("--input JSON bundle required")
                result = ingest_bundle(args.input.read_bytes(), data_dir() / "processed")
            else:
                from fpl_app.features.archive import ingest_archive

                result = {
                    "directory": str(
                        ingest_archive(
                            data_dir() / "processed", args.season, args.max_events, args.lag_days
                        )
                    )
                }
        elif args.command == "features":
            frame = build_features(args.input, args.cutoff, args.event, args.season)
            output = args.output or args.input / f"features-event{args.event}.parquet"
            if output.exists():
                raise ValueError("immutable output exists; choose another path")
            output.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(output, index=False)
            audit_written = False
            envelope_path = args.input / "envelope.json"
            if envelope_path.is_file():
                envelope = json.loads(envelope_path.read_text())
                if envelope.get("data_mode") == "live":
                    from fpl_app.features.pipeline import write_panel_audit

                    write_panel_audit(
                        output,
                        {
                            "data_mode": "live",
                            "replay_timing": "verified",
                            "snapshot_id": envelope.get("snapshot_id"),
                            "limitations": [
                                "Strict deadline replay from verified input versions",
                            ],
                        },
                    )
                    audit_written = True
            result = {
                "path": str(output),
                "rows": len(frame),
                "replay_timing": "verified",
                "audit_written": audit_written,
            }
        elif args.command == "train":
            if args.dataset is None:
                raise ValueError(
                    "Training unavailable: specify --dataset real audited feature Parquet"
                )
            if args.model == "catboost":
                run = train_catboost(
                    args.dataset,
                    data_dir() / "models",
                    args.allow_approximate,
                    args.seed,
                    args.iterations,
                )
                result = {"directory": str(run), "status": "trained", "active": False}
            elif args.model == "bayesian":
                from fpl_app.models.bayesian import train_bayesian

                result = train_bayesian(args.dataset, data_dir() / "models", seed=args.seed)
            else:
                from fpl_app.models.tft import train_tft

                result = train_tft(args.dataset, data_dir() / "models", seed=args.seed)
        else:
            run = Path(args.run)
            if not run.is_dir():
                if not args.run.isalnum():
                    raise ValueError("invalid run ID")
                matches = list((data_dir() / "models").glob(f"*/{args.run}"))
                if len(matches) != 1:
                    raise ValueError("unknown/ambiguous run")
                run = matches[0]
            result = evaluate_run(run)
        print(json.dumps(result, default=str, allow_nan=False, indent=2))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
