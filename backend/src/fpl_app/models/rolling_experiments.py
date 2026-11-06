"""Registered expanding enriched-model evaluation; never refits serving forecasts.

Historical label availability is assumed kickoff + one day, not the actual
publication time. Actual captured label availability is retained separately.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import forecast_metrics
from fpl_app.features.deadline import ATTACK, CONTEXT, DEFENCE, OPPORTUNITY, enriched_panels
from fpl_app.features.football import CATEGORICAL, FEATURES
from fpl_app.models.deadline_experiments import configurations
from fpl_app.models.training import data_dir
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow

TIMING = "retrospective_assumed_kickoff_plus_one_day"
BASELINES = ["app_baseline_reconstructed", "rolling_points_5"]


def protocol(collection: dict[str, Any]) -> dict[str, Any]:
    """Register fixed settings before any fit; previously inspected history is exploratory."""
    captured = _instant(collection["captured_at"])
    labels = collection["labels"]
    events = sorted(
        {
            int(row["event"])
            for row in labels
            if row["label_status"] == "final_revision" and _instant(row["available_at"]) <= captured
        }
        - {int(row["event"]) for row in labels if row["label_status"] != "final_revision"}
    )
    full = FEATURES + ATTACK + DEFENCE + CONTEXT + OPPORTUNITY
    configs = [c for c in configurations() if c["name"] == "full_second_seed"]
    configs += [
        {"name": name, "features": full, "depth": 4, "l2_leaf_reg": 10, "seed": 43, **extra}
        for name, extra in [
            ("opportunity_multiscale", {}),
            ("points_hurdle", {"method": "points_hurdle"}),
        ]
    ]
    return {
        "version": "enriched-expanding-v1",
        "collection_id": collection["collection_id"],
        "registered_at": utcnow(),
        "as_of": collection["captured_at"],
        "finalized_events": events,
        "minimum_training_events": 3,
        "inner_validation_events": 1,
        "outer_test_events": 1,
        "configurations": configs,
        "baseline_comparators": BASELINES,
        "iterations": 400,
        "early_stopping_rounds": 30,
        "learning_rate": 0.04,
        "thread_count": 2,
        "historical_timing": TIMING,
        "selection": "Fixed configurations; inner validation selects iterations only",
        "test_interpretation": "Exploratory historical outer events; previously inspected history",
        "active": False,
        "serving_refit": False,
        "ensemble": False,
    }


def _instant(value: Any) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("Evaluation timestamps must be nonmissing and timezone aware")
    return stamp.tz_convert("UTC")


def chronological_folds(
    panel: pd.DataFrame, as_of: str, minimum_training_events: int = 3
) -> list[dict[str, Any]]:
    """Expand training, validate on the prior event, test once on the next event."""
    if minimum_training_events < 2:
        raise ValueError("At least two training events required")
    required = {"event", "decision_cutoff", "target_available_at", "target_points"}
    if panel.empty or not required <= set(panel):
        raise ValueError("Complete nonempty historical panel required")
    cutoff = _instant(as_of)
    for column in ("decision_cutoff", "target_available_at"):
        for value in panel[column]:
            _instant(value)
    if not np.isfinite(panel.target_points.to_numpy(dtype=float)).all():
        raise ValueError("Finite observed targets required")
    available = panel[pd.to_datetime(panel.target_available_at, utc=True) <= cutoff]
    if "actual_label_available_at" in available:
        for value in available.actual_label_available_at:
            _instant(value)
        available = available[
            pd.to_datetime(available.actual_label_available_at, utc=True) <= cutoff
        ]
    origins = {
        int(cast(Any, event)): {_instant(v) for v in rows.decision_cutoff}
        for event, rows in available.groupby("event")
    }
    if any(len(values) != 1 for values in origins.values()):
        raise ValueError("Each event must share one deadline origin, including doubles")
    events = sorted(origins, key=lambda e: next(iter(origins[e])))
    if len({next(iter(values)) for values in origins.values()}) != len(events):
        raise ValueError("Distinct events require distinct origins")
    result = []
    for index in range(minimum_training_events + 1, len(events)):
        blocks = {
            "train": events[: index - 1],
            "validation": [events[index - 1]],
            "test": [events[index]],
        }
        subsets = {k: available[available.event.isin(v)].copy() for k, v in blocks.items()}
        counts = {k: len(v) for k, v in subsets.items()}
        for name, next_name in [("train", "validation"), ("validation", "test")]:
            boundary = pd.to_datetime(subsets[next_name].decision_cutoff, utc=True).min()
            subsets[name] = subsets[name][
                pd.to_datetime(subsets[name].target_available_at, utc=True) < boundary
            ]
        if (
            any(frame.empty for frame in subsets.values())
            or subsets["train"].event.nunique() < minimum_training_events
        ):
            continue
        result.append(
            {
                "fold_id": f"outer-event-{events[index]}",
                "train_events": sorted(int(e) for e in subsets["train"].event.unique()),
                "validation_events": blocks["validation"],
                "test_events": blocks["test"],
                "indices": {k: v.index.tolist() for k, v in subsets.items()},
                "purged_rows": {k: counts[k] - len(v) for k, v in subsets.items()},
                "train_target_end": pd.to_datetime(subsets["train"].target_available_at, utc=True)
                .max()
                .isoformat(),
                "validation_target_end": pd.to_datetime(
                    subsets["validation"].target_available_at, utc=True
                )
                .max()
                .isoformat(),
                "validation_origin": pd.to_datetime(subsets["validation"].decision_cutoff, utc=True)
                .min()
                .isoformat(),
                "test_origin": pd.to_datetime(subsets["test"].decision_cutoff, utc=True)
                .min()
                .isoformat(),
                "historical_timing": TIMING,
            }
        )
    return result


def _implementations() -> list[Path]:
    base = Path(__file__).parents[1]
    return [
        Path(__file__),
        Path(__file__).with_name("deadline_experiments.py"),
        Path(__file__).with_name("points_hurdle.py"),
        Path(__file__).with_name("training_eligibility.py"),
        base / "features/deadline.py",
        base / "features/football.py",
        base / "features/pipeline.py",
        base / "evaluation/metrics.py",
        base / "providers/collection.py",
    ]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_input(store: Store, payload: dict[str, Any]) -> str:
    spec = payload["protocol"]
    collection = load_collection(store, spec["collection_id"])
    expected = protocol(collection)
    if {k: v for k, v in spec.items() if k != "registered_at"} != {
        k: v for k, v in expected.items() if k != "registered_at"
    }:
        raise ValueError("Unknown rolling evaluation protocol")
    if store.get("rolling_experiment_protocol", fingerprint(spec)) != spec:
        raise ValueError("Register rolling evaluation protocol before fitting")
    from .training_eligibility import require_scored_collection

    require_scored_collection(store, collection)
    return fingerprint(
        {
            "protocol": spec,
            "collection_sha256": collection["envelope_sha256"],
            "code": {
                str(p.relative_to(Path(__file__).parents[1])): _sha(p) for p in _implementations()
            },
        }
    )


def _json(path: Path, value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)
    if path.exists():
        if path.read_text() != encoded:
            raise ValueError(f"Immutable artifact differs: {path.name}")
    else:
        temporary = path.parent / (".json-" + uuid4().hex)
        try:
            temporary.write_text(encoded)
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_text() != encoded:
                    raise ValueError(f"Immutable artifact differs: {path.name}") from None
        finally:
            temporary.unlink(missing_ok=True)


def _completed(directory: Path, identity: str) -> dict[str, Any] | None:
    if not directory.exists():
        return None
    manifest = json.loads((directory / "complete.json").read_text())
    if manifest["input_fingerprint"] != identity:
        raise ValueError("Checkpoint input fingerprint mismatch")
    actual = {
        str(p.relative_to(directory)): _sha(p)
        for p in directory.rglob("*")
        if p.is_file() and p.name != "complete.json"
    }
    if actual != manifest["files"]:
        raise ValueError("Checkpoint checksum mismatch")
    return manifest


def _fit_unit(
    root: Path,
    identity: str,
    fold: dict[str, Any],
    config: dict[str, Any],
    spec: dict[str, Any],
    panel: pd.DataFrame,
) -> pd.DataFrame:
    unit_id = fingerprint({"experiment": identity, "fold": fold, "configuration": config})
    directory = root / fold["fold_id"] / config["name"]
    completed = _completed(directory, unit_id)
    if completed is not None:
        return pd.read_parquet(directory / "predictions.parquet")
    train, validation, test = (
        panel.loc[fold["indices"][k]].copy() for k in ("train", "validation", "test")
    )
    columns = config["features"]
    categories = [c for c in columns if c in CATEGORICAL]
    kwargs = {
        "depth": config["depth"],
        "l2_leaf_reg": config["l2_leaf_reg"],
        "learning_rate": spec["learning_rate"],
        "random_seed": config["seed"],
        "loss_function": "RMSE",
        "thread_count": spec["thread_count"],
        "verbose": False,
        "allow_writing_files": False,
        "allow_const_label": True,
    }
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = directory.parent / (".attempt-" + uuid4().hex)
    staging.mkdir()
    try:
        if config.get("method") == "points_hurdle":
            from fpl_app.models.points_hurdle import fit_hurdle, predict_hurdle

            iterations: int | dict[str, int] = fit_hurdle(
                train,
                validation,
                columns,
                categories,
                kwargs,
                spec["iterations"],
                spec["early_stopping_rounds"],
                staging / "model",
            )
            prediction = predict_hurdle(staging / "model", test, columns)
        else:
            from catboost import CatBoostRegressor

            model = CatBoostRegressor(iterations=spec["iterations"], **kwargs)
            model.fit(
                train[columns],
                train.target_points,
                cat_features=categories,
                eval_set=(validation[columns], validation.target_points),
                early_stopping_rounds=spec["early_stopping_rounds"],
            )
            iterations = model.tree_count_
            model.save_model(str(staging / "model.cbm"))
            reloaded = CatBoostRegressor()
            reloaded.load_model(str(staging / "model.cbm"))
            prediction = reloaded.predict(test[columns])
            if not np.array_equal(prediction, model.predict(test[columns])):
                raise ValueError("Checkpoint reload changed outer predictions")
        if len(prediction) != len(test) or not np.isfinite(prediction).all():
            raise ValueError("Complete finite outer predictions required")
        predicted = test.copy()
        predicted["predicted_points"] = prediction
        predicted["model"] = config["name"]
        predicted["selected_iterations"] = json.dumps(iterations, sort_keys=True)
        predicted.to_parquet(staging / "predictions.parquet", index=False)
        _json(
            staging / "complete.json",
            {
                "input_fingerprint": unit_id,
                "selected_iterations": iterations,
                "files": {
                    str(p.relative_to(staging)): _sha(p) for p in staging.rglob("*") if p.is_file()
                },
            },
        )
        staging.rename(directory)
        return predicted
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _metrics(frame: pd.DataFrame, names: list[str]) -> dict[str, Any]:
    aggregate = frame.groupby(["event", "player_id"], as_index=False)[
        ["target_points", *names]
    ].sum()
    return {
        level: {
            name: forecast_metrics(rows.target_points, rows[name], events=rows.event)
            for name in names
        }
        for level, rows in [("player_fixture", frame), ("player_event", aggregate)]
    }


def train_job(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker entry point; retry resumes only checksum-verified completed fit units."""
    spec = payload["protocol"]
    identity = training_input(store, payload)
    collection = load_collection(store, spec["collection_id"])
    root = data_dir() / "models/rolling_experiments" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    if (root / "report.json").exists():
        retained = json.loads((root / "report.json").read_text())
        if any(_sha(root / path) != digest for path, digest in retained["files"].items()):
            raise ValueError("Retained rolling report checksum mismatch")
    _json(root / "protocol.json", spec)
    implementation = root / "implementation"
    for path in _implementations():
        destination = implementation / path.relative_to(Path(__file__).parents[1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and _sha(destination) != _sha(path):
            raise ValueError("Retained implementation differs")
        if not destination.exists():
            destination.write_bytes(path.read_bytes())
    sources = {s["resource"]: s for s in collection["sources"]}
    fixtures = json.loads(store.snapshot(sources["fixtures/"]["id"])["raw"])
    panel, _, _ = enriched_panels(collection, fixtures)
    panel = panel[panel.event.isin(spec["finalized_events"])].reset_index(drop=True)
    actual = {
        (r["provider_player_id"], r["fixture_id"]): r["available_at"]
        for r in collection["labels"]
        if r["label_status"] == "final_revision"
    }
    panel["actual_label_available_at"] = [
        actual[(int(p), int(f))] for p, f in zip(panel.player_id, panel.fixture_id)
    ]
    if panel.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("Duplicate player-fixture target")
    panel["rolling_points_5"] = panel.points_5
    folds = chronological_folds(panel, spec["as_of"], spec["minimum_training_events"])
    if not folds:
        raise ValueError("No eligible purged expanding folds")
    _json(root / "splits.json", folds)
    # Bind exact reconstructed panel before checkpoint reuse, independent of Parquet encoding.
    panel_identity = fingerprint(json.loads(panel.to_json(orient="split", date_format="iso")))
    _json(
        root / "inputs.json", {"input_fingerprint": identity, "panel_fingerprint": panel_identity}
    )
    panel.to_parquet(root / "historical_features.parquet", index=False)
    wide, long = [], []
    for fold in folds:
        outer = panel.loc[fold["indices"]["test"]].copy()
        for key in ("train_events", "validation_events", "test_events"):
            outer[key] = json.dumps(fold[key])
        for key in (
            "fold_id",
            "train_target_end",
            "validation_target_end",
            "validation_origin",
            "test_origin",
            "historical_timing",
        ):
            outer[key] = fold[key]
        outer["partition"] = "outer_test"
        for config in spec["configurations"]:
            fitted = _fit_unit(root, identity, fold, config, spec, panel)
            if (
                fitted[["player_id", "fixture_id"]].to_records(index=False).tolist()
                != outer[["player_id", "fixture_id"]].to_records(index=False).tolist()
            ):
                raise ValueError("Checkpoint outer row identity mismatch")
            outer[config["name"]] = fitted.predicted_points.to_numpy()
            rows = outer.copy()
            rows["model"] = config["name"]
            rows["predicted_points"] = fitted.predicted_points.to_numpy()
            rows["selected_iterations"] = fitted.selected_iterations.to_numpy()
            long.append(rows)
        for name in BASELINES:
            rows = outer.copy()
            rows["model"] = name
            rows["predicted_points"] = outer[name]
            rows["selected_iterations"] = "not_fitted"
            long.append(rows)
        wide.append(outer)
    outer_predictions = pd.concat(wide, ignore_index=True)
    oof = pd.concat(long, ignore_index=True)
    names = [c["name"] for c in spec["configurations"]] + BASELINES
    outer_predictions.to_parquet(root / "outer_predictions.parquet", index=False)
    oof.to_parquet(root / "oof_predictions.parquet", index=False)
    report = {
        "experiment_id": identity,
        "status": "evaluated_research",
        "collection_id": collection["collection_id"],
        "collection_sha256": collection["envelope_sha256"],
        "protocol": spec,
        "directory": str(root),
        "folds": folds,
        "outer_events": sorted(int(e) for e in outer_predictions.event.unique()),
        "comparators": names,
        "pooled": _metrics(outer_predictions, names),
        "per_fold": {str(k): _metrics(v, names) for k, v in outer_predictions.groupby("fold_id")},
        "active": False,
        "champion_promoted": False,
        "serving_refit": False,
        "files": {
            str(p.relative_to(root)): _sha(p)
            for p in root.rglob("*")
            if p.is_file()
            and p.name != "report.json"
            and not any(part.startswith(".") for part in p.relative_to(root).parts)
        },
        "limitations": [
            "Retrospective assumed kickoff+1day label timing; actual capture times retained separately",
            "Current captured universe, positions, and schedule are reconstructed, not verified historical snapshots",
            "Historical outer events were previously inspected; results remain exploratory",
            "Inner validation controls early stopping only; no outer-driven configuration or ensemble weights",
            "No promotion, serving refit, probability calibration, or modification of frozen GW9/GW10 forecasts",
        ],
    }
    _json(root / "report.json", report)
    return {**report, "_artifacts": [("rolling_experiment", identity, report)]}
