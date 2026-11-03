"""Register and execute the fixed legacy/binary opportunity comparison on final labels."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.features.football import FEATURES, collection_frames
from fpl_app.models.football_catboost import (
    _fit,
    checksum,
    chronological_folds,
    errors,
    write_json,
)
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store


def score(frame: pd.DataFrame) -> dict:
    result = {
        "rows": len(frame),
        "points": errors(frame.target_points, frame.points_mean),
        "minutes": errors(frame.target_minutes, frame.minutes_mean),
    }
    for name, threshold in [("appearance", 1), ("sixty", 60)]:
        y = (frame.target_minutes >= threshold).to_numpy(dtype=float)
        p = np.clip(frame[f"{name}_probability"].to_numpy(), 1e-8, 1 - 1e-8)
        raw = np.clip(frame[f"raw_{name}_probability"].to_numpy(), 1e-8, 1 - 1e-8)
        bins = []
        for low in [0.0, 0.2, 0.4, 0.6, 0.8]:
            mask = (p >= low) & (p < low + 0.2 + (1e-9 if low == 0.8 else 0))
            bins.append(
                {
                    "lower": low,
                    "rows": int(mask.sum()),
                    "mean_probability": float(p[mask].mean()) if mask.any() else None,
                    "observed_rate": float(y[mask].mean()) if mask.any() else None,
                }
            )
        result[name] = {
            "brier": float(((p - y) ** 2).mean()),
            "log_loss": float(-(y * np.log(p) + (1 - y) * np.log1p(-p)).mean()),
            "raw_brier": float(((raw - y) ** 2).mean()),
            "bins": bins,
        }
    result["projection"] = {
        "minutes_rows": int((frame.minutes_projection_delta.abs() > 1e-9).sum()),
        "mean_absolute_minutes_delta": float(
            frame.minutes_projection_delta.abs().mean()
        ),
        "sixty_rows": int((frame.sixty_projection_delta.abs() > 1e-9).sum()),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = perf_counter()
    args.output.mkdir(parents=True, exist_ok=False)
    # Consistent SQLite backup: never open or migrate the source through Store.
    with (
        sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True) as source,
        sqlite3.connect(args.output / "source.sqlite") as target,
    ):
        source.backup(target)
    store = Store(f"sqlite:///{args.output / 'source.sqlite'}")
    collection = load_collection(store, args.collection_id)
    require_scored_collection(store, collection)
    rules = f"fpl-{collection['season'].replace('/', '-')}"
    panel, _, _ = collection_frames(collection, rules)
    folds = chronological_folds(panel, collection["captured_at"])
    if not folds:
        raise ValueError("no eligible chronological folds")
    implementation = [
        "backend/src/fpl_app/models/football_catboost.py",
        "backend/src/fpl_app/models/opportunity.py",
        "backend/src/fpl_app/features/football.py",
        "backend/src/fpl_app/models/training_eligibility.py",
        "scripts/research/opportunity_comparison.py",
        "backend/uv.lock",
    ]
    sources = args.output / "implementation"
    sources.mkdir()
    for filename in implementation:
        shutil.copyfile(ROOT / filename, sources / Path(filename).name)
    protocol = {
        "registered_at": datetime.now(UTC).isoformat(),
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "implementation_sha256": {
            filename: checksum(ROOT / filename) for filename in implementation
        },
        "collection_id": args.collection_id,
        "collection_sha256": collection["envelope_sha256"],
        "feature_columns": FEATURES,
        "hypothesis": "Binary Logloss plus earlier model-bound sigmoid calibration improves appearance/60-minute probabilities and coherent expected minutes over legacy RMSE heads/additive offsets.",
        "primary_metrics": ["appearance Brier", "sixty Brier", "minutes MAE"],
        "methods": ["legacy_regression_offset", "binary_sigmoid_projected"],
        "folds": folds,
        "news_treatment": "No historical news in either method; injury/return/club-change subgroups unavailable",
        "evidence_mode": "previously inspected retrospective development; reconstructed membership and availability",
        "serving_design": "latest-data refit explicitly uncalibrated; holdout calibrators never transferred",
        "champion_promoted": False,
    }
    write_json(args.output / "protocol.json", protocol)
    provenance = {
        "season": collection["season"],
        "source_ref": collection["envelope_sha256"],
        "captured_at": collection["captured_at"],
        "player_universe": collection["player_universe"],
    }
    frames = []
    for method in protocol["methods"]:
        for fold in folds:
            run = _fit(
                panel,
                args.output / method,
                provenance,
                fold,
                rules,
                binary_opportunity=method == "binary_sigmoid_projected",
            )
            frame = pd.read_parquet(run / "test_predictions.parquet")
            frame["method"] = method
            frame["artifact"] = str(run.relative_to(args.output))
            frames.append(frame)
    all_predictions = pd.concat(frames, ignore_index=True)
    all_predictions.to_parquet(args.output / "predictions.parquet", index=False)
    subgroup_masks = {
        "sparse_history": all_predictions.history_count < 3,
        "likely_starters": all_predictions.sixty_5 >= 0.6,
        "substitute_history": (all_predictions.appearance_5 > all_predictions.starts_5)
        & (all_predictions.starts_missing == 0),
    }
    report = {
        "protocol_sha256": checksum(args.output / "protocol.json"),
        "predictions_sha256": checksum(args.output / "predictions.parquet"),
        "rows_per_method": int(len(all_predictions) / 2),
        "methods": {},
        "unavailable_subgroups": ["known injury", "return from injury", "club changes"],
        "runtime_seconds": perf_counter() - start,
        "champion_promoted": False,
    }
    for method, frame in all_predictions.groupby("method"):
        report["methods"][method] = {
            "overall": score(frame),
            "events": {
                str(event): score(part) for event, part in frame.groupby("event")
            },
            "positions": {
                str(position): score(part)
                for position, part in frame.groupby("position")
            },
            "origin_subgroups": {
                name: score(frame.loc[mask.loc[frame.index]])
                if mask.loc[frame.index].any()
                else None
                for name, mask in subgroup_masks.items()
            },
        }
    write_json(args.output / "report.json", report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "runtime_seconds": report["runtime_seconds"],
                "rows_per_method": report["rows_per_method"],
                "overall": {k: v["overall"] for k, v in report["methods"].items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
