"""Bounded, origin-frozen real football research; never an activation command."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from fpl_app.features.football import reconstructed_comparators
from fpl_app.models.football_catboost import checksum, errors, write_json

BASE = ["position", "lead", "points_5", "history_count"]
FIXTURE = [
    "opponent",
    "home",
    "team_for_5",
    "team_against_5",
    "opponent_for_5",
    "opponent_against_5",
]
MINUTES = ["minutes_5", "appearance_5", "starts_5", "starts_missing"]
CONGESTION = ["rest_days", "fixtures_next_7d"]
ROLE_ADVANCED = ["club", "xg_90", "xa_90", "saves_90"]
REGISTERED_ABLATIONS = {
    "points_position": BASE,
    "fixture_team_strength": BASE + FIXTURE,
    "minutes_starts": BASE + FIXTURE + MINUTES,
    "congestion": BASE + FIXTURE + MINUTES + CONGESTION,
    "role_permitted_advanced": BASE + FIXTURE + MINUTES + CONGESTION + ROLE_ADVANCED,
}
CATEGORIES = {"position", "club", "opponent", "home"}
CONFIG = {
    "iterations": 180,
    "depth": 5,
    "learning_rate": 0.06,
    "random_seed": 43,
    "thread_count": 2,
    "loss_function": "RMSE",
}
PARTITIONS = {
    "train": list(range(2, 19)),
    "validation": list(range(19, 22)),
    "calibration": list(range(22, 25)),
    "test": list(range(25, 32)),
}


def experiment_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ablations": REGISTERED_ABLATIONS,
        "config": CONFIG,
        "partitions": PARTITIONS,
        "selected_method": "role_permitted_advanced",
        "selection": {
            "early_stopping_rounds": 25,
            "selection_partition": "validation",
            "ensemble_weight_partition": "calibration",
            "final_test_never_selects_method": True,
        },
        "maximum_lead": 8,
        "origin": "event_earliest_kickoff_minus_48h_assumed",
        "historical_label_available": "fixture_kickoff_plus_7d_assumed",
        "player_universe": "seen_in_origin_usable_history; future_joins_excluded",
        "hyperparameter_search": False,
    }


def build_archive_multilead(csv_path: Path, maximum_lead: int = 8) -> pd.DataFrame:
    """Direct lead-specific targets share history frozen at the original origin.

    Final archive schedule reconstruction is explicitly assumed. Later observed
    player role, membership, outcomes and statistics are never feature inputs.
    Missing future rows remain missing, and are never manufactured zeros.
    """
    if not 1 <= maximum_lead <= 8:
        raise ValueError("maximum lead must be between one and eight")
    raw = pd.read_csv(csv_path)
    required = {
        "GW",
        "element",
        "fixture",
        "kickoff_time",
        "team",
        "position",
        "minutes",
        "total_points",
        "opponent_team",
        "was_home",
        "team_h_score",
        "team_a_score",
    }
    if not required <= set(raw):
        raise ValueError("archive lacks covered outcomes and schedule")
    raw = raw[raw.position.isin(["GK", "DEF", "MID", "FWD"])].copy()
    raw = raw.rename(
        columns={
            "GW": "event",
            "element": "player_id",
            "fixture": "fixture_id",
            "kickoff_time": "kickoff",
            "total_points": "points",
        }
    )
    if raw.duplicated(["player_id", "fixture_id"]).any():
        raise ValueError("duplicate player fixture archive rows")
    if raw[["points", "minutes", "kickoff"]].isna().any().any():
        raise ValueError("missing outcomes are not zero")
    raw["kickoff"] = pd.to_datetime(raw.kickoff, utc=True)
    raw["available_at"] = raw.kickoff + pd.Timedelta(days=7)
    raw["player_key"] = raw.player_id.map(lambda i: f"fpl:2024-25:{i}")
    raw["goals"] = raw.get("goals_scored", 0)
    for column in [
        "starts",
        "expected_goals",
        "expected_assists",
        "saves",
        "assists",
        "clean_sheets",
    ]:
        if column not in raw:
            raw[column] = np.nan
    club_ids: dict[str, int] = {}
    for _, fixture_rows in raw.groupby("fixture_id"):
        clubs = fixture_rows.drop_duplicates("team")
        if len(clubs) != 2:
            continue
        first, second = clubs.iloc[0], clubs.iloc[1]
        for club, identifier in [
            (first.team, int(second.opponent_team)),
            (second.team, int(first.opponent_team)),
        ]:
            if club in club_ids and club_ids[club] != identifier:
                raise ValueError("conflicting explicit season club mapping")
            club_ids[club] = identifier
    if set(raw.team.unique()) != set(club_ids):
        raise ValueError("incomplete season club mapping")
    raw["club"] = raw.team.map(club_ids).astype(str)
    raw["goals_for"] = np.where(raw.was_home, raw.team_h_score, raw.team_a_score)
    raw["goals_against"] = np.where(raw.was_home, raw.team_a_score, raw.team_h_score)
    origins = raw.groupby("event").kickoff.min() - pd.Timedelta(hours=48)
    schedule = raw.drop_duplicates(["club", "fixture_id"])
    rows: list[dict[str, Any]] = []
    for origin_event, origin in origins.items():
        usable = raw[(raw.available_at <= origin) & (raw.event < origin_event)]
        if usable.empty:
            continue
        usable = usable.sort_values("kickoff")
        latest = usable.groupby("player_id").tail(1).set_index("player_id")
        recent = usable.groupby("player_id").tail(5)
        histories = {i: group for i, group in usable.groupby("player_id")}
        recent_groups = {i: group for i, group in recent.groupby("player_id")}
        team_history = usable.drop_duplicates(["club", "fixture_id"]).groupby("club").tail(5)
        strength = team_history.groupby("club")[["goals_for", "goals_against"]].mean()
        future = raw[
            raw.event.between(int(origin_event), int(origin_event) + maximum_lead - 1)
            & raw.player_id.isin(latest.index)
        ]
        comparator_cache: dict[tuple[int, str], dict[str, float]] = {}
        frozen_cache: dict[int, dict[str, Any]] = {}
        roles = latest.to_dict("index")
        strengths = strength.to_dict("index")
        congestion = (
            schedule[
                (schedule.kickoff >= origin) & (schedule.kickoff < origin + pd.Timedelta(days=7))
            ]
            .groupby("club")
            .size()
            .to_dict()
        )
        for target in future.to_dict("records"):
            player_id = target["player_id"]
            role = roles[player_id]
            if target["club"] != role["club"]:
                continue
            history = histories[player_id]
            club = str(role["club"])
            opponent = str(target["opponent_team"])
            exposure = {
                "player_key": role["player_key"],
                "position": role["position"],
                "club": club,
                "opponent": opponent,
                "home": str(target["was_home"]),
                "fixture_id": target["fixture_id"],
                "event": target["event"],
            }
            if player_id not in frozen_cache:
                rec = recent_groups[player_id]
                minutes = max(float(history.minutes.sum()), 90)
                team = strengths.get(club, {})
                frozen_cache[player_id] = {
                    "player_key": str(role["player_key"]),
                    "position": str(role["position"]),
                    "club": club,
                    "decision_cutoff": origin.isoformat(),
                    "history_available_max": history.available_at.max().isoformat(),
                    "history_count": len(history),
                    "points_5": float(rec.points.mean()),
                    "minutes_5": float(rec.minutes.mean()),
                    "appearance_5": float((rec.minutes > 0).mean()),
                    "starts_5": float(rec.starts.mean()) if rec.starts.notna().any() else 0,
                    "starts_missing": int(not rec.starts.notna().any()),
                    "rest_days": min(60, (origin - history.kickoff.max()).total_seconds() / 86400),
                    "fixtures_next_7d": int(congestion.get(club, 0)),
                    "xg_90": 90 * float(history.expected_goals.sum(min_count=1)) / minutes,
                    "xa_90": 90 * float(history.expected_assists.sum(min_count=1)) / minutes,
                    "saves_90": 90 * float(history.saves.sum(min_count=1)) / minutes,
                    "team_for_5": float(team.get("goals_for", np.nan)),
                    "team_against_5": float(team.get("goals_against", np.nan)),
                }
            opp = strengths.get(opponent, {})
            row = {
                **frozen_cache[player_id],
                "origin_event": int(origin_event),
                "event": int(target["event"]),
                "lead": int(target["event"] - origin_event + 1),
                "player_id": int(player_id),
                "fixture_id": int(target["fixture_id"]),
                "opponent": opponent,
                "home": str(target["was_home"]),
                "target_available_at": target["available_at"].isoformat(),
                "target_points": float(target["points"]),
                "target_minutes": int(target["minutes"]),
                "opponent_for_5": float(opp.get("goals_for", np.nan)),
                "opponent_against_5": float(opp.get("goals_against", np.nan)),
            }
            # Baseline is evaluated on the identical target universe; statistics
            # are origin aggregates, not final season bootstrap totals.
            key = (int(player_id), str(target["was_home"]))
            if key not in comparator_cache:
                comparator_cache[key] = reconstructed_comparators(history, exposure, origin)
            row.update(comparator_cache[key])
            rows.append(row)
    return pd.DataFrame(rows)


def partition_panel(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frames = {
        name: panel[panel.origin_event.isin(events)].copy() for name, events in PARTITIONS.items()
    }
    for name, next_name in [
        ("train", "validation"),
        ("validation", "calibration"),
        ("calibration", "test"),
    ]:
        if frames[next_name].empty:
            raise ValueError("insufficient chronological origin coverage")
        boundary = pd.to_datetime(frames[next_name].decision_cutoff, utc=True).min()
        frames[name] = frames[name][
            pd.to_datetime(frames[name].target_available_at, utc=True) < boundary
        ]
    if any(frame.empty for frame in frames.values()):
        raise ValueError("timing purge emptied experiment partition")
    return frames


def metric_table(frame: pd.DataFrame, methods: list[str]) -> dict[str, Any]:
    return {
        name: {"rows": len(frame), **errors(frame.target_points, frame[name])} for name in methods
    }


def run_archive_experiment(csv_path: Path, output_root: Path, maximum_lead: int = 8) -> Path:
    from catboost import CatBoostRegressor

    from fpl_app.evaluation.metrics import block_difference, fit_ensemble

    source_path = csv_path.parent / "source.json"
    source = json.loads(source_path.read_text())
    if source.get("sha256") != checksum(csv_path) or source.get("season") != "2024-25":
        raise ValueError("retained source hash or scoring regime mismatch")
    contract = experiment_contract()
    contract["maximum_lead"] = maximum_lead
    run = output_root / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    # Registration is written before loading targets or fitting any candidate.
    write_json(run / "registered_protocol.json", contract)
    panel = build_archive_multilead(csv_path, maximum_lead)
    panel.to_parquet(run / "origin_frozen_panel.parquet", index=False)
    frames = partition_panel(panel)
    train, validation, calibration, test = (frames[n] for n in PARTITIONS)
    for name, frame in frames.items():
        frame["partition"] = name
    fit_end = max(train.target_available_at.max(), validation.target_available_at.max())
    for frame in [calibration, test]:
        frame["train_target_end"] = fit_end
    for method, columns in REGISTERED_ABLATIONS.items():
        model = CatBoostRegressor(**CONFIG, verbose=False, allow_writing_files=False)
        model.fit(
            train[columns],
            train.target_points,
            cat_features=[c for c in columns if c in CATEGORIES],
            eval_set=(validation[columns], validation.target_points),
            early_stopping_rounds=25,
        )
        model.save_model(str(run / f"{method}.cbm"))
        loaded = CatBoostRegressor()
        loaded.load_model(str(run / f"{method}.cbm"))
        for frame in [calibration, test]:
            frame[method] = loaded.predict(frame[columns])
        if not np.array_equal(model.predict(test[columns]), test[method]):
            raise ValueError("reloading changed predictions")
    selected = contract["selected_method"]
    population = float(train.target_points.mean())
    for label, keys in [
        ("position_shrinkage", ["position"]),
        ("club_position_shrinkage", ["club", "position"]),
    ]:
        totals = train.groupby(keys).target_points.agg(["sum", "count"])
        priors = ((totals["sum"] + 20 * population) / (totals["count"] + 20)).to_dict()
        for frame in [calibration, test]:
            frame[label] = [
                priors.get(tuple(row) if len(keys) > 1 else row[0], population)
                for row in frame[keys].itertuples(index=False, name=None)
            ]
    weight_rows = calibration.copy()
    weight_rows["partition"] = "validation"
    ensemble = fit_ensemble(weight_rows, ["app_baseline_reconstructed", selected])
    weights = ensemble["weights"]
    test["mean_blend"] = sum(test[name] * weight for name, weight in weights.items())
    methods = [
        *REGISTERED_ABLATIONS,
        "app_baseline_reconstructed",
        "points_5",
        "rolling_minutes_points",
        "position_shrinkage",
        "club_position_shrinkage",
        "mean_blend",
    ]
    test.to_parquet(run / "test_predictions.parquet", index=False)
    calibration.to_parquet(run / "ensemble_validation_predictions.parquet", index=False)
    write_json(run / "ensemble_weights.json", ensemble)
    report = {
        "status": "evaluated_research",
        "evaluation_kind": "reconstructed_historical_assumed",
        "champion_promoted": False,
        "distinct_actual_seasons": 1,
        "rules_version": "fpl-2024-25",
        "source": source,
        "source_manifest_sha256": checksum(source_path),
        "dataset_sha256": checksum(run / "origin_frozen_panel.parquet"),
        "protocol_sha256": checksum(run / "registered_protocol.json"),
        "selected_method": selected,
        "supported_horizon": maximum_lead,
        "partitions": {
            name: {
                "origin_events": sorted(map(int, frame.origin_event.unique())),
                "target_events": sorted(map(int, frame.event.unique())),
                "rows": len(frame),
                "players": int(frame.player_id.nunique()),
                "origin_min": frame.decision_cutoff.min(),
                "origin_max": frame.decision_cutoff.max(),
                "label_available_max": frame.target_available_at.max(),
            }
            for name, frame in frames.items()
        },
        "metrics": metric_table(test, methods),
        "per_event": {
            str(event): metric_table(group, methods) for event, group in test.groupby("event")
        },
        "per_origin": {
            str(event): metric_table(group, methods)
            for event, group in test.groupby("origin_event")
        },
        "per_position": {
            str(position): metric_table(group, methods)
            for position, group in test.groupby("position")
        },
        "per_lead": {
            str(lead): metric_table(group, methods) for lead, group in test.groupby("lead")
        },
        "ensemble": {**ensemble, "fit_partition": "calibration", "untouched_test": True},
        "uncertainty": block_difference(
            test.target_points, test[selected], test.app_baseline_reconstructed, test.origin_event
        ),
        "limitations": [
            "One actual season; repeated player/lead rows are dependent, not independent seasons",
            "Archive deadlines are assumed earliest kickoff minus 48h; label publication assumed kickoff plus 7d",
            "Final-season fixture schedule is reconstructed; historic fixture availability is unverified",
            "Universe excludes players absent from origin-usable history; missing target rows remain excluded",
            "Historical price, injury and difficulty snapshots unavailable; baseline uses neutral difficulty and unknown availability",
            "Team/position frozen from last usable row; later club changes are excluded",
            "No final-test configuration selection, no current-era deployment or promotion",
            "Origin-block interval is descriptive with overlapping targets; no calibrated probability or distribution claim",
        ],
    }
    write_json(run / "evaluation.json", report)
    # A separately identified latest refit may consume all retained labels only
    # after the untouched evaluation has been written. It remains research-only.
    latest = CatBoostRegressor(**CONFIG, verbose=False, allow_writing_files=False)
    columns = REGISTERED_ABLATIONS[selected]
    latest.fit(
        panel[columns], panel.target_points, cat_features=[c for c in columns if c in CATEGORIES]
    )
    latest.save_model(str(run / "latest_research_refit.cbm"))
    manifest = {
        "model_family": "football_catboost_multilead",
        "model_status": "trained_research",
        "artifact_id": run.name,
        "rules_version": "fpl-2024-25",
        "supported_horizon": maximum_lead,
        "available_at": datetime.now(UTC).isoformat(),
        "evaluation_kind": report["evaluation_kind"],
        "active": False,
        "serving_eligible": False,
        "evaluation_reference": "evaluation.json",
        "selected_method": selected,
        "training_config": CONFIG,
        "latest_refit": "latest_research_refit.cbm",
        "files": {p.name: checksum(p) for p in sorted(run.iterdir()) if p.is_file()},
    }
    write_json(run / "manifest.json", manifest)
    return run
