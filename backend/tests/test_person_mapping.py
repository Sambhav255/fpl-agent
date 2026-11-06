import hashlib
import json

import pandas as pd
import pytest

from fpl_app.features.person_mapping import link_archive_people


def bundle(root, season, rows):
    path = root / season
    (path / "raw").mkdir(parents=True)
    pd.DataFrame(rows).to_csv(path / "raw/players_raw.csv", index=False)
    (path / "player_identity.json").write_text(
        json.dumps(
            [
                {"provider_player_id": r["id"], "canonical_player_id": f"fpl:{season}:{r['id']}"}
                for r in rows
            ]
        )
    )
    hashes = {
        name: hashlib.sha256((path / name).read_bytes()).hexdigest()
        for name in ["raw/players_raw.csv", "player_identity.json"]
    }
    (path / "manifest.json").write_text(json.dumps({"season": season, "artifact_sha256": hashes}))
    return path


def player(identifier, code, first="José", last="Example"):
    return {"id": identifier, "code": code, "first_name": first, "second_name": last}


def test_links_provider_code_with_supporting_name_but_never_names_alone(tmp_path):
    a = bundle(tmp_path, "2022-23", [player(1, 100), player(2, 200)])
    b = bundle(tmp_path, "2023-24", [player(42, 100, first="Jose"), player(43, 300)])
    result = link_archive_people([a, b])
    assert len(result["links"]) == 1
    assert result["links"][0]["person_id"] == "fpl-provider-code:100"
    assert len(result["unresolved"]) == 2
    assert result["production_qualified"] is False
    assert (
        json.loads((a / "player_identity.json").read_text())[0]["canonical_player_id"]
        == "fpl:2022-23:1"
    )


def test_duplicate_codes_name_conflicts_and_tampering_fail_safely(tmp_path):
    a = bundle(tmp_path, "2022-23", [player(1, 100), player(2, 100), player(3, 200)])
    b = bundle(tmp_path, "2023-24", [player(42, 100), player(43, 200, last="Different")])
    result = link_archive_people([a, b])
    assert not result["links"]
    assert {r["reason"] for r in result["unresolved"]} == {
        "duplicate_provider_code_within_season",
        "supporting_name_conflict",
    }
    with pytest.raises(ValueError, match="canonical bundle"):
        link_archive_people([a, a])
    (a / "raw/players_raw.csv").write_text("changed")
    with pytest.raises(ValueError, match="checksum"):
        link_archive_people([a, b])
