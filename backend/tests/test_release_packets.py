"""Producer and frozen-member integrity; authored source data proves mechanics."""

import json

import pandas as pd
import pytest
import test_forecast_router

from fpl_app.features.football import collection_frames
from fpl_app.models.advanced_serving import input_path, register_bundle
from fpl_app.models.release_packets import (
    checked_baseline_member,
    create_baseline_member,
    freeze_ensemble_inputs,
    freeze_football_inputs,
    produce_football_ensemble,
)
from fpl_app.models.router import create_serving_bundle, forecast_job
from fpl_app.storage import utcnow

configured = test_forecast_router.configured


def test_serving_only_builder_matches_full_builder(configured):
    _, _, _, _, _, _, collection, _ = configured
    panel, future, mapping = collection_frames(collection, "fpl-2026-27")
    empty, fast, fast_mapping = collection_frames(collection, "fpl-2026-27", include_training=False)
    assert not panel.empty and empty.empty
    pd.testing.assert_frame_equal(future, fast)
    pd.testing.assert_frame_equal(mapping, fast_mapping)


def test_football_and_baseline_packets_freeze_sources_and_reject_mutation(configured, monkeypatch):
    store, state, data, model, _, _, collection, _ = configured
    monkeypatch.setenv("DATA_DIR", str(model.parent.parent.parent))
    before = store.get("state", state.team_id)
    input_id = freeze_football_inputs(store, collection["collection_id"], model.name, utcnow())
    football = create_serving_bundle(
        store, state, collection["collection_id"], model.name, input_id
    )
    baseline = create_baseline_member(store, state, football)
    run = checked_baseline_member(store, state, data, baseline)
    assert run.player_universe_ids == football["player_ids"]
    assert run.prediction_origin == football["prediction_origin"]
    assert {(p.player_id, p.fixture_id) for p in run.projections} == {
        (i, f) for i in collection["player_ids"] for f in (71, 72)
    }
    payload = input_path(baseline["input_bundle_id"]) / "baseline.json"
    payload.write_text(payload.read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        checked_baseline_member(store, state, data, baseline)
    assert store.get("state", state.team_id) == before


def test_produced_ensemble_has_assumed_research_and_actual_shadow_separate(configured, monkeypatch):
    store, state, data, model, _, _, collection, _ = configured
    monkeypatch.setenv("DATA_DIR", str(model.parent.parent.parent))
    artifact = produce_football_ensemble(store, collection["collection_id"], model.name)
    path = model.parent.parent / "ensemble" / artifact
    metadata = json.loads((path / "manifest.json").read_text())
    assert metadata["replay_timing"] == "historical_assumed_shadow"
    assert metadata["active"] is False
    audit = json.loads((path / "release_audit.json").read_text())
    assert audit["evaluation_evidence"] == "retrospective_assumed"
    input_id = freeze_football_inputs(store, collection["collection_id"], model.name, utcnow())
    football = create_serving_bundle(
        store, state, collection["collection_id"], model.name, input_id
    )
    baseline = create_baseline_member(store, state, football)
    ensemble_input = freeze_ensemble_inputs(store, state, artifact, football, baseline)
    bundle = register_bundle(store, state, "ensemble", artifact, ensemble_input)
    run = forecast_job(
        store,
        state,
        data,
        {
            "provider": "ensemble",
            "artifact_id": artifact,
            "serving_bundle_id": bundle["serving_bundle_id"],
            "mode": "shadow",
            "horizon_events": 1,
        },
    )
    assert run.model_family == "ensemble" and len(run.projections) == 12
    assert run.model_status == "experimental"


@pytest.mark.parametrize("configured", [6], indirect=True)
def test_ensemble_weights_remain_earlier_than_every_later_untouched_fold(configured, monkeypatch):
    store, _, _, model, _, _, collection, _ = configured
    monkeypatch.setenv("DATA_DIR", str(model.parent.parent.parent))
    artifact = produce_football_ensemble(store, collection["collection_id"], model.name)
    directory = model.parent.parent / "ensemble" / artifact
    report = json.loads((directory / "evaluation.json").read_text())
    receipts = json.loads((directory / "training_receipts.json").read_text())
    assert report["test_origin_count"] == 2
    assert report["blend"]["n"] == 12
    assert receipts["later_untouched_fold_receipts"][0]["test_events"] == [6]
    assert len(receipts["later_untouched_fold_receipts"][0]["manifest_sha256"]) == 64
