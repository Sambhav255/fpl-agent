"""Source-bound cross-season research links; never infer identity from a name alone."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


def _name(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if c.isalnum())


def link_archive_people(bundles: list[Path]) -> dict[str, Any]:
    """Link a unique provider code only with agreeing supporting full names.

    Code/name conflicts and duplicate codes within a season remain unresolved.
    This is an auditable research mapping, not historical availability evidence.
    Original normalized bundles are never rewritten.
    """
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unresolved = []
    sources = []
    seasons = set()
    for bundle in bundles:
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        season = manifest["season"]
        if season in seasons:
            raise ValueError("One canonical bundle per season required")
        seasons.add(season)
        for name, digest in manifest["artifact_sha256"].items():
            path = bundle / name
            if not path.resolve().is_relative_to(bundle.resolve()):
                raise ValueError("Artifact outside bundle")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Archive checksum mismatch")
        required = {"raw/players_raw.csv", "player_identity.json"}
        if not required <= manifest["artifact_sha256"].keys():
            raise ValueError("Hashed player metadata and identities required")
        metadata = pd.read_csv(bundle / "raw/players_raw.csv").set_index("id")
        if metadata.index.duplicated().any():
            raise ValueError("Duplicate source player IDs")
        identities = json.loads((bundle / "player_identity.json").read_text())
        sources.append(
            {
                "season": season,
                "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            }
        )
        for row in identities:
            identifier = row["provider_player_id"]
            record = {"season": season, "player_identity": row["canonical_player_id"]}
            if identifier not in metadata.index or pd.isna(metadata.loc[identifier].get("code")):
                unresolved.append(record | {"reason": "missing_provider_metadata"})
                continue
            person = metadata.loc[identifier]
            first, last = person.get("first_name"), person.get("second_name")
            if not isinstance(first, str) or not isinstance(last, str) or not _name(first + last):
                unresolved.append(record | {"reason": "missing_supporting_name"})
                continue
            code = int(person["code"])
            groups[code].append(
                record | {"provider_code": code, "name_key": _name(first + " " + last)}
            )
    links = []
    for code, records in sorted(groups.items()):
        if len({r["season"] for r in records}) != len(records):
            reason = "duplicate_provider_code_within_season"
        elif len({r["name_key"] for r in records}) != 1:
            reason = "supporting_name_conflict"
        elif len(records) < 2:
            reason = "single_season_only"
        else:
            links.append(
                {
                    "person_id": f"fpl-provider-code:{code}",
                    "members": records,
                    "evidence": "unique_provider_code_and_normalized_full_name_agree",
                    "qualification": "research_source_link_not_independent_person_attestation",
                }
            )
            continue
        unresolved.extend(r | {"reason": reason} for r in records)
    return {
        "version": "archive-person-links-v1",
        "sources": sources,
        "links": links,
        "unresolved": unresolved,
        "strict_historical_availability": False,
        "production_qualified": False,
    }
