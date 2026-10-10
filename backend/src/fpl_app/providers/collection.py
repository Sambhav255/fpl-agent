"""Bounded football-only captures; never reads manager state or switches live data."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fpl_app.providers import Provider
from fpl_app.storage import Store, fingerprint

MAX_PLAYERS = 100


def _instant(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Source timestamps must include timezone")
    return result.astimezone(UTC)


def _reference(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot["validation_status"] != "valid" or snapshot["provider"] != "official_fpl":
        raise ValueError("Collection requires validated official football snapshots")
    if hashlib.sha256(snapshot["raw"]).hexdigest() != snapshot["payload_sha256"]:
        raise ValueError("Source checksum mismatch")
    _instant(snapshot["captured_at"])
    _instant(snapshot["available_at"])
    return {
        key: snapshot[key]
        for key in (
            "id",
            "provider",
            "resource",
            "season",
            "captured_at",
            "available_at",
            "source_published_at",
            "payload_sha256",
            "storage_path",
            "validation_status",
        )
    }


def collect_football(
    store: Store,
    provider: Provider | None = None,
    player_ids: list[int] | None = None,
    force: bool = True,
) -> dict[str, Any]:
    """Capture bootstrap, fixtures and at most 100 explicitly selected element summaries."""
    ids = [] if player_ids is None else player_ids
    if not isinstance(ids, list) or any(
        type(identifier) is not int or not 1 <= identifier <= 2_147_483_647 for identifier in ids
    ):
        raise ValueError("player_ids must be explicit positive integer IDs")
    ids = sorted(set(ids))
    if len(ids) > MAX_PLAYERS:
        raise ValueError("Collection is bounded to 100 distinct players")
    provider = provider or Provider(store)
    bootstrap = provider.fetch("bootstrap-static/", force=force)
    fixture_snapshot = provider.fetch("fixtures/", force=force)
    sources = [_reference(bootstrap), _reference(fixture_snapshot)]
    b = json.loads(bootstrap["raw"])
    fixtures = json.loads(fixture_snapshot["raw"])
    season = bootstrap["season"]
    elements = {p["id"]: p for p in b["elements"]}
    if any(identifier not in elements for identifier in ids):
        raise ValueError("Requested player absent from bootstrap universe")
    events = {e["id"]: e for e in b["events"]}
    fixture_by_id = {f["id"]: f for f in fixtures}
    histories: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    for identifier in ids:
        snapshot = provider.fetch(f"element-summary/{identifier}/", force=force)
        sources.append(_reference(snapshot))
        histories[identifier] = (snapshot, json.loads(snapshot["raw"]))
    if any(s["season"] != season for s in sources):
        raise ValueError("Mixed source seasons")
    captured_at = datetime.now(UTC).isoformat()
    if any(_instant(s["captured_at"]) > _instant(captured_at) for s in sources):
        raise ValueError("Source capture is in the future")
    available_at = max((s["available_at"] for s in sources), key=_instant)
    event_evidence = []
    for event in events.values():
        deadline = event["deadline_time"]
        before = _instant(captured_at) < _instant(deadline) and all(
            max(_instant(s["captured_at"]), _instant(s["available_at"])) < _instant(deadline)
            for s in sources
        )
        event_evidence.append(
            {
                "event": event["id"],
                "actual_deadline": deadline,
                "before_deadline": before,
                "evidence_mode": "prospective_capture" if before else "retrospective_capture",
            }
        )
    labels: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for identifier, (snapshot, history) in histories.items():
        seen: set[int] = set()
        for row in history["history"]:
            fixture_id = row["fixture"]
            if fixture_id in seen:
                raise ValueError("Duplicate player fixture history")
            seen.add(fixture_id)
            fixture = fixture_by_id.get(fixture_id)
            event = events.get(row["round"], {})
            final = (
                fixture is not None
                and fixture.get("finished_provisional") is True
                and (event.get("data_checked") is True)
            )
            normalized = {
                "provider": "official_fpl",
                "season": season,
                "provider_player_id": identifier,
                "canonical_player_id": f"official_fpl:{season}:element:{identifier}",
                "canonical_id_scope": "season_local_unverified_cross_season",
                "fixture_id": fixture_id,
                "event": row["round"],
                "minutes": row.get("minutes"),
                "total_points": row.get("total_points"),
                "statistics": {k: v for k, v in row.items() if k not in ("fixture", "round")},
                "label_status": "final_revision" if final else "preliminary",
                "original_timing": "unknown_original_timing",
                "source_published_at": None,
                "available_at": snapshot["available_at"],
                "snapshot_id": snapshot["id"],
                "revision_sha256": fingerprint(row),
                "actual_deadline": event.get("deadline_time"),
                "strict_historical_replay_eligible": False,
            }
            labels.append(normalized)
        club = elements[identifier]["team"]
        for event_id in events:
            scheduled = [
                f
                for f in fixtures
                if f.get("event") == event_id and (f["team_h"] == club or f["team_a"] == club)
            ]
            coverage.append(
                {
                    "provider_player_id": identifier,
                    "event": event_id,
                    "schedule_basis": "captured_current_club_not_historical_membership",
                    "scheduled_fixture_ids": [f["id"] for f in scheduled],
                    "missing_history_fixture_ids": [
                        f["id"] for f in scheduled if f["id"] not in seen
                    ],
                    "status": "blank_event"
                    if not scheduled
                    else "rows_present"
                    if all(f["id"] in seen for f in scheduled)
                    else "missing_rows",
                }
            )
            for f in scheduled:
                exposures.append(
                    {
                        "provider": "official_fpl",
                        "season": season,
                        "provider_player_id": identifier,
                        "canonical_player_id": f"official_fpl:{season}:element:{identifier}",
                        "provider_club_id": club,
                        "canonical_club_id": f"official_fpl:{season}:team:{club}",
                        "fixture_id": f["id"],
                        "event": event_id,
                        "kickoff": f.get("kickoff_time"),
                        "is_home": f["team_h"] == club,
                        "opponent_provider_club_id": f["team_a"]
                        if f["team_h"] == club
                        else f["team_h"],
                        "snapshot_id": fixture_snapshot["id"],
                        "available_at": fixture_snapshot["available_at"],
                        "schedule_basis": "captured_current_club_not_historical_membership",
                    }
                )
    next_event = next((e for e in event_evidence if events[e["event"]].get("is_next")), None)
    result = {
        "schema_version": 1,
        "collection_id": uuid.uuid4().hex,
        "provider": "official_fpl",
        "season": season,
        "data_mode": "live",
        "captured_at": captured_at,
        "available_at": available_at,
        "actual_deadline": next_event["actual_deadline"] if next_event else None,
        "before_deadline": next_event["before_deadline"] if next_event else None,
        "evidence_mode": next_event["evidence_mode"] if next_event else "no_next_deadline",
        "player_ids": ids,
        "player_mappings": [
            {
                "provider": "official_fpl",
                "season": season,
                "provider_player_id": i,
                "canonical_player_id": f"official_fpl:{season}:element:{i}",
                "provider_club_id": elements[i]["team"],
                "canonical_club_id": f"official_fpl:{season}:team:{elements[i]['team']}",
                "position": elements[i]["element_type"],
                "mapping_status": "season_local_unverified_cross_season",
                "bootstrap_snapshot_id": bootstrap["id"],
            }
            for i in ids
        ],
        "fixture_versions": fixtures,
        "sources": sources,
        "event_evidence": event_evidence,
        "labels": labels,
        "schedule_exposures": exposures,
        "coverage": coverage,
        "limitations": [
            "Historical labels have unknown original publication timing; captures cannot backdate availability.",
            "Canonical IDs are season-local; cross-season identity is not verified.",
            "Schedule exposures use current club; historical eligibility and absent players remain unknown.",
            "Missing history rows and statistics are not zero outcomes.",
        ],
    }
    result["envelope_sha256"] = fingerprint(result)
    store.put("football_collection", result["collection_id"], result, expected=0)
    return result


def load_collection(store: Store, collection_id: str) -> dict[str, Any]:
    """Read and verify an immutable collection without changing any pointer."""
    result = store.get("football_collection", collection_id)
    content = {k: v for k, v in result.items() if k != "envelope_sha256"}
    if result["envelope_sha256"] != fingerprint(content):
        raise ValueError("Collection checksum mismatch")
    for source in result["sources"]:
        if _reference(store.snapshot(source["id"])) != source:
            raise ValueError("Collection source reference mismatch")
    return result


def collection_coverage(store: Store, collection_id: str) -> dict[str, Any]:
    result = load_collection(store, collection_id)
    return {
        k: result[k]
        for k in (
            "collection_id",
            "player_ids",
            "coverage",
            "event_evidence",
            "limitations",
        )
    }


def export_collection_parquet(store: Store, collection_id: str) -> dict[str, Any]:
    """Optional, immutable export under the repository's ignored data/collections."""
    import pandas as pd

    result = load_collection(store, collection_id)
    directory = (
        Path(__file__).resolve().parents[4] / "data" / "collections" / result["collection_id"]
    )
    directory.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for table in ("labels", "schedule_exposures", "coverage"):
        path = directory / f"{table}.parquet"
        if not path.exists():
            frame = pd.DataFrame(result[table])
            # Nested statistics remain explicit JSON, including nulls.
            if "statistics" in frame:
                frame["statistics"] = frame["statistics"].map(json.dumps)
            with path.open("xb") as stream:
                frame.to_parquet(stream, index=False)
        artifacts.append(
            {
                "table": table,
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {"collection_id": collection_id, "artifacts": artifacts}
