"""Compare planners on actual frozen multilead football research predictions.

This is a forecast-path decision benchmark under current financial rules, not a
historical season replay or a current-era serving qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

import pandas as pd
from benchmark_season_planning import benchmark
from fpl_app.contracts import Fixture, Player, Projection, ProjectionRun
from fpl_app.domain.rules import RULES


def frozen_inputs(experiment: Path, archive: Path, origin_event: int):
    manifest = json.loads((experiment / "manifest.json").read_text())
    for name, checksum in manifest["files"].items():
        path = experiment / name
        if (
            Path(name).name != name
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
        ):
            raise ValueError("Changed or unsafe historical experiment payload")
    evaluation = json.loads((experiment / "evaluation.json").read_text())
    if (
        hashlib.sha256(archive.read_bytes()).hexdigest()
        != evaluation["source"]["sha256"]
    ):
        raise ValueError("Archive source checksum differs from fitted experiment")
    predictions = pd.read_parquet(experiment / "test_predictions.parquet")
    predictions = predictions[predictions.origin_event == origin_event].copy()
    if predictions.empty or set(predictions.lead) != set(range(1, 9)):
        raise ValueError("An actual untouched eight-lead frozen origin is required")
    method = manifest["selected_method"]  # Registered before test, never selected here.
    cutoff = predictions.decision_cutoff.iloc[0]
    raw = pd.read_csv(archive)
    raw["available"] = pd.to_datetime(raw.kickoff_time, utc=True) + pd.Timedelta(days=7)
    earlier = raw[(raw.available <= pd.Timestamp(cutoff)) & (raw.GW < origin_event)]
    prices = (
        earlier.sort_values("available")
        .groupby("element")
        .tail(1)
        .set_index("element")
        .value.to_dict()
    )
    times = raw.drop_duplicates("fixture").set_index("fixture").kickoff_time.to_dict()
    fixtures = {}
    for row in predictions.to_dict("records"):
        club, opponent = int(row["club"]), int(row["opponent"])
        home = str(row["home"]).lower() == "true"
        fixture = Fixture(
            fixture_id=int(row["fixture_id"]),
            event=int(row["event"]),
            home_club=club if home else opponent,
            away_club=opponent if home else club,
            kickoff=times[row["fixture_id"]],
        )
        if fixture.fixture_id in fixtures and fixtures[fixture.fixture_id] != fixture:
            raise ValueError("Conflicting reconstructed fixture sides")
        fixtures[fixture.fixture_id] = fixture
    positions = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}
    players = []
    rejected = 0
    for identifier, rows in predictions.groupby("player_id"):
        player_id = int(str(identifier))
        first = rows.iloc[0]
        club = int(first.club)
        expected = {
            f.fixture_id
            for f in fixtures.values()
            if club in (f.home_club, f.away_club)
        }
        if (
            player_id not in prices
            or set(rows.fixture_id) != expected
            or rows.club.nunique() != 1
            or rows.position.nunique() != 1
        ):
            rejected += 1
            continue
        players.append(
            Player(
                player_id=player_id,
                name=f"Archive player {player_id}",
                club=club,
                position=positions[first.position],
                market_price_units=int(prices[player_id]),
            )
        )
    universe = {p.player_id for p in players}
    run = ProjectionRun(
        projection_run_id="archive-planning-"
        + hashlib.sha256((str(experiment) + str(origin_event)).encode()).hexdigest()[
            :20
        ],
        snapshot_id=evaluation["dataset_sha256"],
        source_cutoff=cutoff,
        prediction_origin=cutoff,
        model_family="football_catboost_reconstructed",
        model_status="experimental",
        data_mode="live",
        rules_version=RULES.version,
        horizon_events=8,
        player_universe_ids=sorted(universe),
        artifact_id=manifest["artifact_id"],
        evidence_mode="reconstructed_historical_assumed",
        fixtures=list(fixtures.values()),
        projections=[
            Projection(
                player_id=int(row["player_id"]),
                fixture_id=int(row["fixture_id"]),
                event=int(row["event"]),
                expected_points=float(row[method]),
                expected_minutes=max(0, min(90, float(row["minutes_5"]))),
            )
            for row in predictions.to_dict("records")
            if row["player_id"] in universe
        ],
        warnings=[
            "Historical 2024/25 scoring means with current 2026/27 financial rules: counterfactual forecast-path comparison only"
        ],
    )
    return (
        players,
        run,
        {
            "original_scoring_regime": manifest["rules_version"],
            "financial_rules": RULES.version,
            "complete_case_players": len(players),
            "coverage_rejections": rejected,
            "source_sha256": evaluation["source"]["sha256"],
            "experiment_manifest_sha256": hashlib.sha256(
                (experiment / "manifest.json").read_bytes()
            ).hexdigest(),
            "origin_event": origin_event,
            "prediction_origin": cutoff,
            "price_assumption": "last origin-usable archive value; synthetic acquisition; frozen future price scenario",
            "selection_limitation": "Historical complete-case future row coverage, never an independent prospective universe",
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--origin-event", type=int, default=25)
    parser.add_argument("--time-limit", type=float, default=4.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0 < args.time_limit <= 10:
        parser.error("Bounded benchmark time limit must be in (0,10]")
    players, run, evidence = frozen_inputs(
        args.experiment, args.archive, args.origin_event
    )
    report = benchmark(players, run, args.time_limit)
    report["historical_evidence"] = evidence
    report["limitations"].extend(
        [
            "Scoring-era mismatch prevents current-era performance claims or deployment",
            "Financial rules are current counterfactual rules, not a reconstructed 2024/25 manager season",
            "No realized points, rank, global optimality or independent-season claim",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        json.dump(report, file, indent=2, sort_keys=True)
    print(
        json.dumps(
            {
                "report": str(args.output),
                "comparisons": len(report["results"]),
                "input_sha256": report["input_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
