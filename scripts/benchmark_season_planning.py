"""Benchmark frozen forecast paths with constructed, non-personal starting squads.

DATA_DIR=/ignored/path backend/.venv/bin/python scripts/benchmark_season_planning.py
--projection-run-id ID --output /ignored/path/benchmark.json
No fetching, private manager reads, account actions or state writes occur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from time import monotonic
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.contracts import ManagerState, Pick, Player, ProjectionRun, Settings
from fpl_app.domain.plans import validate_plan
from fpl_app.domain.rules import RULES
from fpl_app.optimisation.planner import recommend
from fpl_app.storage import Store


def synthetic_start(
    players: list[Player], run: ProjectionRun, seed: int = 42
) -> ManagerState:
    """Declared hypothetical acquisition at current market prices; never a team import."""
    rng = random.Random(seed)
    for attempt in range(500):
        chosen: list[Player] = []
        clubs: dict[int, int] = {}
        for position, count in enumerate(RULES.squad_counts, 1):
            group = [p for p in players if p.position == position]
            rng.shuffle(group)
            group.sort(key=lambda p: p.market_price_units)
            for player in group:
                if clubs.get(player.club, 0) >= 3:
                    continue
                chosen.append(player)
                clubs[player.club] = clubs.get(player.club, 0) + 1
                count -= 1
                if count == 0:
                    break
            if count:
                break
        total = sum(p.market_price_units for p in chosen)
        if len(chosen) != 15 or total > 1000:
            continue
        picks = [
            Pick(
                player_id=p.player_id,
                purchase_price_units=p.market_price_units,
                position=i + 1,
            )
            for i, p in enumerate(chosen)
        ]
        event = min(p.event for p in run.projections)
        window = 1 if event <= 19 else 2
        return ManagerState(
            team_id=-1,
            snapshot_id=run.snapshot_id,
            season=RULES.season,
            next_event=event,
            data_mode=run.data_mode,
            current_chip_confirmed=True,
            bank_units=1000 - total,
            free_transfers_at_event_start=2,
            transfers_made_this_event=0,
            confirmed_hit_points=0,
            picks=picks,
            event_start_picks=[p.model_copy(deep=True) for p in picks],
            event_start_bank_units=1000 - total,
            chips={f"{chip}_{window}": True for chip in ("wildcard", "free_hit")},
        )
    raise ValueError(
        "Cannot construct a legal hypothetical squad within 1000 price units"
    )


def benchmark(
    players: list[Player], run: ProjectionRun, time_limit: float = 2.0
) -> dict[str, Any]:
    state = synthetic_start(players, run)
    rows: list[dict[str, Any]] = []
    for horizon in (4, 6, 8):
        if horizon > run.horizon_events or state.next_event + horizon - 1 > 38:
            rows.append(
                {"horizon": horizon, "status": "unsupported_frozen_forecast_horizon"}
            )
            continue
        for menu, cap, hits, chip in (
            ("roll", 0, 0, "none"),
            ("singles", 1, 0, "none"),
            ("funding_pairs", 2, 0, "none"),
            ("hits", None, 8, "none"),
            ("wildcard", None, 0, "wildcard"),
            ("free_hit", None, 0, "free_hit"),
        ):
            for mode in ("bounded", "sequence"):
                settings = Settings(
                    horizon_events=horizon,
                    planner_mode=mode,
                    chip_policy=chip,
                    max_transfers_this_event=cap,
                    max_additional_hit_points=hits,
                    solver_time_limit_seconds=time_limit,
                )
                started = monotonic()
                result = recommend(state, players, run, settings)
                best = max(
                    [result.baseline_plan, *result.alternatives],
                    key=lambda p: p.net_points,
                )
                errors = validate_plan(
                    best,
                    state,
                    players,
                    run,
                    settings,
                    result.baseline_plan,
                    enforce_preferences=best is not result.baseline_plan,
                )
                if errors:
                    raise ValueError(
                        "Independent benchmark plan validation: " + "; ".join(errors)
                    )
                rows.append(
                    {
                        "horizon": horizon,
                        "menu": menu,
                        "planner": mode,
                        "forecast_net_points": best.net_points,
                        "forecast_delta_keep": best.net_points
                        - result.baseline_plan.net_points,
                        "total_hits": best.total_hits,
                        "first_event_moves": len(best.weeks[0]["actions"]),
                        "latency_seconds": monotonic() - started,
                        "legal": True,
                        "solver": best.solver,
                    }
                )
    frozen = json.dumps(
        {"players": [p.model_dump() for p in players], "run": run.model_dump()},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "schema_version": 1,
        "input_sha256": hashlib.sha256(frozen).hexdigest(),
        "projection_run_id": run.projection_run_id,
        "source_cutoff": run.source_cutoff,
        "forecast_artifact_id": run.artifact_id,
        "forecast_horizon": run.horizon_events,
        "starting_squad": "deterministic hypothetical, current-market acquisition, budget1000, FT2",
        "seed": 42,
        "time_limit_seconds_per_planner": time_limit,
        "evidence": "frozen forecast decision benchmark; not realized football returns",
        "limitations": [
            "Menus cap current-event moves; future ordinary moves remain bounded by each planner",
            "Forecast means omit joint uncertainty and expected autosubs",
            "No sequence global optimality certificate or future price observations",
        ],
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection-run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, default=2.0)
    args = parser.parse_args()
    if not 0 < args.time_limit <= 60:
        parser.error("time limit must be in (0,60]")
    store = Store()
    run = ProjectionRun.model_validate(store.get("projection", args.projection_run_id))
    data = store.get("dataset", run.snapshot_id)
    players = [Player.model_validate(row) for row in data["players"]]
    report = benchmark(players, run, args.time_limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(
        json.dumps({"report": str(args.output), "input_sha256": report["input_sha256"]})
    )


if __name__ == "__main__":
    main()
