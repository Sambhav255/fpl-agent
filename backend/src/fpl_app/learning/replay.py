"""Connect pre-deadline journal seals to strict replay, without retroactive capture."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fpl_app.contracts import ManagerState, Player, ProjectionRun
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.provenance import replay_time, verify_replay_manifest
from fpl_app.evaluation.strategy import Policy, ReplayOrigin
from fpl_app.models.training import data_dir
from fpl_app.storage import Conflict, Store, fingerprint, utcnow


def packet_path(packet_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", packet_id):
        raise ValueError("Invalid replay packet ID")
    path = data_dir() / "replay_inputs" / packet_id / "manifest.json"
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Replay packet symlinks are not allowed")
    return path


def _seal_id(decision_id: str, policy: Policy) -> str:
    return f"{decision_id}:{fingerprint(_policy_id(policy))[:24]}"


def _policy_id(policy: Policy) -> str:
    return f"{policy.__module__}.{policy.__qualname__}"


def _inputs(journal: dict[str, Any]) -> tuple[ManagerState, ProjectionRun, list[Player]]:
    state = ManagerState.model_validate(journal["manager_state"])
    run = ProjectionRun.model_validate(journal["forecast"])
    players = [Player.model_validate(player) for player in journal["players"]]
    if (
        journal["data_mode"] != "live"
        or state.data_mode != "live"
        or run.data_mode != "live"
        or state.team_id != journal["team_id"]
        or state.next_event != journal["event"]
        or state.state_version != journal["state_version"]
        or state.snapshot_id != run.snapshot_id
        or run.snapshot_id != journal["snapshot_id"]
        or run.projection_run_id != journal["forecast_reference"]
        or fingerprint(run.model_dump(mode="json")) != journal["forecast_sha256"]
        or sorted(player.player_id for player in players) != sorted(journal["player_universe_ids"])
    ):
        raise ValueError("Journal forecast, state or universe binding mismatch")
    return state, run, players


def _verify_packet(journal: dict[str, Any], packet_id: str, digest: str, policy: Policy) -> None:
    state, run, players = _inputs(journal)
    verify_replay_manifest(
        packet_path(packet_id),
        digest,
        run,
        players,
        journal["deadline"],
        journal["decision_origin"],
        list(range(state.next_event, min(39, state.next_event + run.horizon_events))),
        policy,
    )


def seal_journal_replay(
    store: Store, decision_id: str, packet_id: str, manifest_sha256: str, policy: Policy
) -> dict[str, Any]:
    """Seal an already captured evidence packet before the actual deadline.

    No caller-supplied seal time is accepted. An old unsealed decision cannot gain
    prospective status after its deadline. Policies may seal separate comparisons.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256):
        raise ValueError("Valid frozen manifest SHA256 required")
    journal = store.get("decision_journal", decision_id)
    identifier = _seal_id(decision_id, policy)
    binding = {
        "schema_version": 1,
        "decision_id": decision_id,
        "decision_sha256": fingerprint(journal),
        "packet_id": packet_id,
        "manifest_sha256": manifest_sha256,
        "policy_identifier": _policy_id(policy),
    }
    try:
        existing = store.get("decision_replay_seal", identifier)
    except KeyError:
        existing = None
    if existing is not None:
        if any(existing[key] != value for key, value in binding.items()):
            raise Conflict("Replay seal already binds different evidence")
        _verify_packet(journal, packet_id, manifest_sha256, policy)
        return existing
    record: dict[str, Any] = {**binding, "sealed_at": utcnow()}

    def verify() -> None:
        if store.get("decision_journal", decision_id) != journal:
            raise Conflict("Journal changed before replay seal")
        if not (
            replay_time(journal["decision_origin"])
            <= replay_time(record["sealed_at"])
            <= replay_time(utcnow())
            < replay_time(journal["deadline"])
        ):
            raise ValueError("Replay seal must be recorded before the deadline")
        _verify_packet(journal, packet_id, manifest_sha256, policy)

    store.put_checked("decision_replay_seal", identifier, record, verify, same=lambda a, b: a == b)
    return store.get("decision_replay_seal", identifier)


def journal_replay_inputs(
    store: Store, decision_id: str, policy: Policy, outcomes: dict[int, list[MatchStats]]
) -> tuple[ManagerState, ReplayOrigin]:
    """Use the persisted seal's checksum, never a new digest of today's packet.

    Caller supplies finalized outcome components. Outcomes stay outside the policy
    input. This is a paper-policy benchmark, not proof of actual manager execution.
    """
    journal = store.get("decision_journal", decision_id)
    seal = store.get("decision_replay_seal", _seal_id(decision_id, policy))
    if (
        seal["decision_id"] != decision_id
        or seal["decision_sha256"] != fingerprint(journal)
        or seal["policy_identifier"] != _policy_id(policy)
        or not replay_time(journal["decision_origin"])
        <= replay_time(seal["sealed_at"])
        < replay_time(journal["deadline"])
    ):
        raise ValueError("Journal replay seal binding or timing mismatch")
    _verify_packet(journal, seal["packet_id"], seal["manifest_sha256"], policy)
    state, run, players = _inputs(journal)
    return state, ReplayOrigin(
        deadline=journal["deadline"],
        information_available_at=journal["decision_origin"],
        players=players,
        forecasts=run,
        outcomes=outcomes,
        evidence_mode="prospective_strict",
        financial_coverage="journal_known_prices_only",
        manifest_path=packet_path(seal["packet_id"]),
        manifest_sha256=seal["manifest_sha256"],
        journal_reference={
            "decision_id": decision_id,
            "decision_sha256": seal["decision_sha256"],
            "seal_sha256": fingerprint(seal),
        },
    )
