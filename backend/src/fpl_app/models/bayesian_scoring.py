"""Fitted Bayesian minutes/component profiles and complete domain point scoring.

Profiles require explicit historical components, starts and publication times.
No absent component is manufactured as zero. This is an uncalibrated research
world model until chronological probability and full-point evaluation supports it.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.domain.rules import MatchStats, bonus_points, score_match
from fpl_app.features.pipeline import utc
from fpl_app.storage import fingerprint

SCORING_PROFILE_VERSION = "complete-bayesian-player-scoring-v2"
BPS_MODEL_KIND = "empirical-signed-minute-category-v1"

COMPONENTS = [
    f.name
    for f in fields(MatchStats)
    if f.name
    not in {
        "minutes",
        "goals",
        "assists",
        "goals_conceded_on_pitch",
        "goals_conceded_after_red",
        "bonus",
    }
]


def fit_scoring_profiles(frame: pd.DataFrame, cutoff: str, *, prior_strength=8.0) -> dict[str, Any]:
    required = {
        "player_id",
        "position",
        "available_at",
        "started",
        "bps",
        *(f.name for f in fields(MatchStats)),
    }
    if not required <= set(frame) or not np.isfinite(prior_strength) or prior_strength <= 0:
        raise ValueError("Complete explicit player scoring components and starts required")
    data = frame[[utc(t) <= utc(cutoff) for t in frame.available_at]].copy()
    data["available_at"] = [utc(t).isoformat() for t in data.available_at]
    if data.empty:
        raise ValueError("No scoring labels available at fit cutoff")
    count_columns = [f.name for f in fields(MatchStats)]
    values = data[count_columns].to_numpy(dtype=float)
    if (
        not np.isfinite(values).all()
        or (values < 0).any()
        or np.any(values != np.floor(values))
        or not data.position.isin([1, 2, 3, 4]).all()
    ):
        raise ValueError("Invalid finite scoring counts")
    signed_bps = data.bps.to_numpy(dtype=float)
    if not np.isfinite(signed_bps).all() or np.any(signed_bps != np.floor(signed_bps)):
        raise ValueError("Invalid finite signed integer BPS")
    if (
        not data.started.isin([True, False]).all()
        or (data.minutes > 90).any()
        or (data.started.astype(bool) & (data.minutes == 0)).any()
    ):
        raise ValueError("Explicit starts and bounded fixture minutes required")
    data["category"] = np.where(
        data.minutes == 0,
        0,
        np.where(~data.started.astype(bool), 1, np.where(data.minutes < 60, 2, 3)),
    )
    priors = {}
    for pos in range(1, 5):
        rows = data[data.position == pos]
        if rows.empty:
            raise ValueError("Training position prior coverage missing")
        categories = np.bincount(rows.category, minlength=4).astype(float) + 1
        priors[pos] = {
            "mixture": (categories / categories.sum() * prior_strength).tolist(),
            "rates": {
                name: (float(rows[name].sum()) + 0.5) / (float(rows.minutes.sum()) / 90 + 10)
                for name in COMPONENTS
            },
            "minutes": {
                c: rows.loc[rows.category == c, "minutes"].astype(int).tolist() for c in range(4)
            },
            "bps": {c: rows.loc[rows.category == c, "bps"].astype(int).tolist() for c in range(4)},
            "active_bps": rows.loc[rows.minutes > 0, "bps"].astype(int).tolist(),
        }
    profiles = {}
    for player, rows in data.groupby("player_id"):
        if rows.position.nunique() != 1:
            raise ValueError("Explicit season position mapping required")
        pos = int(rows.position.iloc[0])
        prior = priors[pos]
        counts = np.bincount(rows.category, minlength=4).astype(float) + prior["mixture"]
        profiles[str(player)] = {
            "position": pos,
            "mixture_alpha": counts.tolist(),
            "minutes": {
                str(c): rows.loc[rows.category == c, "minutes"].astype(int).tolist()
                or prior["minutes"][c]
                for c in range(4)
            },
            "bps": {
                "kind": BPS_MODEL_KIND,
                "label": "signed whole-fixture BPS conditional on minutes/start category",
                "values_by_category": {
                    str(c): rows.loc[rows.category == c, "bps"].astype(int).tolist()
                    or prior["bps"][c]
                    or (prior["active_bps"] if c > 0 else [])
                    for c in range(4)
                },
                "source_by_category": {
                    str(c): (
                        "player_category"
                        if (rows.category == c).any()
                        else "position_category"
                        if prior["bps"][c]
                        else "position_active_fallback"
                        if c > 0 and prior["active_bps"]
                        else "unavailable"
                    )
                    for c in range(4)
                },
            },
            "components": {
                name: {
                    "alpha": float(rows[name].sum()) + prior["rates"][name] * prior_strength,
                    "beta": float(rows.minutes.sum()) / 90 + prior_strength,
                }
                for name in COMPONENTS
            },
        }
    return {
        "version": SCORING_PROFILE_VERSION,
        "fit_cutoff": cutoff,
        "data_sha256": fingerprint(data.drop(columns="category").to_dict("records")),
        "profiles": profiles,
        "prior_strength": prior_strength,
        "status": "fitted_research",
        "calibrated": False,
        "limitations": [
            "Gamma-Poisson ancillary components and empirical minutes mixtures need chronological calibration",
            "Signed BPS uses empirical category resampling with explicit position fallbacks; no Gamma-Poisson count assumption",
            "Empirical BPS is not jointly calibrated to simulated goals/cards; bonus ranking uses domain tie rules",
            "On-pitch concessions use a declared temporal allocation assumption",
            "Minutes-scaled ancillary counts do not model zero-minute disciplinary participation",
        ],
    }


def sample_signed_bps(profile, minutes, starts, rng):
    """Draw actual signed whole-fixture scores, never Poisson rates or abs(BPS).

    Conditioning uses the same observed categories as profile fitting. BPS is not
    scaled again by minutes. Inactive rows with no observed category have no bonus
    competition; active rows may use only the declared fitted category fallback.
    """
    if profile.get("kind") != BPS_MODEL_KIND:
        raise ValueError("Signed empirical BPS profile required; refit legacy count profiles")
    categories = np.where(minutes == 0, 0, np.where(~starts, 1, np.where(minutes < 60, 2, 3)))
    result = np.zeros(len(minutes), dtype=int)
    for category in range(4):
        mask = categories == category
        if not mask.any():
            continue
        observed = np.asarray(profile["values_by_category"][str(category)], dtype=float)
        if (
            observed.ndim != 1
            or not np.isfinite(observed).all()
            or np.any(observed != np.floor(observed))
        ):
            raise ValueError("Invalid signed empirical BPS samples")
        if observed.size == 0:
            if category > 0:
                raise ValueError("Missing active signed BPS observations")
            continue
        result[mask] = rng.choice(observed.astype(int), size=int(mask.sum()))
    return result


def complete_scenarios(
    trace,
    diagnostics,
    home_club,
    away_club,
    players: pd.DataFrame,
    profile_artifact: dict[str, Any],
    *,
    samples=500,
    seed=42,
    time_index=None,
):
    from fpl_app.models.bayesian import shared_scenarios

    if profile_artifact.get("version") != SCORING_PROFILE_VERSION:
        raise ValueError(
            "Legacy/unsupported scoring profile: refit signed BPS profiles as v2; old artifacts remain unchanged"
        )
    profiles = profile_artifact["profiles"]
    rng = np.random.default_rng(seed)
    if not {str(i) for i in players.player_id} <= profiles.keys():
        raise ValueError("Missing fitted scoring profiles; no implicit component prior")
    minutes = np.zeros((samples, len(players)), dtype=int)
    starts = np.zeros_like(minutes, dtype=bool)
    for j, row in enumerate(players.to_dict("records")):
        profile = profiles[str(row["player_id"])]
        if profile["position"] != int(row["position"]):
            raise ValueError("Profile position mapping differs")
        probs = rng.dirichlet(profile["mixture_alpha"], size=samples)
        category = np.array([rng.choice(4, p=p) for p in probs])
        for c in range(1, 4):
            observed = profile["minutes"][str(c)]
            if not observed:
                # A category with no historical exposure cannot invent minutes.
                category[category == c] = 0
                continue
            mask = category == c
            minutes[mask, j] = rng.choice(observed, size=int(mask.sum()))
            starts[mask, j] = c >= 2
    for club in (home_club, away_club):
        keepers = np.flatnonzero(
            (players.club.to_numpy() == club) & (players.position.to_numpy() == 1)
        )
        for sample in range(samples):
            active = keepers[minutes[sample, keepers] > 0]
            if len(active) > 1:
                selected = int(rng.choice(active))
                minutes[sample, active] = 0
                starts[sample, active] = False
                minutes[sample, selected] = 90
                starts[sample, selected] = True
    base = shared_scenarios(
        trace,
        diagnostics,
        home_club,
        away_club,
        players,
        samples=samples,
        seed=seed,
        time_index=time_index,
        minutes_override=minutes,
    )
    points = np.zeros_like(minutes, dtype=float)
    components = {name: np.zeros_like(minutes, dtype=int) for name in COMPONENTS}
    bps = np.zeros_like(minutes, dtype=int)
    scored_components = {f.name: np.zeros_like(minutes, dtype=int) for f in fields(MatchStats)}
    for j, row in enumerate(players.to_dict("records")):
        profile = profiles[str(row["player_id"])]
        for name in COMPONENTS:
            fitted = profile["components"][name]
            rates = rng.gamma(fitted["alpha"], 1 / fitted["beta"], samples)
            value = rng.poisson(rates * minutes[:, j] / 90)
            if name in {"yellow_cards", "red_cards"}:
                value = np.minimum(value, 1)
            components[name][:, j] = value
        bps[:, j] = sample_signed_bps(profile["bps"], minutes[:, j], starts[:, j], rng)
        if int(row["position"]) != 1:
            components["saves"][:, j] = 0
            components["penalty_saves"][:, j] = 0
    for sample in range(samples):
        bonuses = bonus_points(
            {j: int(bps[sample, j]) for j in range(len(players)) if minutes[sample, j] > 0}
        )
        for j, row in enumerate(players.to_dict("records")):
            full_conceded = int(
                base["away_goals" if row["club"] == home_club else "home_goals"][sample]
            )
            on_pitch = int(rng.binomial(full_conceded, minutes[sample, j] / 90))
            stats = MatchStats(
                minutes=int(minutes[sample, j]),
                goals=int(base["goals"][sample, j]),
                assists=int(base["assists"][sample, j]),
                goals_conceded_on_pitch=on_pitch,
                goals_conceded_after_red=full_conceded - on_pitch
                if components["red_cards"][sample, j]
                else 0,
                bonus=bonuses.get(j, 0),
                **{name: int(value[sample, j]) for name, value in components.items()},
            )
            points[sample, j] = score_match(int(row["position"]), stats)
            for name, value in vars(stats).items():
                scored_components[name][sample, j] = value
    return {
        **base,
        "minutes": minutes,
        "starts": starts,
        "points": points,
        "components": components,
        "scored_components": scored_components,
        "bps": bps,
        "appearance_probability": (minutes > 0).mean(axis=0),
        "start_probability": starts.mean(axis=0),
        "minutes_60_probability": (minutes >= 60).mean(axis=0),
        "expected_points": points.mean(axis=0),
        "point_quantiles": np.quantile(points, [0.1, 0.5, 0.9], axis=0),
        "limitations": profile_artifact["limitations"]
        + [
            "Partial universe has unrepresented team-goal mass and incomplete bonus competition; not a calibrated realistic world model"
        ],
    }
