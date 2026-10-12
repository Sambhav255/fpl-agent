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
from fpl_app.domain.rules import RULES
from fpl_app.features.pipeline import utc

from .bayesian import shared_scenarios
from .inference import common_projection
from .tft import predict_tft


def _artifact(path: Path, family: str, cutoff: str) -> dict[str, Any]:
    if path.is_symlink() or (path / "manifest.json").is_symlink():
        raise ValueError("Unsafe artifact path")
    manifest: dict[str, Any] = json.loads((path / "manifest.json").read_text())
    if (
        manifest.get("model_family") != family
        or manifest.get("data_mode") != "live"
        or manifest.get("replay_timing") != "verified"
        or manifest.get("model_status") != "trained"
        or manifest.get("rules_version") != RULES.version
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
    scoring = None
    if "scoring_profiles.json" in manifest["artifacts"]:
        scoring = json.loads((artifact / "scoring_profiles.json").read_text())
        if (
            scoring.get("version") != "complete-bayesian-player-scoring-v1"
            or utc(scoring["fit_cutoff"]) > utc(manifest["training_cutoff"])
            or not set(player_map) <= set(scoring["profiles"])
        ):
            raise ValueError(
                "Complete scoring profiles differ from artifact cutoff or canonical mapping"
            )
        scoring["profiles"] = {str(player_map[key]): scoring["profiles"][key] for key in player_map}
    predictions = []
    limitations = list(manifest.get("limitations", []))
    for fixture in sorted(schedule, key=lambda f: f.fixture_id):
        home, away = club_map[fixture.home_club], club_map[fixture.away_club]
        subset = rows[rows.club.isin([home, away])]
        if subset.empty:
            continue
        if scoring is None:
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
        else:
            from fpl_app.models.bayesian_scoring import complete_scenarios

            outcomes = complete_scenarios(
                trace,
                diagnostics,
                home,
                away,
                subset,
                scoring,
                samples=samples,
                seed=seed + fixture.fixture_id,
                time_index=fixture_times[fixture.fixture_id],
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
                    start_probability=float(outcomes["starts"][:, i].mean())
                    if scoring is not None
                    else None,
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
                    "Inactive complete-component posterior adapter; empirical temporal/BPS approximations remain uncalibrated"
                    if scoring is not None
                    else "Inactive partial-scoring posterior adapter; not evaluated or approved for recommendations",
                    "No second availability multiplier; fitted starts when complete profiles exist",
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
    "start_probability",
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
    """Adapt independent mean/quantile heads via returned series and lead index.

    Caller supplies a deadline-safe slot_panel and separately sourced unconditional
    minute estimates. Legacy artifacts support one event; verified multilead
    artifacts require exact horizon and purged model-selection label timing.
    """
    declared_family = json.loads((artifact / "manifest.json").read_text()).get("model_family")
    if declared_family not in {"tft", "tft_multilead"}:
        raise ValueError("Unsupported TFT artifact family")
    manifest = _artifact(artifact, declared_family, cutoff)
    multilead = declared_family == "tft_multilead"
    schedule = _schedule(fixtures, next_event, horizon)
    current = _mapping(players, player_map)
    if not multilead and horizon != 1:
        raise ValueError("TFT supports one-event decoder only")
    if multilead and (
        manifest.get("horizon_events") != horizon
        or "selection_labels_available_at" not in manifest
        or utc(manifest["selection_labels_available_at"]) >= utc(cutoff)
    ):
        raise ValueError("Multilead horizon or selection-label cutoff differs")
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
    if multilead and not {"lead", "schedule_known"} <= set(panel):
        raise ValueError("Multilead decoder contract missing")
    if (
        panel.duplicated(["series", "time_idx"]).any()
        or set(panel.forecast_origin) != {next_event}
        or any(utc(v) != utc(cutoff) for v in panel.decision_cutoff)
    ):
        raise ValueError("duplicate series or inconsistent forecast deadline/origin")
    targets = (
        panel[panel.lead > 0].copy()
        if multilead
        else panel.sort_values("time_idx").groupby("series", as_index=False).tail(1)
    )
    if multilead:
        for _, group in targets.groupby("series"):
            ordered = group.sort_values("time_idx")
            if (
                ordered.lead.tolist() != list(range(1, horizon + 1))
                or ordered.source_event.tolist() != list(range(next_event, next_event + horizon))
                or not (ordered.schedule_known == 1).all()
                or ordered.player.nunique() != 1
            ):
                raise ValueError("Incomplete or inconsistent frozen multilead schedule")
    if (not multilead and not (targets.source_event == next_event).all()) or not (
        targets[["points", "encoder_points", "observation_mask", "weight"]] == 0
    ).all().all():
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
        if row["source_event"] != f.event:
            raise ValueError("Decoder fixture event differs from frozen schedule")
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
    if mean.shape != (n, horizon) or quantiles.shape != (n, horizon, 3):
        raise ValueError("unsupported TFT output dimensions")
    if not np.isfinite(mean).all() or not np.isfinite(quantiles).all():
        raise ValueError("nonfinite TFT output")
    if index.series.duplicated().any() or set(index.series) != set(targets.series):
        raise ValueError("TFT index does not cover decoder series")
    records = []
    for i, row in enumerate(index.to_dict("records")):
        window = targets[targets.series == row["series"]].sort_values("time_idx")
        if row["time_idx"] != window.iloc[0].time_idx:
            raise ValueError("TFT index decoder step mismatch")
        for lead, target in enumerate(window.itertuples(index=False)):
            if target.fixture_exists != 1:
                continue
            records.append(
                dict(
                    player_id=player_map[target.player],
                    fixture_id=int(target.fixture_id),
                    event=int(target.source_event),
                    decision_cutoff=cutoff,
                    expected_points=float(mean[i, lead]),
                    **{f"p{q}": float(quantiles[i, lead, j]) for j, q in enumerate((10, 50, 90))},
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
            f"Inactive {horizon}-event TFT adapter; external unconditional minutes, not a TFT minutes head",
            "Encoder point publication provenance must be verified by the upstream slot builder",
            "Quantiles are fixture marginals; mean is separate and never availability-scaled",
        ],
    )
