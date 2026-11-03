"""Typed binary heads and model-bound calibration for football opportunity outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit

from fpl_app.features.football import CATEGORICAL, FEATURE_VERSION, FEATURES

BINARY_HEADS = {"appearance", "sixty", "start"}


class ConstantProbability:
    """Beta(1,1) posterior mean when a binary head cannot be estimated."""

    def __init__(self, probability: float):
        self.probability = probability

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), self.probability)


def probability(model: Any, frame: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        classes = list(model.classes_)
        if set(classes) != {0, 1}:
            raise ValueError("binary classifier requires explicit classes 0 and 1")
        return np.asarray(model.predict_proba(frame))[:, classes.index(1)]
    return np.asarray(model.predict(frame), dtype=float)


def fit_head(
    head: str,
    frame: pd.DataFrame,
    target: str,
    validation: pd.DataFrame | None = None,
    *,
    binary: bool = True,
) -> tuple[Any, dict[str, Any]]:
    from catboost import CatBoostClassifier, CatBoostRegressor

    valid = frame[frame[target].notna()]
    metadata: dict[str, Any] = {
        "label": target,
        "feature_version": FEATURE_VERSION,
        "sample_size": len(valid),
        "missing_labels": int(frame[target].isna().sum()),
        "calibration": "unavailable",
        "probability_semantics": "unconditional_per_fixture" if head in BINARY_HEADS else None,
    }
    if head in BINARY_HEADS and binary:
        if not valid[target].isin([0, 1]).all():
            raise ValueError("binary head labels must be 0, 1 or missing")
        if valid.empty:
            return None, {**metadata, "kind": "unavailable", "reason": "no observed labels"}
        if valid[target].nunique() < 2:
            prior = float((valid[target].sum() + 1) / (len(valid) + 2))
            return ConstantProbability(prior), {
                **metadata,
                "kind": "constant_probability",
                "probability": prior,
                "objective": "Beta(1,1) prior",
                "reason": "one class training fold",
            }
        loss = "Logloss"
        cls = CatBoostClassifier
        metadata.update(kind="classifier", class_mapping=[0, 1])
    else:
        if valid.empty:
            return None, {**metadata, "kind": "unavailable", "reason": "no observed labels"}
        loss = f"Quantile:alpha={int(head[1:]) / 100}" if head.startswith("q") else "RMSE"
        cls = CatBoostRegressor
        metadata.update(kind="regressor")
    kwargs: dict[str, Any] = {
        "iterations": 180,
        "depth": 5,
        "learning_rate": 0.06,
        "loss_function": loss,
        "random_seed": 43,
        "thread_count": 2,
        "verbose": False,
        "allow_writing_files": False,
    }
    if cls is CatBoostRegressor:
        kwargs["allow_const_label"] = True
    model = cls(**kwargs)
    fit_kwargs: dict[str, Any] = {"cat_features": CATEGORICAL}
    if validation is not None:
        held_out = validation[validation[target].notna()]
        if not held_out.empty:
            fit_kwargs.update(
                eval_set=(held_out[FEATURES], held_out[target]), early_stopping_rounds=25
            )
    model.fit(valid[FEATURES], valid[target], **fit_kwargs)
    return model, {**metadata, "objective": loss}


def load_head(path: Path, metadata: dict[str, Any]) -> Any:
    from catboost import CatBoostClassifier, CatBoostRegressor

    kind = metadata["kind"]
    if kind == "constant_probability":
        return ConstantProbability(metadata["probability"])
    if kind == "unavailable":
        return None
    if kind not in {"classifier", "regressor"}:
        raise ValueError(f"unsupported head kind: {kind}")
    model = CatBoostClassifier() if kind == "classifier" else CatBoostRegressor()
    model.load_model(str(path))
    if kind == "classifier" and list(model.classes_) != metadata["class_mapping"]:
        raise ValueError("saved classifier class mapping mismatch")
    return model


def fit_sigmoid(prediction: np.ndarray, target: pd.Series, **binding: Any) -> dict[str, Any]:
    valid = target.notna().to_numpy()
    y = target.to_numpy(dtype=float)[valid]
    base = {**binding, "sample_size": len(y), "positive_count": int(y.sum())}
    if len(y) < 20 or len(np.unique(y)) < 2:
        return {
            **base,
            "kind": "unavailable",
            "reason": "insufficient two-class calibration labels",
        }
    x = logit(np.clip(prediction[valid], 1e-6, 1 - 1e-6))

    # Conservative ridge toward identity; calibration never sees outer labels.
    def loss(theta: np.ndarray) -> float:
        z = theta[0] * x + theta[1]
        return float(
            np.logaddexp(0, z).sum() - (y * z).sum() + 5 * ((theta[0] - 1) ** 2 + theta[1] ** 2)
        )

    fitted = minimize(loss, [1.0, 0.0], method="L-BFGS-B", bounds=[(0, 5), (-5, 5)])
    if not fitted.success:
        return {**base, "kind": "unavailable", "reason": "sigmoid optimization failed"}
    return {**base, "kind": "sigmoid", "slope": float(fitted.x[0]), "intercept": float(fitted.x[1])}


def calibrate(prediction: np.ndarray, value: Any) -> np.ndarray:
    if isinstance(value, (float, int)):
        return np.clip(prediction + value, 0, 1)  # legacy additive calibration
    if value.get("kind") == "sigmoid":
        return expit(
            value["slope"] * logit(np.clip(prediction, 1e-6, 1 - 1e-6)) + value["intercept"]
        )
    return np.clip(prediction, 0, 1)
