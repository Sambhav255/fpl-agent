"""Run a registered immutable football experiment from retained bytes, without fetching."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from fpl_app.models.football_experiment import run_archive_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-lead", type=int, default=8, choices=range(1, 9))
    args = parser.parse_args()
    run = run_archive_experiment(args.archive, args.output, args.maximum_lead)
    report = json.loads((run / "evaluation.json").read_text())
    print(
        json.dumps(
            {
                "artifact": str(run),
                "evaluation_kind": report["evaluation_kind"],
                "metrics": report["metrics"],
                "supported_horizon": report["supported_horizon"],
                "champion_promoted": False,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
