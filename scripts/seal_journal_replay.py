"""Seal existing replay evidence against a frozen decision before its deadline."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.evaluation.strategy import (
    keep_policy,
    planner_policy,
    proxy_planner_policy,
)
from fpl_app.learning.replay import seal_journal_replay
from fpl_app.storage import Store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--packet-id", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--policy", choices=["keep", "planner", "proxy"], required=True)
    args = parser.parse_args()
    policies = {
        "keep": keep_policy,
        "planner": planner_policy,
        "proxy": proxy_planner_policy,
    }
    result = seal_journal_replay(
        Store(),
        args.decision_id,
        args.packet_id,
        args.manifest_sha256,
        policies[args.policy],
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
