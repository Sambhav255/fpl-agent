"""Fixed linear/LightGBM research comparison on an existing verified rolling panel.

No serving refit or promotion. Optional LightGBM imports occur only within its fit.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import forecast_metrics
from fpl_app.features.deadline import ATTACK, CONTEXT, DEFENCE, OPPORTUNITY
from fpl_app.features.football import CATEGORICAL, FEATURES
from fpl_app.models.rolling_experiments import _completed, _json, _sha, chronological_folds
from fpl_app.models.training import data_dir
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow

COLUMNS = FEATURES + ATTACK + DEFENCE + CONTEXT + OPPORTUNITY
METHODS = ["ridge", "lightgbm"]


def protocol(reference: Path) -> dict[str, Any]:
    report = json.loads((reference / "report.json").read_text())
    return {
        "version": "simple-expanding-v1",
        "registered_at": utcnow(),
        "reference_directory": str(reference.resolve()),
        "reference_report_sha256": _sha(reference / "report.json"),
        "collection_id": report["collection_id"],
        "features": COLUMNS,
        "methods": METHODS,
        "ridge_alpha": 10.0,
        "lightgbm": {
            "objective": "regression",
            "n_estimators": 250,
            "num_leaves": 15,
            "max_depth": 4,
            "learning_rate": 0.04,
            "min_child_samples": 30,
            "reg_lambda": 10.0,
            "random_state": 43,
            "n_jobs": 2,
            "deterministic": True,
            "force_col_wise": True,
            "verbosity": -1,
        },
        "early_stopping_rounds": 30,
        "selection": "Fixed methods and hyperparameters; validation selects boosting iteration only",
        "hypothesis": "Regularized linear and modest leaf-wise trees provide complementary unconditional point forecasts",
        "interpretation": "Exploratory previously inspected historical weeks, not prospective confirmation",
        "active": False,
    }


def training_input(store: Store, payload: dict[str, Any]) -> str:
    spec = payload["protocol"]
    reference = Path(spec["reference_directory"])
    expected = protocol(reference)
    if {k: v for k, v in spec.items() if k != "registered_at"} != {
        k: v for k, v in expected.items() if k != "registered_at"
    }:
        raise ValueError("Unknown simple comparison protocol")
    if store.get("simple_experiment_protocol", fingerprint(spec)) != spec:
        raise ValueError("Register fixed comparison before fitting")
    report = json.loads((reference / "report.json").read_text())
    for path, digest in report["files"].items():
        if _sha(reference / path) != digest:
            raise ValueError("Reference rolling artifact checksum mismatch")
    collection = load_collection(store, spec["collection_id"])
    if report["collection_sha256"] != collection["envelope_sha256"]:
        raise ValueError("Reference collection checksum mismatch")
    require_scored_collection(store, collection)
    return fingerprint(
        {
            "protocol": spec,
            "implementation": _sha(Path(__file__)),
            "eligibility": _sha(Path(__file__).with_name("training_eligibility.py")),
            "collection": collection["envelope_sha256"],
            "dependency_lock": _sha(Path(__file__).parents[3] / "uv.lock"),
            "shared_code": {
                name: _sha(Path(__file__).parents[1] / name)
                for name in (
                    "evaluation/metrics.py",
                    "models/rolling_experiments.py",
                    "models/training_eligibility.py",
                )
            },
        }
    )


def fit_preprocessing(frame: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    """Fit only on a fold's training data, including vocabulary and missing medians."""
    numeric = [c for c in columns if c not in CATEGORICAL]
    x = frame[numeric].to_numpy(dtype=float)
    medians = [
        float(np.nanmedian(x[:, i])) if np.isfinite(x[:, i]).any() else 0.0
        for i in range(len(numeric))
    ]
    filled = np.where(np.isfinite(x), x, np.array(medians))
    scale = filled.std(axis=0)
    return {
        "columns": columns,
        "numeric": numeric,
        "medians": medians,
        "means": filled.mean(axis=0).tolist(),
        "scales": np.where(scale > 1e-10, scale, 1.0).tolist(),
        "categories": {
            c: sorted(frame[c].astype(str).unique().tolist()) for c in columns if c in CATEGORICAL
        },
        "unknown_categories": "all-zero one-hot; no vocabulary fitted on validation or test",
    }


def transform(frame: pd.DataFrame, metadata: dict[str, Any]) -> np.ndarray:
    x = frame[metadata["numeric"]].to_numpy(dtype=float)
    missing = ~np.isfinite(x)
    filled = np.where(missing, np.array(metadata["medians"]), x)
    result = [(filled - metadata["means"]) / metadata["scales"], missing.astype(float)]
    for column, levels in metadata["categories"].items():
        values = frame[column].astype(str).to_numpy()
        result.append(np.column_stack([values == level for level in levels]).astype(float))
    return np.concatenate(result, axis=1)


def fit_ridge(x: np.ndarray, target: np.ndarray, alpha: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.solve(design.T @ design + penalty, design.T @ target)


def _fit_unit(
    root: Path,
    identity: str,
    spec: dict[str, Any],
    fold: dict[str, Any],
    panel: pd.DataFrame,
    method: str,
) -> pd.DataFrame:
    directory = root / fold["fold_id"] / method
    unit = fingerprint({"identity": identity, "fold": fold, "method": method})
    if _completed(directory, unit) is not None:
        return pd.read_parquet(directory / "predictions.parquet")
    train, validation, test = [
        panel.loc[fold["indices"][k]].copy() for k in ("train", "validation", "test")
    ]
    preprocessing = fit_preprocessing(train, spec["features"])
    x, xv, xt = [transform(rows, preprocessing) for rows in (train, validation, test)]
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = directory.parent / (".attempt-" + uuid4().hex)
    staging.mkdir()
    try:
        _json(staging / "preprocessing.json", preprocessing)
        if method == "ridge":
            coefficients = fit_ridge(
                x, train.target_points.to_numpy(dtype=float), spec["ridge_alpha"]
            )
            _json(
                staging / "ridge.json",
                {
                    "coefficients": coefficients.tolist(),
                    "alpha": spec["ridge_alpha"],
                    "target": "unconditional fixture points, signed",
                },
            )
            loaded = np.asarray(json.loads((staging / "ridge.json").read_text())["coefficients"])
            prediction = np.column_stack([np.ones(len(xt)), xt]) @ loaded
            selected = 1
        elif method == "lightgbm":
            try:
                import lightgbm as lgb
            except ImportError as exc:
                raise ValueError(
                    "LightGBM research extra unavailable; install backend[research]"
                ) from exc
            model = lgb.LGBMRegressor(**spec["lightgbm"])
            model.fit(
                x,
                train.target_points,
                eval_set=[(xv, validation.target_points)],
                callbacks=[lgb.early_stopping(spec["early_stopping_rounds"], verbose=False)],
            )
            selected = model.best_iteration_
            model.booster_.save_model(str(staging / "model.txt"))
            prediction = np.asarray(
                lgb.Booster(model_file=str(staging / "model.txt")).predict(xt, num_threads=2)
            )
            if not np.allclose(prediction, model.predict(xt), rtol=0, atol=1e-12):
                raise ValueError("LightGBM save/load parity failed")
            _json(staging / "dependency.json", {"lightgbm": lgb.__version__})
        else:
            raise ValueError("Unknown registered method")
        if len(prediction) != len(test) or not np.isfinite(prediction).all():
            raise ValueError("Complete finite predictions required")
        result = test.copy()
        result["predicted_points"] = prediction
        result["model"] = method
        result["selected_iterations"] = selected
        result.to_parquet(staging / "predictions.parquet", index=False)
        _json(
            staging / "complete.json",
            {
                "input_fingerprint": unit,
                "files": {
                    str(p.relative_to(staging)): _sha(p) for p in staging.rglob("*") if p.is_file()
                },
            },
        )
        staging.rename(directory)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def train_job(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    spec = payload["protocol"]
    identity = training_input(store, payload)
    reference = Path(spec["reference_directory"])
    root = data_dir() / "models/simple_experiments" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    _json(root / "protocol.json", spec)
    _json(root / "input.json", {"fingerprint": identity})
    implementation = root / "implementation.py"
    if implementation.exists() and _sha(implementation) != _sha(Path(__file__)):
        raise ValueError("Saved implementation mismatch")
    if not implementation.exists():
        implementation.write_bytes(Path(__file__).read_bytes())
    panel = pd.read_parquet(reference / "historical_features.parquet")
    reference_spec = json.loads((reference / "protocol.json").read_text())
    folds = chronological_folds(
        panel, reference_spec["as_of"], reference_spec["minimum_training_events"]
    )
    if folds != json.loads((reference / "splits.json").read_text()):
        raise ValueError("Reference fold contract differs")
    _json(root / "splits.json", folds)
    outputs = []
    for fold in folds:
        for method in spec["methods"]:
            rows = _fit_unit(root, identity, spec, fold, panel, method)
            rows["fold_id"] = fold["fold_id"]
            outputs.append(rows)
    predicted = pd.concat(outputs, ignore_index=True)
    predicted.to_parquet(root / "outer_predictions.parquet", index=False)
    reference_outer = pd.read_parquet(reference / "outer_predictions.parquet")
    metrics = {
        method: forecast_metrics(group.target_points, group.predicted_points, events=group.event)
        for method, group in predicted.groupby("model")
    }
    comparators = [
        "app_baseline_reconstructed",
        "rolling_points_5",
        "full_second_seed",
        "opportunity_multiscale",
        "points_hurdle",
    ]
    for name in comparators:
        metrics[name] = forecast_metrics(
            reference_outer.target_points, reference_outer[name], events=reference_outer.event
        )
    for method, rows in predicted.groupby("model"):
        if (
            rows[["player_id", "fixture_id"]].to_records(index=False).tolist()
            != reference_outer[["player_id", "fixture_id"]].to_records(index=False).tolist()
        ):
            raise ValueError("Matched comparator row identity differs for " + str(method))
    report = {
        "experiment_id": identity,
        "registered_at": spec["registered_at"],
        "interpretation": spec["interpretation"],
        "metrics": metrics,
        "per_fold": {
            str(key): {
                str(method): forecast_metrics(
                    rows.target_points, rows.predicted_points, events=rows.event
                )
                for method, rows in group.groupby("model")
            }
            for key, group in predicted.groupby("fold_id")
        },
        "dependency_lock_sha256": _sha(Path(__file__).parents[3] / "uv.lock"),
        "outer_events": sorted(int(i) for i in predicted.event.unique()),
        "rows_per_model": int(len(predicted) / len(spec["methods"])),
        "active": False,
        "champion_promoted": False,
        "files": {
            str(p.relative_to(root)): _sha(p)
            for p in root.rglob("*")
            if p.is_file() and p.name != "report.json"
        },
    }
    _json(root / "report.json", report)
    return {**report, "_artifacts": [("simple_experiment", identity, report)]}
