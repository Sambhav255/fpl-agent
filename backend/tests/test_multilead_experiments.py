import copy
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from fpl_app.features.football import FEATURES
from fpl_app.features.multilead import EXTRA, direct_panel
from fpl_app.models import multilead_experiments as multi
from fpl_app.models.rolling_experiments import _fit_unit
from fpl_app.storage import Store, fingerprint


def collection(events=10, players=4):
    start = pd.Timestamp("2026-07-01T00:00:00Z")
    labels, exposures, coverage = [], [], []
    for event in range(1, events + 3):
        origin = start + timedelta(days=7 * event)
        for player in range(1, players + 1):
            fixture_ids = [event * 10]
            if event == 6 and player == 2:
                fixture_ids = []  # explicit blank
            if event == 7:
                fixture_ids.append(event * 10 + 1)  # double
            for fixture in fixture_ids:
                kickoff = origin + timedelta(days=1 + fixture % 10)
                exposures.append(
                    {
                        "provider_player_id": player,
                        "canonical_player_id": f"player-{player}",
                        "fixture_id": fixture,
                        "event": event,
                        "is_home": True,
                        "canonical_club_id": "club-1",
                        "opponent_provider_club_id": 2,
                        "kickoff": kickoff.isoformat(),
                        "snapshot_id": "fixtures",
                        "available_at": "2026-10-30T00:00:00Z",
                    }
                )
                if event > events or (event == 5 and player == 3):
                    continue
                minutes = [0, 30, 60, 90][player % 4]
                points = [-2, 1, 4, 7][player % 4]
                labels.append(
                    {
                        "provider_player_id": player,
                        "canonical_player_id": f"player-{player}",
                        "fixture_id": fixture,
                        "event": event,
                        "minutes": minutes,
                        "total_points": points,
                        "label_status": "final_revision",
                        "available_at": "2026-10-30T00:00:00Z",
                        "statistics": {
                            "kickoff_time": kickoff.isoformat(),
                            "minutes": minutes,
                            "total_points": points,
                            "starts": int(minutes >= 60),
                            "expected_goals": 0.1,
                            "expected_assists": 0.05,
                        },
                    }
                )
            coverage.append(
                {
                    "provider_player_id": player,
                    "event": event,
                    "status": "blank_event" if not fixture_ids else "rows_present",
                }
            )
    return {
        "collection_id": "collection",
        "season": "2026/27",
        "envelope_sha256": "source",
        "captured_at": "2026-10-31T00:00:00Z",
        "labels": labels,
        "player_mappings": [
            {
                "provider_player_id": player,
                "canonical_player_id": f"player-{player}",
                "position": player % 4 + 1,
            }
            for player in range(1, players + 1)
        ],
        "event_evidence": [
            {"event": event, "actual_deadline": (start + timedelta(days=7 * event)).isoformat()}
            for event in range(1, events + 3)
        ],
        "schedule_exposures": exposures,
        "coverage": coverage,
    }


def test_no_intervening_results_enter_direct_lead_features():
    source = collection()
    before, _ = direct_panel(source, [1, 3])
    altered = copy.deepcopy(source)
    for label in altered["labels"]:
        if label["event"] >= 4:
            label["total_points"] += 10000
            label["statistics"]["total_points"] += 10000
            label["minutes"] = 1
            label["statistics"]["minutes"] = 1
            label["statistics"]["expected_goals"] = 10000
    after, _ = direct_panel(altered, [1, 3])
    mask = (before.event == 6) & (before.lead == 3)
    assert set(before.loc[mask, "origin_event"]) == {4}
    pd.testing.assert_frame_equal(
        before.loc[mask, FEATURES + EXTRA], after.loc[mask, FEATURES + EXTRA]
    )
    assert (before.loc[mask, "target_points"] != after.loc[mask, "target_points"]).any()


def test_doubles_blank_missing_and_negative_targets_are_distinct():
    frame, ledger = direct_panel(collection(), [2])
    double = frame[(frame.event == 7) & (frame.player_id == 1)]
    assert len(double) == 2
    assert double.decision_cutoff.nunique() == 1
    assert double.history_refs.nunique() == 1
    blank = ledger[(ledger.event == 6) & (ledger.player_id == 2)].iloc[0]
    assert blank.coverage_status == "blank_event" and blank.target_points == 0
    assert frame[(frame.event == 6) & (frame.player_id == 2)].empty
    missing = frame[(frame.event == 5) & (frame.player_id == 3)].iloc[0]
    assert missing.outcome_status == "missing_or_unfinalized" and pd.isna(missing.target_points)
    assert (frame.target_points < 0).any()


def test_spaced_validation_and_target_completion_purge_includes_entire_double():
    frame, _ = direct_panel(collection(events=16), [3])
    folds = multi.chronological_folds(frame, "2026-10-31T00:00:00Z")
    assert folds
    for fold in folds:
        assert pd.Timestamp(fold["train_target_end"]) < pd.Timestamp(fold["validation_origin"])
        assert pd.Timestamp(fold["validation_target_end"]) < pd.Timestamp(fold["test_origin"])
        assert (
            max(fold["validation_events"])
            < frame.loc[fold["indices"]["test"], "origin_event"].min()
        )
    # A later fixture delays the WHOLE event, even when its first fixture completed.
    target = frame[(frame.event == 7) & (frame.fixture_id == 71)].index
    frame.loc[target, "target_available_at"] = "2026-12-01T00:00:00Z"
    # Actual-as-of gate excludes those delayed rows entirely; use a within-as-of
    # delay to ensure common-event embargo prevents partial target-event fitting.
    frame.loc[target, "target_available_at"] = "2026-10-29T00:00:00Z"
    changed = multi.chronological_folds(frame, "2026-10-31T00:00:00Z")
    for fold in changed:
        assert 7 not in fold["train_events"] + fold["validation_events"]


def test_short_history_keeps_unsupported_leads_unavailable():
    frame, _ = direct_panel(collection(events=8), multi.LEADS)
    support = {
        lead: multi.chronological_folds(frame[frame.lead == lead], "2026-10-31T00:00:00Z")
        for lead in multi.LEADS
    }
    assert support[1] and support[2]
    assert all(not support[lead] for lead in [3, 4, 6, 8])


def test_late_asof_fixture_excludes_whole_event_and_missing_double_is_not_partial():
    frame, _ = direct_panel(collection(events=10), [1])
    late = frame[(frame.event == 7) & (frame.fixture_id == 71)].index
    frame.loc[late, "target_available_at"] = "2026-12-01T00:00:00Z"
    folds = multi.chronological_folds(frame, "2026-10-31T00:00:00Z")
    assert all(
        7 not in fold["test_events"] + fold["validation_events"] + fold["train_events"]
        for fold in folds
    )
    frame, _ = direct_panel(collection(events=10), [1])
    missing = frame[(frame.event == 7) & (frame.fixture_id == 71) & (frame.player_id == 1)].index
    frame.loc[missing, "target_points"] = np.nan
    folds = multi.chronological_folds(frame, "2026-10-31T00:00:00Z")
    first = frame[(frame.event == 7) & (frame.player_id == 1)].index
    assert all(
        not set(first) & {i for values in fold["indices"].values() for i in values}
        for fold in folds
    )


def test_registration_and_shared_score_before_reuse_guard(monkeypatch):
    store = Store("sqlite:///:memory:")
    source = collection()
    monkeypatch.setattr(multi, "load_collection", lambda *_: source)
    spec = multi.protocol(source)
    with pytest.raises(KeyError):
        multi.training_input(store, {"protocol": spec})
    store.put("multilead_experiment_protocol", fingerprint(spec), spec, expected=0)
    identity = multi.training_input(store, {"protocol": spec})
    assert identity
    store.put("forecast_benchmark", "frozen", {"benchmark_id": "frozen", "event": 8})
    with pytest.raises(ValueError, match="Score finalized"):
        multi.training_input(store, {"protocol": spec})


def test_real_head_fit_outer_labels_cannot_change_predictions_and_retry_verifies_bytes(tmp_path):
    frame, _ = direct_panel(collection(events=8), [2])
    fold = multi.chronological_folds(frame, "2026-10-31T00:00:00Z")[0]
    config = {
        "name": "direct_points",
        "features": FEATURES + EXTRA,
        "depth": 2,
        "l2_leaf_reg": 10,
        "seed": 43,
    }
    spec = {"iterations": 5, "early_stopping_rounds": 2, "thread_count": 2, "learning_rate": 0.04}
    first = _fit_unit(tmp_path / "a", "identity", fold, config, spec, frame)
    changed = frame.copy()
    changed.loc[fold["indices"]["test"], "target_points"] += 10000
    second = _fit_unit(tmp_path / "b", "identity", fold, config, spec, changed)
    np.testing.assert_array_equal(first.predicted_points, second.predicted_points)
    resumed = _fit_unit(tmp_path / "a", "identity", fold, config, spec, frame)
    np.testing.assert_array_equal(first.predicted_points, resumed.predicted_points)
    predictions = tmp_path / "a" / fold["fold_id"] / "direct_points/predictions.parquet"
    predictions.write_bytes(predictions.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        _fit_unit(tmp_path / "a", "identity", fold, config, spec, frame)


def test_complete_research_run_reuses_verified_report_and_preserves_unavailable_leads(
    tmp_path, monkeypatch
):
    source = collection(events=8)
    store = Store("sqlite:///:memory:")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(multi, "load_collection", lambda *_: source)
    specification = multi.protocol(source)
    specification.update(iterations=5, early_stopping_rounds=2)
    monkeypatch.setattr(multi, "protocol", lambda *_: specification)
    store.put(
        "multilead_experiment_protocol", fingerprint(specification), specification, expected=0
    )
    first = multi.train_job(store, {"protocol": specification})
    assert set(first["metrics_by_lead"]) == {"1", "2"}
    assert first["support_by_lead"]["3"]["status"] == "unavailable_insufficient_purged_history"
    assert not first["champion_promoted"] and not first["serving_refit"]
    monkeypatch.setattr(
        multi, "_fit_unit", lambda *_: pytest.fail("Verified completed report refitted")
    )
    resumed = multi.train_job(store, {"protocol": specification})
    assert first == resumed
    predictions = multi.Path(first["directory"]) / "outer_predictions.parquet"
    predictions.write_bytes(predictions.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        multi.train_job(store, {"protocol": specification})
