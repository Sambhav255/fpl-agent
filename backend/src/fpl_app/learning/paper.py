"""Immutable one-event paper comparisons using exact finalized official revisions."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from typing import Any

from fpl_app.contracts import Settings
from fpl_app.evaluation.strategy import Policy, replay_policy
from fpl_app.learning.official_replay import official_replay_inputs
from fpl_app.models.training import data_dir
from fpl_app.storage import Conflict, Store, fingerprint, utcnow


def evaluate_paper_journal(
    store: Store,
    decision_id: str,
    outcome_revision: str,
    policies: Mapping[str, Policy],
) -> dict[str, Any]:
    """Persist a local report only after every selected policy passes strict replay.

    Manager, journal and finalized revision fingerprints fence concurrent changes.
    No label fetching, fitting, manager edits or execution records are performed.
    """
    if not policies:
        raise ValueError("At least one paper policy required")
    revision = outcome_revision
    if ":" not in revision:
        revision = f"{decision_id}:{revision}"
    if not re.fullmatch(re.escape(decision_id) + r":[0-9a-f]{64}", revision):
        raise ValueError("Exact decision-bound outcome revision SHA256 required")
    journal = store.get("decision_journal", decision_id)
    settings = Settings.model_validate(journal["settings"])
    outcome = store.get("learning_outcome", revision)
    state = store.get("state", journal["team_id"])
    before = fingerprint({"journal": journal, "outcome": outcome, "state": state})
    reports = {}
    for name, policy in policies.items():
        initial, origin = official_replay_inputs(store, decision_id, policy, revision)
        reports[name] = replay_policy(initial, [origin], policy, settings)
    after = fingerprint(
        {
            "journal": store.get("decision_journal", decision_id),
            "outcome": store.get("learning_outcome", revision),
            "state": store.get("state", journal["team_id"]),
        }
    )
    if before != after:
        raise Conflict("Paper evaluation state, journal or outcome revision changed")
    report = {
        "schema_version": 1,
        "decision_id": decision_id,
        "outcome_revision_id": revision,
        "created_at": utcnow(),
        "evidence_mode": "prospective_strict",
        "execution_claim": "hypothetical policy actions; actual execution remains a separate journal record",
        "distinct_actual_season_paths": 1,
        "covered_events": 1,
        "uncertainty": "one event cannot establish independent season evidence or promotion",
        "reports": reports,
    }
    path = data_dir() / "replay_reports" / ("paper-" + uuid.uuid4().hex + ".json")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Replay report symlinks are not allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode()
    staging = path.with_suffix(".tmp")
    with staging.open("xb") as stream:
        stream.write(raw)
    staging.rename(path)
    return {
        "report_path": str(path),
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_mode": report["evidence_mode"],
        "covered_events": 1,
        "policies": list(reports),
        "execution_status": "unchanged",
    }
