"""Write new immutable research person links from checksum-verified archive bundles."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from fpl_app.features.person_mapping import link_archive_people


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = link_archive_people(args.bundle)
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(
        json.dumps(
            {
                "linked_people": len(report["links"]),
                "unresolved_records": len(report["unresolved"]),
                "production_qualified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
