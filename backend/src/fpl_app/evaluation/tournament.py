"""Comparable point/opportunity/interval diagnostics; shortlist scores are not policies."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import forecast_metrics


def point_metrics(frame: pd.DataFrame, predicted: str) -> dict[str, Any]:
    result = forecast_metrics(frame.target_points, frame[predicted], events=frame.event)
    result["bias"] = float((frame[predicted] - frame.target_points).mean())
    selection = []
    for (event, position), group in frame.groupby(["event", "position"]):
        chosen = group.sort_values([predicted, "player_id"], ascending=[False, True]).head(5)
        oracle = group.nlargest(min(5, len(group)), "target_points")
        selection.append(
            {
                "event": int(str(event)),
                "position": str(position),
                "k": len(chosen),
                "selected_actual_points": float(chosen.target_points.sum()),
                "hindsight_top_k_points": float(oracle.target_points.sum()),
                "regret": float(oracle.target_points.sum() - chosen.target_points.sum()),
            }
        )
    result["top_five_by_position"] = selection
    result["top_pick_by_event"] = [
        {
            "event": int(str(event)),
            "player_id": int(
                group.sort_values([predicted, "player_id"], ascending=[False, True])
                .iloc[0]
                .player_id
            ),
            "selected_actual_points": float(
                group.sort_values([predicted, "player_id"], ascending=[False, True])
                .iloc[0]
                .target_points
            ),
            "hindsight_best_points": float(group.target_points.max()),
        }
        for event, group in frame.groupby("event")
    ]
    result["selection_semantics"] = (
        "Unconstrained diagnostic shortlists, not legal squads or transfer policies"
    )
    return result


def auxiliary_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "expected_minutes" in frame:
        observed = frame[["target_minutes", "expected_minutes"]].dropna()
        result["minutes_n"] = len(observed)
        result["minutes_mae"] = (
            float(abs(observed.expected_minutes - observed.target_minutes).mean())
            if len(observed)
            else None
        )
        result["minutes_bias"] = (
            float((observed.expected_minutes - observed.target_minutes).mean())
            if len(observed)
            else None
        )
    for name, threshold in [("appearance", 1), ("sixty", 60)]:
        key = name + "_probability"
        if key not in frame:
            continue
        observed = frame[[key, "target_minutes"]].dropna()
        probability = observed[key].to_numpy(dtype=float)
        y = (observed.target_minutes >= threshold).to_numpy(dtype=float)
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError("Invalid probability diagnostics")
        p = np.clip(probability, 1e-6, 1 - 1e-6)
        result[name] = {
            "n": len(y),
            "brier": float(np.mean((probability - y) ** 2)) if len(y) else None,
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
            if len(y)
            else None,
            "reliability_bins": [
                {
                    "lower": a / 5,
                    "n": int(mask.sum()),
                    "predicted": float(probability[mask].mean()),
                    "observed": float(y[mask].mean()),
                }
                for a in range(5)
                if (
                    mask := (
                        (probability >= a / 5)
                        & (probability < ((a + 1) / 5) if a < 4 else probability <= 1)
                    )
                ).any()
            ],
        }
    keys = ["q0.1", "q0.5", "q0.9"]
    if set(keys) <= set(frame):
        observed = frame[["target_points", *keys]].dropna()
        if len(observed):
            result["quantiles"] = forecast_metrics(
                observed.target_points,
                np.zeros(len(observed)),
                quantiles={q: observed[f"q{q}"] for q in [0.1, 0.5, 0.9]},
            )
            result["quantiles"].pop("mae")
            result["quantiles"].pop("rmse")
            result["quantiles"]["mean_interval_width"] = float(
                (observed["q0.9"] - observed["q0.1"]).mean()
            )
            result["quantiles"]["nominal_coverage"] = 0.8
            result["quantiles"]["qualification"] = (
                "Marginal research quantiles; coverage measured, no calibrated guarantee"
            )
    return result


def evaluate_panel(frame: pd.DataFrame, methods: list[str]) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("Observed evaluation rows required")
    if frame.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("Duplicate player fixture outcomes")
    # Sum fixture means and observed totals for event point comparisons. Do not sum quantiles.
    event = frame.groupby(["event", "player_id", "position"], as_index=False)[
        ["target_points", *methods]
    ].sum()
    comparators = [c for c in ["app_baseline_reconstructed", "rolling_points_5"] if c in frame]
    metrics = {name: point_metrics(event, name) for name in methods}
    for name in comparators:
        grouped = frame.groupby(["event", "player_id", "position"], as_index=False)[
            ["target_points", name]
        ].sum()
        metrics[name] = point_metrics(grouped, name)
    return {
        "event_point_metrics": metrics,
        "fixture_auxiliary_metrics": auxiliary_metrics(frame),
        "auxiliary_by_position": {
            str(p): auxiliary_metrics(g) for p, g in frame.groupby("position")
        },
        "auxiliary_by_origin_subset": {
            name: auxiliary_metrics(g)
            for name, g in [
                ("likely_starters", frame[frame.minutes_5 >= 60]),
                ("sparse_history", frame[frame.history_count < 3]),
            ]
            if len(g)
        },
        "residual_correlations": {
            a: {
                b: (
                    float((frame[a] - frame.target_points).corr(frame[b] - frame.target_points))
                    if (frame[a] - frame.target_points).nunique() > 1
                    and (frame[b] - frame.target_points).nunique() > 1
                    else None
                )
                for b in methods
            }
            for a in methods
        },
        "per_event": {
            str(e): {m: point_metrics(g, m) for m in methods} for e, g in event.groupby("event")
        },
        "by_position": {
            str(p): {m: point_metrics(g, m) for m in methods} for p, g in event.groupby("position")
        },
        "origin_subsets": {
            name: {m: forecast_metrics(g.target_points, g[m], events=g.event) for m in methods}
            for name, g in [
                ("likely_starters", frame[frame.minutes_5 >= 60]),
                ("sparse_history", frame[frame.history_count < 3]),
            ]
            if len(g)
        },
        "distinct_events": int(event.event.nunique()),
        "player_event_rows": len(event),
        "interpretation": "Dependent reconstructed historical blocks; no production promotion",
    }


def score_frozen_rows(
    rows: list[dict[str, Any]], actual: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    records = []
    for row in rows:
        stats = actual[row["player_id"]]["stats"]
        records.append(
            {
                **row,
                "predicted": row["expected_points"],
                "target_points": stats["total_points"],
                "target_minutes": stats["minutes"],
                "event": 0,
                "position": str(row.get("position", "unknown")),
            }
        )
    if not records:
        return {"n": 0}
    frame = pd.DataFrame(records)
    return {
        "points": point_metrics(frame, "predicted"),
        "auxiliary": auxiliary_metrics(frame),
        "by_position": {
            str(p): point_metrics(g, "predicted") for p, g in frame.groupby("position")
        },
    }
