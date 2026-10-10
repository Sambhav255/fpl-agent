#!/usr/bin/env python3
"""Run a real, partial team-goal model without changing live application state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
os.environ.setdefault("PYTENSOR_FLAGS", "compiledir=/private/tmp/fpl-deadline-pytensor")
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/fpl-deadline-matplotlib")
os.environ.setdefault("NUMBA_CACHE_DIR", "/private/tmp/fpl-deadline-numba")

import numpy as np
import pandas as pd
from fpl_app.models.bayesian import fit_matches
from fpl_app.models.training import audited_panel, split_panel
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(UTC)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare_matches(fixtures: list[dict[str, Any]], origin: str) -> pd.DataFrame:
    """Union of each club's last five observed completed fixtures before actual origin."""
    cutoff = instant(origin)
    eligible = [
        f
        for f in fixtures
        if f.get("finished") is True
        and f.get("finished_provisional") is True
        and f.get("kickoff_time")
        and instant(f["kickoff_time"]) < cutoff
        and type(f.get("team_h_score")) is int
        and type(f.get("team_a_score")) is int
    ]
    clubs = {f[k] for f in fixtures for k in ("team_h", "team_a")}
    chosen = {}
    for club in clubs:
        recent = sorted(
            (f for f in eligible if club in (f["team_h"], f["team_a"])),
            key=lambda f: instant(f["kickoff_time"]),
        )[-5:]
        for fixture in recent:
            chosen[fixture["id"]] = fixture
    rows = [
        {
            "fixture_id": f["id"],
            "home_club": f["team_h"],
            "away_club": f["team_a"],
            "home_goals": f["team_h_score"],
            "away_goals": f["team_a_score"],
            "time_index": f["event"],
            "kickoff": f["kickoff_time"],
        }
        for f in chosen.values()
    ]
    if not rows:
        raise ValueError("No completed observed matches before origin")
    return (
        pd.DataFrame(rows)
        .sort_values(["time_index", "fixture_id"])
        .reset_index(drop=True)
    )


def posterior_predictions(
    trace: Any,
    diagnostics: dict[str, Any],
    fixtures: list[dict[str, Any]],
    names: dict[int, str],
) -> list[dict[str, Any]]:
    posterior = trace.posterior

    def values(name: str) -> np.ndarray:
        variable = posterior[name]
        array = variable.transpose(
            "chain", "draw", *[d for d in variable.dims if d not in ("chain", "draw")]
        ).values
        return array.reshape((-1, *array.shape[2:]))

    base, venue = values("base"), values("venue")
    attack, defence = values("attack"), values("defence")
    trend, alpha = values("trend"), values("dispersion")
    result = []
    for fixture in fixtures:
        h = diagnostics["clubs"].index(fixture["team_h"])
        a = diagnostics["clubs"].index(fixture["team_a"])
        t = (fixture["event"] - diagnostics["time_center"]) / diagnostics["time_scale"]
        home_mu = np.exp(base + venue + attack[:, h] - defence[:, a] + trend * t)
        away_mu = np.exp(base + attack[:, a] - defence[:, h] + trend * t)
        # NB zero probability integrates posterior parameters, without sampling noise.
        home_cs = np.exp(alpha * (np.log(alpha) - np.log(alpha + away_mu)))
        away_cs = np.exp(alpha * (np.log(alpha) - np.log(alpha + home_mu)))
        result.append(
            {
                "fixture_id": fixture["id"],
                "event": fixture["event"],
                "kickoff": fixture["kickoff_time"],
                "home_club": fixture["team_h"],
                "away_club": fixture["team_a"],
                "home_team": names.get(fixture["team_h"]),
                "away_team": names.get(fixture["team_a"]),
                "home_mean_goals": float(home_mu.mean()),
                "away_mean_goals": float(away_mu.mean()),
                "home_clean_sheet_probability": float(home_cs.mean()),
                "away_clean_sheet_probability": float(away_cs.mean()),
                "probability_definition": "posterior mean of NB opponent-zero probability",
            }
        )
    return result


def run(collection_id: str) -> dict[str, Any]:
    store = Store()
    try:
        pointer_before = fingerprint(store.get("current", "live"))
    except KeyError:
        pointer_before = None
    collection = load_collection(store, collection_id)
    sources = {s["resource"]: s for s in collection["sources"]}
    fixtures = json.loads(store.snapshot(sources["fixtures/"]["id"])["raw"])
    bootstrap = json.loads(store.snapshot(sources["bootstrap-static/"]["id"])["raw"])
    deadline = next(e["deadline_time"] for e in bootstrap["events"] if e["id"] == 6)
    started = datetime.now(UTC).isoformat()
    origin = started
    if instant(collection["available_at"]) > instant(origin):
        raise ValueError("Collection not yet available at actual origin")
    upcoming = [f for f in fixtures if f.get("event") == 6]
    if not upcoming or any(f.get("started") is True for f in upcoming):
        raise ValueError("GW6 fixture schedule unavailable or already started")
    matches = prepare_matches(fixtures, origin)
    directory = ROOT / "data/research" / f"deadline-bayesian-{uuid.uuid4().hex}"
    directory.mkdir(parents=True)
    matches.to_parquet(directory / "matches.parquet", index=False)
    # Invoke production gates against the retained real evidence, without changing trainers.
    labels = pd.DataFrame(collection["labels"])
    labels["decision_cutoff"] = labels["actual_deadline"]
    labels["target_available_at"] = labels["available_at"]
    labels.to_parquet(directory / "eligibility-panel.parquet", index=False)
    write_json(
        directory / "audit.json",
        {"data_mode": "live", "replay_timing": "unknown_original_timing"},
    )
    gates: dict[str, dict[str, Any]] = {}
    for name, check in (
        ("current_tft_chronological_partition", lambda: split_panel(labels)),
        (
            "historical_verified_availability_audit",
            lambda: audited_panel(directory / "eligibility-panel.parquet"),
        ),
    ):
        try:
            check()
            gates[name] = {"eligible": True}
        except ValueError as exc:
            gates[name] = {
                "eligible": False,
                "reason": str(exc),
                "actually_invoked": True,
            }
    report = {
        "collection_id": collection_id,
        "source_envelope_sha256": collection["envelope_sha256"],
        "sources": collection["sources"][:2],
        "season": collection["season"],
        "started_at": started,
        "actual_origin": origin,
        "actual_deadline": deadline,
        "before_deadline_at_start": instant(started) < instant(deadline),
        "model_scope": "partial_team_goal_model_only",
        "full_fpl_forecast": False,
        "active": False,
        "draws_per_chain": 500,
        "tune_per_chain": 500,
        "chains": 2,
        "match_count": len(matches),
        "training_events": sorted(matches["time_index"].unique().tolist()),
        "eligibility_checks": gates,
        "directory": str(directory),
        "status": "running",
        "limitations": [
            "No player minutes, goal allocation, injuries, saves, BPS or full FPL scoring.",
            "Confirmed-zero player availability is not changed by this team-goal model.",
            "Historical revisions have unknown original timing; no strict replay claim.",
            "Only five completed events; current TFT requires at least eight chronological events.",
            "No held-out model evaluation or performance superiority claim.",
        ],
    }
    write_json(ROOT / "docs/local/deadline-bayesian.json", report)
    print(
        json.dumps(
            {"status": "sampling", "matches": len(matches), "directory": str(directory)}
        ),
        flush=True,
    )
    trace, diagnostics = fit_matches(matches, draws=500, tune=500, seed=42)
    import arviz as az

    all_rhat = az.rhat(trace).to_array().values
    all_ess = az.ess(trace, method="bulk").to_array().values
    diagnostics["unrounded_all_parameter_max_rhat"] = float(np.nanmax(all_rhat))
    diagnostics["all_parameter_min_ess_bulk"] = float(np.nanmin(all_ess))
    diagnostics["all_parameter_converged"] = bool(
        np.isfinite(all_rhat).all()
        and np.isfinite(all_ess).all()
        and diagnostics["unrounded_all_parameter_max_rhat"] <= 1.01
        and diagnostics["all_parameter_min_ess_bulk"] >= 100
        and diagnostics["divergences"] == 0
    )
    diagnostics["convergence_caveat"] = (
        "Two chains only; four chains recommended; no held-out predictive validation."
    )
    trace.to_netcdf(directory / "posterior.nc")
    write_json(directory / "diagnostics.json", diagnostics)
    report["diagnostics"] = diagnostics
    report["gw6_team_predictions"] = posterior_predictions(
        trace, diagnostics, upcoming, {t["id"]: t["name"] for t in bootstrap["teams"]}
    )
    report["status"] = (
        "completed_partial_goal_model"
        if diagnostics["all_parameter_converged"]
        else "completed_with_convergence_warning"
    )
    report["completed_at"] = datetime.now(UTC).isoformat()
    report["before_deadline_at_completion"] = instant(report["completed_at"]) < instant(
        deadline
    )
    try:
        pointer_after = fingerprint(store.get("current", "live"))
    except KeyError:
        pointer_after = None
    report["live_pointer_preserved"] = pointer_before == pointer_after
    report["artifacts"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.iterdir()
        if p.is_file()
    }
    write_json(directory / "report.json", report)
    write_json(ROOT / "docs/local/deadline-bayesian.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "diagnostics": diagnostics,
                "fixture_count": len(report["gw6_team_predictions"]),
                "report": str(ROOT / "docs/local/deadline-bayesian.json"),
            }
        ),
        flush=True,
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", default="5ca9f12d261942b69ba6c69e693cb1bb")
    args = parser.parse_args()
    run(args.collection_id)
