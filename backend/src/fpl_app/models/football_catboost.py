"""Standalone immutable research challenger. No registry activation or dependency imports at startup."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from fpl_app.features.football import CATEGORICAL, FEATURE_VERSION, FEATURES, archive_panel


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    with path.open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)


def errors(target: Any, prediction: Any) -> dict[str, float]:
    residual = np.asarray(prediction) - np.asarray(target)
    return {
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt((residual**2).mean())),
        "bias": float(residual.mean()),
    }


def _fit(
    panel: pd.DataFrame,
    output_root: Path,
    provenance: dict[str, Any],
    partitions: dict[str, list[int]],
    rules: str,
) -> Path:
    from catboost import CatBoostRegressor

    executed = datetime.now(UTC).isoformat()
    run = output_root / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    subsets = {name: panel[panel.event.isin(events)].copy() for name, events in partitions.items()}
    if any(s.empty for s in subsets.values()):
        raise ValueError("empty chronological partition")
    train, validation, calibration, test = (
        subsets[n] for n in ["train", "validation", "calibration", "test"]
    )
    # Purge labels whose assumed availability crosses the next fitting/forecast origin.
    for name, next_name in [
        ("train", "validation"),
        ("validation", "calibration"),
        ("calibration", "test"),
    ]:
        boundary = pd.to_datetime(subsets[next_name].decision_cutoff, utc=True).min()
        subsets[name] = subsets[name][
            pd.to_datetime(subsets[name].target_available_at, utc=True) < boundary
        ]
    train, validation, calibration = (subsets[n] for n in ["train", "validation", "calibration"])
    if any(s.empty for s in [train, validation, calibration]):
        raise ValueError("timing purge emptied development partition")
    models = {}
    targets = {
        "points": "target_points",
        "minutes": "target_minutes",
        "appearance": "appearance",
        "sixty": "sixty",
        "start": "start",
        "q10": "target_points",
        "q50": "target_points",
        "q90": "target_points",
    }
    for frame in [train, validation, calibration, test]:
        frame["appearance"] = (frame.target_minutes > 0).astype(float)
        frame["sixty"] = (frame.target_minutes >= 60).astype(float)
        frame["start"] = frame.target_start
    for head, target in targets.items():
        if target == "start" and train[target].isna().any():
            continue
        loss = f"Quantile:alpha={int(head[1:]) / 100}" if head.startswith("q") else "RMSE"
        model = CatBoostRegressor(
            iterations=180,
            depth=5,
            learning_rate=0.06,
            loss_function=loss,
            random_seed=43,
            thread_count=2,
            verbose=False,
            allow_writing_files=False,
            allow_const_label=True,
        )
        model.fit(
            train[FEATURES],
            train[target],
            cat_features=CATEGORICAL,
            eval_set=(validation[FEATURES], validation[target]),
            early_stopping_rounds=25,
        )
        model.save_model(str(run / f"{head}.cbm"))
        reloaded = CatBoostRegressor()
        reloaded.load_model(str(run / f"{head}.cbm"))
        if not np.array_equal(model.predict(test[FEATURES]), reloaded.predict(test[FEATURES])):
            raise ValueError("reload changed predictions")
        models[head] = reloaded
    # Calibration-only additive reliability adjustment; explicit small-sample limitation.
    offsets = {
        head: float(
            calibration[target].mean()
            - np.clip(models[head].predict(calibration[FEATURES]), 0, 1).mean()
        )
        for head, target in [("appearance", "appearance"), ("sixty", "sixty"), ("start", "start")]
        if head in models
    }
    write_json(run / "calibration.json", offsets)
    predicted = _predict(models, offsets, test)
    test = test.reset_index(drop=True)
    test = pd.concat([test, predicted], axis=1)
    population = float(train.target_points.mean())
    comparisons = {
        "football_catboost": errors(test.target_points, test.points_mean),
        "rolling_points_5": errors(test.target_points, test.points_5),
        "population_train": errors(test.target_points, np.full(len(test), population)),
        "zero": errors(test.target_points, np.zeros(len(test))),
    }
    brier = {
        name: float(((test[col] - (test.target_minutes >= threshold).astype(float)) ** 2).mean())
        for name, col, threshold in [
            ("appearance", "appearance_probability", 1),
            ("sixty", "sixty_probability", 60),
        ]
    }
    report = {
        "comparators": comparisons,
        "probability_brier": brier,
        "minutes": errors(test.target_minutes, test.minutes_mean),
        "position": {
            str(k): errors(g.target_points, g.points_mean) for k, g in test.groupby("position")
        },
        "appearance": {
            str(k): errors(g.target_points, g.points_mean)
            for k, g in test.groupby(test.target_minutes > 0)
        },
        "likely_starters": errors(
            test.loc[test.sixty_5 >= 0.6, "target_points"],
            test.loc[test.sixty_5 >= 0.6, "points_mean"],
        )
        if (test.sixty_5 >= 0.6).any()
        else None,
        "events": {
            str(k): errors(g.target_points, g.points_mean) for k, g in test.groupby("event")
        },
        "lead_time": {"1": comparisons["football_catboost"]},
        "interval_80_coverage": float(
            ((test.target_points >= test.q10) & (test.target_points <= test.q90)).mean()
        ),
        "interval_width": float((test.q90 - test.q10).mean()),
        "pinball": {
            str(q): float(
                np.maximum(
                    q * (test.target_points - test[c]), (q - 1) * (test.target_points - test[c])
                ).mean()
            )
            for q, c in [(0.1, "q10"), (0.5, "q50"), (0.9, "q90")]
        },
        "evaluation_kind": "retrospective_assumed",
        "champion_promoted": False,
    }
    write_json(run / "evaluation.json", report)
    panel.to_parquet(run / "features.parquet", index=False)
    test.to_parquet(run / "test_predictions.parquet", index=False)
    mappings = (
        panel[["player_key", "player_id"]]
        .drop_duplicates()
        .assign(
            season=provenance["season"],
            mapping_status="same_season_identity_only",
            source_ref=provenance["source_ref"],
        )
    )
    mappings.to_parquet(run / "mappings.parquet", index=False)
    available = datetime.now(UTC).isoformat()
    boundaries = {
        name: {
            "events": partitions[name],
            "rows": len(frame),
            "information_cutoff": frame.target_available_at.max(),
            "origin_min": frame.decision_cutoff.min(),
            "origin_max": frame.decision_cutoff.max(),
        }
        for name, frame in [
            ("train", train),
            ("validation", validation),
            ("calibration", calibration),
            ("test", test),
        ]
    }
    manifest = {
        "family": "football_catboost",
        "model_family": "football_catboost",
        "data_mode": "live",
        "artifact_id": run.name,
        "mode": "experimental",
        "data_evidence_mode": "retrospective_assumed",
        "executed_at": executed,
        "available_at": available,
        "artifact_available_at": available,
        "information_cutoff": max(
            boundaries[n]["information_cutoff"] for n in ["train", "validation", "calibration"]
        ),
        "training_cutoff": provenance.get("captured_at", executed),
        "current_training_data_available_at": provenance.get("captured_at", executed),
        "supported_horizon": 1,
        "feature_version": FEATURE_VERSION,
        "mapping_version": "season-scoped-explicit-v1",
        "rules_version": rules,
        "partitions": boundaries,
        "provenance": provenance,
        "evaluation_reference": "evaluation.json",
        "active": False,
        "files": {p.name: checksum(p) for p in sorted(run.iterdir())},
        "limitations": [
            "Archive publication timing, fixture versions, positions and clubs are assumed, not historically verified",
            "Cutoff is earliest kickoff minus 48h; labels usable at kickoff plus 7d",
            "Archive listed exposures only; missing rows are not nonappearances; no blanks inferred",
            "One fixture/event ahead only; no strategy replay or champion gate",
            "Quantile intervals and calibration need broader prospective validation",
            "Same-season IDs only; current rule mismatch requires separate current-era fit",
        ],
    }
    manifest["artifacts"] = manifest["files"]
    write_json(run / "manifest.json", manifest)
    return run


def _predict(
    models: dict[str, Any], offsets: dict[str, float], features: pd.DataFrame
) -> pd.DataFrame:
    p = {head: model.predict(features[FEATURES]) for head, model in models.items()}
    appearance = np.clip(p["appearance"] + offsets["appearance"], 0, 1)
    sixty = np.minimum(appearance, np.clip(p["sixty"] + offsets["sixty"], 0, 1))
    quantiles = np.sort(np.stack([p["q10"], p["q50"], p["q90"]]), axis=0)
    return pd.DataFrame(
        {
            "points_mean": p["points"],
            "minutes_mean": np.clip(p["minutes"], 0, 90),
            "appearance_probability": appearance,
            "sixty_probability": sixty,
            "start_probability": np.minimum(
                appearance, np.clip(p["start"] + offsets["start"], 0, 1)
            )
            if "start" in p
            else np.nan,
            "q10": quantiles[0],
            "points_median": quantiles[1],
            "q50": quantiles[1],
            "q90": quantiles[2],
        }
    )


def train_experiment(csv_path: Path, output_root: Path, source_commit: str) -> Path:
    source = json.loads((csv_path.parent / "source.json").read_text())
    if source["git_commit"] != source_commit or source["sha256"] != checksum(csv_path):
        raise ValueError("pinned source mismatch")
    panel = archive_panel(str(csv_path))
    return _fit(
        panel,
        output_root,
        {
            **source,
            "source_ref": "sha256:" + checksum(csv_path),
            "source_manifest_sha256": checksum(csv_path.parent / "source.json"),
        },
        {
            "train": list(range(1, 7)),
            "validation": [7, 8],
            "calibration": [9, 10],
            "test": list(range(11, 17)),
        },
        "fpl-2024-25",
    )


def forecast_frozen(
    run_dir: Path, features: pd.DataFrame, mappings: pd.DataFrame, prediction_origin: str
) -> pd.DataFrame:
    from catboost import CatBoostRegressor

    manifest = json.loads((run_dir / "manifest.json").read_text())
    origin = pd.Timestamp(prediction_origin)
    if origin.tzinfo is None or origin < pd.Timestamp(manifest["artifact_available_at"]):
        raise ValueError("artifact did not exist at origin")
    for name, sha in manifest["files"].items():
        if checksum(run_dir / name) != sha:
            raise ValueError("artifact checksum mismatch")
    required = {
        *FEATURES,
        "player_id",
        "player_key",
        "event",
        "fixture_id",
        "decision_cutoff",
        "source_available_at",
        "source_ref",
        "feature_version",
    }
    if features.empty or not required <= set(features):
        raise ValueError("incomplete frozen feature bundle")
    if (
        not features.rule_era.eq(manifest["rules_version"]).all()
        or not features.feature_version.eq(FEATURE_VERSION).all()
    ):
        raise ValueError("scoring era or feature version incompatible; current-era fit required")
    if (
        not pd.to_datetime(features.decision_cutoff, utc=True).eq(origin).all()
        or (pd.to_datetime(features.source_available_at, utc=True) > origin).any()
    ):
        raise ValueError("future/unfrozen source")
    if features.event.nunique() != 1 or features.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("unsupported horizon or duplicate fixture")
    if (
        not {"current_player_id", "player_key", "season", "source_ref"} <= set(mappings)
        or mappings.duplicated("current_player_id").any()
    ):
        raise ValueError("explicit unique current-ID mappings required")
    joined = features.merge(
        mappings,
        left_on=["player_id", "player_key"],
        right_on=["current_player_id", "player_key"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_mapping"),
    )
    if joined.season.isna().any() or joined.source_ref_mapping.isna().any():
        raise ValueError("unmapped current player")
    expected_season = manifest["provenance"]["season"]
    if (
        not joined.season.eq(expected_season).all()
        or not joined.player_key.str.startswith(
            (f"fpl:{expected_season}:", f"official_fpl:{expected_season}:element:")
        ).all()
    ):
        raise ValueError("cross-season mapping unsupported")
    models = {}
    for name in manifest["files"]:
        if name.endswith(".cbm"):
            model = CatBoostRegressor()
            model.load_model(str(run_dir / name))
            models[name[:-4]] = model
    predictions = _predict(models, json.loads((run_dir / "calibration.json").read_text()), features)
    return pd.concat(
        [
            features[["player_id", "player_key", "event", "fixture_id"]].reset_index(drop=True),
            predictions,
        ],
        axis=1,
    )


def train_collection_experiment(
    envelope: dict[str, Any],
    output_root: Path,
    rules_version: str,
    bootstrap: dict[str, Any] | None = None,
) -> Path:
    """Small current-era diagnostic; no claim of broad evaluation or promotion."""
    from fpl_app.features.football import collection_frames
    from fpl_app.storage import fingerprint

    content = {k: v for k, v in envelope.items() if k != "envelope_sha256"}
    if fingerprint(content) != envelope["envelope_sha256"] or envelope["data_mode"] != "live":
        raise ValueError("collection checksum/mode invalid")
    if rules_version != f"fpl-{envelope['season'].replace(chr(47), chr(45))}":
        raise ValueError("explicit scoring era must match collection season")
    if "player_mappings" not in envelope:
        if bootstrap is None:
            raise ValueError("retained bootstrap required for explicit current mappings")
        elements = {p["id"]: p for p in bootstrap["elements"]}
        envelope = {
            **envelope,
            "player_mappings": [
                {
                    "provider_player_id": i,
                    "canonical_player_id": f"official_fpl:{envelope['season']}:element:{i}",
                    "position": elements[i]["element_type"],
                }
                for i in envelope["player_ids"]
            ],
        }
    panel, future, mappings = collection_frames(envelope, rules_version)
    provenance = {
        "season": envelope["season"],
        "provider": envelope["provider"],
        "collection_id": envelope["collection_id"],
        "source_ref": envelope["envelope_sha256"],
        "sources": envelope["sources"],
        "captured_at": envelope["captured_at"],
    }
    run = _fit(
        panel,
        output_root,
        provenance,
        {"train": [1, 2], "validation": [3], "calibration": [4], "test": [5]},
        rules_version,
    )
    # Freeze output at actual artifact completion, after captured inputs existed.
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    origin = datetime.now(UTC).isoformat()
    future["decision_cutoff"] = origin
    predictions = forecast_frozen(run, future, mappings, origin)
    future.to_parquet(run / "future_features.parquet", index=False)
    mappings.to_parquet(run / "current_mappings.parquet", index=False)
    predictions.to_parquet(run / "future_predictions.parquet", index=False)
    write_json(
        run / "forecast_origin.json",
        {
            "prediction_origin": origin,
            "input_captured_at": envelope["captured_at"],
            "event": int(future.event.iloc[0]),
            "limitations": [
                "30 selected players, five events; selection-biased tiny retrospective test",
                "Historical role and schedule use current capture; historical availability assumed kickoff+1day",
                "No default promotion, calibrated confidence unavailable",
                "Current-era labels are captured today and legitimate for future fitting; original publication unknown",
            ],
            "files": {
                name: checksum(run / name)
                for name in [
                    "future_features.parquet",
                    "current_mappings.parquet",
                    "future_predictions.parquet",
                ]
            },
            "artifact_manifest_sha256": checksum(manifest_path),
            "rules_version": manifest["rules_version"],
        },
    )
    return run
