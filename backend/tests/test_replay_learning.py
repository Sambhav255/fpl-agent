"""Authored mechanics/provenance fixtures, never prospective football evidence."""

import hashlib
import inspect
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import Fixture, Settings
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.provenance import ReplayArtifact, ReplayManifest, implementation_sha256
from fpl_app.evaluation.strategy import (
    ReplayOrigin,
    greedy_policy,
    keep_policy,
    planner_policy,
    replay_policy,
)


def make_origin(horizon=6, event=8):
    state, players, run = funding_fixture(horizon)
    state.next_event = event
    for projection in run.projections:
        projection.event += event - 8
    outcomes = {p.player_id: [MatchStats(minutes=90, goals_conceded_on_pitch=1)] for p in players}
    return state, ReplayOrigin(
        "2026-10-10T12:00:00Z",
        "2026-10-09T01:00:00Z",
        players,
        run,
        outcomes,
        evidence_mode="synthetic_mechanics",
    )


def test_full_horizon_then_replan_only_executes_first_week():
    state, first = make_origin()
    _, second = make_origin(event=9)
    second.deadline = "2026-10-17T12:00:00Z"
    second.information_available_at = "2026-10-16T01:00:00Z"
    second.forecasts.source_cutoff = "2026-10-16T00:00:00Z"
    second.forecasts.snapshot_id = "later"
    # Deliberately different later forecasts cannot overwrite the first origin's path.
    for projection in second.forecasts.projections:
        projection.expected_points = 1000
    seen = []

    def delayed_policy(current, players, run, settings):
        seen.append((settings.horizon_events, current.next_event, run.snapshot_id))
        plan = keep_policy(current, players, run, settings)
        assert run.projections[0].expected_points == (10 if current.next_event == 8 else 1000)
        return plan

    report = replay_policy(state, [first, second], delayed_policy, Settings(horizon_events=6))
    assert seen == [(6, 8, "audit"), (6, 9, "later")]
    assert [r["planning_horizon_events"] for r in report["rows"]] == [6, 6]
    assert report["realised_net_points"] == 48  # Only two events scored, not twelve.
    assert report["forecast_net_points"] == 84 + 12000
    assert report["rows"][0]["forecast_path_net_points"] == 6 * 84
    assert state.next_event == 8 and state.snapshot_id == "audit"


def test_delayed_transfers_are_validated_but_not_executed():
    state, item = make_origin(horizon=2)
    state.free_transfers_at_event_start = 1
    item.players = item.players[:17]
    item.forecasts.projections = [p for p in item.forecasts.projections if p.player_id != 18]
    for projection in item.forecasts.projections:
        if projection.player_id == 17:
            projection.expected_points = 0 if projection.event == 8 else 40
    report = replay_policy(
        state,
        [item],
        planner_policy,
        Settings(horizon_events=2, max_additional_hit_points=0, max_transfers_this_event=1),
    )
    assert report["rows"][0]["actions"] == []
    assert {p["player_id"] for p in report["final_state"]["picks"]} == set(range(1, 16))
    assert report["rows"][0]["forecast_path_net_points"] > 168


def test_invalid_future_week_rejected_before_any_execution():
    state, item = make_origin()
    initial = state.model_dump()

    def invalid_policy(current, players, run, settings):
        plan = keep_policy(current, players, run, settings)
        plan.weeks[-1]["bank_units"] = 999
        return plan

    with pytest.raises(ValueError, match="Replay mismatch: bank_units"):
        replay_policy(state, [item], invalid_policy, Settings(horizon_events=6))
    assert state.model_dump() == initial


@pytest.mark.parametrize("support,event,expected", [(1, 8, 1), (6, 37, 2), (6, 38, 1)])
def test_support_and_season_end_cap(support, event, expected):
    state, item = make_origin(horizon=min(support, 39 - event), event=event)
    item.forecasts.horizon_events = support
    observed = []

    def observe(current, players, run, settings):
        observed.append(settings.horizon_events)
        return keep_policy(current, players, run, settings)

    report = replay_policy(state, [item], observe, Settings(horizon_events=6))
    assert observed == [expected]
    assert report["rows"][0]["planning_horizon_events"] == expected


def test_greedy_remains_a_valid_one_event_comparator():
    state, item = make_origin()
    report = replay_policy(state, [item], greedy_policy, Settings(horizon_events=6))
    assert report["rows"][0]["planning_horizon_events"] == 1
    assert report["rows"][0]["transfers"] <= 1


def strict_fixture(tmp_path):
    state, item = make_origin(horizon=1)
    state.data_mode = item.forecasts.data_mode = "live"
    item.evidence_mode = "prospective_strict"
    item.forecasts.prediction_origin = "2026-10-09T00:30:00Z"
    item.forecasts.mapping_version = "authored-v1"
    item.forecasts.fixtures = [
        Fixture(fixture_id=800 + club, event=8, home_club=club, away_club=100 + club)
        for club in {p.club for p in item.players}
    ]
    artifacts = []
    for role in ("source", "model", "policy", "mapping"):
        raw = (
            Path(inspect.getsourcefile(keep_policy)).read_bytes()
            if role == "policy"
            else role.encode()
        )
        filename = f"{role}.bin"
        (tmp_path / filename).write_bytes(raw)
        artifacts.append(
            ReplayArtifact(
                role=role,
                filename=filename,
                sha256=hashlib.sha256(raw).hexdigest(),
                captured_at="2026-10-09T00:00:00Z",
                available_at="2026-10-09T00:00:00Z",
            )
        )
    manifest = ReplayManifest(
        deadline=item.deadline,
        information_available_at=item.information_available_at,
        forecast=item.forecasts,
        players=item.players,
        schedule_complete_events=[8],
        artifacts=artifacts,
        policy_identifier=f"{keep_policy.__module__}.{keep_policy.__qualname__}",
        implementation_sha256=implementation_sha256(),
    )
    item.manifest_path = tmp_path / "replay.json"
    write_manifest(item, manifest)
    return state, item, manifest


def write_manifest(item, manifest):
    raw = manifest.model_dump_json().encode()
    item.manifest_path.write_bytes(raw)
    item.manifest_sha256 = hashlib.sha256(raw).hexdigest()


def test_strict_retained_evidence_success_and_mutation(tmp_path):
    state, item, _ = strict_fixture(tmp_path)
    report = replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    assert report["rows"][0]["provenance"]["verified"]
    (tmp_path / "model.bin").write_bytes(b"changed model")
    with pytest.raises(ValueError, match="artifact checksum"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("prediction", "prediction origin"),
        ("artifact", "artifact availability"),
        ("capture", "artifact availability"),
        ("schedule", "fixture schedule"),
        ("mapping", "does not bind"),
        ("catalogue", "does not bind"),
        ("forecast", "does not bind"),
        ("role", "Missing source"),
        ("checksum", "manifest checksum"),
        ("reference", "frozen manifest"),
        ("path", "filename"),
        ("policy", "Policy implementation"),
        ("implementation", "Policy implementation"),
        ("source_cutoff", "Source artifact"),
    ],
)
def test_strict_gates(tmp_path, mutation, error):
    state, item, manifest = strict_fixture(tmp_path)
    if mutation == "prediction":
        item.forecasts.prediction_origin = "2026-10-11T00:00:00Z"
        manifest.forecast = item.forecasts
    elif mutation == "artifact":
        manifest.artifacts[0].available_at = "2026-10-11T00:00:00Z"
    elif mutation == "capture":
        manifest.artifacts[0].captured_at = "2026-10-11T00:00:00Z"
    elif mutation == "schedule":
        manifest.schedule_complete_events = []
    elif mutation == "mapping":
        item.forecasts = item.forecasts.model_copy(update={"mapping_version": "changed"})
    elif mutation == "catalogue":
        item.players = deepcopy(item.players)
        item.players[0].market_price_units = 51
    elif mutation == "forecast":
        item.forecasts = item.forecasts.model_copy(deep=True)
        item.forecasts.projections[0].expected_points = 100
    elif mutation == "role":
        manifest.artifacts = manifest.artifacts[1:]
    elif mutation == "path":
        manifest.artifacts[0].filename = "../source.bin"
    elif mutation == "policy":
        manifest.policy_identifier = "different.policy"
    elif mutation == "implementation":
        manifest.implementation_sha256 = "a" * 64
    elif mutation == "source_cutoff":
        manifest.artifacts[0].available_at = "2026-10-09T00:15:00Z"
    write_manifest(item, manifest)
    if mutation == "checksum":
        item.manifest_path.write_text("{}")
    elif mutation == "reference":
        item.manifest_sha256 = None
    with pytest.raises(ValueError, match=error):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


def test_strict_requires_frozen_schedule_and_all_model_payloads(tmp_path):
    state, item, manifest = strict_fixture(tmp_path)
    item.forecasts.fixtures = []
    manifest.forecast = item.forecasts
    write_manifest(item, manifest)
    with pytest.raises(ValueError, match="fixture schedule"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    state, item, manifest = strict_fixture(tmp_path)
    model = {
        "artifact_id": "authored",
        "artifacts": {"weights.cbm": "a" * 64},
        "available_at": "2026-10-09T00:00:00Z",
        "training_cutoff": "2026-10-08T00:00:00Z",
    }
    raw = json.dumps(model).encode()
    (tmp_path / "model.bin").write_bytes(raw)
    manifest.artifacts[1].sha256 = hashlib.sha256(raw).hexdigest()
    item.forecasts.artifact_id = "authored"
    item.forecasts.artifact_manifest_sha256 = manifest.artifacts[1].sha256
    manifest.forecast = item.forecasts
    write_manifest(item, manifest)
    with pytest.raises(ValueError, match="bound model payloads"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


@pytest.mark.parametrize("model_time", ["available_at", "training_cutoff"])
def test_advanced_model_cannot_hide_future_actual_timing(tmp_path, model_time):
    state, item, manifest = strict_fixture(tmp_path)
    raw_payload = b"authored model bytes, no training claim"
    payload_digest = hashlib.sha256(raw_payload).hexdigest()
    (tmp_path / "weights.cbm").write_bytes(raw_payload)
    manifest.artifacts.append(
        ReplayArtifact(
            role="model",
            filename="weights.cbm",
            sha256=payload_digest,
            captured_at="2026-10-09T00:00:00Z",
            available_at="2026-10-09T00:00:00Z",
        )
    )
    metadata = {
        "artifact_id": "authored",
        "artifacts": {"weights.cbm": payload_digest},
        "available_at": "2026-10-09T00:00:00Z",
        "training_cutoff": "2026-10-08T00:00:00Z",
    }
    item.forecasts.model_family = "football_catboost"
    item.forecasts.artifact_id = "authored"

    def bind_model():
        raw = json.dumps(metadata).encode()
        (tmp_path / "model.bin").write_bytes(raw)
        manifest.artifacts[1].sha256 = hashlib.sha256(raw).hexdigest()
        item.forecasts.artifact_manifest_sha256 = manifest.artifacts[1].sha256
        manifest.forecast = item.forecasts
        write_manifest(item, manifest)

    bind_model()
    assert replay_policy(state, [item], keep_policy, Settings(horizon_events=1))["legal"]
    metadata[model_time] = "2026-10-11T00:00:00Z"
    bind_model()
    with pytest.raises(ValueError, match="future replay model timing"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


def test_reconstruction_allows_present_artifact_but_not_future_fitting_labels():
    state, item = make_origin(horizon=1)
    item.evidence_mode = "historical_reconstructed"
    item.forecasts.prediction_origin = "2026-10-12T00:00:00Z"
    item.fitting_labels_available_at = "2026-10-08T00:00:00Z"
    report = replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    assert not report["rows"][0]["provenance"]["verified"]
    assert report["rows"][0]["evidence_mode"] == "historical_reconstructed"
    item.fitting_labels_available_at = "2026-10-11T00:00:00Z"
    with pytest.raises(ValueError, match="Future reconstructed fitting labels"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    item.fitting_labels_available_at = None
    with pytest.raises(ValueError, match="simulated fitting label cutoff"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))


@pytest.mark.parametrize("field", ["deadline", "information_available_at"])
def test_naive_timing_and_unknown_modes_rejected(field):
    state, item = make_origin(horizon=1)
    setattr(item, field, "2026-10-09T00:00:00")
    with pytest.raises(ValueError, match="timezone"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
    setattr(item, field, "2026-10-09T01:00:00Z")
    item.evidence_mode = "invented_prospective"
    with pytest.raises(ValueError, match="Unsupported replay evidence mode"):
        replay_policy(state, [item], keep_policy, Settings(horizon_events=1))
