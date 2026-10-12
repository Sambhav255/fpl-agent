"""Eligible deterministic mean blend; never average marginal quantiles."""

from __future__ import annotations

import hashlib
import json
from math import isclose, isfinite
from pathlib import Path

import pandas as pd

from fpl_app.contracts import Projection, ProjectionRun
from fpl_app.domain.rules import RULES
from fpl_app.features.pipeline import utc
from fpl_app.storage import fingerprint, utcnow


def blend_runs(
    runs: dict[str, ProjectionRun],
    weights: dict[str, float],
    *,
    validated_artifact_id: str,
    evaluation_reference: str,
) -> ProjectionRun:
    if not runs or not weights or not validated_artifact_id or not evaluation_reference:
        raise ValueError("Explicit evaluated ensemble artifact required")
    if any(
        type(w) not in (int, float) or not isfinite(w) or w < 0 for w in weights.values()
    ) or not isclose(sum(weights.values()), 1.0, abs_tol=1e-8):
        raise ValueError("Invalid nonnegative normalized weights")
    if not {name for name, w in weights.items() if w > 0} <= runs.keys():
        raise ValueError("Positively weighted forecast unavailable")
    active = {name: runs[name] for name, w in weights.items() if w > 0}
    if not active:
        raise ValueError("No positively weighted eligible forecasts")
    first = next(iter(active.values()))

    def exposures(run):
        return {(p.player_id, p.fixture_id, p.event): p for p in run.projections}

    common = exposures(first)
    for run in active.values():
        if (
            run.snapshot_id,
            run.source_cutoff,
            run.prediction_origin,
            run.rules_version,
            run.data_mode,
            run.horizon_events,
            run.player_universe_ids,
            [f.model_dump() for f in run.fixtures],
        ) != (
            first.snapshot_id,
            first.source_cutoff,
            first.prediction_origin,
            first.rules_version,
            first.data_mode,
            first.horizon_events,
            first.player_universe_ids,
            [f.model_dump() for f in first.fixtures],
        ):
            raise ValueError("Ensemble input origin, coverage, rules or horizon differ")
        if len(exposures(run)) != len(run.projections) or set(exposures(run)) != set(common):
            raise ValueError("Ensemble fixture coverage differs")
    projections = []
    maps = {name: exposures(run) for name, run in active.items()}
    for key in sorted(common):
        mean = sum(weights[name] * rows[key].expected_points for name, rows in maps.items())
        minutes = sum(weights[name] * rows[key].expected_minutes for name, rows in maps.items())
        projections.append(
            Projection(
                player_id=key[0],
                fixture_id=key[1],
                event=key[2],
                expected_points=mean,
                expected_minutes=minutes,
                assumptions=[
                    "Eligible weighted unconditional means; marginal probabilities/quantiles unavailable without evaluated mixture distributions"
                ],
            )
        )
    return first.model_copy(
        update={
            "projection_run_id": "ensemble-"
            + fingerprint(
                {
                    "artifact_id": validated_artifact_id,
                    "evaluation_reference": evaluation_reference,
                    "weights": weights,
                    "runs": {name: run.model_dump(mode="json") for name, run in active.items()},
                }
            )[:24],
            "model_family": "ensemble",
            "requested_provider": "ensemble",
            "resolved_provider": "ensemble",
            "artifact_id": validated_artifact_id,
            "evaluation_reference": evaluation_reference,
            "artifact_manifest_sha256": None,
            "evidence_mode": "unverified_research",
            "model_status": "experimental",
            "projections": projections,
            "joint_scenario_reference": None,
            "warnings": [
                *first.warnings,
                "Experimental mean blend; supplied evaluation reference needs independent verification; no promotion",
            ],
        }
    )


def fit_mean_ensemble(
    validation: pd.DataFrame, test: pd.DataFrame, model_columns: list[str], output: Path
):
    """Fit weights on validation only, then retain untouched chronological scores."""
    from fpl_app.evaluation.metrics import fit_ensemble, forecast_metrics

    required = {
        "target_available_at",
        "event",
        "partition",
        "decision_cutoff",
        "target_points",
        *model_columns,
    }
    if (
        not required <= set(validation)
        or not required <= set(test)
        or validation.empty
        or test.empty
        or set(test.partition) != {"test"}
    ):
        raise ValueError("Explicit separate chronological ensemble partitions required")
    fitting_cutoff = max(utc(t) for t in validation.target_available_at)
    if fitting_cutoff > utc(utcnow()):
        raise ValueError("Validation labels are not yet available for fitting")
    if max(utc(t) for t in validation.decision_cutoff) >= min(
        utc(t) for t in test.decision_cutoff
    ) or fitting_cutoff >= min(utc(t) for t in test.decision_cutoff):
        raise ValueError("Validation labels overlap held-out origin")
    if "train_target_end" not in test or any(
        utc(t) >= utc(c) for t, c in zip(test.train_target_end, test.decision_cutoff)
    ):
        raise ValueError("Held-out base model fitting overlaps origin")
    fitted = fit_ensemble(validation, model_columns)
    weights = fitted["weights"]
    blended = sum(test[name].to_numpy(dtype=float) * weights[name] for name in model_columns)
    report = {
        "partition": "test",
        "blend": forecast_metrics(test.target_points, blended, events=test.event),
        "individuals": {
            name: forecast_metrics(test.target_points, test[name], events=test.event)
            for name in model_columns
        },
        "validation": fitted,
        "test_origin_count": test.decision_cutoff.nunique(),
        "promotion": "retain_champion_pending_qualified_evidence",
        "distribution_metrics": None,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "weights.json").write_text(json.dumps(weights, sort_keys=True, indent=2))
    (output / "evaluation.json").write_text(json.dumps(report, sort_keys=True, indent=2))
    inputs = {
        "validation": validation.to_dict("records"),
        "test": test.to_dict("records"),
        "models": model_columns,
    }
    manifest = {
        "artifact_id": "ensemble/" + fingerprint(inputs),
        "model_family": "ensemble",
        "status": "evaluated_research",
        "rules_version": RULES.version,
        "fitting_labels_available_at": fitting_cutoff.isoformat(),
        "available_at": utcnow(),
        "input_sha256": fingerprint(inputs),
        "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()},
        "active": False,
        "limitations": [
            "Caller base forecast provenance still requires audit",
            "Mean blend only; no calibrated mixture distribution or forced family inclusion",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2))
    return manifest, report


def ensemble_run(artifact: Path, runs: dict[str, ProjectionRun]) -> ProjectionRun:
    """Load a real fitted mean blend; never inherit another family's evidence."""
    if artifact.is_symlink() or (artifact / "manifest.json").is_symlink():
        raise ValueError("Unsafe ensemble artifact")
    raw = (artifact / "manifest.json").read_bytes()
    meta = json.loads(raw)
    if (
        meta.get("model_family") != "ensemble"
        or meta.get("status") != "evaluated_research"
        or meta.get("rules_version") != RULES.version
    ):
        raise ValueError("Evaluated compatible ensemble artifact required")
    if utc(meta["fitting_labels_available_at"]) > utc(meta["available_at"]):
        raise ValueError("Fitting labels unavailable when artifact was created")
    hashes = meta.get("artifacts", {})
    if not {"weights.json", "evaluation.json"} <= set(hashes):
        raise ValueError("Incomplete ensemble artifact")
    for name, digest in hashes.items():
        target = artifact / name
        if (
            Path(name).name != name
            or target.is_symlink()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Ensemble checksum mismatch")
    weights = json.loads((artifact / "weights.json").read_text())
    result = blend_runs(
        runs,
        weights,
        validated_artifact_id=meta["artifact_id"],
        evaluation_reference=hashes["evaluation.json"],
    )
    if any(
        utc(meta["available_at"]) > utc(runs[name].prediction_origin or runs[name].source_cutoff)
        for name, weight in weights.items()
        if weight > 0
    ):
        raise ValueError("Ensemble artifact unavailable at forecast origin")
    return result.model_copy(
        update={
            "artifact_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "lifecycle_state": "experimental",
            "warnings": [*result.warnings, *meta["limitations"]],
        }
    )
