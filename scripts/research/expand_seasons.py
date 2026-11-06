"""Capture fixed-provider archive seasons and normalize with explicit coverage limits."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from fpl_app.features.season_archive import FILES, ingest_season


def capture(season: str, revision: str, output: Path) -> dict:
    if not re.fullmatch(r"20\d{2}-\d{2}", season) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Season and full immutable source revision required")
    source = output / "sources" / revision / season
    source.mkdir(parents=True, exist_ok=True)
    receipt = source / "capture.json"
    if receipt.exists():
        metadata = json.loads(receipt.read_text())
        for name, digest in metadata["sha256"].items():
            if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
                raise ValueError("Retained capture checksum mismatch")
    else:
        # Preserve partial bytes. A retry must use a clean directory rather than
        # attribute a newly fetched file to an earlier capture time.
        if any((source / name).exists() for name in FILES):
            raise ValueError("Incomplete capture retained; use a new output directory")
        captures = {}
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            for name in FILES:
                remote = "gws/merged_gw.csv" if name == "gws_merged_gw.csv" else name
                url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{revision}/data/{season}/{remote}"
                response = client.get(url)
                response.raise_for_status()
                with (source / name).open("xb") as handle:
                    handle.write(response.content)
                captures[name] = datetime.now(UTC).isoformat()
        metadata = {
            "retrieved_at": datetime.now(UTC).isoformat(),
            "captured_at": captures,
            "sha256": {
                name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES
            },
        }
        with receipt.open("x") as handle:
            json.dump(metadata, handle, indent=2)
    dest = ingest_season(
        source,
        output / "archives",
        season=season,
        revision=revision,
        retrieved_at=metadata["retrieved_at"],
    )
    quality = json.loads((dest / "quality.json").read_text())
    return {
        "season": season,
        "artifact": str(dest),
        "rows": quality["rows"],
        "fixtures_covered": quality["fixtures_covered"],
        "fixtures_in_source": quality["fixtures_in_source"],
        "complete_fixture_coverage": quality["fixtures_covered"] == quality["fixtures_in_source"],
        "strict_historical_timing": False,
        "promoted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", action="append", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for season in args.season:
        print(json.dumps(capture(season, args.revision, args.output)), flush=True)


if __name__ == "__main__":
    main()
