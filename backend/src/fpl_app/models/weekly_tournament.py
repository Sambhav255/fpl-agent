"""Fixed weekly all-player research competition; independent of manager finances.

Never promotes a model. Historical folds retain collection reconstruction limits.
Only genuine pre-deadline predictions become prospective benchmark streams.
"""

from __future__ import annotations

import json
import shutil
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from fpl_app.features.deadline import enriched_panels
from fpl_app.learning.forecast_benchmark import make_benchmark
from fpl_app.models.opportunity import calibrate, fit_sigmoid
from fpl_app.models.rolling_experiments import _completed, _json, _sha, chronological_folds
from fpl_app.models.simple_experiments import COLUMNS, fit_preprocessing, transform
from fpl_app.models.training import data_dir
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow

METHODS = ["ridge", "extra_trees", "hist_gradient", "catboost", "catboost_recency", "lightgbm"]


def protocol(collection_id: str, study_id: str) -> dict[str, Any]:
    return {
        "version": "weekly-tournament-v1",
        "registered_at": utcnow(),
        "collection_id": collection_id,
        "study_id": study_id,
        "methods": METHODS,
        "features": COLUMNS,
        "seed": 43,
        "iterations": 180,
        "trees": 160,
        "minimum_training_events": 3,
        "recency_decay": 0.85,
        "primary_metric": "event_point_rmse",
        "secondary_metrics": [
            "mae",
            "bias",
            "spearman",
            "top_k",
            "minutes_mae",
            "appearance_brier",
            "sixty_brier",
            "log_loss",
            "pinball",
            "coverage",
        ],
        "point_semantics": "unconditional_signed_mean",
        "historical_timing": "reconstructed_kickoff_plus_one_day",
        "promotion": False,
        "ensemble": "fixed_equal_weight_point_means",
    }


def training_input(store: Store, payload: dict[str, Any]) -> str:
    spec = payload["protocol"]
    expected = protocol(spec["collection_id"], spec["study_id"])
    if {k: v for k, v in spec.items() if k != "registered_at"} != {
        k: v for k, v in expected.items() if k != "registered_at"
    }:
        raise ValueError("Unregistered tournament settings")
    if store.get("weekly_tournament_protocol", fingerprint(spec)) != spec:
        raise ValueError("Register before fitting")
    collection = load_collection(store, spec["collection_id"])
    bootstrap_ref = next(s for s in collection["sources"] if s["resource"] == "bootstrap-static/")
    universe = {p["id"] for p in json.loads(store.snapshot(bootstrap_ref["id"])["raw"])["elements"]}
    if set(collection["player_ids"]) != universe:
        raise ValueError("Weekly tournament requires the full captured bootstrap universe")
    require_scored_collection(store, collection)
    base = Path(__file__).parents[1]
    names = [
        "models/weekly_tournament.py",
        "models/news_sensitivity.py",
        "models/simple_experiments.py",
        "models/rolling_experiments.py",
        "models/training_eligibility.py",
        "models/opportunity.py",
        "features/deadline.py",
        "features/football.py",
        "evaluation/tournament.py",
        "evaluation/metrics.py",
        "features/pipeline.py",
        "models/baseline.py",
        "providers/__init__.py",
        "learning/forecast_benchmark.py",
    ]
    return fingerprint(
        {
            "protocol": spec,
            "collection": collection["envelope_sha256"],
            "code": {n: _sha(base / n) for n in names},
            "lock": _sha(base.parents[1] / "uv.lock"),
        }
    )


def _point_model(method: str, spec: dict):
    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge

    if method == "ridge":
        return Ridge(alpha=10)
    if method == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=spec["trees"],
            min_samples_leaf=15,
            max_features=0.8,
            n_jobs=2,
            random_state=spec["seed"],
        )
    if method == "hist_gradient":
        return HistGradientBoostingRegressor(
            max_iter=spec["iterations"],
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=10,
            early_stopping=False,
            random_state=spec["seed"],
        )
    if method.startswith("catboost"):
        from catboost import CatBoostRegressor

        return CatBoostRegressor(
            iterations=spec["iterations"],
            depth=4,
            l2_leaf_reg=10,
            learning_rate=0.04,
            loss_function="RMSE",
            thread_count=2,
            random_seed=spec["seed"],
            verbose=False,
            allow_writing_files=False,
        )
    if method == "lightgbm":
        from lightgbm import LGBMRegressor

        return LGBMRegressor(
            n_estimators=spec["iterations"],
            num_leaves=15,
            max_depth=4,
            learning_rate=0.04,
            min_child_samples=30,
            reg_lambda=10,
            n_jobs=2,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
            random_state=spec["seed"],
        )
    raise ValueError("Unknown point model")


def _unit(
    root: Path,
    identity: str,
    label: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    spec: dict,
) -> pd.DataFrame:
    import joblib
    from sklearn.ensemble import (
        ExtraTreesClassifier,
        ExtraTreesRegressor,
        HistGradientBoostingRegressor,
    )

    directory = root / label
    key = fingerprint({"identity": identity, "unit": label})
    if _completed(directory, key) is not None:
        return pd.read_parquet(directory / "predictions.parquet")
    staging = root / (".attempt-" + uuid4().hex)
    staging.mkdir(parents=True)
    try:
        preprocessing = fit_preprocessing(train, spec["features"])
        x, xv, xt = [transform(f, preprocessing) for f in (train, validation, test)]
        _json(staging / "preprocessing.json", preprocessing)
        result = test.copy().reset_index(drop=True)
        for method in spec["methods"]:
            model = _point_model(method, spec)
            weight = (
                spec["recency_decay"] ** (train.event.max() - train.event.to_numpy())
                if method == "catboost_recency"
                else None
            )
            model.fit(x, train.target_points, sample_weight=weight)
            joblib.dump(model, staging / f"{method}.joblib")
            loaded = joblib.load(staging / f"{method}.joblib")
            result[method] = loaded.predict(xt)
            if not np.allclose(result[method], model.predict(xt), rtol=0, atol=1e-10):
                raise ValueError("Point model reload parity failed")
        result["equal_weight"] = result[spec["methods"]].mean(axis=1)
        auxiliary = {}
        for name, threshold in [("appearance", 1), ("sixty", 60)]:
            y = (train.target_minutes >= threshold).astype(int)
            if y.nunique() < 2:
                pv = np.full(len(validation), (y.sum() + 1) / (len(y) + 2))
                pt = np.full(len(test), (y.sum() + 1) / (len(y) + 2))
                auxiliary[name] = {"kind": "constant_beta_prior", "probability": float(pt[0])}
            else:
                model = ExtraTreesClassifier(
                    n_estimators=spec["trees"],
                    min_samples_leaf=15,
                    n_jobs=2,
                    random_state=spec["seed"],
                )
                model.fit(x, y)
                joblib.dump(model, staging / f"{name}.joblib")
                model = joblib.load(staging / f"{name}.joblib")
                positive = list(model.classes_).index(1)
                pv = model.predict_proba(xv)[:, positive] if len(validation) else np.array([])
                pt = model.predict_proba(xt)[:, positive]
                auxiliary[name] = {"kind": "extra_trees_classifier"}
            cal = (
                fit_sigmoid(pv, (validation.target_minutes >= threshold).astype(int), fit_unit=key)
                if len(validation)
                else {"kind": "unavailable"}
            )
            result[name + "_raw"] = pt
            result[name + "_probability"] = calibrate(pt, cal)
            auxiliary[name]["calibration"] = cal
        result["sixty_probability"] = np.minimum(
            result.sixty_probability, result.appearance_probability
        )
        minutes = ExtraTreesRegressor(
            n_estimators=spec["trees"], min_samples_leaf=15, n_jobs=2, random_state=spec["seed"]
        )
        minutes.fit(x, train.target_minutes)
        joblib.dump(minutes, staging / "minutes.joblib")
        result["minutes_raw"] = joblib.load(staging / "minutes.joblib").predict(xt)
        lower = result.appearance_probability + 59 * result.sixty_probability
        upper = 59 * result.appearance_probability + 31 * result.sixty_probability
        result["expected_minutes"] = np.clip(result.minutes_raw, lower, upper)
        for q in [0.1, 0.5, 0.9]:
            model = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=q,
                max_iter=120,
                max_leaf_nodes=15,
                min_samples_leaf=30,
                l2_regularization=10,
                early_stopping=False,
                random_state=spec["seed"],
            )
            model.fit(x, train.target_points)
            joblib.dump(model, staging / f"quantile-{q}.joblib")
            result[f"q{q}_raw"] = joblib.load(staging / f"quantile-{q}.joblib").predict(xt)
        quantiles = np.sort(result[[f"q{q}_raw" for q in [0.1, 0.5, 0.9]]].to_numpy(), axis=1)
        for i, q in enumerate([0.1, 0.5, 0.9]):
            result[f"q{q}"] = quantiles[:, i]
        _json(staging / "auxiliary.json", auxiliary)
        result.to_parquet(staging / "predictions.parquet", index=False)
        _json(
            staging / "complete.json",
            {
                "input_fingerprint": key,
                "files": {p.name: _sha(p) for p in staging.iterdir() if p.is_file()},
            },
        )
        staging.rename(directory)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def train_job(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    from fpl_app.evaluation.tournament import evaluate_panel

    spec = payload["protocol"]
    identity = training_input(store, payload)
    collection = load_collection(store, spec["collection_id"])
    root = data_dir() / "models/weekly_tournament" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    if (root / "complete.json").exists():
        _completed(root, identity)
        report = json.loads((root / "report.json").read_text())
        benchmark = json.loads((root / "benchmark.json").read_text())
        if (
            fingerprint({k: v for k, v in benchmark.items() if k != "benchmark_id"})
            != benchmark["benchmark_id"]
        ):
            raise ValueError("Retained benchmark checksum mismatch")
        sensitivity = json.loads((root / "news_sensitivity.json").read_text())
        return {
            **report,
            "_artifacts": [
                ("forecast_benchmark", sensitivity["benchmark_id"], sensitivity),
                ("forecast_benchmark", benchmark["benchmark_id"], benchmark),
                ("weekly_tournament", identity, report),
            ],
        }
    for name, path in [
        ("implementation.py", Path(__file__)),
        ("uv.lock", Path(__file__).parents[3] / "uv.lock"),
    ]:
        target = root / name
        if target.exists() and _sha(target) != _sha(path):
            raise ValueError("Retained execution changed")
        if not target.exists():
            target.write_bytes(path.read_bytes())
    implementation = root / "implementation"
    implementation.mkdir(exist_ok=True)
    base = Path(__file__).parents[1]
    for name in [
        "models/simple_experiments.py",
        "models/news_sensitivity.py",
        "models/baseline.py",
        "providers/__init__.py",
        "models/rolling_experiments.py",
        "models/opportunity.py",
        "models/training_eligibility.py",
        "features/deadline.py",
        "features/football.py",
        "features/pipeline.py",
        "evaluation/tournament.py",
        "evaluation/metrics.py",
        "learning/forecast_benchmark.py",
    ]:
        target = implementation / name.replace("/", "__")
        if target.exists() and _sha(target) != _sha(base / name):
            raise ValueError("Retained shared implementation changed")
        if not target.exists():
            target.write_bytes((base / name).read_bytes())
    _json(root / "protocol.json", spec)
    _json(
        root / "dependencies.json",
        {n: version(n) for n in ["scikit-learn", "catboost", "lightgbm", "numpy", "pandas"]},
    )
    refs = {s["resource"]: s for s in collection["sources"]}
    fixtures = json.loads(store.snapshot(refs["fixtures/"]["id"])["raw"])
    bootstrap = json.loads(store.snapshot(refs["bootstrap-static/"]["id"])["raw"])
    panel, future, _ = enriched_panels(collection, fixtures)
    folds = chronological_folds(panel, collection["captured_at"], 3)
    if not folds:
        raise ValueError("Insufficient chronological training/evaluation events")
    _json(root / "splits.json", folds)
    panel.to_parquet(root / "historical_features.parquet", index=False)
    outputs = []
    for fold in folds:
        train, validation, test = [
            panel.loc[fold["indices"][k]].copy() for k in ["train", "validation", "test"]
        ]
        out = _unit(root, identity, fold["fold_id"], train, validation, test, spec)
        out["fold_id"] = fold["fold_id"]
        outputs.append(out)
    outer = pd.concat(outputs, ignore_index=True)
    outer.to_parquet(root / "outer_predictions.parquet", index=False)
    evaluation = evaluate_panel(outer, spec["methods"] + ["equal_weight"])
    _json(root / "evaluation.json", evaluation)
    # Latest-data point refit: no calibration rows are silently borrowed from its fit.
    current = panel[
        pd.to_datetime(panel.target_available_at, utc=True)
        < pd.Timestamp(collection["captured_at"])
    ]
    predicted = _unit(root, identity, "current", current, current.iloc[:0], future, spec)
    predicted.to_parquet(root / "future_predictions.parquet", index=False)
    event = int(future.event.iloc[0])
    expected = {
        (p["id"], f["id"])
        for p in bootstrap["elements"]
        for f in fixtures
        if f.get("event") == event and p["team"] in (f["team_h"], f["team_a"])
    }
    actual = list(zip(future.player_id, future.fixture_id))
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Future feature coverage differs from full official schedule")
    models = {}
    published = utcnow()
    elements = {p["id"]: p for p in bootstrap["elements"]}
    for method in spec["methods"] + ["equal_weight"]:
        rows = []
        for player in sorted(elements):
            group = predicted[predicted.player_id == player]
            row = {
                "player_id": player,
                "expected_points": float(group[method].sum()),
                "position": elements[player]["element_type"],
                "expected_minutes": float(group.expected_minutes.sum()),
                "fixture_count": len(group),
            }
            if len(group) == 1:
                r = group.iloc[0]
                row.update(
                    {
                        k: float(r[k])
                        for k in [
                            "appearance_probability",
                            "sixty_probability",
                            "q0.1",
                            "q0.5",
                            "q0.9",
                        ]
                    }
                )
            elif group.empty:
                row.update(
                    {
                        "appearance_probability": 0.0,
                        "sixty_probability": 0.0,
                        "q0.1": 0.0,
                        "q0.5": 0.0,
                        "q0.9": 0.0,
                    }
                )
            rows.append(row)
        models[method] = {
            "published_at": published,
            "predictions": rows,
            "point_semantics": "unconditional_mean",
            "auxiliary": "shared extra-trees + histogram quantiles; uncalibrated current refit",
        }
    from fpl_app.contracts import Fixture, Player
    from fpl_app.models.baseline import baseline_run
    from fpl_app.providers import dataset

    data = dataset(
        store.snapshot(refs["bootstrap-static/"]["id"]), store.snapshot(refs["fixtures/"]["id"])
    )
    baseline = baseline_run(
        [Player.model_validate(p) for p in data["players"]],
        [Fixture.model_validate(f) for f in data["fixtures"]],
        "weekly-tournament-baseline",
        data["source_cutoff"],
        "live",
        event,
        1,
    )
    models["baseline_football"] = {
        "published_at": published,
        "predictions": [
            {
                "player_id": p,
                "position": elements[p]["element_type"],
                "expected_points": sum(
                    r.expected_points for r in baseline.projections if r.player_id == p
                ),
                "expected_minutes": sum(
                    r.expected_minutes for r in baseline.projections if r.player_id == p
                ),
            }
            for p in sorted(elements)
        ],
    }
    if (root / "benchmark.json").exists():
        benchmark = json.loads((root / "benchmark.json").read_text())
        if (
            benchmark["protocol"].get("input_fingerprint") != identity
            or fingerprint({k: v for k, v in benchmark.items() if k != "benchmark_id"})
            != benchmark["benchmark_id"]
        ):
            raise ValueError("Partial publication identity mismatch")
    else:
        benchmark = make_benchmark(
            store,
            refs["bootstrap-static/"]["id"],
            refs["fixtures/"]["id"],
            event,
            models,
            produced_at=published,
            protocol={
                **spec,
                "input_fingerprint": identity,
                "evaluation_reference": str(root / "evaluation.json"),
                "limitations": [
                    "historical timing reconstructed",
                    "shared auxiliaries across point methods",
                    "quantiles are marginal, not calibrated joint scenarios",
                    "double-event probabilities/quantiles unavailable; fixture means sum",
                    "no live promotion or legal policy superiority claim",
                ],
            },
        )
    _json(root / "benchmark.json", benchmark)
    from fpl_app.models.news_sensitivity import freeze_news_sensitivity

    sensitivity_path = root / "news_sensitivity.json"
    sensitivity = (
        json.loads(sensitivity_path.read_text())
        if sensitivity_path.exists()
        else freeze_news_sensitivity(store, benchmark["benchmark_id"], benchmark)
    )
    _json(sensitivity_path, sensitivity)
    report = {
        "sensitivity_benchmark_id": sensitivity["benchmark_id"],
        "study_id": spec["study_id"],
        "event": event,
        "benchmark_id": benchmark["benchmark_id"],
        "players_per_model": len(elements),
        "methods": list(models),
        "evaluation": evaluation,
        "artifact_directory": str(root),
        "input_fingerprint": identity,
        "promoted": False,
    }
    _json(root / "report.json", report)
    _json(
        root / "complete.json",
        {
            "input_fingerprint": identity,
            "files": {
                str(p.relative_to(root)): _sha(p)
                for p in root.rglob("*")
                if p.is_file() and p.name != "complete.json"
            },
        },
    )
    return {
        **report,
        "_artifacts": [
            ("forecast_benchmark", sensitivity["benchmark_id"], sensitivity),
            ("forecast_benchmark", benchmark["benchmark_id"], benchmark),
            ("weekly_tournament", identity, report),
        ],
    }
