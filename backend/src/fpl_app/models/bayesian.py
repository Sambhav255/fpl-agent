"""Optional hierarchical goal model and shared, explicitly partial football scenarios."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.features.pipeline import fingerprint, immutable_json

from .training import audited_panel, split_panel


def fit_matches(
    matches: pd.DataFrame, draws: int = 300, tune: int = 300, seed: int = 42
) -> tuple[Any, dict[str, Any]]:
    """Low-level fitting also supports labelled installation tests; never registers."""
    import arviz as az
    import pymc as pm

    required = {"fixture_id", "home_club", "away_club", "home_goals", "away_goals", "time_index"}
    if not required <= set(matches) or matches.duplicated("fixture_id").any() or len(matches) < 4:
        raise ValueError("one complete match record per fixture required")
    if (
        not np.isfinite(matches[["home_goals", "away_goals", "time_index"]].to_numpy()).all()
        or (matches[["home_goals", "away_goals"]] < 0).any().any()
    ):
        raise ValueError("invalid match counts")
    clubs = sorted(set(matches["home_club"]) | set(matches["away_club"]))
    index = {club: i for i, club in enumerate(clubs)}
    home = matches["home_club"].map(index).to_numpy()
    away = matches["away_club"].map(index).to_numpy()
    time = matches["time_index"].to_numpy(dtype=float)
    time_center, time_scale = float(time.mean()), max(1.0, float(time.std()))
    time = (time - time_center) / time_scale
    with pm.Model(coords={"club": list(map(str, clubs)), "match": list(range(len(matches)))}):
        base = pm.Normal("base", 0.2, 0.5)
        venue = pm.Normal("venue", 0.1, 0.3)
        attack_scale = pm.HalfNormal("attack_scale", 0.5)
        defence_scale = pm.HalfNormal("defence_scale", 0.5)
        raw_attack = pm.Normal("raw_attack", 0, 1, dims="club")
        raw_defence = pm.Normal("raw_defence", 0, 1, dims="club")
        attack = pm.Deterministic(
            "attack", (raw_attack - pm.math.mean(raw_attack)) * attack_scale, dims="club"
        )
        defence = pm.Deterministic(
            "defence", (raw_defence - pm.math.mean(raw_defence)) * defence_scale, dims="club"
        )
        trend = pm.Normal("trend", 0, 0.1)
        dispersion = pm.Exponential("dispersion", 1)
        home_mu = pm.math.exp(base + venue + attack[home] - defence[away] + trend * time)
        away_mu = pm.math.exp(base + attack[away] - defence[home] + trend * time)
        pm.NegativeBinomial(
            "home_goals",
            mu=home_mu,
            alpha=dispersion,
            observed=matches["home_goals"].to_numpy(),
            dims="match",
        )
        pm.NegativeBinomial(
            "away_goals",
            mu=away_mu,
            alpha=dispersion,
            observed=matches["away_goals"].to_numpy(),
            dims="match",
        )
        trace = pm.sample(
            draws=draws,
            tune=tune,
            chains=2,
            cores=1,
            random_seed=seed,
            target_accept=0.9,
            progressbar=False,
            compute_convergence_checks=True,
        )
        predictive = pm.sample_posterior_predictive(trace, random_seed=seed, progressbar=False)
        trace.extend(predictive)
    summary = az.summary(
        trace, var_names=["base", "venue", "attack", "defence", "trend", "dispersion"]
    )
    rhat = float(summary["r_hat"].max())
    ess = float(summary["ess_bulk"].min())
    divergences = int(trace.sample_stats["diverging"].sum())
    diagnostics = {
        "clubs": clubs,
        "max_rhat": rhat if np.isfinite(rhat) else None,
        "min_ess_bulk": ess if np.isfinite(ess) else None,
        "divergences": divergences,
        "converged": bool(np.isfinite(rhat) and rhat <= 1.01 and ess >= 100 and divergences == 0),
        "home_goals_observed_mean": float(matches["home_goals"].mean()),
        "home_goals_predictive_mean": float(trace.posterior_predictive["home_goals"].mean()),
        "time_center": time_center,
        "time_scale": time_scale,
        "seed": seed,
        "limitations": [
            "Team-goal count model only; player minutes/allocation use empirical hierarchical priors",
            "No exact BPS, defensive actions, cards or save component; partial points scenarios not active forecasts",
        ],
    }
    return trace, diagnostics


def shared_scenarios(
    trace: Any,
    diagnostics: dict[str, Any],
    home_club: int,
    away_club: int,
    players: pd.DataFrame,
    samples: int = 500,
    seed: int = 42,
    time_index: float | None = None,
) -> dict[str, Any]:
    """One shared score per match; goals conserved and competing GKs exclusive.

    Player rows require player_id,club,position, appearances,total_matches,
    minutes_per_appearance,goals,assists,total_minutes. Priors shrink exposure and
    opportunity. Output is joint outcome variability, not parameter-only intervals.
    """
    required = {
        "player_id",
        "club",
        "position",
        "appearances",
        "total_matches",
        "minutes_per_appearance",
        "goals",
        "assists",
        "total_minutes",
    }
    if not required <= set(players) or players.duplicated("player_id").any() or samples < 1:
        raise ValueError("complete distinct player exposure rows required")
    if (
        not set(players["club"]) <= {home_club, away_club}
        or not players["position"].isin([1, 2, 3, 4]).all()
    ):
        raise ValueError("invalid fixture player club/position")
    if (players["appearances"] > players["total_matches"]).any() or (
        players[["appearances", "total_matches", "total_minutes", "goals", "assists"]] < 0
    ).any().any():
        raise ValueError("invalid exposure/counts")
    rng = np.random.default_rng(seed)
    posterior = trace.posterior

    def values(name: str) -> np.ndarray[Any, Any]:
        value = posterior[name]
        dims = ["chain", "draw", *[d for d in value.dims if d not in ("chain", "draw")]]
        arr = value.transpose(*dims).values
        return arr.reshape((-1, *arr.shape[2:]))

    base = values("base")
    selected = rng.integers(0, len(base), size=samples)
    attack, defence = values("attack"), values("defence")
    clubs = diagnostics["clubs"]
    h, a = clubs.index(home_club), clubs.index(away_club)
    t = (
        0.0
        if time_index is None
        else (time_index - diagnostics["time_center"]) / diagnostics["time_scale"]
    )
    home_mu = np.exp(
        base[selected]
        + values("venue")[selected]
        + attack[selected, h]
        - defence[selected, a]
        + values("trend")[selected] * t
    )
    away_mu = np.exp(
        base[selected] + attack[selected, a] - defence[selected, h] + values("trend")[selected] * t
    )
    alpha = values("dispersion")[selected]
    home_goals = rng.negative_binomial(alpha, alpha / (alpha + home_mu))
    away_goals = rng.negative_binomial(alpha, alpha / (alpha + away_mu))
    rows = players.reset_index(drop=True)
    n = len(rows)
    minutes = np.zeros((samples, n))
    goals = np.zeros((samples, n), dtype=int)
    assists = np.zeros((samples, n), dtype=int)
    appearance = (rows["appearances"].to_numpy(dtype=float) + 2) / (
        rows["total_matches"].to_numpy(dtype=float) + 4
    )
    # GK choice is categorical, not independent Bernoulli draws.
    for club in (home_club, away_club):
        indices = rows.index[(rows["club"] == club) & (rows["position"] == 1)].to_numpy()
        if len(indices):
            weights = appearance[indices]
            probabilities = weights / max(1.0, weights.sum())
            choices = rng.choice(
                np.append(indices, -1),
                size=samples,
                p=np.append(probabilities, max(0.0, 1 - probabilities.sum())),
            )
            for idx in indices:
                minutes[choices == idx, idx] = 90
    for idx, (_, row) in enumerate(rows.iterrows()):
        if row["position"] != 1:
            active = rng.random(samples) < appearance[idx]
            # Explicit heuristic two-state minute mixture, not an estimated full minute model.
            mean_minutes = np.clip(float(row["minutes_per_appearance"]), 1, 90)
            long_prob = np.clip((mean_minutes - 20) / 60, 0, 1)
            minutes[:, idx] = active * np.where(rng.random(samples) < long_prob, 80.0, 20.0)
    unallocated = np.zeros((samples, 2), dtype=int)
    for side, (club, scores) in enumerate(((home_club, home_goals), (away_club, away_goals))):
        indices = rows.index[rows["club"] == club].to_numpy()
        scoring_rates = (rows.loc[indices, "goals"].to_numpy(dtype=float) + 0.5) / (
            rows.loc[indices, "total_minutes"].to_numpy(dtype=float) + 900
        )
        assist_rates = (rows.loc[indices, "assists"].to_numpy(dtype=float) + 0.5) / (
            rows.loc[indices, "total_minutes"].to_numpy(dtype=float) + 900
        )
        for sample, total in enumerate(scores):
            weight = scoring_rates * minutes[sample, indices]
            # An unrepresented teammate bucket prevents allocating every goal to partial squad.
            weights = np.append(weight, 0.15)
            scorers = rng.choice(np.append(indices, -1), size=int(total), p=weights / weights.sum())
            for scorer in scorers:
                if scorer >= 0:
                    goals[sample, scorer] += 1
                else:
                    unallocated[sample, side] += 1
                aw = assist_rates * minutes[sample, indices]
                aw[indices == scorer] = 0
                aw = np.append(aw, 0.2)  # no FPL assist / unrepresented teammate
                assister = rng.choice(np.append(indices, -1), p=aw / aw.sum())
                if assister >= 0:
                    assists[sample, assister] += 1
    points = (minutes > 0).astype(float) + (minutes >= 60)
    for idx, (_, row) in enumerate(rows.iterrows()):
        conceded = away_goals if row["club"] == home_club else home_goals
        position = int(row["position"])
        points[:, idx] += goals[:, idx] * {1: 10, 2: 6, 3: 5, 4: 4}[position] + 3 * assists[:, idx]
        points[:, idx] += (
            (minutes[:, idx] >= 60) * (conceded == 0) * {1: 4, 2: 4, 3: 1, 4: 0}[position]
        )
        if position in (1, 2):
            points[:, idx] -= (minutes[:, idx] > 0) * (conceded // 2)
    return {
        "player_ids": rows["player_id"].tolist(),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "minutes": minutes,
        "goals": goals,
        "assists": assists,
        "unallocated_goals": unallocated,
        "points": points,
        "expected_points": points.mean(axis=0),
        "point_quantiles": np.quantile(points, [0.1, 0.5, 0.9], axis=0),
        "limitations": [
            *diagnostics["limitations"],
            "Minutes/GK/full-match concessions approximate; scoring missing several components",
        ],
        "seed": seed,
    }


def train_bayesian(
    dataset: Path, output: Path, seed: int = 42, draws: int = 300, tune: int = 300
) -> dict[str, Any]:
    frame, audit = audited_panel(dataset)
    train, _, _ = split_panel(frame)
    required = {"home_club", "away_club", "home_goals", "away_goals", "time_index"}
    if not required <= set(train):
        raise ValueError(
            "Bayesian unavailable: verified match scores, season-mapped clubs and time_index missing"
        )
    matches = train[["fixture_id", *sorted(required)]].drop_duplicates()
    checksum = hashlib.sha256(dataset.read_bytes()).hexdigest()
    run_id = fingerprint({"dataset": checksum, "seed": seed, "draws": draws, "tune": tune})[:24]
    published = output / "bayesian" / run_id
    from .publication import open_model_run, publish_model_run, reuse_model_run

    if reuse_model_run(published, checksum):
        diagnostics = json.loads((published / "diagnostics.json").read_text())
        return {
            "directory": str(published),
            "status": "trained",
            "diagnostics": diagnostics,
            "active": False,
            "reused": True,
        }
    dest, complete = open_model_run(published)
    if complete:
        diagnostics = json.loads((published / "diagnostics.json").read_text())
        return {
            "directory": str(published),
            "status": "trained",
            "diagnostics": diagnostics,
            "active": False,
            "reused": True,
        }
    trace, diagnostics = fit_matches(matches, draws, tune, seed)
    trace.to_netcdf(dest / "posterior.nc")
    immutable_json(dest / "diagnostics.json", diagnostics)
    artifacts = {
        name: hashlib.sha256((dest / name).read_bytes()).hexdigest()
        for name in ("posterior.nc", "diagnostics.json")
    }
    immutable_json(
        dest / "manifest.json",
        {
            "run_id": run_id,
            "model_family": "bayesian",
            "data_mode": "live",
            "dataset_sha256": checksum,
            "replay_timing": audit["replay_timing"],
            "model_status": "trained",
            "artifacts": artifacts,
            "seed": seed,
            "limitations": diagnostics["limitations"],
            "diagnostics_converged": diagnostics["converged"],
        },
    )
    publish_model_run(dest, published)
    return {
        "directory": str(published),
        "status": "trained",
        "diagnostics": diagnostics,
        "active": False,
    }
