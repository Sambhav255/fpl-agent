from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import chronological_folds, forecast_metrics
from fpl_app.features.pipeline import NUMERIC_FEATURES, fingerprint, immutable_json


def data_dir() -> Path:
    root = Path(__file__).resolve().parents[4]
    configured = Path(os.environ.get("DATA_DIR", str(root / "data")))
    return configured if configured.is_absolute() else root / "backend" / configured


def audited_panel(
    dataset: Path, allow_approximate: bool = False, drop_missing_targets: bool = True
) -> tuple[pd.DataFrame, dict[str, Any]]:
    audit_path = dataset.parent / "audit.json"
    if not dataset.is_file() or not audit_path.is_file():
        raise ValueError("Training unavailable: real feature Parquet and audit.json required")
    audit = json.loads(audit_path.read_text())
    if audit.get("data_mode") != "live":
        raise ValueError(
            "Training unavailable: synthetic/demo panel cannot create trained artifacts"
        )
    if audit.get("replay_timing") != "verified" and not (
        allow_approximate and audit.get("replay_timing") == "conservative_assumed"
    ):
        raise ValueError(
            "Training unavailable: verified availability audit required; explicit --allow-approximate for conservative archive experiment"
        )
    frame = pd.read_parquet(dataset)
    required = {
        "decision_cutoff",
        "target_available_at",
        "target_points",
        "canonical_player_id",
        "fixture_id",
        *NUMERIC_FEATURES,
    }
    if not required <= set(frame) or frame.empty:
        raise ValueError("Training unavailable: feature/target schema incomplete")
    if frame.duplicated(["season", "canonical_player_id", "fixture_id"]).any():
        raise ValueError("duplicate player fixture targets")
    from .panel_audit import bind_panel_audit, filter_targets

    bind_panel_audit(frame, audit, hashlib.sha256(dataset.read_bytes()).hexdigest())
    return filter_targets(frame, drop_missing_targets), audit


def split_panel(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cutoffs = pd.to_datetime(frame["decision_cutoff"], utc=True)
    known = pd.to_datetime(frame["target_available_at"], utc=True)
    events = sorted(cutoffs.unique())
    if len(events) < 8:
        raise ValueError("Training unavailable: at least 8 chronological events required")
    test_start = events[-2]
    validation_start = events[-6]
    train = frame[(cutoffs < validation_start) & (known < validation_start)].copy()
    validation = frame[
        (cutoffs >= validation_start) & (cutoffs < test_start) & (known < test_start)
    ].copy()
    test = frame[cutoffs >= test_start].copy()
    if any(len(part) < 10 for part in (train, validation, test)):
        raise ValueError("Training unavailable: purged partitions too small")
    return train, validation, test


def train_catboost(
    dataset: Path,
    output: Path,
    allow_approximate: bool = False,
    seed: int = 42,
    iterations: int = 120,
) -> Path:
    from catboost import CatBoostClassifier, CatBoostRegressor

    frame, audit = audited_panel(dataset, allow_approximate)
    train, validation, test = split_panel(frame)
    checksum = hashlib.sha256(dataset.read_bytes()).hexdigest()
    run_id = fingerprint(
        {"dataset": checksum, "model": "catboost", "seed": seed, "iterations": iterations}
    )[:24]
    published = output / "catboost" / run_id
    from .publication import open_model_run, publish_model_run, reuse_model_run

    if reuse_model_run(published, checksum):
        return published
    dest, complete = open_model_run(published)
    if complete:
        return published
    kwargs = {
        "iterations": iterations,
        "depth": 4,
        "learning_rate": 0.05,
        "random_seed": seed,
        "thread_count": 2,
        "verbose": False,
        "allow_writing_files": False,
    }
    model = CatBoostRegressor(loss_function="RMSE", **kwargs)
    model.fit(
        train[NUMERIC_FEATURES],
        train["target_points"],
        eval_set=(validation[NUMERIC_FEATURES], validation["target_points"]),
        early_stopping_rounds=20,
    )
    model.save_model(str(dest / "mean.cbm"))
    artifacts = ["mean.cbm"]
    # Every label is unconditional; no subsequent availability scaling of mean.
    probabilities: dict[str, np.ndarray[Any, Any]] = {}
    from .labels import minute_appearance_labels

    auxiliary_notes = []
    for name in ("appearance", "minutes_60", "start"):
        if "target_minutes" not in train or (name == "start" and "target_start" not in train):
            auxiliary_notes.append(f"{name}: missing label")
            continue
        if name == "appearance":
            y_train = minute_appearance_labels(train["target_minutes"])
            y_val = minute_appearance_labels(validation["target_minutes"])
        elif name == "minutes_60":
            y_train = minute_appearance_labels(train["target_minutes"], 60, at_least=True)
            y_val = minute_appearance_labels(validation["target_minutes"], 60, at_least=True)
        else:
            y_train = pd.to_numeric(train["target_start"], errors="coerce")
            y_val = pd.to_numeric(validation["target_start"], errors="coerce")
        known_train, known_val = y_train.notna(), y_val.notna()
        if bool((~known_train).any()) or bool((~known_val).any()):
            auxiliary_notes.append(f"{name}: unknown labels excluded")
        y_fit = y_train.loc[known_train].astype(int)
        y_eval = y_val.loc[known_val].astype(int)
        if len(y_fit) < 2 or int(y_fit.nunique()) < 2 or len(y_eval) == 0:
            auxiliary_notes.append(f"{name}: incomplete/single-class labels")
            continue
        clf = CatBoostClassifier(loss_function="Logloss", **kwargs)
        clf.fit(
            train.loc[known_train, NUMERIC_FEATURES],
            y_fit,
            eval_set=(validation.loc[known_val, NUMERIC_FEATURES], y_eval),
            early_stopping_rounds=20,
        )
        namefile = f"{name}.cbm"
        clf.save_model(str(dest / namefile))
        artifacts.append(namefile)
        probabilities[name] = clf.predict_proba(test[NUMERIC_FEATURES])[:, 1]
    if "appearance" in probabilities:
        for name in ("minutes_60", "start"):
            if name in probabilities:
                probabilities[name] = np.minimum(probabilities[name], probabilities["appearance"])
    predictions = test[
        [
            "season",
            "event",
            "canonical_player_id",
            "fixture_id",
            "decision_cutoff",
            "target_points",
            "target_minutes",
        ]
    ].copy()
    predictions["predicted_points"] = model.predict(test[NUMERIC_FEATURES])
    # Predeclared recent points baseline; training-only mean for cold starts.
    predictions["baseline_points"] = test["mean_points_5"].fillna(
        float(train["target_points"].mean())
    )
    for name, values in probabilities.items():
        predictions[f"{name}_probability"] = values
    predictions["partition"] = "test"
    predictions.to_parquet(dest / "test_predictions.parquet", index=False)
    artifacts.append("test_predictions.parquet")
    pd.DataFrame(
        {"feature": NUMERIC_FEATURES, "importance": model.get_feature_importance()}
    ).to_parquet(dest / "feature_importance.parquet", index=False)
    artifacts.append("feature_importance.parquet")
    manifest = {
        "run_id": run_id,
        "model_family": "catboost",
        "model_status": "trained",
        "data_mode": "live",
        "dataset_sha256": checksum,
        "dataset_path": str(dataset.resolve()),
        "snapshot_id": audit.get("snapshot_id"),
        "feature_columns": NUMERIC_FEATURES,
        "replay_timing": audit["replay_timing"],
        "seed": seed,
        "iterations": iterations,
        "training_cutoff": max(train["decision_cutoff"]),
        "train_target_end": max(train["target_available_at"]),
        "validation_cutoffs": sorted(validation["decision_cutoff"].unique().tolist()),
        "test_cutoffs": sorted(test["decision_cutoff"].unique().tolist()),
        "partitions": {"train": len(train), "validation": len(validation), "test": len(test)},
        "artifacts": {
            name: hashlib.sha256((dest / name).read_bytes()).hexdigest() for name in artifacts
        },
        "created_at": datetime.now(UTC).isoformat(),
        "limitations": [
            *audit.get("limitations", []),
            *auxiliary_notes,
            "Auxiliary probabilities assessed on held-out set, not post-hoc calibrated; no active promotion",
            "Mean unconditional on appearance; no quantiles; feature importance is attribution, not causation",
        ],
    }
    immutable_json(dest / "manifest.json", manifest)
    return publish_model_run(dest, published)


def evaluate_run(run: Path) -> dict[str, Any]:
    meta = json.loads((run / "manifest.json").read_text())
    forecasts = pd.read_parquet(run / "test_predictions.parquet")
    metrics = forecast_metrics(
        forecasts["target_points"],
        forecasts["predicted_points"],
        events=forecasts["event"].to_numpy(),
    )
    if "appearance_probability" in forecasts and "target_minutes" in forecasts:
        parsed = pd.to_numeric(forecasts["target_minutes"], errors="coerce")
        known = np.isfinite(parsed.to_numpy(dtype="float64"))
        if bool(known.any()):
            subset = forecasts.loc[known]
            minutes = pd.to_numeric(subset["target_minutes"], errors="coerce")
            appearance_metrics = forecast_metrics(
                subset["target_points"],
                subset["predicted_points"],
                probabilities=subset["appearance_probability"].to_numpy(),
                appearance=(minutes > 0).astype(int).to_numpy(),
                events=subset["event"].to_numpy(),
            )
            metrics["appearance_brier"] = appearance_metrics["appearance_brier"]
            metrics["appearance_calibration"] = appearance_metrics["appearance_calibration"]
    baseline = forecast_metrics(
        forecasts["target_points"],
        forecasts["baseline_points"],
        events=forecasts["event"].to_numpy(),
    )
    result = {
        "run_id": meta["run_id"],
        "dataset_sha256": meta["dataset_sha256"],
        "partition": "test",
        "metrics": metrics,
        "baseline_metrics": baseline,
        "replay_timing": meta["replay_timing"],
        "active": False,
        "evaluation_kind": "deadline_verified"
        if meta["replay_timing"] == "verified"
        else "retrospective_unverified",
        "strict_release_eligible": False,
        "limitations": meta["limitations"],
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
    path = run / "evaluation.json"
    if path.exists():
        return json.loads(path.read_text())
    immutable_json(path, result)
    return result


def catboost_predict(run: Path, features: pd.DataFrame) -> pd.DataFrame:
    from catboost import CatBoostClassifier, CatBoostRegressor

    meta = json.loads((run / "manifest.json").read_text())
    for name, checksum in meta["artifacts"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("artifact checksum mismatch")
    x = features[meta["feature_columns"]]
    model = CatBoostRegressor()
    model.load_model(str(run / "mean.cbm"))
    result = pd.DataFrame({"expected_points": model.predict(x)}, index=features.index)
    for name in ("appearance", "start", "minutes_60"):
        if (run / f"{name}.cbm").exists():
            classifier = CatBoostClassifier()
            classifier.load_model(str(run / f"{name}.cbm"))
            result[f"{name}_probability"] = classifier.predict_proba(x)[:, 1]
    if "appearance_probability" in result:
        for column in ("start_probability", "minutes_60_probability"):
            if column in result:
                result[column] = np.minimum(result[column], result["appearance_probability"])
    return result


def validation_forecasts(
    dataset: Path, allow_approximate: bool = False, seed: int = 42
) -> pd.DataFrame:
    from catboost import CatBoostRegressor

    frame, _ = audited_panel(dataset, allow_approximate)
    # Final test events are excluded from tuning and blend weights.
    _, _, test = split_panel(frame)
    development = frame[
        pd.to_datetime(frame["decision_cutoff"], utc=True)
        < pd.to_datetime(test["decision_cutoff"], utc=True).min()
    ]
    output = []
    for train_ids, val_ids in chronological_folds(development):
        training, val = frame.loc[train_ids], frame.loc[val_ids]
        model = CatBoostRegressor(
            iterations=60,
            depth=4,
            loss_function="RMSE",
            random_seed=seed,
            verbose=False,
            thread_count=2,
            allow_writing_files=False,
        )
        model.fit(training[NUMERIC_FEATURES], training["target_points"])
        part = val[["decision_cutoff", "event", "target_points"]].copy()
        part["catboost"] = model.predict(val[NUMERIC_FEATURES])
        part["baseline"] = val["mean_points_5"].fillna(float(training["target_points"].mean()))
        part["train_target_end"] = max(training["target_available_at"])
        part["partition"] = "validation"
        output.append(part)
    if not output:
        raise ValueError("no purged validation folds")
    return pd.concat(output, ignore_index=True)
