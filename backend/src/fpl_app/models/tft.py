"""Optional compact TFT with separate mean/quantile objectives and fixture slots.

Without publication timestamps, one series per player-season-slot uses the event
index. With timestamps, each forecast deadline has its own series and the encoder
sees only point versions published by that deadline. Both fixtures of an event
share the deadline and do not see each other's realised points. Blank slot zero is
an observed zero; padding and missing observations have zero loss weight. No future
points, minutes, injuries or xG are decoder covariates.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fpl_app.features.pipeline import fingerprint, immutable_json

from .training import audited_panel, split_panel

KNOWN_REALS = ["time_idx", "fixture_exists", "was_home", "opponent", "slot"]
UNKNOWN_REALS = ["points", "observation_mask"]


def slot_panel(frame: pd.DataFrame, max_slots: int = 3) -> pd.DataFrame:
    """Keep fixture slots. With publication times, build one as-of encoder per deadline."""
    from .tft_slots import slot_panel as build_slot_panel

    return build_slot_panel(frame, max_slots)

def fit_tft(
    panel: pd.DataFrame,
    train_end: int,
    max_epochs: int = 3,
    seed: int = 42,
    output: Path | None = None,
) -> dict[str, Any]:
    import lightning.pytorch as pl
    from lightning.pytorch.callbacks import EarlyStopping
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
    from pytorch_forecasting.data import GroupNormalizer, NaNLabelEncoder
    from pytorch_forecasting.metrics import RMSE, QuantileLoss

    pl.seed_everything(seed, workers=True)
    from .tft_slots import forecast_windows

    windows = forecast_windows(panel, train_end)
    training_rows = windows["training_rows"]
    training = TimeSeriesDataSet(
        training_rows,
        time_idx="time_idx",
        target="points",
        weight="weight",
        group_ids=["series"],
        min_encoder_length=windows["min_encoder_length"],
        max_encoder_length=windows["max_encoder_length"],
        min_prediction_length=1,
        max_prediction_length=1,
        static_categoricals=["player", "season"],
        static_reals=["slot"],
        time_varying_known_reals=[c for c in KNOWN_REALS if c != "slot"],
        time_varying_unknown_reals=windows["unknown_reals"],
        categorical_encoders={
            "player": NaNLabelEncoder(add_nan=True),
            "season": NaNLabelEncoder(add_nan=True),
            "series": NaNLabelEncoder(add_nan=True),
            "__group_id__series": NaNLabelEncoder(add_nan=True),
        },
        target_normalizer=GroupNormalizer(groups=["series"], transformation=None),
        add_relative_time_idx=True,
        add_encoder_length=True,
        allow_missing_timesteps=False,
    )
    if windows["asof"]:
        validation = TimeSeriesDataSet.from_dataset(
            training, windows["future_rows"], stop_randomization=True, predict=True
        )
    else:
        validation = TimeSeriesDataSet.from_dataset(
            training, panel, min_prediction_idx=train_end + 1, stop_randomization=True
        )
    train_loader = training.to_dataloader(train=True, batch_size=32, num_workers=0)
    val_loader = validation.to_dataloader(train=False, batch_size=64, num_workers=0)
    trained = {}
    predictions = {}
    for name, loss, output_size in (
        ("mean", RMSE(), 1),
        ("quantiles", QuantileLoss(quantiles=[0.1, 0.5, 0.9]), 3),
    ):
        model = TemporalFusionTransformer.from_dataset(
            training,
            hidden_size=8,
            attention_head_size=1,
            hidden_continuous_size=4,
            lstm_layers=1,
            dropout=0.15,
            learning_rate=0.01,
            output_size=output_size,
            loss=loss,
            reduce_on_plateau_patience=2,
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
        trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)
        raw = model.predict(
            val_loader,
            mode="prediction" if name == "mean" else "quantiles",
            return_index=True,
            trainer_kwargs={"accelerator": "cpu", "logger": False, "enable_progress_bar": False},
        )
        array = raw.output.detach().cpu().numpy()
        if name == "quantiles":
            array = np.sort(array, axis=-1)  # explicit crossing repair; mean remains independent
        predictions[name] = {"values": array, "index": raw.index}
        if output is not None:
            output.mkdir(parents=True, exist_ok=True)
            trainer.save_checkpoint(output / f"{name}.ckpt")
        trained[name] = model
    return {
        "models": trained,
        "predictions": predictions,
        "dataset_parameters": training.get_parameters(),
        "limitations": [
            "CPU compact one-event fixture-slot model; no calibrated joint Gameweek quantiles",
            "Mean uses RMSE, quantiles separate pinball objective; optional monotone crossing repair",
            "Each origin uses points published by that deadline; later revisions stay masked",
            "If no earlier version was retained, a delayed final total is masked rather than used",
            "Origin series unseen during training are encoded as missing categories",
            "Fixed multiweek decoder is not implemented",
        ],
        "seed": seed,
    }


def train_tft(dataset: Path, output: Path, seed: int = 42, max_epochs: int = 3) -> dict[str, Any]:
    import torch

    from .publication import open_model_run, publish_model_run, reuse_model_run

    frame, audit = audited_panel(dataset, drop_missing_targets=False)
    if "event" not in frame.columns:
        raise ValueError("TFT unavailable: event column required for contiguous slots")
    observed = frame[pd.to_numeric(frame["target_points"], errors="coerce").notna()].copy()
    train, validation, _ = split_panel(observed)
    kept = set(train["decision_cutoff"]).union(validation["decision_cutoff"])
    panel = slot_panel(frame[frame["decision_cutoff"].isin(kept)].sort_values("event"))
    train_end = int(train["event"].max())
    checksum = hashlib.sha256(dataset.read_bytes()).hexdigest()
    run_id = fingerprint({"dataset": checksum, "seed": seed, "epochs": max_epochs})[:24]
    published = output / "tft" / run_id
    if reuse_model_run(published, checksum):
        return {"directory": str(published), "status": "trained", "active": False, "reused": True}
    dest, complete = open_model_run(published)
    if complete:
        return {"directory": str(published), "status": "trained", "active": False, "reused": True}
    fitted = fit_tft(panel, train_end, max_epochs, seed, dest)
    torch.save(fitted["dataset_parameters"], dest / "dataset.pt")
    artifacts = {
        name: hashlib.sha256((dest / name).read_bytes()).hexdigest()
        for name in ("mean.ckpt", "quantiles.ckpt", "dataset.pt")
    }
    immutable_json(
        dest / "manifest.json",
        {
            "run_id": run_id,
            "model_family": "tft",
            "data_mode": "live",
            "model_status": "trained",
            "dataset_sha256": checksum,
            "replay_timing": audit["replay_timing"],
            "seed": seed,
            "artifacts": artifacts,
            "limitations": fitted["limitations"],
        },
    )
    publish_model_run(dest, published)
    return {"directory": str(published), "status": "trained", "active": False}



def predict_tft(run: Path, future_panel: pd.DataFrame) -> dict[str, Any]:
    import torch
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

    # Only load trusted locally generated artifacts; torch parameter files use pickle.
    parameters = torch.load(run / "dataset.pt", weights_only=False, map_location="cpu")
    data = TimeSeriesDataSet.from_parameters(
        parameters, future_panel, predict=True, stop_randomization=True
    )
    loader = data.to_dataloader(train=False, batch_size=64, num_workers=0)
    result = {}
    for name in ("mean", "quantiles"):
        model = TemporalFusionTransformer.load_from_checkpoint(
            run / f"{name}.ckpt", map_location="cpu", weights_only=False
        )
        predicted = model.predict(
            loader,
            mode="prediction" if name == "mean" else "quantiles",
            return_index=True,
            trainer_kwargs={"accelerator": "cpu", "logger": False, "enable_progress_bar": False},
        )
        values = predicted.output.detach().cpu().numpy()
        result[name] = np.sort(values, axis=-1) if name == "quantiles" else values
        result["index"] = predicted.index
    return result
