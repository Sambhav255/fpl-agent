"""Optional genuine multilead TFT windows with origin-frozen fixture evidence.

Separate from legacy one-event artifacts. Every decoder lead uses one origin's
schedule; a later fixture announcement cannot become an earlier known covariate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.domain.rules import RULES
from fpl_app.features.pipeline import known_number, utc
from fpl_app.models.tft_slots import ENCODER_LENGTH, _asof, _player_slots, _point_versions
from fpl_app.storage import fingerprint, utcnow


def multilead_panel(frame: pd.DataFrame, horizon: int, max_slots: int = 3) -> pd.DataFrame:
    if not 1 <= horizon <= 8 or not {"target_available_at", "fixture_available_at"} <= set(frame):
        raise ValueError("Multilead TFT requires dated targets and as-of fixture evidence")
    prepared = _player_slots(frame, max_slots)
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for prepared_item in prepared:
        groups.setdefault(
            (prepared_item["season"], prepared_item["player"], prepared_item["slot"]), []
        ).append(prepared_item)
    result = []
    for (season, player, slot), events in groups.items():
        ordered = sorted(events, key=lambda i: i["event"])
        by_event = {item["event"]: item for item in ordered}
        for origin in ordered:
            origin_event = origin["event"]
            cutoff = utc(origin["decision_cutoff"])
            future = [by_event.get(e) for e in range(origin_event, origin_event + horizon)]
            if any(item is None for item in future) or origin_event + horizon > 39:
                continue
            previous = [i for i in ordered if i["event"] < origin_event][-ENCODER_LENGTH:]
            steps = [None] * (ENCODER_LENGTH - len(previous)) + previous + future
            series = f"{season}:{player}:slot{slot}:origin{origin_event}:h{horizon}"
            for step_index, item in enumerate(steps):
                decoder = step_index >= ENCODER_LENGTH
                source = None if item is None else item["row"]
                schedule_known = source is None or utc(source["fixture_available_at"]) <= cutoff
                exists = (
                    source is not None and source["outcome_state"] != "blank" and schedule_known
                )
                encoder_points, mask = (
                    (0.0, 0.0) if decoder else _asof(_point_versions(source), cutoff)
                )
                target = 0.0
                weight = 0.0
                target_time = None
                if (
                    decoder
                    and source is not None
                    and known_number(source.get("target_points"))
                    and pd.notna(source.get("target_available_at"))
                    and schedule_known
                ):
                    target = float(source["target_points"])
                    weight = 1.0
                    target_time = utc(source["target_available_at"]).isoformat()
                result.append(
                    {
                        "series": series,
                        "player": player,
                        "season": season,
                        "slot": float(slot),
                        "time_idx": step_index,
                        "forecast_origin": origin_event,
                        "source_event": -1 if item is None else item["event"],
                        "fixture_id": int(source["fixture_id"])
                        if source is not None and exists
                        else -1,
                        "fixture_exists": float(exists),
                        "schedule_known": float(schedule_known),
                        "opponent": float(source["opponent"])
                        if source is not None and exists
                        else 0.0,
                        "was_home": float(source["was_home"])
                        if source is not None and exists
                        else 0.0,
                        "lead": float(step_index - ENCODER_LENGTH + 1) if decoder else 0.0,
                        "encoder_points": encoder_points,
                        "observation_mask": mask,
                        "points": target,
                        "weight": weight,
                        "target_available_at": target_time,
                        "decision_cutoff": cutoff.isoformat(),
                    }
                )
    if not result:
        raise ValueError("Insufficient contiguous events for requested decoder horizon")
    return pd.DataFrame(result)


def fit_multilead(
    panel: pd.DataFrame,
    train_end: int,
    validation_end: int,
    horizon: int,
    output: Path,
    *,
    seed=42,
    max_epochs=2,
):
    import lightning.pytorch as pl
    import torch
    from lightning.pytorch.callbacks import EarlyStopping
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    from pytorch_forecasting.data import NaNLabelEncoder, TorchNormalizer
    from pytorch_forecasting.metrics import RMSE, QuantileLoss

    if not 1 <= horizon <= 8 or train_end >= validation_end:
        raise ValueError("Chronological train/validation boundaries and valid horizon required")
    validation = panel[
        (panel.forecast_origin > train_end) & (panel.forecast_origin <= validation_end)
    ].copy()
    if validation.empty:
        raise ValueError("Separate validation origins required")
    later = panel[panel.forecast_origin > validation_end]
    test_cutoff = min((utc(t) for t in later.decision_cutoff), default=None)
    validation_series = []
    selection_times = []
    for name, group in validation.groupby("series"):
        targets = group[group.lead > 0]
        times = [utc(t) for t in targets.loc[targets.weight > 0, "target_available_at"]]
        if (
            not times
            or targets.source_event.max() > validation_end
            or (test_cutoff is not None and max(times) >= test_cutoff)
        ):
            continue
        validation_series.append(name)
        selection_times.extend(times)
    validation = validation[validation.series.isin(validation_series)].copy()
    if validation.empty:
        raise ValueError("No validation targets purged before held-out origin")
    val_origin = min(utc(x) for x in validation.decision_cutoff)
    allowed = []
    for name, group in panel[panel.forecast_origin <= train_end].groupby("series"):
        targets = group[group.lead > 0]
        if (
            len(targets) != horizon
            or targets.source_event.max() > train_end
            or not (targets.schedule_known == 1).all()
        ):
            continue
        times = [utc(t) for t in targets.loc[targets.weight > 0, "target_available_at"]]
        if times and max(times) < val_origin:
            allowed.append(name)
    training_rows = panel[panel.series.isin(allowed)].copy()
    if training_rows.empty:
        raise ValueError("No purged multilead training targets before validation origin")
    torch.set_num_threads(1)
    pl.seed_everything(seed, workers=True)
    training = TimeSeriesDataSet(
        training_rows,
        time_idx="time_idx",
        target="points",
        weight="weight",
        group_ids=["series"],
        min_encoder_length=ENCODER_LENGTH,
        max_encoder_length=ENCODER_LENGTH,
        min_prediction_length=horizon,
        max_prediction_length=horizon,
        static_categoricals=["player", "season"],
        static_reals=["slot"],
        time_varying_known_reals=[
            "time_idx",
            "fixture_exists",
            "schedule_known",
            "opponent",
            "was_home",
            "lead",
        ],
        time_varying_unknown_reals=["encoder_points", "observation_mask"],
        categorical_encoders={
            "player": NaNLabelEncoder(add_nan=True),
            "season": NaNLabelEncoder(add_nan=True),
            # Group IDs identify windows, never model covariates. New inference
            # windows extend a contiguous ID map; add_nan creates gaps on refit.
            "__group_id__series": NaNLabelEncoder(add_nan=False),
        },
        target_normalizer=TorchNormalizer(method="standard"),
        add_relative_time_idx=True,
        add_encoder_length=True,
        allow_missing_timesteps=False,
    )
    val_dataset = TimeSeriesDataSet.from_dataset(
        training, validation, predict=True, stop_randomization=True
    )
    output.mkdir(parents=True, exist_ok=False)
    predictions = {}
    for name, loss, size in [
        ("mean", RMSE(), 1),
        ("quantiles", QuantileLoss(quantiles=[0.1, 0.5, 0.9]), 3),
    ]:
        model = TemporalFusionTransformer.from_dataset(
            training,
            hidden_size=8,
            attention_head_size=1,
            hidden_continuous_size=4,
            lstm_layers=1,
            dropout=0.15,
            learning_rate=0.01,
            output_size=size,
            loss=loss,
            log_interval=-1,
        )
        trainer = pl.Trainer(
            max_epochs=max_epochs,
            accelerator="cpu",
            devices=1,
            gradient_clip_val=0.1,
            logger=False,
            enable_checkpointing=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            callbacks=[EarlyStopping(monitor="val_loss", patience=2, mode="min")],
        )
        trainer.fit(
            model,
            training.to_dataloader(train=True, batch_size=32, num_workers=0),
            val_dataset.to_dataloader(train=False, batch_size=64, num_workers=0),
        )
        trainer.save_checkpoint(output / f"{name}.ckpt")
        predicted = model.predict(
            val_dataset.to_dataloader(train=False, batch_size=64, num_workers=0),
            mode="prediction" if name == "mean" else "quantiles",
            return_index=True,
            trainer_kwargs={"accelerator": "cpu", "logger": False, "enable_progress_bar": False},
        )
        values = predicted.output.detach().cpu().numpy()
        predictions[name] = {
            "values": np.sort(values, axis=-1) if name == "quantiles" else values,
            "index": predicted.index,
        }
    torch.save(training.get_parameters(), output / "dataset.pt")
    meta = {
        "model_family": "tft_multilead",
        "status": "trained_research",
        "horizon_events": horizon,
        "rules_version": RULES.version,
        "available_at": utcnow(),
        "training_end_event": train_end,
        "validation_end_event": validation_end,
        "selection_labels_available_at": max(selection_times).isoformat(),
        "validation_series": len(validation_series),
        "seed": seed,
        "target_normalizer": "global standard normalization fitted on training windows only",
        "panel_sha256": fingerprint(panel.replace({np.nan: None}).to_dict("records")),
        "artifacts": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.iterdir()
            if p.is_file()
        },
        "active": False,
        "limitations": [
            "Research fit; held-out lead-specific evaluation required before serving",
            "Unknown future schedules have masked targets; no fabricated fixtures",
            "Marginal quantiles are not joint event or squad intervals",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(meta, sort_keys=True, indent=2))
    return {"manifest": meta, "predictions": predictions, "training_series": len(allowed)}


def multilead_metrics(panel: pd.DataFrame, predictions: dict[str, Any], horizon: int):
    from fpl_app.evaluation.metrics import forecast_metrics

    reports = {}
    predicted = predictions["mean"]["values"]
    index = predictions["mean"]["index"]
    for lead in range(1, horizon + 1):
        actual = []
        means = []
        events = []
        quantiles: dict[float, list[float]] = {q: [] for q in [0.1, 0.5, 0.9]}
        quantile_rows = {
            row["series"]: predictions["quantiles"]["values"][i]
            for i, row in enumerate(predictions["quantiles"]["index"].to_dict("records"))
        }
        for i, row in enumerate(index.to_dict("records")):
            target = panel[(panel.series == row["series"]) & (panel.lead == lead)]
            if len(target) != 1 or float(target.iloc[0]["weight"]) != 1:
                continue
            actual.append(float(target.iloc[0]["points"]))
            means.append(float(predicted[i, lead - 1]))
            events.append(int(target.iloc[0]["source_event"]))
            if row["series"] not in quantile_rows:
                raise ValueError("Mean and quantile forecast coverage differ")
            for j, q in enumerate(quantiles):
                quantiles[q].append(float(quantile_rows[row["series"]][lead - 1, j]))
        reports[str(lead)] = (
            None
            if not actual
            else forecast_metrics(actual, means, quantiles=quantiles, events=events)
        )
    return reports


def evaluate_multilead(run: Path, panel: pd.DataFrame) -> dict[str, Any]:
    """Score untouched later origins without refitting or selecting a checkpoint."""
    from fpl_app.models.tft import predict_tft

    manifest_bytes = (run / "manifest.json").read_bytes()
    meta = json.loads(manifest_bytes)
    for name, digest in meta["artifacts"].items():
        target = run / name
        if (
            Path(name).name != name
            or target.is_symlink()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("TFT artifact checksum mismatch")
    if (
        meta["rules_version"] != RULES.version
        or panel.empty
        or (panel.forecast_origin <= meta["validation_end_event"]).any()
    ):
        raise ValueError("Untouched later held-out origins required")
    if min(utc(t) for t in panel.decision_cutoff) <= utc(meta["selection_labels_available_at"]):
        raise ValueError("Validation selection labels overlap held-out origin")
    raw = predict_tft(run, panel)
    predictions = {
        name: {"values": raw[name], "index": raw["index"]} for name in ["mean", "quantiles"]
    }
    report = {
        "model_family": "tft_multilead",
        "partition": "test",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "panel_sha256": fingerprint(panel.replace({np.nan: None}).to_dict("records")),
        "lead_metrics": multilead_metrics(panel, predictions, meta["horizon_events"]),
        "active": False,
        "available_at": utcnow(),
        "limitations": meta["limitations"],
    }
    digest = fingerprint(report)
    target = run / f"evaluation-{digest}.json"
    with target.open("x") as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
    return report
