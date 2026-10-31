"""Fixed research ablations; validation selects, future scoring stays untouched."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.features.deadline import ATTACK, CONTEXT, DEFENCE, enriched_panels
from fpl_app.features.football import CATEGORICAL, FEATURES
from fpl_app.features.pipeline import utc
from fpl_app.learning.forecast_benchmark import make_benchmark
from fpl_app.models.football_catboost import errors
from fpl_app.models.training import data_dir
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow


def configurations() -> list[dict[str, Any]]:
    full = FEATURES + ATTACK + DEFENCE + CONTEXT
    return [
        {"name": name, "features": features, "depth": depth, "l2_leaf_reg": penalty, "seed": seed}
        for name, features, depth, penalty, seed in [
            ("points_position", ["position", "rule_era", "history_count", "points_5"], 4, 10, 43),
            ("opportunity_fixture", FEATURES, 4, 10, 43),
            ("plus_xg_xa", FEATURES + ATTACK, 4, 10, 43),
            ("plus_defensive_actions", FEATURES + ATTACK + DEFENCE, 4, 10, 43),
            ("full_context", full, 4, 10, 43),
            ("full_shallow_regularized", full, 3, 30, 43),
            ("full_deeper_regularized", full, 5, 30, 43),
            ("full_second_seed", full, 4, 10, 47),
        ]
    ]


def protocol(collection_id: str) -> dict[str, Any]:
    return {
        "version": "deadline-ablation-v1",
        "collection_id": collection_id,
        "registered_at": utcnow(),
        "configurations": configurations(),
        "train_events": [1, 2, 3, 4],
        "validation_events": [5, 6],
        "test_events": [7, 8],
        "iterations": 400,
        "early_stopping_rounds": 30,
        "learning_rate": 0.04,
        "selection": "lowest validation RMSE only; no test-driven selection",
        "historical_timing": "retrospective_assumed_kickoff_plus_one_day",
        "test_interpretation": "exploratory; these historical event blocks were inspected earlier",
        "future_interpretation": "GW9 forecast genuinely prospective if published before actual deadline",
        "active": False,
    }


def training_input(store: Store, payload: dict[str, Any]) -> str:
    spec = payload["protocol"]
    collection = load_collection(store, spec["collection_id"])
    code = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), Path(__file__).parents[1] / "features/deadline.py")
    }
    expected = protocol(spec["collection_id"])
    if any(spec.get(k) != v for k, v in expected.items() if k != "registered_at"):
        raise ValueError("Unknown benchmark protocol")
    return fingerprint(
        {"protocol": spec, "collection_sha256": collection["envelope_sha256"], "code": code}
    )


def train_job(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    from catboost import CatBoostRegressor

    from fpl_app.evaluation.metrics import fit_ensemble

    spec = payload["protocol"]
    identity = training_input(store, payload)
    root = data_dir() / "models/deadline_experiments" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    (root / "protocol.json").write_text(json.dumps(spec, sort_keys=True, indent=2))
    collection = load_collection(store, spec["collection_id"])
    sources = {s["resource"]: s for s in collection["sources"][:2]}
    fixtures = json.loads(store.snapshot(sources["fixtures/"]["id"])["raw"])
    panel, future, _ = enriched_panels(collection, fixtures)
    if not set(range(1, 9)) <= set(panel.event):
        raise ValueError("Eight explicit finalized current-era events required")
    train = panel[panel.event.isin(spec["train_events"])].copy()
    validation = panel[panel.event.isin(spec["validation_events"])].copy()
    test = panel[panel.event.isin(spec["test_events"])].copy()
    train = train[
        pd.to_datetime(train.target_available_at, utc=True)
        < pd.to_datetime(validation.decision_cutoff, utc=True).min()
    ]
    validation = validation[
        pd.to_datetime(validation.target_available_at, utc=True)
        < pd.to_datetime(test.decision_cutoff, utc=True).min()
    ]
    if min(map(len, (train, validation, test))) < 10:
        raise ValueError("Chronological purge left insufficient data")
    panel.to_parquet(root / "historical_features.parquet", index=False)
    future.to_parquet(root / "future_features.parquet", index=False)
    summaries: list[dict[str, Any]] = []
    models: dict[str, dict[str, Any]] = {}
    val_predictions, test_predictions = validation.copy(), test.copy()
    current = panel[
        pd.to_datetime(panel.target_available_at, utc=True) <= utc(collection["captured_at"])
    ].copy()
    for config in spec["configurations"]:
        name, columns = config["name"], config["features"]
        directory = root / name
        directory.mkdir(exist_ok=True)
        categories = [c for c in columns if c in CATEGORICAL]
        kwargs = {
            "depth": config["depth"],
            "l2_leaf_reg": config["l2_leaf_reg"],
            "learning_rate": spec["learning_rate"],
            "random_seed": config["seed"],
            "loss_function": "RMSE",
            "thread_count": 2,
            "verbose": False,
            "allow_writing_files": False,
            "allow_const_label": True,
        }
        selection = CatBoostRegressor(iterations=spec["iterations"], **kwargs)
        selection.fit(
            train[columns],
            train.target_points,
            cat_features=categories,
            eval_set=(validation[columns], validation.target_points),
            early_stopping_rounds=spec["early_stopping_rounds"],
        )
        iterations = max(1, selection.get_best_iteration() + 1)
        selection.save_model(str(directory / "selection.cbm"))
        val_predictions[name] = selection.predict(validation[columns])
        test_predictions[name] = selection.predict(test[columns])
        latest = CatBoostRegressor(iterations=iterations, **kwargs)
        latest.fit(current[columns], current.target_points, cat_features=categories)
        latest.save_model(str(directory / "current.cbm"))
        reloaded = CatBoostRegressor()
        reloaded.load_model(str(directory / "current.cbm"))
        predictions = reloaded.predict(future[columns])
        if not np.array_equal(predictions, latest.predict(future[columns])):
            raise ValueError("Checkpoint reload changed future predictions")
        models[name] = {
            "published_at": utcnow(),
            "scope": "unconditional fixture mean; one fixture in this event",
            "predictions": [
                {"player_id": int(p), "expected_points": float(v)}
                for p, v in zip(future.player_id, predictions)
            ],
        }
        summaries.append(
            {
                **config,
                "selected_iterations": iterations,
                "validation": errors(validation.target_points, val_predictions[name]),
                "exploratory_test": errors(test.target_points, test_predictions[name]),
            }
        )
        (directory / "metrics.json").write_text(json.dumps(summaries[-1], indent=2))
    names = [c["name"] for c in spec["configurations"]]
    val_predictions["partition"] = "validation"
    val_predictions["train_target_end"] = (
        pd.to_datetime(train.target_available_at, utc=True).max().isoformat()
    )
    fitted = fit_ensemble(val_predictions, names)
    weights = fitted["weights"]
    test_blend, latest_blend = np.zeros(len(test)), np.zeros(len(future))
    for name in names:
        test_blend += weights[name] * test_predictions[name].to_numpy()
        latest_blend += weights[name] * np.array(
            [r["expected_points"] for r in models[name]["predictions"]]
        )
    models["validation_fit_ensemble"] = {
        "published_at": utcnow(),
        "weights": weights,
        "predictions": [
            {"player_id": int(p), "expected_points": float(v)}
            for p, v in zip(future.player_id, latest_blend)
        ],
    }
    winner = min(summaries, key=lambda r: r["validation"]["rmse"])["name"]
    val_predictions.to_parquet(root / "validation_predictions.parquet", index=False)
    test_predictions.to_parquet(root / "exploratory_test_predictions.parquet", index=False)
    benchmark = make_benchmark(
        store,
        sources["bootstrap-static/"]["id"],
        sources["fixtures/"]["id"],
        int(future.event.iloc[0]),
        models,
        produced_at=utcnow(),
        protocol=spec,
    )
    report = {
        "experiment_id": identity,
        "status": "evaluated_research",
        "active": False,
        "selected_by_validation": winner,
        "variants": summaries,
        "ensemble_weights": weights,
        "ensemble_exploratory_test": errors(test.target_points, test_blend),
        "benchmark_id": benchmark["benchmark_id"],
        "directory": str(root),
        "limitations": [
            "Historical timing and schedule assumptions remain explicit",
            "Previously inspected historical test blocks are exploratory",
            "Prospective event is not scored or used to choose settings",
            "No automatic production promotion",
        ],
    }
    (root / "report.json").write_text(json.dumps(report, indent=2))
    (root / "frozen_benchmark.json").write_text(json.dumps(benchmark, indent=2))
    return {
        **report,
        "_artifacts": [
            ("deadline_experiment", identity, report),
            ("forecast_benchmark", benchmark["benchmark_id"], benchmark),
        ],
    }
