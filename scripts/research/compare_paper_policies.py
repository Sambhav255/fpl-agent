"""Compare declared forecast/planner methods from identical retained paper inputs.

Input JSON contains initial_state, settings, and candidates. Each candidate has
policy (keep or planner) and origins. Origin fields mirror ReplayOrigin; players
and forecasts use existing runtime schemas, outcomes use complete MatchStats
records. For official totals, official_outcomes uses points/minutes/appeared.
Prospective strict origins still require their own exact manifest and seal.
Private finances and full trajectories belong in an ignored output directory.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from fpl_app.contracts import ManagerState, Player, ProjectionRun, Settings
from fpl_app.domain.rules import MatchStats, OfficialEventPoints
from fpl_app.evaluation.strategy import (
    ForecastPolicy,
    ReplayOrigin,
    compare_forecast_policies,
    keep_policy,
    planner_policy,
)
from fpl_app.storage import utcnow


def load_origin(row):
    values = dict(row)
    values["players"] = [Player.model_validate(p) for p in row["players"]]
    values["forecasts"] = ProjectionRun.model_validate(row["forecasts"])
    values["outcomes"] = {
        int(key): [MatchStats(**stats) for stats in rows]
        for key, rows in row.get("outcomes", {}).items()
    }
    if row.get("official_outcomes") is not None:
        values["official_outcomes"] = {
            int(key): OfficialEventPoints(**stats)
            for key, stats in row["official_outcomes"].items()
        }
    if row.get("manifest_path") is not None:
        values["manifest_path"] = Path(row["manifest_path"])
    return ReplayOrigin(**values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--comparator", default="keep")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    payload = json.loads(raw)
    policies = {"keep": keep_policy, "planner": planner_policy}
    candidates = {
        name: ForecastPolicy(
            [load_origin(row) for row in item["origins"]], policies[item["policy"]]
        )
        for name, item in payload["candidates"].items()
    }
    result = compare_forecast_policies(
        ManagerState.model_validate(payload["initial_state"]),
        candidates,
        Settings.model_validate(payload["settings"]),
        comparator=args.comparator,
    )
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["created_at"] = utcnow()
    result["candidate_policies"] = {
        name: item["policy"] for name, item in payload["candidates"].items()
    }
    output = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Publish complete bytes atomically without replacing any earlier report.
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as stream:
        staging = Path(stream.name)
        stream.write(output)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(staging, args.output)
    finally:
        staging.unlink()
    print(
        json.dumps(
            {
                "report_sha256": hashlib.sha256(output).hexdigest(),
                "covered_events": result["covered_events"],
            }
        )
    )


if __name__ == "__main__":
    main()
