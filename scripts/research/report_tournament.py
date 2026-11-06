"""Produce additional offline diagnostics from checksum-verified tournament units."""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))
from fpl_app.evaluation.tournament import auxiliary_metrics, evaluate_panel
from fpl_app.models.rolling_experiments import _completed
from fpl_app.storage import fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.directory
    report = json.loads((root / "report.json").read_text())
    identity = report["input_fingerprint"]
    frames = []
    for fold in json.loads((root / "splits.json").read_text()):
        label = fold["fold_id"]
        _completed(root / label, fingerprint({"identity": identity, "unit": label}))
        frame = pd.read_parquet(root / label / "predictions.parquet")
        frame["fold_id"] = label
        frames.append(frame)
    outer = pd.concat(frames, ignore_index=True)
    pd.testing.assert_frame_equal(outer, pd.read_parquet(root / "outer_predictions.parquet"))
    methods = [m for m in report["methods"] if m in outer]
    diagnostics = evaluate_panel(outer, methods)
    rolling = outer.copy()
    rolling["expected_minutes"] = rolling.minutes_5
    rolling["appearance_probability"] = rolling.appearance_5
    rolling["sixty_probability"] = rolling.sixty_5
    rolling = rolling.drop(columns=[k for k in rolling if k.startswith("q0.")])
    diagnostics["rolling_opportunity_comparator"] = auxiliary_metrics(rolling)
    diagnostics["parent_benchmark_id"] = report["benchmark_id"]
    diagnostics["source_verification"] = (
        "Each retained fold checkpoint and prediction hash verified; no refitting"
    )
    with args.output.open("x") as handle:
        json.dump(diagnostics, handle, indent=2, allow_nan=False)
    print(json.dumps({"output": str(args.output), "events": diagnostics["distinct_events"]}))


if __name__ == "__main__":
    main()
