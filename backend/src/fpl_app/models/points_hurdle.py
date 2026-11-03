"""Research mean: P(nonzero FPL points) × E(points | nonzero).

This is a points hurdle, not an appearance probability. Negative disciplinary
points at zero minutes are retained. Availability must not be applied again.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def fit_hurdle(
    train: pd.DataFrame,
    validation: pd.DataFrame | None,
    columns: list[str],
    categories: list[str],
    kwargs: dict[str, Any],
    iterations: int | dict[str, int],
    stopping_rounds: int,
    directory: Path,
) -> dict[str, int]:
    from catboost import CatBoostClassifier, CatBoostRegressor

    nonzero = train.target_points.ne(0)
    if nonzero.nunique() < 2 or not nonzero.any():
        raise ValueError("Points hurdle requires both zero and nonzero training labels")
    settings = {k: v for k, v in kwargs.items() if k not in {"loss_function", "allow_const_label"}}
    counts = (
        {"gate": iterations, "conditional": iterations}
        if isinstance(iterations, int)
        else iterations
    )
    gate = CatBoostClassifier(iterations=counts["gate"], loss_function="Logloss", **settings)
    conditional = CatBoostRegressor(
        iterations=counts["conditional"], loss_function="RMSE", allow_const_label=True, **settings
    )
    gate_eval, points_eval = {}, {}
    if validation is not None:
        valid_nonzero = validation.target_points.ne(0)
        if not valid_nonzero.any():
            raise ValueError("Nonzero validation labels required")
        gate_eval = {
            "eval_set": (validation[columns], valid_nonzero.astype(int)),
            "early_stopping_rounds": stopping_rounds,
        }
        points_eval = {
            "eval_set": (
                validation.loc[valid_nonzero, columns],
                validation.loc[valid_nonzero, "target_points"],
            ),
            "early_stopping_rounds": stopping_rounds,
        }
    gate.fit(train[columns], nonzero.astype(int), cat_features=categories, **gate_eval)
    conditional.fit(
        train.loc[nonzero, columns],
        train.loc[nonzero, "target_points"],
        cat_features=categories,
        **points_eval,
    )
    directory.mkdir(exist_ok=True, parents=True)
    gate.save_model(str(directory / "nonzero.cbm"))
    conditional.save_model(str(directory / "conditional.cbm"))
    original = gate.predict_proba(train[columns])[:, 1] * conditional.predict(train[columns])
    if not np.array_equal(original, predict_hurdle(directory, train, columns)):
        raise ValueError("Points hurdle checkpoint reload changed predictions")
    return {"gate": gate.tree_count_, "conditional": conditional.tree_count_}


def predict_hurdle(directory: Path, frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    from catboost import CatBoostClassifier, CatBoostRegressor

    gate, conditional = CatBoostClassifier(), CatBoostRegressor()
    gate.load_model(str(directory / "nonzero.cbm"))
    conditional.load_model(str(directory / "conditional.cbm"))
    return gate.predict_proba(frame[columns])[:, 1] * conditional.predict(frame[columns])
