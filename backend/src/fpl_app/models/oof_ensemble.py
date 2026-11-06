"""Registered walk-forward convex blending of earlier out-of-fold predictions.

The first OOF week is development warmup only. Each subsequent evaluation origin
fits weights only on earlier OOF labels available before that origin. No serving
refit, prospective claim or automatic activation is implied.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import fit_ensemble, forecast_metrics
from fpl_app.models.rolling_experiments import _json, _sha
from fpl_app.models.training import data_dir
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow

METHODS = ["ridge", "lightgbm", "opportunity_multiscale"]
KEYS = ["event", "player_id", "fixture_id"]


def protocol(simple_directory: Path) -> dict[str, Any]:
    simple_spec = json.loads((simple_directory / "protocol.json").read_text())
    return {
        "version": "prior-oof-convex-v1",
        "registered_at": utcnow(),
        "simple_directory": str(simple_directory.resolve()),
        "simple_report_sha256": _sha(simple_directory / "report.json"),
        "reference_directory": simple_spec["reference_directory"],
        "reference_report_sha256": simple_spec["reference_report_sha256"],
        "collection_id": simple_spec["collection_id"],
        "methods": METHODS,
        "warmup": "first OOF event is development only, excluded from reported ensemble metrics",
        "weight_rule": "Expanding prior OOF rows with targets strictly available before current origin; nonnegative weights summing to one, least squares",
        "hypothesis": "Earlier OOF-fitted convex blending reduces unconditional point RMSE against same-window fixed individuals",
        "interpretation": "Exploratory previously inspected history; each reported origin excludes its own labels from weight fitting",
        "active": False,
    }


def blend_walk_forward(
    wide: pd.DataFrame, methods: list[str]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    required = {
        *KEYS,
        "decision_cutoff",
        "target_available_at",
        "train_target_end",
        "target_points",
        *methods,
    }
    if not required <= set(wide) or wide.duplicated(KEYS).any():
        raise ValueError("Complete unique origin-bound OOF predictions required")
    if not np.isfinite(wide[["target_points", *methods]].to_numpy(dtype=float)).all():
        raise ValueError("Finite complete matched OOF predictions required")
    origins = pd.to_datetime(wide.decision_cutoff, utc=True)
    known = pd.to_datetime(wide.target_available_at, utc=True)
    trained = pd.to_datetime(wide.train_target_end, utc=True)
    if (trained >= origins).any():
        raise ValueError("Base prediction training overlaps its held-out origin")
    ordered = sorted(wide.event.unique(), key=lambda e: origins[wide.event == e].min())
    if len(ordered) < 2:
        raise ValueError("Warmup and separate outer events required")
    output, history = [], []
    for index, event in enumerate(ordered[1:], start=1):
        outer = wide[wide.event == event].copy()
        event_origins = pd.to_datetime(outer.decision_cutoff, utc=True)
        if event_origins.nunique() != 1:
            raise ValueError("One shared deadline per event required")
        origin = event_origins.iloc[0]
        development = wide[wide.event.isin(ordered[:index]) & (known < origin)].copy()
        if development.empty:
            raise ValueError("No earlier available OOF calibration labels")
        if (pd.to_datetime(development.decision_cutoff, utc=True) >= origin).any():
            raise ValueError("Calibration origins overlap current event")
        development["partition"] = "validation"
        fitted = fit_ensemble(development, methods)
        weights = np.array([fitted["weights"][name] for name in methods])
        outer["ensemble"] = outer[methods].to_numpy(dtype=float) @ weights
        output.append(outer)
        history.append(
            {
                "event": int(event),
                "origin": origin.isoformat(),
                "development_events": sorted(int(e) for e in development.event.unique()),
                "development_rows": len(development),
                "development_target_end": pd.to_datetime(development.target_available_at, utc=True)
                .max()
                .isoformat(),
                "weights": fitted["weights"],
                "development_mse": fitted["validation_mse"],
                "best_development_individual_mse": fitted["best_individual_mse"],
            }
        )
    return pd.concat(output, ignore_index=True), history


def _verified(directory: Path, expected: str) -> dict[str, Any]:
    if _sha(directory / "report.json") != expected:
        raise ValueError("Reference report checksum differs")
    report = json.loads((directory / "report.json").read_text())
    if any(_sha(directory / p) != digest for p, digest in report["files"].items()):
        raise ValueError("Reference artifact checksum differs")
    return report


def run_experiment(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    expected = protocol(Path(spec["simple_directory"]))
    if {k: v for k, v in spec.items() if k != "registered_at"} != {
        k: v for k, v in expected.items() if k != "registered_at"
    }:
        raise ValueError("Unknown OOF ensemble protocol")
    if store.get("oof_ensemble_protocol", fingerprint(spec)) != spec:
        raise ValueError("Register OOF ensemble before weight fitting")
    simple = Path(spec["simple_directory"])
    reference = Path(spec["reference_directory"])
    _verified(simple, spec["simple_report_sha256"])
    ref_report = _verified(reference, spec["reference_report_sha256"])
    collection = load_collection(store, spec["collection_id"])
    if ref_report["collection_sha256"] != collection["envelope_sha256"]:
        raise ValueError("Collection identity mismatch")
    require_scored_collection(store, collection)
    identity = fingerprint(
        {
            "protocol": spec,
            "implementation": _sha(Path(__file__)),
            "dependency_lock": _sha(Path(__file__).parents[3] / "uv.lock"),
            "shared_code": {
                name: _sha(Path(__file__).parents[1] / name)
                for name in (
                    "evaluation/metrics.py",
                    "models/rolling_experiments.py",
                    "models/training_eligibility.py",
                )
            },
            "collection": collection["envelope_sha256"],
        }
    )
    root = data_dir() / "models/oof_ensemble" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    _json(root / "protocol.json", spec)
    reference_rows = pd.read_parquet(reference / "outer_predictions.parquet")
    wide = reference_rows.copy()
    predictions = pd.read_parquet(simple / "outer_predictions.parquet")
    for method in ["ridge", "lightgbm"]:
        rows = predictions[predictions.model == method]
        if rows.duplicated(KEYS).any() or len(rows) != len(wide):
            raise ValueError("Incomplete simple OOF row coverage")
        aligned = wide[KEYS + ["target_points"]].merge(
            rows[KEYS + ["target_points", "predicted_points"]],
            on=KEYS,
            how="left",
            validate="one_to_one",
            suffixes=("", "_simple"),
        )
        if not np.array_equal(aligned.target_points, aligned.target_points_simple):
            raise ValueError("Matched simple OOF outcomes differ")
        wide[method] = aligned.predicted_points.to_numpy()
    result, weights = blend_walk_forward(wide, spec["methods"])
    result.to_parquet(root / "outer_predictions.parquet", index=False)
    _json(root / "weights.json", weights)
    implementation = root / "implementation.py"
    if implementation.exists() and _sha(implementation) != _sha(Path(__file__)):
        raise ValueError("Saved implementation differs")
    if not implementation.exists():
        implementation.write_bytes(Path(__file__).read_bytes())
    names = [
        *spec["methods"],
        "ensemble",
        "app_baseline_reconstructed",
        "full_second_seed",
        "points_hurdle",
    ]
    report = {
        "experiment_id": identity,
        "registered_at": spec["registered_at"],
        "interpretation": spec["interpretation"],
        "metrics": {
            name: forecast_metrics(result.target_points, result[name], events=result.event)
            for name in names
        },
        "outer_events": sorted(int(e) for e in result.event.unique()),
        "outer_rows": len(result),
        "weights": weights,
        "active": False,
        "champion_promoted": False,
        "files": {
            str(p.relative_to(root)): _sha(p)
            for p in root.rglob("*")
            if p.is_file() and p.name != "report.json"
        },
    }
    _json(root / "report.json", report)
    store.put("oof_ensemble_report", identity, report)
    return report
