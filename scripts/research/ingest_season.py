#!/usr/bin/env python3
"""Normalize retained pinned Vaastav season CSVs; see --help for acquisition."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from fpl_app.features.season_archive import ingest_season


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Acquire gws/merged_gw.csv (save as gws_merged_gw.csv), fixtures.csv, teams.csv and players_raw.csv from https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/<full revision>/data/<season>/. Record actual retrieval UTC time. All original bytes are retained; no historical timing is verified.",
    )
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--lag-days", type=int, default=7)
    args = parser.parse_args()
    print(
        ingest_season(
            args.source_directory,
            args.output,
            season=args.season,
            revision=args.revision,
            retrieved_at=args.retrieved_at,
            lag_days=args.lag_days,
        )
    )


if __name__ == "__main__":
    main()
