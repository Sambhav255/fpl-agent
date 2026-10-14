"""Reconstruct strict replay labels from one explicitly selected official revision."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from fpl_app.contracts import ManagerState
from fpl_app.domain.rules import OfficialEventPoints
from fpl_app.evaluation.provenance import replay_time
from fpl_app.evaluation.strategy import Policy, ReplayOrigin
from fpl_app.learning.outcomes import SCORING_VERSION, build_finalized_outcomes
from fpl_app.learning.replay import journal_replay_inputs
from fpl_app.storage import Store, fingerprint


def _source(store: Store, identifier: str, digest: str, resource: str) -> dict[str, Any]:
    snapshot = store.snapshot(identifier)
    if (
        snapshot["resource"] != resource
        or snapshot["provider"] != "official_fpl"
        or snapshot["data_mode"] != "live"
        or snapshot["validation_status"] != "valid"
        or snapshot["payload_sha256"] != digest
        or sha256(snapshot["raw"]).hexdigest() != digest
        or replay_time(snapshot["available_at"]) < replay_time(snapshot["captured_at"])
    ):
        raise ValueError("Official replay source identity/checksum/timing mismatch")
    return snapshot


def official_replay_inputs(
    store: Store, decision_id: str, policy: Policy, outcome_revision_id: str
) -> tuple[ManagerState, ReplayOrigin]:
    """Load a sealed origin and independently reconcile immutable official labels.

    The full persisted key ``decision_id:revision_sha256`` is mandatory. No latest
    revision selection, network requests, policy outcome access or manager writes.
    Ambiguous zero-minute cards/points stay excluded until participation is reconciled.
    """
    state, origin = journal_replay_inputs(store, decision_id, policy, outcomes={})
    journal = store.get("decision_journal", decision_id)
    revision = store.get("learning_outcome", outcome_revision_id)
    if (
        revision["decision_id"] != decision_id
        or revision["event"] != journal["event"]
        or outcome_revision_id != f"{decision_id}:{revision['revision']}"
    ):
        raise ValueError("Official outcome revision identity mismatch")
    if revision["scoring_version"] != SCORING_VERSION:
        raise ValueError("Unsupported official scoring revision; collect a new checked v2 revision")
    final = revision["finalization_source"]
    status_source = _source(
        store, final["finalization_snapshot_id"], final["finalization_sha256"], "bootstrap-static/"
    )
    fixture_source = _source(
        store,
        revision["fixture_source_snapshot_id"],
        revision["fixture_source_sha256"],
        "fixtures/",
    )
    live_source = _source(
        store,
        revision["live_source_snapshot_id"],
        revision["live_source_sha256"],
        f"event/{journal['event']}/live/",
    )
    if (
        final["source_captured_at"] != status_source["captured_at"]
        or revision["captured_at"] != live_source["captured_at"]
        or not replay_time(journal["deadline"])
        <= replay_time(status_source["captured_at"])
        <= replay_time(fixture_source["captured_at"])
        <= replay_time(live_source["captured_at"])
    ):
        raise ValueError("Official finalization capture timing mismatch")
    events = json.loads(status_source["raw"])["events"]
    matching = [row for row in events if row.get("id") == journal["event"]]
    if (
        len(matching) != 1
        or matching[0].get("finished") is not True
        or matching[0].get("data_checked") is not True
    ):
        raise ValueError("Official event is not finalized and checked")
    rows, scores = build_finalized_outcomes(
        journal,
        {"event": journal["event"], "ready": True},
        json.loads(fixture_source["raw"]),
        json.loads(live_source["raw"]),
    )
    digest = fingerprint(
        {
            "decision_id": decision_id,
            "finalization_sha256": final["finalization_sha256"],
            "fixture_sha256": revision["fixture_source_sha256"],
            "live_sha256": revision["live_source_sha256"],
            "outcomes": rows,
            "scoring_version": SCORING_VERSION,
        }
    )
    if (
        digest != revision["revision"]
        or rows != revision["outcomes"]
        or scores != revision["scores"]
    ):
        raise ValueError(
            "Official outcome revision changed or does not reconcile to retained sources"
        )
    outcomes: dict[int, OfficialEventPoints] = {}
    for row in rows:
        if row["status"] not in {"final", "blank_event"}:
            raise ValueError("Official replay requires complete finalized frozen-universe coverage")
        minutes, points = row["minutes"], row["points"]
        if type(minutes) is not int or minutes < 0 or type(points) is not int:
            raise ValueError("Official replay requires known points and minutes")
        if minutes == 0:
            cards = [row[key] for key in ("yellow_cards", "red_cards")]
            if any(type(value) is not int or value < 0 for value in cards):
                raise ValueError("Missing official participation coverage")
            if any(cards) or points != 0:
                raise ValueError(
                    "Zero-minute cards/points require reconciled participation coverage"
                )
        outcomes[row["player_id"]] = OfficialEventPoints(points, minutes, minutes > 0)
    if set(outcomes) != set(journal["player_universe_ids"]):
        raise ValueError("Official replay requires exact frozen-universe coverage")
    origin.official_outcomes = outcomes
    origin.journal_reference = {
        **(origin.journal_reference or {}),
        "outcome_revision_id": outcome_revision_id,
        "outcome_revision_sha256": fingerprint(revision),
        "finalization_sha256": final["finalization_sha256"],
        "fixture_source_sha256": revision["fixture_source_sha256"],
        "live_source_sha256": revision["live_source_sha256"],
    }
    return state, origin
