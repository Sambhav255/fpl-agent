from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from fpl_app.contracts import Fixture, Player, Projection, ProjectionRun
from fpl_app.features.pipeline import fingerprint, utc

from .training import catboost_predict


def common_projection(
    predictions: pd.DataFrame,
    players: list[Player],
    fixtures: list[Fixture],
    snapshot_id: str,
    cutoff: str,
    data_mode: Literal["demo", "live"],
    next_event: int,
    horizon: int,
    model_family: str,
    model_status: str = "trained",
    artifact_id: str = "",
    assumptions: list[str] | None = None,
) -> ProjectionRun:
    """Independent frozen-schedule coverage and scalar/probability validation.

    Each row uses explicit current player_id mapping supplied by the caller, never
    implicit historical element-ID/name joins. Blanks emit no fixture prediction;
    missing scheduled rows fail. Only fixture quantiles are emitted, never summed.
    """
    utc(cutoff)
    if not 1 <= horizon <= 8 or not 1 <= next_event <= 38:
        raise ValueError("invalid event/horizon")
    schedule = [
        f for f in fixtures if f.event is not None and next_event <= f.event < next_event + horizon
    ]
    expected = {
        (p.player_id, f.fixture_id, f.event)
        for p in players
        for f in schedule
        if p.club in (f.home_club, f.away_club)
    }
    required = {
        "player_id",
        "fixture_id",
        "event",
        "decision_cutoff",
        "expected_points",
        "expected_minutes",
    }
    if not required <= set(predictions):
        raise ValueError("common prediction columns missing")
    if predictions.duplicated(["player_id", "fixture_id", "event"]).any():
        raise ValueError("duplicate fixture projections")
    if len({p.player_id for p in players}) != len(players) or len(
        {f.fixture_id for f in schedule}
    ) != len(schedule):
        raise ValueError("duplicate player/fixture schedule")
    seen = {
        (int(r["player_id"]), int(r["fixture_id"]), int(r["event"]))
        for r in predictions.to_dict("records")
    }
    if seen != expected:
        raise ValueError("missing or extraneous frozen fixture forecast")
    projections = []
    for row in predictions.to_dict("records"):
        if not np.isfinite([float(row["expected_points"]), float(row["expected_minutes"])]).all():
            raise ValueError("Nonfinite point or minute forecast")
        if utc(row["decision_cutoff"]) != utc(cutoff):
            raise ValueError("inconsistent forecast deadline")
        quantiles = None
        if all(f"p{q}" in row for q in (10, 50, 90)):
            values = [float(row[f"p{q}"]) for q in (10, 50, 90)]
            if not np.isfinite(values).all() or values != sorted(values):
                raise ValueError("nonfinite/crossed fixture quantiles")
            quantiles = dict(zip(["0.1", "0.5", "0.9"], values))

        def optional(column: str, current: Any = row) -> float | None:
            return (
                float(current[column]) if column in current and pd.notna(current[column]) else None
            )

        appearance = optional("appearance_probability")
        start, sixty = optional("start_probability"), optional("minutes_60_probability")
        if appearance is not None and any(p is not None and p > appearance for p in (start, sixty)):
            raise ValueError("incoherent appearance probabilities")
        projections.append(
            Projection(
                player_id=int(row["player_id"]),
                fixture_id=int(row["fixture_id"]),
                event=int(row["event"]),
                expected_points=float(row["expected_points"]),
                expected_minutes=float(row["expected_minutes"]),
                appearance_probability=appearance,
                start_probability=start,
                minutes_60_probability=sixty,
                point_quantiles=quantiles,
                assumptions=assumptions or [],
            )
        )
    identity = fingerprint(
        {
            "artifact": artifact_id,
            "snapshot": snapshot_id,
            "cutoff": cutoff,
            "model": model_family,
            "predictions": [p.model_dump() for p in projections],
        }
    )
    return ProjectionRun(
        requested_provider=model_family,
        resolved_provider=model_family,
        artifact_id=artifact_id or None,
        prediction_origin=cutoff,
        lifecycle_state="experimental",
        player_universe_ids=sorted(p.player_id for p in players),
        projection_run_id=f"{model_family}-{identity[:24]}",
        snapshot_id=snapshot_id,
        source_cutoff=cutoff,
        data_mode=data_mode,
        horizon_events=horizon,
        model_family=model_family,
        model_status=model_status,
        projections=projections,
        fixtures=schedule,
        warnings=assumptions or [],
    )


def catboost_run(
    artifact: Path,
    features: pd.DataFrame,
    players: list[Player],
    fixtures: list[Fixture],
    snapshot_id: str,
    cutoff: str,
    data_mode: Literal["demo", "live"],
    next_event: int,
    horizon: int,
    allow_retrospective: bool = False,
) -> ProjectionRun:
    metadata: dict[str, Any] = json.loads((artifact / "manifest.json").read_text())
    if metadata["replay_timing"] != "verified" and not allow_retrospective:
        raise ValueError(
            "Model inactive: unverified retrospective timing cannot serve deadline-compliant forecasts"
        )
    predicted = catboost_predict(artifact, features)
    result = features[["player_id", "fixture_id", "event", "decision_cutoff"]].copy()
    for column in predicted:
        # Name used internally by CatBoost auxiliary artifact is translated once.
        result["minutes_60_probability" if column == "minutes_60_probability" else column] = (
            predicted[column]
        )
    result["expected_minutes"] = features["mean_minutes_5"].fillna(45.0).clip(0, 90)
    return common_projection(
        result,
        players,
        fixtures,
        snapshot_id,
        cutoff,
        data_mode,
        next_event,
        horizon,
        "catboost",
        artifact_id=metadata["run_id"],
        assumptions=[
            *metadata["limitations"],
            "Expected minutes uses lagged unconditional average/cold-start prior; mean points never availability-scaled",
        ],
    )
