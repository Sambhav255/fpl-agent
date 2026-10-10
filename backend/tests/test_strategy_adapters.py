"""Synthetic contract fixtures; no training/evaluation claims."""

import hashlib
import json
import os

import numpy as np
import pandas as pd
import pytest

from fpl_app.contracts import Fixture, Player
from fpl_app.models.strategy_adapters import bayesian_run, tft_run

CUTOFF = "2026-10-01T10:00:00Z"


def artifact(path, family="tft"):
    names = (
        ["mean.ckpt", "quantiles.ckpt", "dataset.pt"]
        if family == "tft"
        else ["posterior.nc", "diagnostics.json"]
    )
    for name in names:
        (path / name).write_bytes(b"synthetic fixture")
    if family == "bayesian":
        (path / "diagnostics.json").write_text(
            json.dumps(
                {
                    "clubs": [10, 20],
                    "converged": True,
                    "time_center": 0,
                    "time_scale": 1,
                    "limitations": ["partial scoring"],
                }
            )
        )
    manifest = {
        "model_family": family,
        "model_status": "trained",
        "data_mode": "live",
        "replay_timing": "verified",
        "run_id": "synthetic-contract-only",
        "training_cutoff": "2026-09-01T00:00:00Z",
        "available_at": "2026-09-02T00:00:00Z",
        "artifacts": {n: hashlib.sha256((path / n).read_bytes()).hexdigest() for n in names},
    }
    (path / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def inputs():
    players = [
        Player(
            player_id=7,
            name="Synthetic",
            club=1,
            position=3,
            market_price_units=50,
            availability=0.1,
        )
    ]
    fixtures = [Fixture(fixture_id=i, event=8, home_club=1, away_club=2) for i in (11, 12)]
    panel = pd.DataFrame(
        [
            {
                "series": f"s{i}",
                "player": "person",
                "time_idx": t,
                "forecast_origin": 8,
                "source_event": 7 if t == 0 else 8,
                "fixture_id": i,
                "fixture_exists": 1,
                "opponent": 20,
                "was_home": 1,
                "decision_cutoff": CUTOFF,
                "points": 0,
                "encoder_points": 0,
                "observation_mask": 0,
                "weight": 0,
            }
            for i in (11, 12)
            for t in (0, 1)
        ]
    )
    minutes = pd.DataFrame(
        [
            {"player_id": 7, "fixture_id": i, "expected_minutes": 60, "available_at": CUTOFF}
            for i in (11, 12)
        ]
    )
    return {
        "players": players,
        "fixtures": fixtures,
        "panel": panel,
        "minutes": minutes,
        "snapshot_id": "s",
        "cutoff": CUTOFF,
        "next_event": 8,
        "horizon": 1,
        "player_map": {"person": 7},
        "club_map": {1: 10, 2: 20},
    }


def call(path, monkeypatch, **changes):
    monkeypatch.setattr(
        "fpl_app.models.strategy_adapters.predict_tft",
        lambda *_: {
            "mean": np.array([[-2.0], [4.0]]),
            "quantiles": np.array([[[-5.0, 0.0, 7.0]], [[-1.0, 2.0, 9.0]]]),
            "index": pd.DataFrame({"series": ["s12", "s11"], "time_idx": [1, 1]}),
        },
    )
    args = inputs()
    args.update(changes)
    return tft_run(artifact=path, **args)


def test_index_mean_double_and_no_availability_rescale(tmp_path, monkeypatch):
    artifact(tmp_path)
    run = call(tmp_path, monkeypatch)
    assert [(p.fixture_id, p.expected_points) for p in run.projections] == [(12, -2), (11, 4)]
    assert run.projections[0].point_quantiles["0.5"] == 0
    assert run.model_status == "trained"
    assert run.projections[0].appearance_probability is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("replay_timing", "conservative_assumed"),
        ("data_mode", "demo"),
        ("available_at", "2026-10-02T00:00:00Z"),
        ("training_cutoff", None),
    ],
)
def test_artifact_guards(tmp_path, monkeypatch, field, value):
    manifest = artifact(tmp_path)
    if value is None:
        manifest.pop(field)
    else:
        manifest[field] = value
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        call(tmp_path, monkeypatch)


def test_corruption_horizon_missing_double(tmp_path, monkeypatch):
    artifact(tmp_path)
    with pytest.raises(ValueError, match="one-event"):
        call(tmp_path, monkeypatch, horizon=2)
    with pytest.raises(ValueError, match="missing"):
        call(
            tmp_path,
            monkeypatch,
            fixtures=inputs()["fixtures"]
            + [Fixture(fixture_id=13, event=8, home_club=1, away_club=2)],
        )
    (tmp_path / "mean.ckpt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        call(tmp_path, monkeypatch)


@pytest.mark.parametrize("kind", ["outcome", "future_encoder", "venue", "mapping", "minutes"])
def test_leakage_mapping_guards(tmp_path, monkeypatch, kind):
    artifact(tmp_path)
    args = inputs()
    panel = args["panel"]
    if kind == "outcome":
        panel.loc[panel.time_idx == 1, "points"] = 100
    elif kind == "future_encoder":
        panel.loc[panel.time_idx == 0, "source_event"] = 8
    elif kind == "venue":
        panel.loc[panel.time_idx == 1, "was_home"] = 0
    elif kind == "mapping":
        args["player_map"] = {"wrong": 7}
    else:
        args["minutes"].loc[0, "available_at"] = "2026-10-02T00:00:00Z"
    with pytest.raises(ValueError):
        call(tmp_path, monkeypatch, **args)


@pytest.mark.skipif(
    os.environ.get("FPL_OPTIONAL_SMOKE") != "1",
    reason="opt-in optional ArviZ contract check, never training",
)
def test_actual_bayesian_sampler_library_shaped_posterior(tmp_path, monkeypatch):
    az = pytest.importorskip("arviz")
    artifact(tmp_path, "bayesian")
    trace = az.from_dict(
        posterior={
            **{k: np.zeros((2, 8)) for k in ("base", "venue", "trend")},
            "dispersion": np.ones((2, 8)),
            "attack": np.zeros((2, 8, 2)),
            "defence": np.zeros((2, 8, 2)),
        }
    )
    monkeypatch.setattr(az, "from_netcdf", lambda *_: trace)
    args = inputs()
    args.pop("panel")
    args.pop("minutes")
    exposures = pd.DataFrame(
        [
            {
                "canonical_player_id": "person",
                "club": 1,
                "position": 3,
                "available_at": CUTOFF,
                "appearances": 6,
                "total_matches": 8,
                "minutes_per_appearance": 70,
                "goals": 2,
                "assists": 1,
                "total_minutes": 420,
            }
        ]
    )
    args.update(
        artifact=tmp_path, exposures=exposures, fixture_times={11: 8.0, 12: 9.0}, samples=100
    )
    run = bayesian_run(**args)
    assert len(run.projections) == 2
    assert 0 < run.projections[0].appearance_probability < 1
    assert run.projections[0].start_probability is None
    assert any("partial" in w for w in run.warnings)
    assert bayesian_run(**args).projection_run_id == run.projection_run_id
    exposures.loc[0, "club"] = 2
    with pytest.raises(ValueError, match="club/position"):
        bayesian_run(**args)
