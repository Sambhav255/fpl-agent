"""Registered origin-frozen direct leads; isolated research, never live serving."""

from __future__ import annotations

import json
import platform
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from fpl_app.evaluation.metrics import forecast_metrics
from fpl_app.features.football import FEATURES
from fpl_app.features.multilead import EXTRA, direct_panel
from fpl_app.models.rolling_experiments import _fit_unit, _instant, _json, _sha
from fpl_app.models.training import data_dir
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, fingerprint, utcnow

LEADS = [1, 2, 3, 4, 6, 8]


def protocol(collection: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "direct-origin-frozen-v1",
        "registered_at": utcnow(),
        "collection_id": collection["collection_id"],
        "leads": LEADS,
        "features": FEATURES + EXTRA,
        "minimum_training_events": 3,
        "iterations": 180,
        "early_stopping_rounds": 25,
        "learning_rate": 0.04,
        "thread_count": 2,
        "configuration": {"depth": 4, "l2_leaf_reg": 10, "seed": 43},
        "targets": ["points", "minutes"],
        "as_of": collection["captured_at"],
        "hypothesis": "Direct lead-specific signed point and minute regression improves on unchanged origin rolling means",
        "selection": "One fixed configuration per lead; latest pre-origin validation chooses iterations only",
        "historical_timing": "assumed_kickoff_plus_one_day_not_verified_original_publication",
        "schedule_evidence": "captured_current_schedule_membership_universe_not_verified_historically",
        "interpretation": "Exploratory previously inspected history; no prospective policy or calibration claim",
        "probability_calibration": "unavailable; no future probability or joint distribution qualification",
        "active": False,
        "serving_refit": False,
    }


def chronological_folds(
    panel: pd.DataFrame, as_of: str, minimum_training_events: int = 3
) -> list[dict[str, Any]]:
    """Leave a full target-completion embargo before EACH next origin.

    Validation is the latest *completed* earlier target event, not the adjacent
    origin, which would be unobserved at multi-lead prediction time. A double's
    rows are retained or purged together, even if its first fixture ended earlier.
    """
    required = {
        "lead",
        "origin_event",
        "event",
        "decision_cutoff",
        "target_available_at",
        "actual_label_available_at",
        "target_points",
    }
    if not required <= set(panel) or minimum_training_events < 1:
        raise ValueError("Dated direct-lead panel and positive minimum required")
    if panel.empty:
        return []
    if panel.lead.nunique() != 1 or panel.index.has_duplicates:
        raise ValueError("Unique indices and one direct lead required")
    cutoff = _instant(as_of)
    # Do not turn an incompletely observed double into an ordinary event.
    complete_players = panel.groupby(["event", "player_id"])["target_points"].transform(
        lambda values: values.notna().all()
    )
    eligible = panel[complete_players & panel.target_points.notna()].copy()
    for name in ("decision_cutoff", "target_available_at", "actual_label_available_at"):
        for value in eligible[name]:
            _instant(value)
    known = (pd.to_datetime(eligible.target_available_at, utc=True) <= cutoff) & (
        pd.to_datetime(eligible.actual_label_available_at, utc=True) <= cutoff
    )
    unavailable_events = set(eligible.loc[~known, "event"])
    eligible = eligible[~eligible.event.isin(unavailable_events)]
    if not np.isfinite(eligible.target_points.to_numpy(dtype=float)).all():
        raise ValueError("Finite observed targets required")
    groups: list[dict[str, Any]] = []
    for event, rows in eligible.groupby("event", sort=True):
        origins = {_instant(v) for v in rows.decision_cutoff}
        if len(origins) != 1 or rows.origin_event.nunique() != 1:
            raise ValueError("All target-event fixture rows require one origin")
        groups.append(
            {
                "event": int(cast(Any, event)),
                "origin": next(iter(origins)),
                "end": pd.to_datetime(rows.target_available_at, utc=True).max(),
                "indices": rows.index.tolist(),
            }
        )
    folds = []
    for test in groups:
        previous = [g for g in groups if g["origin"] < test["origin"] and g["end"] < test["origin"]]
        if not previous:
            continue
        validation = max(previous, key=lambda g: g["origin"])
        training = [
            g
            for g in previous
            if g["origin"] < validation["origin"] and g["end"] < validation["origin"]
        ]
        if len(training) < minimum_training_events:
            continue
        folds.append(
            {
                "fold_id": f"lead-{int(panel.lead.iloc[0])}-outer-{test['event']}",
                "lead": int(panel.lead.iloc[0]),
                "train_events": [g["event"] for g in training],
                "validation_events": [validation["event"]],
                "test_events": [test["event"]],
                "indices": {
                    "train": [i for g in training for i in g["indices"]],
                    "validation": validation["indices"],
                    "test": test["indices"],
                },
                "train_target_end": max(g["end"] for g in training).isoformat(),
                "validation_target_end": validation["end"].isoformat(),
                "validation_origin": validation["origin"].isoformat(),
                "test_origin": test["origin"].isoformat(),
                "purged_events_before_test": [
                    g["event"]
                    for g in groups
                    if g["origin"] < test["origin"] and g["end"] >= test["origin"]
                ],
            }
        )
    return folds


def _implementations() -> list[Path]:
    base = Path(__file__).parents[1]
    return [
        Path(__file__),
        *[
            base / name
            for name in (
                "features/multilead.py",
                "features/deadline.py",
                "features/football.py",
                "features/pipeline.py",
                "models/rolling_experiments.py",
                "models/training_eligibility.py",
                "evaluation/metrics.py",
                "providers/collection.py",
            )
        ],
    ]


def training_input(store: Store, payload: dict[str, Any]) -> str:
    spec = payload["protocol"]
    collection = load_collection(store, spec["collection_id"])
    expected = protocol(collection)
    if {k: v for k, v in spec.items() if k != "registered_at"} != {
        k: v for k, v in expected.items() if k != "registered_at"
    }:
        raise ValueError("Unknown direct-lead protocol")
    if store.get("multilead_experiment_protocol", fingerprint(spec)) != spec:
        raise ValueError("Register direct-lead protocol before fitting")
    require_scored_collection(store, collection)
    return fingerprint(
        {
            "protocol": spec,
            "collection_sha256": collection["envelope_sha256"],
            "code": {
                str(p.relative_to(Path(__file__).parents[1])): _sha(p) for p in _implementations()
            },
            "dependency_lock": _sha(Path(__file__).parents[3] / "uv.lock"),
        }
    )


def _metrics(rows: pd.DataFrame, coverage: pd.DataFrame) -> dict[str, Any]:
    fixture = {
        "points": {
            name: forecast_metrics(rows.target_points, rows[name], events=rows.event)
            for name in ("direct_points", "points_5")
        },
        "minutes": {
            name: forecast_metrics(rows.target_minutes, rows[name], events=rows.event)
            for name in ("direct_minutes", "minutes_5")
        },
    }
    keys = ["lead", "event", "origin_event", "player_id"]
    grouped = rows.groupby(keys, as_index=False)[
        ["target_points", "direct_points", "points_5"]
    ].sum()
    eligible = coverage[(coverage.coverage_status == "complete") & coverage.event_finalized]
    grouped = grouped.merge(eligible[keys], on=keys, how="inner", validate="one_to_one")
    blanks = coverage[
        (coverage.coverage_status == "blank_event")
        & coverage.event_finalized
        & coverage.event.isin(rows.event)
    ]
    if not blanks.empty:
        empty = blanks[keys].copy()
        empty[["target_points", "direct_points", "points_5"]] = 0.0
        grouped = pd.concat([grouped, empty], ignore_index=True)
    return {
        "player_fixture": fixture,
        "player_event": {
            name: forecast_metrics(grouped.target_points, grouped[name], events=grouped.event)
            for name in ("direct_points", "points_5")
        }
        if len(grouped)
        else None,
        "explicit_blank_player_events": len(blanks),
        "by_position": {
            str(position): {
                name: forecast_metrics(part.target_points, part[name], events=part.event)
                for name in ("direct_points", "points_5")
            }
            for position, part in rows.groupby("position")
        },
        "probability_calibration": "unavailable; these heads predict signed means and minutes only",
        "legal_policy_performance": "unavailable; no reconciled same-state prospective comparison",
    }


def train_job(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    spec = payload["protocol"]
    identity = training_input(store, payload)
    root = data_dir() / "models/multilead_experiments" / identity[:24]
    root.mkdir(parents=True, exist_ok=True)
    if (root / "report.json").exists():
        retained = json.loads((root / "report.json").read_text())
        if any(_sha(root / path) != digest for path, digest in retained["files"].items()):
            raise ValueError("Retained direct-lead report checksum mismatch")
        return {**retained, "_artifacts": [("multilead_experiment", identity, retained)]}
    _json(root / "protocol.json", spec)
    for path in _implementations():
        destination = root / "implementation" / path.relative_to(Path(__file__).parents[1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and _sha(destination) != _sha(path):
            raise ValueError("Retained direct-lead implementation mismatch")
        if not destination.exists():
            destination.write_bytes(path.read_bytes())
    (root / "uv.lock").write_bytes((Path(__file__).parents[3] / "uv.lock").read_bytes())
    collection = load_collection(store, spec["collection_id"])
    panel, coverage = direct_panel(collection, spec["leads"])
    _json(
        root / "inputs.json",
        {
            "identity": identity,
            "panel_sha256": fingerprint(json.loads(panel.to_json(orient="split"))),
            "coverage_sha256": fingerprint(json.loads(coverage.to_json(orient="split"))),
        },
    )
    panel.to_parquet(root / "historical_features.parquet", index=False)
    coverage.to_parquet(root / "coverage.parquet", index=False)
    outputs, folds, support = [], [], {}
    for lead in spec["leads"]:
        part = panel[panel.lead == lead]
        lead_folds = chronological_folds(part, spec["as_of"], spec["minimum_training_events"])
        support[str(lead)] = {
            "status": "evaluated_research"
            if lead_folds
            else "unavailable_insufficient_purged_history",
            "outer_events": [f["test_events"][0] for f in lead_folds],
            "eligible_observed_events": sorted(
                int(v) for v in part.loc[part.target_points.notna(), "event"].unique()
            ),
            "reason": None
            if lead_folds
            else "No complete train/validation/outer split after both target-completion embargoes; more historical events required",
        }
        for fold in lead_folds:
            outer = part.loc[fold["indices"]["test"]].copy()
            for target in spec["targets"]:
                config = {
                    **spec["configuration"],
                    "name": f"direct_{target}",
                    "features": spec["features"],
                }
                target_panel = part.copy()
                if target == "minutes":
                    target_panel["target_points"] = target_panel["target_minutes"]
                result = _fit_unit(root, identity, fold, config, spec, target_panel)
                if (
                    result.index.size != len(outer)
                    or result[["player_id", "fixture_id"]].to_records(index=False).tolist()
                    != outer[["player_id", "fixture_id"]].to_records(index=False).tolist()
                ):
                    raise ValueError("Direct-lead checkpoint row identity mismatch")
                raw = result.predicted_points.to_numpy()
                outer[f"direct_{target}_raw"] = raw
                outer[f"direct_{target}"] = np.clip(raw, 0, 90) if target == "minutes" else raw
                outer[f"{target}_selected_iterations"] = result.selected_iterations.to_numpy()
            outer["fold_id"] = fold["fold_id"]
            outputs.append(outer)
            folds.append(fold)
    _json(root / "splits.json", folds)
    if not outputs:
        raise ValueError(
            "No eligible direct-lead folds; retain registration and acquire more history"
        )
    predictions = pd.concat(outputs, ignore_index=True)
    predictions.to_parquet(root / "outer_predictions.parquet", index=False)
    report = {
        "experiment_id": identity,
        "status": "evaluated_research",
        "collection_id": collection["collection_id"],
        "collection_sha256": collection["envelope_sha256"],
        "directory": str(root),
        "protocol": spec,
        "support_by_lead": support,
        "folds": folds,
        "metrics_by_lead": {
            str(int(cast(Any, lead))): _metrics(rows, coverage[coverage.lead == lead])
            for lead, rows in predictions.groupby("lead")
        },
        "runtime_seconds": time.monotonic() - started,
        "environment": {
            "python": platform.python_version(),
            "packages": {
                name: version(name) for name in ("catboost", "numpy", "pandas", "pyarrow")
            },
        },
        "active": False,
        "champion_promoted": False,
        "serving_refit": False,
        "coverage_counts": {
            str(int(cast(Any, lead))): {
                str(k): int(v) for k, v in rows.coverage_status.value_counts().items()
            }
            for lead, rows in coverage.groupby("lead")
        },
        "limitations": [
            "Historical schedule, position, club membership and player universe are reconstructed from one capture, not verified at origin",
            "Historical label availability assumes kickoff+one day; actual captures gate eligibility as of collection time only",
            "Each lead freezes all player history at its origin; intervening future outcomes are excluded",
            "Short current-season history cannot qualify all requested leads; missing leads remain unavailable",
            "Minutes are clipped per fixture to 0..90 with raw values retained; no calibrated future opportunity probabilities or joint distribution",
            "No future serving freeze or modification of registered GW9/GW10 studies; no legal policy or rank improvement established",
        ],
        "files": {
            str(p.relative_to(root)): _sha(p)
            for p in root.rglob("*")
            if p.is_file()
            and p.name != "report.json"
            and not any(v.startswith(".") for v in p.relative_to(root).parts)
        },
    }
    _json(root / "report.json", report)
    return {**report, "_artifacts": [("multilead_experiment", identity, report)]}
