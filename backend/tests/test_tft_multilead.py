import pandas as pd
import pytest

from fpl_app.models.tft_multilead import multilead_panel


def frame(n=12):
    return pd.DataFrame(
        [
            {
                "season": "2026/27",
                "canonical_player_id": "p",
                "event": e,
                "fixture_id": 100 + e,
                "decision_cutoff": f"2026-10-{e:02d}T00:00:00Z",
                "fixture_available_at": "2026-09-01T00:00:00Z",
                "target_available_at": f"2026-10-{e + 1:02d}T00:00:00Z",
                "target_points": float(e),
                "opponent": 2,
                "was_home": True,
                "outcome_state": "observed",
            }
            for e in range(1, n + 1)
        ]
    )


@pytest.mark.parametrize("horizon", range(1, 9))
def test_every_supported_decoder_horizon_keeps_one_origin_cutoff(horizon):
    panel = multilead_panel(frame(20), horizon, max_slots=1)
    window = panel[panel.forecast_origin == 7]
    assert window[window.lead > 0].source_event.tolist() == list(range(7, 7 + horizon))
    assert window.decision_cutoff.nunique() == 1
    assert (window[window.lead > 0].encoder_points == 0).all()


def test_multilead_decoder_never_sees_future_points_and_purges_schedule_changes():
    data = frame()
    panel = multilead_panel(data, 3, max_slots=1)
    window = panel[panel.forecast_origin == 7]
    assert window[window.lead > 0].source_event.tolist() == [7, 8, 9]
    assert (window[window.lead > 0].encoder_points == 0).all()
    altered = data.copy()
    altered.loc[altered.event >= 7, "target_points"] = 999
    other = multilead_panel(altered, 3, max_slots=1)
    features = [
        "encoder_points",
        "observation_mask",
        "opponent",
        "was_home",
        "fixture_exists",
        "schedule_known",
        "lead",
    ]
    pd.testing.assert_frame_equal(
        window[features].reset_index(drop=True),
        other[other.forecast_origin == 7][features].reset_index(drop=True),
    )
    data.loc[data.event == 8, "fixture_available_at"] = "2026-10-08T00:00:00Z"
    unknown = multilead_panel(data, 3, max_slots=1)
    future = unknown[(unknown.forecast_origin == 7) & (unknown.lead == 2)].iloc[0]
    assert future.schedule_known == 0 and future.weight == 0 and future.fixture_id == -1
    with pytest.raises(ValueError, match="dated"):
        multilead_panel(data.drop(columns="fixture_available_at"), 3)


def test_real_multilead_tft_fit_save_reload_on_authored_data(tmp_path):
    pytest.importorskip("pytorch_forecasting")
    from fpl_app.models.tft import predict_tft
    from fpl_app.models.tft_multilead import evaluate_multilead, fit_multilead, multilead_metrics

    panel = multilead_panel(frame(), 2, max_slots=1)
    result = fit_multilead(
        panel, train_end=6, validation_end=9, horizon=2, output=tmp_path / "tft", max_epochs=1
    )
    assert result["manifest"]["horizon_events"] == 2
    assert result["predictions"]["mean"]["values"].shape[1] == 2
    future = panel[panel.series.isin(result["predictions"]["mean"]["index"].series)]
    reloaded = predict_tft(tmp_path / "tft", future)
    import numpy as np

    np.testing.assert_allclose(reloaded["mean"], result["predictions"]["mean"]["values"], atol=1e-6)
    metrics = multilead_metrics(future, result["predictions"], 2)
    assert set(metrics) == {"1", "2"} and all(v["n"] == 1 for v in metrics.values())
    assert future.forecast_origin.unique().tolist() == [7]
    report = evaluate_multilead(tmp_path / "tft", panel[panel.forecast_origin > 9])
    assert all(v["n"] == 2 and "pinball" in v for v in report["lead_metrics"].values())
    with pytest.raises(ValueError, match="held-out"):
        evaluate_multilead(tmp_path / "tft", future)
