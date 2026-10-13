"""Genuine CatBoost adapter mechanics on synthetic football sources, not accuracy evidence."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
import pytest

from fpl_app.contracts import ManagerState, Pick
from fpl_app.jobs import Queue, Worker
from fpl_app.models.football_catboost import forecast_frozen, train_collection_experiment
from fpl_app.models.router import create_serving_bundle, forecast_job, resolve_forecast
from fpl_app.providers import Provider
from fpl_app.providers.collection import collect_football
from fpl_app.storage import Store


@pytest.fixture
def configured(tmp_path, monkeypatch, request):
    from fpl_app.models import router

    monkeypatch.setattr(router, "data_dir", lambda: tmp_path)
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    final_events = getattr(request, "param", 5)
    deadline = (datetime.now(UTC) + timedelta(days=4)).isoformat()
    elements = [
        {
            "id": i,
            "team": 1 if i % 2 else 2,
            "element_type": 1 + i % 4,
            "web_name": f"P{i}",
            "now_cost": 50,
            "points_per_game": "2",
            "minutes": 400,
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 0,
            "status": "u" if i == 3 else "s" if i == 4 else "a",
            "chance_of_playing_next_round": 0 if i == 1 else 75 if i == 2 else None,
            "news": "Confirmed unavailable" if i == 1 else "",
        }
        for i in range(1, 7)
    ]
    bootstrap = {
        "elements": elements,
        "teams": [{"id": 1}, {"id": 2}],
        "events": [
            {
                "id": event,
                "deadline_time": f"2026-08-{event * 5:02d}T00:00:00Z",
                "data_checked": True,
            }
            for event in range(1, final_events + 1)
        ]
        + [{"id": 7, "deadline_time": deadline, "is_next": True}],
    }
    fixtures = [
        {
            "id": event * 10,
            "event": event,
            "team_h": 1,
            "team_a": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
            "kickoff_time": f"2026-08-{event * 5:02d}T02:00:00Z",
            "finished_provisional": True,
        }
        for event in range(1, final_events + 1)
    ]
    fixtures += [
        {
            "id": 70 + j,
            "event": 7,
            "team_h": 1 if j == 1 else 2,
            "team_a": 2 if j == 1 else 1,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
            "kickoff_time": (datetime.now(UTC) + timedelta(days=5 + j)).isoformat(),
            "finished_provisional": False,
        }
        for j in [1, 2]
    ]

    def respond(request):
        path = request.url.path
        if path.endswith("bootstrap-static/"):
            value = bootstrap
        elif path.endswith("/fixtures/"):
            value = fixtures
        else:
            identifier = int(path.rstrip("/").split("/")[-1])
            value = {
                "history": [
                    {
                        "fixture": event * 10,
                        "round": event,
                        "minutes": 60 + identifier,
                        "starts": 1,
                        "total_points": event + identifier,
                        "kickoff_time": f"2026-08-{event * 5:02d}T02:00:00Z",
                    }
                    for event in range(1, final_events + 1)
                ],
                "fixtures": [],
                "history_past": [],
            }
        return httpx.Response(200, json=value)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    data = provider.refresh(force=True)
    collection = collect_football(store, provider, list(range(1, 7)))
    state = ManagerState(
        team_id=1,
        next_event=7,
        data_mode="live",
        snapshot_id=data["snapshot_id"],
        picks=[Pick(player_id=i) for i in range(1, 5)],
    )
    store.put("state", 1, state.model_dump(mode="json"))
    directory = train_collection_experiment(
        collection, tmp_path / "models" / "football_catboost", "fpl-2026-27"
    )
    # Exercise the earlier immutable manifest dialect without changing real local artifacts.
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest.pop("model_family")
    manifest.pop("artifacts")
    manifest.pop("data_mode")
    manifest["training_cutoff"] = manifest["information_cutoff"]
    (directory / "manifest.json").write_text(json.dumps(manifest))
    origin = json.loads((directory / "forecast_origin.json").read_text())
    origin["artifact_manifest_sha256"] = hashlib.sha256(
        (directory / "manifest.json").read_bytes()
    ).hexdigest()
    (directory / "forecast_origin.json").write_text(json.dumps(origin))
    bundle = create_serving_bundle(store, state, collection["collection_id"], directory.name)
    payload = {
        "team_id": 1,
        "horizon_events": 1,
        "provider": "football_catboost",
        "mode": "experimental",
        "artifact_id": directory.name,
        "serving_bundle_id": bundle["serving_bundle_id"],
    }
    return store, state, data, directory, manifest, payload, collection, bundle


def test_real_fit_adapter_reload_worker_and_retry(configured):
    store, state, data, directory, _, payload, _, bundle = configured
    manifest = json.loads((directory / "manifest.json").read_text())
    evaluation = json.loads((directory / "evaluation.json").read_text())
    fitted = pd.read_parquet(directory / "features.parquet")
    assert manifest["artifact_kind"] == "latest_serving_refit"
    assert manifest["partitions"]["fit"]["events"] == [1, 2, 3, 4, 5]
    assert manifest["evaluation_completed_at"] <= manifest["executed_at"]
    assert evaluation["held_out_events"] == [5]
    assert evaluation["selected_method"] == "points_minutes_role_fixture"
    assert len(evaluation["feature_ablation_sequence"]) == 3
    assert manifest["method_matches_evaluation"] is True
    fold = evaluation["folds"][0]
    assert fold["train_events"] == [1, 2]
    assert fold["validation_events"] == [3]
    assert fold["calibration_events"] == [4]
    assert fold["test_events"] == [5]
    assert set(fitted.event) == {1, 2, 3, 4, 5}
    queue = Queue(store)
    first = queue.enqueue("projection", {"team_id": 1, "horizon_events": 1})
    assert Worker(queue).run_once()
    baseline = queue.get(first["id"])["result"]
    second = queue.enqueue("projection", payload)
    assert Worker(queue).run_once()
    job = queue.get(second["id"])
    assert job["status"] == "succeeded", job.get("error")
    challenger = job["result"]
    assert challenger["resolved_provider"] == "football_catboost"
    assert challenger["model_family"] == "football_catboost"
    assert challenger["evidence_mode"] == "experimental_live"
    assert challenger["player_universe_ids"] == list(range(1, 7))
    assert len(challenger["projections"]) == 12  # both fixtures, one frozen origin
    assert challenger["projection_run_id"] != baseline["projection_run_id"]
    direct = forecast_job(store, state, data, job["payload"])
    assert direct.model_dump(mode="json") == challenger
    raw = forecast_frozen(
        directory,
        pd.read_parquet(directory / bundle["features_file"]),
        pd.read_parquet(directory / bundle["mappings_file"]),
        bundle["prediction_origin"],
    )
    for projection in direct.projections:
        model = raw[
            (raw.player_id == projection.player_id) & (raw.fixture_id == projection.fixture_id)
        ].iloc[0]
        assert projection.components["raw_unconditional_points_mean"] == model.points_mean
        if projection.player_id in [1, 3, 4]:
            assert (
                projection.expected_points
                == projection.expected_minutes
                == projection.appearance_probability
                == projection.minutes_60_probability
                == projection.start_probability
                == 0
            )
            assert all(v == 0 for v in projection.point_quantiles.values())
            assert model.points_mean > 0
            assert any("sha256:" in note for note in projection.assumptions)
        else:
            assert projection.expected_points == model.points_mean  # no 75% multiplier
    assert queue.enqueue("projection", payload)["id"] == second["id"]


def test_owned_universe_blocks_missing_players(configured):
    store, state, data, _, _, payload, _, bundle = configured
    state.picks.append(Pick(player_id=99))
    with pytest.raises(ValueError, match="owned"):
        resolve_forecast(store, payload, state)
    state.picks.pop()
    # Extra full-catalog candidates do not become fabricated zeros; explicit universe is retained.
    data["players"].append({**data["players"][0], "player_id": 99})
    store.put("dataset", state.snapshot_id, data)
    run = forecast_job(store, state, data, payload)
    assert run.player_universe_ids == bundle["player_ids"]
    assert 99 not in {p.player_id for p in run.projections}


@pytest.mark.parametrize(
    "filename",
    ["points.cbm", "future_features.parquet", "current_mappings.parquet", "forecast_origin.json"],
)
def test_changed_files_fail_after_enqueue(configured, filename):
    store, _, _, directory, _, payload, _, _ = configured
    queue = Queue(store)
    job = queue.enqueue("projection", payload)
    with (directory / filename).open("ab") as out:
        out.write(b"corruption")
    assert Worker(queue).run_once()
    assert queue.get(job["id"])["status"] == "failed"


def test_changed_manifest_or_bundle_fails(configured):
    store, state, data, directory, metadata, payload, _, bundle = configured
    reference = resolve_forecast(store, payload, state)
    changed = {**bundle, "player_ids": [1]}
    changed.pop("serving_bundle_id")
    store.put("forecast_bundle", payload["serving_bundle_id"], changed)
    with pytest.raises(ValueError, match="bundle changed"):
        forecast_job(store, state, data, {**payload, "_forecast": reference})
    metadata["mapping_version"] = "changed"
    (directory / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="manifest changed"):
        forecast_job(store, state, data, {**payload, "_forecast": reference})


def test_default_needs_recorded_promotion(configured):
    store, state, _, _, _, payload, _, _ = configured
    with pytest.raises(ValueError, match="promotion"):
        resolve_forecast(store, {**payload, "mode": "default"}, state)


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_available_at", "2099-01-01T00:00:00Z"),
        ("current_training_data_available_at", "2099-01-01T00:00:00Z"),
        ("rules_version", "fpl-2024-25"),
        ("rules_version", "fpl-2026-27-unreviewed"),
        ("supported_horizon", 0),
    ],
)
def test_incompatible_artifact_fails(configured, field, value):
    store, state, _, directory, metadata, payload, _, _ = configured
    metadata[field] = value
    (directory / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        resolve_forecast(store, payload, state)


def test_future_and_past_deadline_rejected(configured, monkeypatch):
    store, state, _, _, _, payload, collection, _ = configured
    from fpl_app.models import router

    deadline = next(e["actual_deadline"] for e in collection["event_evidence"] if e["event"] == 7)
    monkeypatch.setattr(router, "utcnow", lambda: deadline)
    with pytest.raises(ValueError, match="deadline has passed"):
        resolve_forecast(store, payload, state)


def test_factory_is_read_only_on_invalid_state(configured):
    store, state, _, directory, _, _, collection, _ = configured
    before = store.get("state", state.team_id)
    state.next_event = 6
    with pytest.raises(ValueError, match="event/artifact|Manager state"):
        create_serving_bundle(store, state, collection["collection_id"], directory.name)
    assert store.get("state", state.team_id) == before
    state.next_event = 7
    store.put("current", "live", {"snapshot_id": "new"})
    with pytest.raises(ValueError, match="stale"):
        create_serving_bundle(store, state, collection["collection_id"], directory.name)


def test_retained_raw_source_checksum_is_required(configured):
    store, state, _, _, _, payload, collection, _ = configured
    from sqlalchemy import update

    from fpl_app.storage import snapshots

    source = collection["sources"][0]
    with store.engine.begin() as connection:
        connection.execute(
            update(snapshots).where(snapshots.c.id == source["id"]).values(raw=b"modified")
        )
    with pytest.raises(ValueError, match="checksum"):
        resolve_forecast(store, payload, state)


@pytest.mark.parametrize(
    "change",
    ["future_origin", "numeric_feature", "missing_exposure", "wrong_mapping", "source_time"],
)
def test_resealed_invalid_frames_still_rejected(configured, change):
    store, state, _, directory, _, _payload, collection, bundle = configured
    features = pd.read_parquet(directory / bundle["features_file"])
    mappings = pd.read_parquet(directory / bundle["mappings_file"])
    record = json.loads((directory / "forecast_origin.json").read_text())
    if change == "future_origin":
        record["prediction_origin"] = "2099-01-01T00:00:00Z"
        features["decision_cutoff"] = record["prediction_origin"]
    elif change == "numeric_feature":
        features.loc[0, "points_5"] = 1000
    elif change == "missing_exposure":
        features = features.iloc[1:]
    elif change == "wrong_mapping":
        mappings.loc[0, "player_key"] = "official_fpl:2025/26:element:1"
    else:
        features["source_available_at"] = "2099-01-01T00:00:00Z"
    features.to_parquet(directory / bundle["features_file"], index=False)
    mappings.to_parquet(directory / bundle["mappings_file"], index=False)
    for name in [bundle["features_file"], bundle["mappings_file"]]:
        record["files"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    (directory / "forecast_origin.json").write_text(json.dumps(record))
    with pytest.raises(ValueError):
        create_serving_bundle(store, state, collection["collection_id"], directory.name)


def test_bundle_paths_and_symlinks_are_rejected(configured):
    store, state, data, directory, _, payload, _, bundle = configured
    reference = resolve_forecast(store, payload, state)
    filename = bundle["features_file"]
    saved = directory / "saved.parquet"
    (directory / filename).rename(saved)
    (directory / filename).symlink_to(saved)
    with pytest.raises(ValueError, match="Unsafe"):
        forecast_job(store, state, data, {**payload, "_forecast": reference})
    (directory / filename).unlink()
    saved.rename(directory / filename)
    changed = {k: v for k, v in bundle.items() if k != "serving_bundle_id"}
    changed["files"] = {**changed["files"], "../outside": "a" * 64}
    store.put("forecast_bundle", payload["serving_bundle_id"], changed)
    with pytest.raises(ValueError, match="Unsafe"):
        resolve_forecast(store, payload, state)


def test_prepare_cli_reuses_artifact_without_private_state_edits(configured):
    import runpy
    from pathlib import Path

    store, state, _, directory, _, _, collection, _ = configured
    namespace = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts" / "prepare_football_forecast.py")
    )
    before = store.get("state", state.team_id)
    result = namespace["prepare_forecast"](
        store, collection["collection_id"], state.team_id, True, directory.name
    )
    assert result["serving_status"] == "registered_experimental_only"
    assert result["promoted"] is False
    assert store.get("state", state.team_id) == before
    state.next_event = 6
    store.put("state", state.team_id, state.model_dump(mode="json"))
    before = store.get("state", state.team_id)
    result = namespace["prepare_forecast"](
        store, collection["collection_id"], state.team_id, True, directory.name
    )
    assert result["serving_status"] == "blocked_pending_state_or_source_review"
    assert store.get("state", state.team_id) == before


def test_earlier_actual_training_alias_and_provenance_binding(configured):
    store, state, data, directory, manifest, _, collection, _ = configured
    manifest["current_training_available"] = manifest.pop("current_training_data_available_at")
    (directory / "manifest.json").write_text(json.dumps(manifest))
    origin = json.loads((directory / "forecast_origin.json").read_text())
    origin["artifact_manifest_sha256"] = hashlib.sha256(
        (directory / "manifest.json").read_bytes()
    ).hexdigest()
    (directory / "forecast_origin.json").write_text(json.dumps(origin))
    bundle = create_serving_bundle(store, state, collection["collection_id"], directory.name)
    run = forecast_job(
        store,
        state,
        data,
        {
            "provider": "football_catboost",
            "mode": "experimental",
            "artifact_id": directory.name,
            "serving_bundle_id": bundle["serving_bundle_id"],
            "horizon_events": 1,
        },
    )
    assert run.resolved_provider == "football_catboost"
    manifest["provenance"]["source_ref"] = "unbound-source"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    origin["artifact_manifest_sha256"] = hashlib.sha256(
        (directory / "manifest.json").read_bytes()
    ).hexdigest()
    (directory / "forecast_origin.json").write_text(json.dumps(origin))
    with pytest.raises(ValueError, match="source evidence"):
        create_serving_bundle(store, state, collection["collection_id"], directory.name)
