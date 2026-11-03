import copy
import hashlib
import json

import pytest

from fpl_app.learning.refit_cache import cached_refit, refit_identity
from fpl_app.storage import Store


def test_refit_identity_ignores_capture_receipts_but_tracks_final_label_revisions():
    collection = {
        "season": "2026/27",
        "labels": [
            {
                "provider_player_id": 1,
                "fixture_id": 1,
                "label_status": "final_revision",
                "revision_sha256": "original",
                "snapshot_id": "old",
                "available_at": "old",
            },
            {
                "provider_player_id": 1,
                "fixture_id": 2,
                "label_status": "preliminary",
                "revision_sha256": "p",
            },
        ],
    }
    first = refit_identity(collection, "code")
    refreshed = copy.deepcopy(collection)
    refreshed["labels"][0].update(snapshot_id="new", available_at="new")
    refreshed["labels"][1]["revision_sha256"] = "changed-preliminary"
    assert refit_identity(refreshed, "code") == first
    refreshed["labels"][0]["revision_sha256"] = "corrected"
    assert refit_identity(refreshed, "code") != first
    assert refit_identity(collection, "new-code") != first


def test_cached_refit_rejects_mutated_artifact(tmp_path):
    store = Store("sqlite:///:memory:")
    model = tmp_path / "mean.cbm"
    model.write_bytes(b"original")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"files": {"mean.cbm": hashlib.sha256(model.read_bytes()).hexdigest()}})
    )
    row = {
        "artifact_directory": str(tmp_path),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    assert cached_refit(store, "new") is None
    store.put("learning_refit", "id", row)
    assert cached_refit(store, "id")["reused_unchanged_inputs"]
    model.write_bytes(b"changed")
    with pytest.raises(ValueError, match="artifact changed"):
        cached_refit(store, "id")
