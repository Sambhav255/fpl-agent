import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fpl_app.contracts import Fixture, Player
from fpl_app.models import baseline_run, registry
from fpl_app.models.inference import common_projection
from fpl_app.models.tft import slot_panel
from fpl_app.models.training import audited_panel


def players():
    return [
        Player(
            player_id=1,
            name="A",
            club=1,
            position=3,
            market_price_units=50,
            points_per_game=4,
            minutes=540,
            appearances=6,
            availability=0.5,
        )
    ]


def fixtures():
    return [Fixture(fixture_id=i, event=8, home_club=1, away_club=2) for i in (1, 2)]


def test_baseline_availability_once_components_and_frozen_schedule():
    half = baseline_run(players(), fixtures(), "snapshot", "2026-10-01T10:00:00Z", "demo", 8, 2)
    full_players = [players()[0].model_copy(update={"availability": 1.0})]
    full = baseline_run(full_players, fixtures(), "snapshot", "2026-10-01T10:00:00Z", "demo", 8, 2)
    assert len(half.projections) == 2 and half.fixtures == fixtures()
    assert half.projections[0].expected_points * 2 == pytest.approx(
        full.projections[0].expected_points
    )
    assert sum(
        v for v in half.projections[0].components.values() if v is not None
    ) == pytest.approx(half.projections[0].expected_points)
    assert half.projections[0].point_quantiles is None
    assert (
        half.projection_run_id
        == baseline_run(
            players(), fixtures(), "snapshot", "2026-10-01T10:00:00Z", "demo", 8, 2
        ).projection_run_id
    )


def test_unavailable_counts_bounded_clean_sheet_and_unknown_label():
    p = players()[0].model_copy(update={"appearances": 0, "clean_sheets": 10, "availability": None})
    run = baseline_run([p], fixtures(), "s", "2026-10-01T10:00:00Z", "live", 8, 1)
    assert run.projections[0].expected_minutes <= 90
    assert any("Unknown availability" in a for a in run.projections[0].assumptions)
    with pytest.raises(ValueError, match="duplicate"):
        baseline_run([p, p], fixtures(), "s", "2026-10-01T10:00:00Z", "demo", 8, 1)


def test_demo_cannot_register_training(tmp_path: Path):
    (tmp_path / "audit.json").write_text(json.dumps({"data_mode": "demo"}))
    pd.DataFrame({"x": [1]}).to_parquet(tmp_path / "features.parquet")
    with pytest.raises(ValueError, match="synthetic/demo"):
        audited_panel(tmp_path / "features.parquet", allow_approximate=True)


def test_registry_missing_artifact_and_dynamic_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert next(x for x in registry() if x["name"] == "catboost")["status"] == "not_trained"
    path = tmp_path / "models/catboost/bad"
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(
        json.dumps(
            {"data_mode": "live", "model_family": "catboost", "artifacts": {"missing.cbm": "no"}}
        )
    )
    assert next(x for x in registry() if x["name"] == "catboost")["status"] == "disabled"


def synthetic_slot_rows():
    rows = []
    for player in range(1, 4):
        for event in range(1, 9):
            for fixture in range(2 if event == 8 else 1):
                rows.append(
                    {
                        "season": "synthetic",
                        "canonical_player_id": str(player),
                        "event": event,
                        "fixture_id": event * 10 + fixture,
                        "decision_cutoff": f"2024-01-{event:02d}T00:00:00Z",
                        "target_points": float((event + player + fixture) % 5 - 1),
                        "opponent": 2 + fixture,
                        "was_home": fixture,
                        "outcome_state": "appeared",
                    }
                )
    return pd.DataFrame(rows)


def test_tft_slots_keep_double_opponents_and_mask_padding_blank_missing():
    rows = synthetic_slot_rows()
    rows.loc[
        (rows.event == 3) & (rows.canonical_player_id == "1"), ["target_points", "outcome_state"]
    ] = [0, "blank"]
    rows.loc[(rows.event == 4) & (rows.canonical_player_id == "1"), "target_points"] = np.nan
    panel = slot_panel(rows, 2)
    double = panel[(panel.player == "1") & (panel.time_idx == 8)]
    assert double.opponent.tolist() == [2, 3] and double.weight.tolist() == [1, 1]
    assert panel[(panel.player == "1") & (panel.time_idx == 3)].weight.tolist() == [1, 0]
    assert panel[(panel.player == "1") & (panel.time_idx == 4)].weight.tolist() == [0, 0]


def test_common_projection_checks_missing_double_and_negative_mean():
    rows = pd.DataFrame(
        [
            {
                "player_id": 1,
                "fixture_id": i,
                "event": 8,
                "decision_cutoff": "2026-10-01T10:00:00Z",
                "expected_points": -1,
                "expected_minutes": 20,
                "p10": -3,
                "p50": 0,
                "p90": 5,
            }
            for i in (1, 2)
        ]
    )
    run = common_projection(
        rows, players(), fixtures(), "s", "2026-10-01T10:00:00Z", "demo", 8, 1, "tft"
    )
    assert (
        run.projections[0].expected_points == -1 and run.projections[0].point_quantiles["0.5"] == 0
    )
    with pytest.raises(ValueError, match="missing"):
        common_projection(
            rows.iloc[:1], players(), fixtures(), "s", "2026-10-01T10:00:00Z", "demo", 8, 1, "tft"
        )


@pytest.mark.skipif(
    os.environ.get("FPL_OPTIONAL_SMOKE") != "1",
    reason="opt-in synthetic installation sanity, never live training",
)
def test_optional_tft_genuine_fit_synthetic_sanity(tmp_path: Path):
    pytest.importorskip("pytorch_forecasting")
    import torch

    from fpl_app.models.tft import fit_tft, predict_tft

    torch.set_num_threads(2)
    panel = slot_panel(synthetic_slot_rows(), 2)
    fitted = fit_tft(panel, train_end=6, max_epochs=1, output=tmp_path)
    assert np.isfinite(fitted["predictions"]["mean"]["values"]).all()
    assert fitted["predictions"]["quantiles"]["values"].shape[-1] == 3
    torch.save(fitted["dataset_parameters"], tmp_path / "dataset.pt")
    prediction = predict_tft(tmp_path, panel)
    assert np.isfinite(prediction["mean"]).all()
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.skipif(
    os.environ.get("FPL_OPTIONAL_SMOKE") != "1",
    reason="opt-in synthetic installation sanity, never live training",
)
def test_optional_bayesian_fit_and_joint_scenarios_synthetic(tmp_path: Path):
    pytest.importorskip("pymc")
    from fpl_app.models.bayesian import fit_matches, shared_scenarios

    matches = pd.DataFrame(
        [
            {
                "fixture_id": i,
                "home_club": 1 if i % 2 else 2,
                "away_club": 2 if i % 2 else 1,
                "home_goals": i % 3,
                "away_goals": (i + 1) % 3,
                "time_index": i,
            }
            for i in range(1, 9)
        ]
    )
    trace, diagnostics = fit_matches(matches, draws=15, tune=15)
    player_rows = pd.DataFrame(
        [
            {
                "player_id": i,
                "club": 1 if i <= 4 else 2,
                "position": 1 if i in (1, 2, 5, 6) else 3,
                "appearances": 6,
                "total_matches": 8,
                "minutes_per_appearance": 70,
                "goals": 2,
                "assists": 1,
                "total_minutes": 420,
            }
            for i in range(1, 9)
        ]
    )
    scenarios = shared_scenarios(trace, diagnostics, 1, 2, player_rows, samples=200)
    assert not ((scenarios["minutes"][:, 0] > 0) & (scenarios["minutes"][:, 1] > 0)).any()
    assert np.array_equal(
        scenarios["goals"][:, :4].sum(axis=1) + scenarios["unallocated_goals"][:, 0],
        scenarios["home_goals"],
    )
    assert np.isfinite(scenarios["points"]).all() and "max_rhat" in diagnostics
    assert not (tmp_path / "manifest.json").exists()


def _feature_row(player: int, event: int, **overrides):
    from fpl_app.features.pipeline import NUMERIC_FEATURES

    row = {
        "season": "2024-25",
        "canonical_player_id": str(player),
        "fixture_id": event * 100 + player,
        "event": event,
        "decision_cutoff": f"2024-01-{event:02d}T00:00:00Z",
        "target_available_at": f"2024-01-{event:02d}T12:00:00Z",
        "target_points": float(event),
        "target_minutes": 90.0,
        "opponent": 2,
        "was_home": 1,
        "outcome_state": "appeared",
        "replay_timing": "verified",
        "timing_verified": True,
        "source_refs": '["src"]',
        **{name: 0.0 for name in NUMERIC_FEATURES},
    }
    row.update(overrides)
    return row


def _write_panel(directory: Path, rows: list[dict], **audit):
    import hashlib

    directory.mkdir(parents=True, exist_ok=True)
    dataset = directory / "features.parquet"
    pd.DataFrame(rows).to_parquet(dataset, index=False)
    body = {
        "data_mode": "live",
        "replay_timing": "verified",
        "limitations": [],
        "rows": len(rows),
        "panel_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
    }
    body.update(audit)
    (directory / "audit.json").write_text(json.dumps(body))
    return dataset


def test_unknown_minutes_are_not_labelled_as_nonappearance():
    from fpl_app.models.labels import minute_appearance_labels

    labels = minute_appearance_labels(pd.Series([90, np.nan, 0]))
    assert labels.iloc[0] == 1
    assert pd.isna(labels.iloc[1])
    assert labels.iloc[2] == 0
    sixty = minute_appearance_labels(pd.Series([90, np.nan, 0, 60]), 60, at_least=True)
    assert sixty.iloc[0] == 1 and pd.isna(sixty.iloc[1]) and sixty.iloc[2] == 0
    assert sixty.iloc[3] == 1


def test_calibration_excludes_unknown_minutes(tmp_path: Path):
    from fpl_app.features.pipeline import immutable_json
    from fpl_app.models.training import evaluate_run

    forecasts = pd.DataFrame(
        {
            "event": [1, 1],
            "target_points": [1.0, 2.0],
            "predicted_points": [1.0, 2.0],
            "baseline_points": [0.0, 0.0],
            "target_minutes": [0.0, np.nan],
            "appearance_probability": [0.0, 1.0],
        }
    )
    forecasts.to_parquet(tmp_path / "test_predictions.parquet", index=False)
    immutable_json(
        tmp_path / "manifest.json",
        {
            "run_id": "probe",
            "dataset_sha256": "x",
            "replay_timing": "verified",
            "limitations": [],
        },
    )
    metrics = evaluate_run(tmp_path)["metrics"]
    assert metrics["appearance_brier"] == 0


def test_strict_audit_rejects_unbound_and_unverified_rows(tmp_path: Path):
    rows = [_feature_row(1, 1, replay_timing="conservative_assumed", timing_verified=False)]
    dataset = _write_panel(tmp_path, rows, replay_timing="verified")
    with pytest.raises(ValueError, match="replay_timing"):
        audited_panel(dataset, allow_approximate=True)
    bad = tmp_path / "bad"
    dataset = _write_panel(bad, [_feature_row(1, 1)], panel_sha256="not-the-file")
    with pytest.raises(ValueError, match="checksum"):
        audited_panel(dataset)
    mixed = [
        _feature_row(1, 1, replay_timing="conservative_assumed", timing_verified=False),
        _feature_row(2, 1, replay_timing="verified", timing_verified=True),
    ]
    dataset = _write_panel(
        tmp_path / "mixed", mixed, replay_timing="conservative_assumed"
    )
    with pytest.raises(ValueError, match="replay_timing|mixed|verified"):
        audited_panel(dataset, allow_approximate=True)
    dataset = _write_panel(
        tmp_path / "approx",
        [_feature_row(1, 1, replay_timing="conservative_assumed", timing_verified=False)],
        replay_timing="conservative_assumed",
    )
    frame, _ = audited_panel(dataset, allow_approximate=True)
    assert len(frame) == 1
    with pytest.raises(ValueError, match="verified availability"):
        audited_panel(dataset, allow_approximate=False)


def test_tft_keeps_missing_target_events_for_masking(tmp_path: Path):
    rows = [_feature_row(1, event) for event in (1, 2, 3)]
    rows[1]["target_points"] = np.nan
    rows[1]["target_available_at"] = None
    dataset = _write_panel(tmp_path, rows)
    kept, _ = audited_panel(dataset, drop_missing_targets=False)
    panel = slot_panel(kept, max_slots=1)
    target = panel[(panel.forecast_origin == 2) & (panel.source_event == 2)]
    assert target.weight.tolist() == [0]
    dropped, _ = audited_panel(dataset, drop_missing_targets=True)
    with pytest.raises(ValueError, match="missing player events"):
        slot_panel(dropped, max_slots=1)


def test_tft_encoder_excludes_delayed_and_revised_points():
    def row(player, event, points, available, versions=None):
        payload = _feature_row(
            player,
            event,
            target_points=points,
            target_available_at=available,
            decision_cutoff={1: "2024-01-01", 2: "2024-01-08", 3: "2024-01-15"}[event]
            + "T00:00:00Z",
        )
        if versions is not None:
            payload["point_versions"] = versions
        return payload

    revised = [{"points": 4, "available_at": "2024-01-03T00:00:00Z"}]
    frame = pd.DataFrame(
        [
            row(1, 1, 99, "2024-01-10T00:00:00Z", revised),
            row(1, 2, 7, "2024-01-09T00:00:00Z"),
            row(1, 3, 1, "2024-01-16T00:00:00Z"),
            row(2, 1, 50, "2024-01-10T00:00:00Z"),
            row(2, 2, 3, "2024-01-09T00:00:00Z"),
            row(2, 3, 2, "2024-01-16T00:00:00Z"),
        ]
    )
    panel = slot_panel(frame, max_slots=1)

    def history(player, origin, source):
        return panel[
            (panel.player == str(player))
            & (panel.forecast_origin == origin)
            & (panel.source_event == source)
        ].iloc[0]

    early = history(1, 2, 1)
    assert early.encoder_points == 4 and early.observation_mask == 1
    assert early.points == 4
    later = history(1, 3, 1)
    assert later.encoder_points == 99 and later.observation_mask == 1
    delayed = history(2, 2, 1)
    assert delayed.encoder_points == 0 and delayed.observation_mask == 0
    published = history(2, 3, 1)
    assert published.encoder_points == 50 and published.observation_mask == 1
    own_label = history(1, 2, 2)
    assert own_label.points == 7 and own_label.weight == 1 and own_label.observation_mask == 0
    origin = panel[(panel.player == "1") & (panel.forecast_origin == 2)]
    assert origin.loc[origin.time_idx < 6, "source_event"].max() < 2


def test_incomplete_model_run_is_not_overwritten(tmp_path: Path):
    from fpl_app.models.publication import open_model_run

    dest = tmp_path / "models" / "tft" / "partial"
    dest.mkdir(parents=True)
    (dest / "mean.ckpt").write_bytes(b"keep")
    with pytest.raises(ValueError, match="incomplete"):
        open_model_run(dest)
    assert (dest / "mean.ckpt").read_bytes() == b"keep"


def test_repeat_publication_reuses_verified_manifest(tmp_path: Path):
    import hashlib

    from fpl_app.features.pipeline import immutable_json
    from fpl_app.models.publication import open_model_run, publish_model_run

    dest = tmp_path / "models" / "bayesian" / "run"
    staging, complete = open_model_run(dest)
    assert complete is False
    (staging / "posterior.nc").write_bytes(b"trace")
    digest = hashlib.sha256(b"trace").hexdigest()
    immutable_json(staging / "manifest.json", {"artifacts": {"posterior.nc": digest}, "dataset_sha256": "abc"})
    publish_model_run(staging, dest)
    again, done = open_model_run(dest)
    assert done is True and again == dest
    assert (dest / "posterior.nc").read_bytes() == b"trace"
    assert not staging.exists()


def test_repeat_bayesian_publication_does_not_refit(tmp_path: Path, monkeypatch):
    rows = []
    for player in range(1, 11):
        for event in range(1, 9):
            rows.append(
                _feature_row(
                    player,
                    event,
                    home_club=1,
                    away_club=2,
                    home_goals=1,
                    away_goals=0,
                    time_index=event,
                )
            )
    dataset = _write_panel(tmp_path / "panel", rows)
    calls = {"n": 0}

    class Trace:
        def to_netcdf(self, path):
            Path(path).write_bytes(b"posterior-bytes")

    def fake_fit(*_args, **_kwargs):
        calls["n"] += 1
        return Trace(), {"limitations": ["partial"], "converged": False}

    monkeypatch.setattr("fpl_app.models.bayesian.fit_matches", fake_fit)
    from fpl_app.models.bayesian import train_bayesian

    first = train_bayesian(dataset, tmp_path / "models", draws=1, tune=1)
    second = train_bayesian(dataset, tmp_path / "models", draws=1, tune=1)
    assert calls["n"] == 1
    assert second["reused"] is True
    assert second["directory"] == first["directory"]
    assert Path(first["directory"], "posterior.nc").read_bytes() == b"posterior-bytes"


def test_repeat_tft_publication_does_not_refit(tmp_path: Path, monkeypatch):
    pytest.importorskip("torch")
    rows = [_feature_row(player, event) for player in range(1, 11) for event in range(1, 9)]
    dataset = _write_panel(tmp_path / "panel", rows)
    calls = {"n": 0}

    def fake_fit(_panel, _train_end, _epochs, _seed, output):
        calls["n"] += 1
        output.mkdir(parents=True, exist_ok=True)
        (output / "mean.ckpt").write_bytes(b"mean")
        (output / "quantiles.ckpt").write_bytes(b"quantiles")
        return {"limitations": ["partial"], "dataset_parameters": {"ok": True}}

    monkeypatch.setattr("fpl_app.models.tft.fit_tft", fake_fit)
    from fpl_app.models.tft import train_tft

    first = train_tft(dataset, tmp_path / "models", max_epochs=1)
    second = train_tft(dataset, tmp_path / "models", max_epochs=1)
    assert calls["n"] == 1
    assert second["reused"] is True
    assert Path(first["directory"], "mean.ckpt").read_bytes() == b"mean"
