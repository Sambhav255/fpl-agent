"""Standalone, inactive adapters for trusted local Bayesian/TFT artifacts.

No registry/job mutation. Hash validation detects corruption, not malicious pickle;
TFT artifacts must originate in the trusted local training pipeline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.contracts import Fixture, Player, ProjectionRun
from fpl_app.features.pipeline import utc

from .bayesian import shared_scenarios
from .inference import common_projection
from .tft import predict_tft


def _artifact(path: Path, family: str, cutoff: str) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads((path / "manifest.json").read_text())
    if (
        manifest.get("model_family") != family
        or manifest.get("data_mode") != "live"
        or manifest.get("replay_timing") != "verified"
        or manifest.get("model_status") != "trained"
    ):
        raise ValueError("verified live trained artifact required; retrospective/demo rejected")
    for field in ("training_cutoff", "available_at"):
        if field not in manifest or utc(manifest[field]) > utc(cutoff):
            raise ValueError(f"missing or future artifact {field}")
    if utc(manifest["training_cutoff"]) > utc(manifest["available_at"]):
        raise ValueError("artifact availability precedes training")
    required = (
        {"posterior.nc", "diagnostics.json"}
        if family == "bayesian"
        else {"mean.ckpt", "quantiles.ckpt", "dataset.pt"}
    )
    hashes = manifest.get("artifacts", {})
    if not required <= set(hashes) or not manifest.get("run_id"):
        raise ValueError("incomplete artifact manifest")
    for name, digest in hashes.items():
        target = path / name
        if Path(name).name != name or target.is_symlink() or not target.is_file():
            raise ValueError("unsafe or missing artifact path")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("artifact checksum mismatch")
    return manifest


def _schedule(fixtures: list[Fixture], next_event: int, horizon: int) -> list[Fixture]:
    if not 1 <= horizon <= 8 or not 1 <= next_event <= 38 or next_event + horizon > 39:
        raise ValueError("invalid event/horizon")
    selected = [
        f for f in fixtures if f.event is not None and next_event <= f.event < next_event + horizon
    ]
    if len({f.fixture_id for f in selected}) != len(selected):
        raise ValueError("duplicate fixture schedule")
    return selected


def _mapping(players: list[Player], player_map: dict[str, int]) -> dict[int, Player]:
    current = {p.player_id: p for p in players}
    if len(current) != len(players) or len(set(player_map.values())) != len(player_map):
        raise ValueError("duplicate or ambiguous player mapping")
    if set(player_map.values()) != set(current) or any(not k for k in player_map):
        raise ValueError("explicit complete canonical player mapping required")
    return current


def bayesian_run(
    artifact: Path,
    exposures: pd.DataFrame,
    players: list[Player],
    fixtures: list[Fixture],
    snapshot_id: str,
    cutoff: str,
    next_event: int,
    horizon: int,
    player_map: dict[str, int],
    club_map: dict[int, int],
    fixture_times: dict[int, float],
    samples: int = 500,
    seed: int = 42,
) -> ProjectionRun:
    """Sample real posterior; exposure rows are canonical, as-of frozen inputs.

    club_map maps current club IDs to posterior training-club IDs. It must be
    season-reviewed explicitly, including transfers; no name/element-ID matching.
    """
    manifest = _artifact(artifact, "bayesian", cutoff)
    schedule = _schedule(fixtures, next_event, horizon)
    current = _mapping(players, player_map)
    if samples < 2:
        raise ValueError("at least two predictive samples required")
    required = {
        "canonical_player_id",
        "club",
        "position",
        "available_at",
        "appearances",
        "total_matches",
        "minutes_per_appearance",
        "goals",
        "assists",
        "total_minutes",
    }
    if not required <= set(exposures) or exposures.canonical_player_id.duplicated().any():
        raise ValueError("distinct complete exposure rows required")
    rows = exposures.copy()
    if set(rows.canonical_player_id) != set(player_map):
        raise ValueError("unmapped or missing exposure player")
    if any(utc(value) > utc(cutoff) for value in rows.available_at):
        raise ValueError("future exposure data")
    numeric = rows[
        [
            "appearances",
            "total_matches",
            "minutes_per_appearance",
            "goals",
            "assists",
            "total_minutes",
        ]
    ].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or (numeric < 0).any() or (numeric[:, 2] > 90).any():
        raise ValueError("invalid exposure statistics")
    rows["player_id"] = rows.canonical_player_id.map(player_map)
    for row in rows.to_dict("records"):
        p = current[row["player_id"]]
        if row["club"] != p.club or row["position"] != p.position:
            raise ValueError("exposure club/position differs from frozen player")
    needed = {c for f in schedule for c in (f.home_club, f.away_club)} | {p.club for p in players}
    diagnostics = json.loads((artifact / "diagnostics.json").read_text())
    if (
        not needed <= set(club_map)
        or len(set(club_map.values())) != len(club_map)
        or not set(club_map.values()) <= set(diagnostics["clubs"])
    ):
        raise ValueError("explicit unambiguous posterior club mapping required")
    if diagnostics.get("converged") is not True:
        raise ValueError("posterior convergence not verified")
    if set(fixture_times) != {f.fixture_id for f in schedule} or not all(
        np.isfinite(t) for t in fixture_times.values()
    ):
        raise ValueError("explicit finite fixture time indices required")
    import arviz as az

    trace = az.from_netcdf(artifact / "posterior.nc")
    rows["club"] = rows.club.map(club_map)
    predictions = []
    limitations = list(manifest.get("limitations", []))
    for fixture in sorted(schedule, key=lambda f: f.fixture_id):
        home, away = club_map[fixture.home_club], club_map[fixture.away_club]
        subset = rows[rows.club.isin([home, away])]
        if subset.empty:
            continue
        outcomes = shared_scenarios(
            trace,
            diagnostics,
            home,
            away,
            subset,
            samples,
            seed + fixture.fixture_id,
            fixture_times[fixture.fixture_id],
        )
        limitations.extend(outcomes["limitations"])
        for i, player_id in enumerate(outcomes["player_ids"]):
            minutes = outcomes["minutes"][:, i]
            predictions.append(
                dict(
                    player_id=player_id,
                    fixture_id=fixture.fixture_id,
                    event=fixture.event,
                    decision_cutoff=cutoff,
                    expected_points=float(outcomes["points"][:, i].mean()),
                    expected_minutes=float(minutes.mean()),
                    appearance_probability=float((minutes > 0).mean()),
                    minutes_60_probability=float((minutes >= 60).mean()),
                    **{
                        f"p{q}": float(outcomes["point_quantiles"][j, i])
                        for j, q in enumerate((10, 50, 90))
                    },
                )
            )
    return common_projection(
        pd.DataFrame(predictions, columns=_COLUMNS),
        players,
        fixtures,
        snapshot_id,
        cutoff,
        "live",
        next_event,
        horizon,
        "bayesian",
        "trained",
        manifest["run_id"],
        list(
            dict.fromkeys(
                [
                    *limitations,
                    "Inactive partial-scoring posterior adapter; not evaluated or approved for recommendations",
                    "Start probability unavailable; no second availability multiplier",
                ]
            )
        ),
    )


_COLUMNS = [
    "player_id",
    "fixture_id",
    "event",
    "decision_cutoff",
    "expected_points",
    "expected_minutes",
    "appearance_probability",
    "minutes_60_probability",
    "p10",
    "p50",
    "p90",
]


def tft_run(
    artifact: Path,
    panel: pd.DataFrame,
    minutes: pd.DataFrame,
    players: list[Player],
    fixtures: list[Fixture],
    snapshot_id: str,
    cutoff: str,
    next_event: int,
    horizon: int,
    player_map: dict[str, int],
    club_map: dict[int, int],
) -> ProjectionRun:
    """Adapt library (N,1) mean and (N,1,3) quantiles via returned series index.

    Caller supplies a deadline-safe slot_panel and separately sourced unconditional
    minute estimates. Reject legacy panels and multi-event forecasts.
    """
    manifest = _artifact(artifact, "tft", cutoff)
    schedule = _schedule(fixtures, next_event, horizon)
    current = _mapping(players, player_map)
    if horizon != 1:
        raise ValueError("TFT supports one-event decoder only")
    required = {
        "series",
        "player",
        "time_idx",
        "forecast_origin",
        "source_event",
        "fixture_id",
        "fixture_exists",
        "opponent",
        "was_home",
        "decision_cutoff",
        "encoder_points",
        "observation_mask",
        "points",
        "weight",
    }
    if not required <= set(panel) or panel.empty:
        raise ValueError("deadline-safe as-of slot panel required")
    if (
        panel.duplicated(["series", "time_idx"]).any()
        or set(panel.forecast_origin) != {next_event}
        or any(utc(v) != utc(cutoff) for v in panel.decision_cutoff)
    ):
        raise ValueError("duplicate series or inconsistent forecast deadline/origin")
    targets = panel.sort_values("time_idx").groupby("series", as_index=False).tail(1)
    if (
        not (targets.source_event == next_event).all()
        or not (targets[["points", "encoder_points", "observation_mask", "weight"]] == 0)
        .all()
        .all()
    ):
        raise ValueError("decoder outcomes must be masked placeholders")
    history = panel.drop(targets.index)
    if (history.source_event >= next_event).any():
        raise ValueError("future encoder event")
    if not {p.club for p in players} <= set(club_map) or len(set(club_map.values())) != len(
        club_map
    ):
        raise ValueError("explicit unambiguous club mapping required")
    by_fixture = {f.fixture_id: f for f in schedule}
    for row in targets[targets.fixture_exists == 1].to_dict("records"):
        if row["player"] not in player_map or row["fixture_id"] not in by_fixture:
            raise ValueError("unmapped decoder player/fixture")
        p, f = current[player_map[row["player"]]], by_fixture[row["fixture_id"]]
        if p.club not in (f.home_club, f.away_club):
            raise ValueError("decoder player not in fixture")
        opponent = f.away_club if p.club == f.home_club else f.home_club
        if (
            opponent not in club_map
            or row["opponent"] != club_map[opponent]
            or (row["was_home"] != int(p.club == f.home_club))
        ):
            raise ValueError("decoder opponent/venue differs from frozen schedule")
    minute_columns = {"player_id", "fixture_id", "expected_minutes", "available_at"}
    if not minute_columns <= set(minutes) or minutes.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("distinct sourced unconditional minute estimates required")
    if any(utc(v) > utc(cutoff) for v in minutes.available_at):
        raise ValueError("future minute estimates")
    output = predict_tft(artifact, panel)
    index = output["index"]
    n = len(index)
    mean, quantiles = np.asarray(output["mean"]), np.asarray(output["quantiles"])
    if mean.shape != (n, 1) or quantiles.shape != (n, 1, 3):
        raise ValueError("unsupported TFT output dimensions")
    if not np.isfinite(mean).all() or not np.isfinite(quantiles).all():
        raise ValueError("nonfinite TFT output")
    if index.series.duplicated().any() or set(index.series) != set(targets.series):
        raise ValueError("TFT index does not cover decoder series")
    records = []
    lookup = targets.set_index("series")
    for i, row in enumerate(index.to_dict("records")):
        target = lookup.loc[row["series"]]
        if row["time_idx"] != target.time_idx:
            raise ValueError("TFT index decoder step mismatch")
        if target.fixture_exists != 1:
            continue
        records.append(
            dict(
                player_id=player_map[target.player],
                fixture_id=int(target.fixture_id),
                event=next_event,
                decision_cutoff=cutoff,
                expected_points=float(mean[i, 0]),
                **{f"p{q}": float(quantiles[i, 0, j]) for j, q in enumerate((10, 50, 90))},
            )
        )
    predicted = pd.DataFrame(
        records,
        columns=[
            "player_id",
            "fixture_id",
            "event",
            "decision_cutoff",
            "expected_points",
            "p10",
            "p50",
            "p90",
        ],
    )
    expected_keys = set(zip(predicted.player_id, predicted.fixture_id))
    if set(zip(minutes.player_id, minutes.fixture_id)) != expected_keys:
        raise ValueError("minute estimates differ from forecast coverage")
    predicted = predicted.merge(
        minutes.drop(columns="available_at"), on=["player_id", "fixture_id"], validate="one_to_one"
    )
    return common_projection(
        predicted,
        players,
        fixtures,
        snapshot_id,
        cutoff,
        "live",
        next_event,
        horizon,
        "tft",
        "trained",
        manifest["run_id"],
        [
            *manifest.get("limitations", []),
            "Inactive one-event TFT adapter; external unconditional minutes, not a TFT minutes head",
            "Encoder point publication provenance must be verified by the upstream slot builder",
            "Quantiles are fixture marginals; mean is separate and never availability-scaled",
        ],
    )
