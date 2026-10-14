"""Reproducible prospective replay evidence, captured before forecast production.

A copy made today retains its original provider receipt, but newly generated code
and mappings get today's actual capture time. Old predictions cannot acquire a
new capture retrospectively. No manager state is inferred or edited here.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

from fpl_app.contracts import Fixture, ManagerState, Player
from fpl_app.evaluation.provenance import (
    ReplayArtifact,
    ReplayManifest,
    implementation_sha256,
    replay_time,
    verify_replay_manifest,
)
from fpl_app.evaluation.strategy import Policy
from fpl_app.jobs import input_state
from fpl_app.learning.replay import _inputs, _policy_id, packet_path, seal_journal_replay
from fpl_app.models.baseline import baseline_run
from fpl_app.models.training import data_dir
from fpl_app.providers import dataset, parse
from fpl_app.storage import Conflict, Store, fingerprint, utcnow


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()


def _capture_path(identifier: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", identifier):
        raise ValueError("Invalid replay capture ID")
    path = data_dir() / "replay_captures" / identifier
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Replay capture symlinks are not allowed")
    return path


def _sources(store: Store, data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, resource in (
        ("bootstrap_snapshot_id", "bootstrap-static/"),
        ("fixture_snapshot_id", "fixtures/"),
    ):
        source = store.snapshot(data[key])
        if (
            source["resource"] != resource
            or source["provider"] != "official_fpl"
            or source["data_mode"] != "live"
            or source["validation_status"] != "valid"
            or _digest(source["raw"]) != source["payload_sha256"]
            or not replay_time(source["captured_at"])
            <= replay_time(source["available_at"])
            <= replay_time(data["source_cutoff"])
        ):
            raise ValueError("Replay requires verified immutable official sources")
        parse(resource, json.loads(source["raw"]))
        rows.append(source)
    reconstructed = dataset(*rows)
    for key in ("players", "fixtures", "events", "next_event", "source_cutoff"):
        if reconstructed[key] != data[key]:
            raise ValueError("Replay catalogue differs from retained official source bytes")
    return rows


def capture_replay_evidence(
    store: Store, team_id: int, horizon: int, policy: Policy
) -> dict[str, Any]:
    """Capture the baseline champion's source/code/mapping evidence before queueing.

    Advanced providers need their own complete pre-origin model/input capture;
    this producer does not waive their timing or qualification gates.
    """
    state, data = input_state(store, team_id)
    if (
        state.data_mode != "live"
        or state.season != "2026/27"
        or not 1 <= horizon <= min(8, 39 - state.next_event)
    ):
        raise ValueError("Replay capture requires a live, supported forecast horizon")
    sources = _sources(store, data)
    events = list(range(state.next_event, state.next_event + horizon))
    declared = {row["id"] for row in data["events"]}
    if not set(events) <= declared:
        raise ValueError("Missing official event schedule declaration")
    deadline = next(row["deadline_time"] for row in data["events"] if row["id"] == state.next_event)
    captured = utcnow()
    if not replay_time(data["source_cutoff"]) <= replay_time(captured) < replay_time(deadline):
        raise ValueError("Replay capture must follow its sources and precede the deadline")
    identifier = "capture-" + uuid.uuid4().hex
    path = _capture_path(identifier)
    path.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, Any]] = []

    def save(role: str, name: str, raw: bytes, at: str, available: str) -> None:
        with (path / name).open("xb") as stream:
            stream.write(raw)
        artifacts.append(
            {
                "role": role,
                "filename": name,
                "sha256": _digest(raw),
                "captured_at": at,
                "available_at": available,
            }
        )

    source_receipts = []
    for index, source in enumerate(sources):
        save(
            "source",
            f"source-{index}.json",
            source["raw"],
            source["captured_at"],
            source["available_at"],
        )
        source_receipts.append(
            {
                key: source[key]
                for key in ("id", "resource", "payload_sha256", "captured_at", "available_at")
            }
        )
    code = inspect.getsourcefile(policy)
    baseline_code = inspect.getsourcefile(baseline_run)
    if code is None or baseline_code is None or "<locals>" in _policy_id(policy):
        raise ValueError("Replay policy must have a retained importable implementation")
    implementation = implementation_sha256()
    save("policy", "policy.py", Path(code).read_bytes(), captured, captured)
    save("model", "baseline.py", Path(baseline_code).read_bytes(), captured, captured)
    # Retain the exact package bytes, not just a digest that a later checkout
    # cannot reproduce. Fixed ZIP metadata makes the archive deterministic.
    package = Path(inspect.getfile(baseline_run)).resolve().parents[1]
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for module in sorted(package.rglob("*.py")):
            archive_entry = zipfile.ZipInfo(str(module.relative_to(package)))
            archive_entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(archive_entry, module.read_bytes())
    save("model", "implementation.zip", archive.getvalue(), captured, captured)
    save(
        "model",
        "implementation.json",
        _json(
            {
                "implementation_sha256": implementation,
                "provider": "baseline",
                "rules_version": "2026-27-v1",
            }
        ),
        captured,
        captured,
    )
    save(
        "mapping",
        "mappings.json",
        _json(
            {
                "season": state.season,
                "players": [
                    {
                        "player_id": row["player_id"],
                        "club": row["club"],
                        "position": row["position"],
                    }
                    for row in data["players"]
                ],
            }
        ),
        captured,
        captured,
    )
    capture_started = captured
    captured = utcnow()
    if not replay_time(capture_started) <= replay_time(captured) < replay_time(deadline):
        raise ValueError("Replay capture must complete before the deadline")
    for entry in artifacts:
        if entry["role"] != "source":
            entry["captured_at"] = captured
            entry["available_at"] = captured
    receipt = {
        "schema_version": 1,
        "capture_id": identifier,
        "team_id": team_id,
        "snapshot_id": state.snapshot_id,
        "data_sha256": fingerprint(data),
        "state_sha256": fingerprint(state.model_dump(mode="json")),
        "provider": "baseline",
        "horizon_events": horizon,
        "schedule_complete_events": events,
        "deadline": deadline,
        "policy_identifier": _policy_id(policy),
        "implementation_sha256": implementation,
        "captured_at": captured,
        "capture_started_at": capture_started,
        "source_receipts": source_receipts,
        "artifacts": artifacts,
        "capture_semantics": "provider receipts retain original capture times; code and generated mappings captured now",
    }
    receipt["available_at"] = captured
    raw = _json(receipt)
    (path / "capture.json").write_bytes(raw)
    digest = _digest(raw)
    reference = {"capture_id": identifier, "team_id": team_id, "capture_sha256": digest}
    store.put_checked(
        "replay_capture",
        identifier,
        reference,
        lambda: checked_capture(store, identifier, state, data, digest),
    )
    return {
        **reference,
        "horizon_events": horizon,
        "policy_identifier": receipt["policy_identifier"],
        "captured_at": captured,
        "available_at": captured,
    }


def checked_capture(
    store: Store,
    identifier: str,
    state: ManagerState,
    data: dict[str, Any],
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    path = _capture_path(identifier)
    target = path / "capture.json"
    if target.is_symlink():
        raise ValueError("Replay capture symlinks are not allowed")
    raw = target.read_bytes()
    if expected_sha256 is None:
        expected_sha256 = store.get("replay_capture", identifier)["capture_sha256"]
    if _digest(raw) != expected_sha256:
        raise ValueError("Replay capture receipt checksum mismatch")
    receipt: dict[str, Any] = json.loads(raw)
    if (
        receipt["capture_id"] != identifier
        or receipt["team_id"] != state.team_id
        or receipt["snapshot_id"] != state.snapshot_id
        or receipt["data_sha256"] != fingerprint(data)
        or receipt["state_sha256"] != fingerprint(state.model_dump(mode="json"))
        or receipt["implementation_sha256"] != implementation_sha256()
    ):
        raise Conflict("Replay capture state, sources or implementation changed")
    sources = _sources(store, data)
    expected_sources = [
        {
            key: source[key]
            for key in ("id", "resource", "payload_sha256", "captured_at", "available_at")
        }
        for source in sources
    ]
    if receipt["source_receipts"] != expected_sources:
        raise ValueError("Replay capture source receipts changed")
    for entry in receipt["artifacts"]:
        parsed = ReplayArtifact.model_validate(entry)
        file = path / parsed.filename
        if (
            Path(parsed.filename).name != parsed.filename
            or file.is_symlink()
            or _digest(file.read_bytes()) != parsed.sha256
        ):
            raise ValueError("Replay capture artifact checksum or path mismatch")
    return receipt


def produce_journal_replay_packet(
    store: Store, decision_id: str, capture_id: str, policy: Policy
) -> dict[str, Any]:
    """Assemble and seal a journal packet using prior evidence, never caller JSON."""
    journal = store.get("decision_journal", decision_id)
    state, run, players = _inputs(journal)
    data = store.get("dataset", state.snapshot_id)
    receipt = checked_capture(store, capture_id, state, data)
    if (
        run.resolved_provider != "baseline"
        or receipt["policy_identifier"] != _policy_id(policy)
        or receipt["horizon_events"] != run.horizon_events
        or run.prediction_origin is None
        or not replay_time(receipt["available_at"]) <= replay_time(run.prediction_origin)
        or receipt["deadline"] != journal["deadline"]
    ):
        raise ValueError("Replay capture must bind this policy/horizon before the forecast origin")
    canonical_players = [Player.model_validate(row) for row in data["players"]]
    if sorted(players, key=lambda row: row.player_id) != sorted(
        canonical_players, key=lambda row: row.player_id
    ):
        raise ValueError("Replay capture requires the complete captured player universe")
    expected = baseline_run(
        canonical_players,
        [Fixture.model_validate(row) for row in data["fixtures"]],
        state.snapshot_id,
        data["source_cutoff"],
        "live",
        state.next_event,
        run.horizon_events,
    )
    if run.projections != expected.projections or run.fixtures != expected.fixtures:
        raise ValueError("Frozen baseline forecast differs from captured provider inputs")
    identifier = (
        "journal-"
        + fingerprint(
            {"decision": decision_id, "capture": capture_id, "policy": _policy_id(policy)}
        )[:48]
    )
    manifest = ReplayManifest(
        deadline=journal["deadline"],
        information_available_at=journal["decision_origin"],
        forecast=run,
        players=players,
        schedule_complete_events=receipt["schedule_complete_events"],
        artifacts=[ReplayArtifact.model_validate(row) for row in receipt["artifacts"]],
        policy_identifier=_policy_id(policy),
        implementation_sha256=receipt["implementation_sha256"],
    )
    path = packet_path(identifier)
    raw = manifest.model_dump_json(indent=2).encode()
    digest = _digest(raw)
    if path.exists():
        if path.read_bytes() != raw:
            raise Conflict("Replay packet already binds different evidence")
    else:
        if not replay_time(utcnow()) < replay_time(journal["deadline"]):
            raise ValueError("New replay packets must be produced before the deadline")
        # Publish a complete directory atomically. Interrupted copies remain
        # separate staging directories and never prevent a clean retry.
        path.parent.parent.mkdir(parents=True, exist_ok=True)
        staging = path.parent.parent / (".staging-" + uuid.uuid4().hex)
        staging.mkdir()
        for entry in manifest.artifacts:
            with (staging / entry.filename).open("xb") as stream:
                stream.write((_capture_path(capture_id) / entry.filename).read_bytes())
        with (staging / path.name).open("xb") as stream:
            stream.write(raw)
        (staging / "producer_receipt.json").write_bytes(
            _json(
                {
                    "capture_id": capture_id,
                    "capture_sha256": store.get("replay_capture", capture_id)["capture_sha256"],
                    "packet_produced_at": utcnow(),
                    "manifest_sha256": digest,
                }
            )
        )
        verify_replay_manifest(
            staging / path.name,
            digest,
            run,
            players,
            journal["deadline"],
            journal["decision_origin"],
            receipt["schedule_complete_events"],
            policy,
        )
        try:
            staging.rename(path.parent)
        except FileExistsError:
            if not path.is_file() or path.read_bytes() != raw:
                raise Conflict("Replay packet already binds different evidence") from None
    verify_replay_manifest(
        path,
        digest,
        run,
        players,
        journal["deadline"],
        journal["decision_origin"],
        receipt["schedule_complete_events"],
        policy,
    )
    seal = seal_journal_replay(store, decision_id, identifier, digest, policy)
    return {
        "decision_id": decision_id,
        "packet_id": identifier,
        "manifest_sha256": digest,
        "seal_sha256": fingerprint(seal),
        "sealed_at": seal["sealed_at"],
        "evidence_mode": "prospective_strict",
        "execution_status": "execution_unknown",
    }
