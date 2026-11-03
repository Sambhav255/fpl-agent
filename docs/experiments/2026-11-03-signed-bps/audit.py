"""Reproduce signed BPS/component coverage audit without fitting full player points."""

import argparse
import hashlib
import json
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd
from fpl_app.domain.rules import MatchStats
from fpl_app.models.bayesian_scoring import BPS_MODEL_KIND, sample_signed_bps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.archive / "manifest.json").read_text())
    for name, digest in manifest["artifact_sha256"].items():
        path = args.archive / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Archive checksum mismatch")
    raw = pd.read_csv(args.archive / "raw/gws_merged_gw.csv")
    data = raw[raw.position.isin(["GK", "DEF", "MID", "FWD"])].copy()
    canonical = pd.read_parquet(args.archive / "player_fixture_outcome.parquet")
    expected = data.sort_values(["element", "fixture"])
    observed = canonical.sort_values(["element", "fixture"])
    if not np.array_equal(
        expected[["element", "fixture", "bps"]], observed[["element", "fixture", "bps"]]
    ):
        raise ValueError("Canonical BPS differs from original source")
    # Provider total concessions cannot identify the domain's separate temporal
    # on-pitch and after-red-card quantities, so those remain unavailable.
    aliases = {
        "goals": "goals_scored",
        "penalty_saves": "penalties_saved",
        "penalty_misses": "penalties_missed",
    }
    coverage = {}
    for field in [*(f.name for f in fields(MatchStats)), "bps", "started"]:
        source = "starts" if field == "started" else aliases.get(field, field)
        coverage[field] = {
            "source_column": source if source in data else None,
            "missing_rows": int(data[source].isna().sum())
            if source in data
            else len(data),
        }
    data["category"] = np.where(
        data.minutes == 0,
        0,
        np.where(data.starts == 0, 1, np.where(data.minutes < 60, 2, 3)),
    )
    profiles = {}
    samples = {}
    for position, rows in data.groupby("position"):
        profiles[position] = {
            "kind": BPS_MODEL_KIND,
            "values_by_category": {
                str(c): rows.loc[rows.category == c, "bps"].astype(int).tolist()
                for c in range(4)
            },
        }
        # Sample each category independently using representative category minutes;
        # these are a sampler support check, not a forecast or held-out evaluation.
        minutes = np.tile([0, 20, 45, 90], 10_000)
        starts = np.tile([False, False, True, True], 10_000)
        values = sample_signed_bps(
            profiles[position], minutes, starts, np.random.default_rng(42)
        )
        samples[position] = {
            "n": len(values),
            "minimum": int(values.min()),
            "maximum": int(values.max()),
            "negative": int((values < 0).sum()),
        }
    missing = [name for name, info in coverage.items() if info["missing_rows"]]
    result = {
        "schema_version": 1,
        "purpose": "historical signed support and component coverage audit; no performance estimate",
        "season": manifest["season"],
        "source_manifest_sha256": hashlib.sha256(
            (args.archive / "manifest.json").read_bytes()
        ).hexdigest(),
        "source_artifact_sha256": manifest["artifact_sha256"],
        "source_urls": manifest["sources"],
        "ordinary_rows": len(data),
        "excluded_nonplayer_rows": len(raw) - len(data),
        "negative_bps_rows": int(data.bps.lt(0).sum()),
        "minimum_bps": int(data.bps.min()),
        "maximum_bps": int(data.bps.max()),
        "zero_minute_negative_bps_rows": int(
            (data.bps.lt(0) & data.minutes.eq(0)).sum()
        ),
        "negative_bps_by_position": {
            position: int(rows.bps.lt(0).sum())
            for position, rows in data.groupby("position")
        },
        "component_coverage": coverage,
        "unavailable_complete_components": missing,
        "full_scoring_fit": "unavailable; complete explicit domain components and verified publication provenance missing",
        "bps_only_sampler_support": samples,
        "bps_only_profile_status": "empirical_signed_research_only_not_calibrated",
        "full_player_scoring_qualified": False,
        "champion_change": False,
        "limitations": [
            "2024/25 BPS rules differ from the current era; no modern re-scoring or cross-era pooling",
            "Archived timestamps do not establish original publication availability",
            "Sampler support checks are not chronological calibration or held-out prediction",
            "Signed BPS is not a calibrated joint model with goals, cards or bonus competition",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "audit.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )
    (args.output / "bps-only-profiles.json").write_text(
        json.dumps(
            {
                "status": "partial_bps_only_research",
                "kind": BPS_MODEL_KIND,
                "profiles": profiles,
            },
            sort_keys=True,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "ordinary_rows": len(data),
                "negative_bps_rows": result["negative_bps_rows"],
                "missing_components": missing,
            }
        )
    )


if __name__ == "__main__":
    main()
