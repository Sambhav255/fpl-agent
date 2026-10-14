"""Score sealed paper policies against an exact retained finalized outcome revision.

Reports include hypothetical financial transitions and remain under ignored
DATA_DIR. This command never changes actual execution, manager state or models.
"""

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
from fpl_app.learning.paper import evaluate_paper_journal
from fpl_app.storage import Store

POLICIES = {
    "keep": keep_policy,
    "planner": planner_policy,
    "proxy": proxy_planner_policy,
}


def main(argv: list[str] | None = None, *, store: Store | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument(
        "--outcome-revision",
        required=True,
        help="Exact revision SHA or decision_id:SHA; never latest",
    )
    parser.add_argument("--policy", choices=[*POLICIES, "all"], default="all")
    args = parser.parse_args(argv)
    try:
        selected = (
            POLICIES if args.policy == "all" else {args.policy: POLICIES[args.policy]}
        )
        result = evaluate_paper_journal(
            store or Store(), args.decision_id, args.outcome_revision, selected
        )
    except (KeyError, ValueError, RuntimeError, OSError) as exc:
        print(
            json.dumps(
                {"error": "PAPER_REPLAY_FAILED", "error_type": type(exc).__name__}
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
