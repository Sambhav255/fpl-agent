from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def chronological_folds(
    frame: pd.DataFrame, min_train_events: int = 5, validation_events: int = 2
) -> list[tuple[list[int], list[int]]]:
    if min_train_events < 1 or validation_events < 1:
        raise ValueError("invalid fold sizes")
    cutoffs = pd.to_datetime(frame["decision_cutoff"], utc=True)
    end = pd.to_datetime(frame["target_available_at"], utc=True)
    events = sorted(cutoffs.unique())
    folds = []
    for start in range(min_train_events, len(events), validation_events):
        val_dates = events[start : start + validation_events]
        val_start = val_dates[0]
        train = frame.index[(cutoffs < val_start) & (end < val_start)].tolist()
        val = frame.index[cutoffs.isin(val_dates)].tolist()
        if train and val:
            folds.append((train, val))
    return folds


def forecast_metrics(
    actual: Any,
    predicted: Any,
    probabilities: Any = None,
    appearance: Any = None,
    quantiles: dict[float, Any] | None = None,
    events: Any = None,
) -> dict[str, Any]:
    y, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if (
        y.shape != p.shape
        or y.ndim != 1
        or not len(y)
        or not np.isfinite(y).all()
        or not np.isfinite(p).all()
    ):
        raise ValueError("metrics require aligned finite vectors")
    residual = p - y
    result: dict[str, Any] = {
        "n": len(y),
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt(np.square(residual).mean())),
    }
    groups = np.zeros(len(y), dtype=int) if events is None else np.asarray(events)
    if groups.shape != y.shape:
        raise ValueError("event vector mismatch")
    ranks = []
    for event in np.unique(groups):
        mask = groups == event
        if mask.sum() > 1 and np.std(y[mask]) > 0 and np.std(p[mask]) > 0:
            ranks.append(float(pd.Series(y[mask]).rank().corr(pd.Series(p[mask]).rank())))
    result["event_mean_spearman"] = float(np.mean(ranks)) if ranks else None
    if probabilities is not None:
        probability = np.asarray(probabilities, dtype=float)
        observed = np.asarray(appearance, dtype=float)
        if (
            probability.shape != y.shape
            or observed.shape != y.shape
            or not np.isfinite(probability).all()
            or not np.isin(observed, [0, 1]).all()
            or ((probability < 0) | (probability > 1)).any()
        ):
            raise ValueError("invalid probability calibration inputs")
        result["appearance_brier"] = float(np.mean((probability - observed) ** 2))
        result["appearance_calibration"] = [
            {
                "lower": float(a),
                "upper": float(b),
                "n": int(mask.sum()),
                "predicted": float(probability[mask].mean()),
                "observed": float(observed[mask].mean()),
            }
            for a, b in zip(np.arange(0, 1, 0.2), np.arange(0.2, 1.01, 0.2))
            if (
                mask := ((probability >= a) & (probability <= b if b >= 1 else probability < b))
            ).any()
        ]
    if quantiles:
        keys = sorted(quantiles)
        q = np.stack([np.asarray(quantiles[k], dtype=float) for k in keys])
        if (
            q.shape != (len(keys), len(y))
            or not np.isfinite(q).all()
            or np.any(np.diff(q, axis=0) < 0)
            or not all(0 < k < 1 for k in keys)
        ):
            raise ValueError("invalid or crossing quantiles")
        result["pinball"] = {
            str(k): float(np.maximum(k * (y - q[i]), (k - 1) * (y - q[i])).mean())
            for i, k in enumerate(keys)
        }
        if len(keys) >= 2:
            result["interval_coverage"] = float(((y >= q[0]) & (y <= q[-1])).mean())
    return result


def fit_ensemble(validation: pd.DataFrame, model_columns: list[str]) -> dict[str, Any]:
    required = {"partition", "decision_cutoff", "train_target_end", "target_points", *model_columns}
    if not required <= set(validation) or set(validation["partition"]) != {"validation"}:
        raise ValueError("weights require validation-only out-of-fold forecasts")
    if not model_columns or len(set(model_columns)) != len(model_columns):
        raise ValueError("invalid model columns")
    if (
        pd.to_datetime(validation["train_target_end"], utc=True)
        >= pd.to_datetime(validation["decision_cutoff"], utc=True)
    ).any():
        raise ValueError("forecast training overlaps validation")
    x = validation[model_columns].to_numpy(dtype=float)
    y = validation["target_points"].to_numpy(dtype=float)
    if len(y) < 2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("insufficient finite validation forecasts")
    opt = minimize(
        lambda w: np.mean((x @ w - y) ** 2),
        np.ones(len(model_columns)) / len(model_columns),
        bounds=[(0, 1)] * len(model_columns),
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
        method="SLSQP",
    )
    if not opt.success or not np.isclose(opt.x.sum(), 1) or np.any(opt.x < -1e-8):
        raise ValueError("ensemble optimisation failed")
    best = float(min(np.mean((x[:, i] - y) ** 2) for i in range(x.shape[1])))
    blend = float(np.mean((x @ opt.x - y) ** 2))
    return {
        "weights": dict(zip(model_columns, map(float, opt.x))),
        "validation_mse": blend,
        "best_individual_mse": best,
        "activation_eligible": blend < best - 1e-8,
        "status": "evaluated",
        "warning": "Validation fit only; held-out evaluation still required",
    }


def block_difference(
    actual: Any, first: Any, second: Any, events: Any, seed: int = 42, draws: int = 1000
) -> dict[str, Any]:
    y, a, b, e = map(np.asarray, (actual, first, second, events))
    if not (y.shape == a.shape == b.shape == e.shape) or draws < 1:
        raise ValueError("invalid block inputs")
    differences = np.array(
        [
            np.mean(np.abs(a[e == g] - y[e == g]) - np.abs(b[e == g] - y[e == g]))
            for g in np.unique(e)
        ]
    )
    if len(differences) < 2 or not np.isfinite(differences).all():
        raise ValueError("at least two finite event blocks required")
    rng = np.random.default_rng(seed)
    means = rng.choice(differences, (draws, len(differences)), replace=True).mean(axis=1)
    return {
        "event_blocks": len(differences),
        "mean_mae_difference": float(differences.mean()),
        "bootstrap_p025": float(np.quantile(means, 0.025)),
        "bootstrap_p975": float(np.quantile(means, 0.975)),
        "seed": seed,
    }
