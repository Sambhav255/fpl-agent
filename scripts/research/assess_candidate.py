"""Read a predeclared candidate gate and evidence; never activate a model."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from fpl_app.learning.promotion import CandidateGate, assess_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    report = assess_candidate(payload["evidence"], CandidateGate(**payload["gate"]))
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(json.dumps({"decision": report["decision"], "automatic_activation": False}))


if __name__ == "__main__":
    main()
