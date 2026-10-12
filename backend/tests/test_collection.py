import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from fpl_app.providers import Provider
from fpl_app.providers.collection import collect_football, collection_coverage, load_collection
from fpl_app.storage import Store


def setup_collection(tmp_path, *, before=True, final=False, unstarted=False):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    deadline = (datetime.now(UTC) + timedelta(days=1 if before else -1)).isoformat()
    bootstrap = {
        "elements": [
            {
                "id": i,
                "team": 1,
                "element_type": 3,
                "web_name": f"P{i}",
                "now_cost": 50,
                "points_per_game": "2",
                "minutes": 90,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "status": "a",
            }
            for i in (1, 2)
        ],
        "teams": [{"id": 1}],
        "events": [
            {"id": 1, "deadline_time": deadline, "data_checked": final},
            {"id": 2, "deadline_time": deadline, "is_next": True},
            {"id": 3, "deadline_time": deadline},
        ],
    }
    fixtures = [
        {
            "id": i,
            "event": 1 if i < 3 else 2,
            "team_h": 1,
            "team_a": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
            "finished_provisional": final,
            "started": not unstarted,
        }
        for i in (1, 2, 3)
    ]
    history = {
        "history": [
            {
                "fixture": 1,
                "round": 1,
                "minutes": 0,
                "total_points": 0,
                "defensive_contribution": None,
            }
        ],
        "fixtures": [],
        "history_past": [],
    }
    requests = []

    def respond(request):
        requests.append(request.url.path)
        return httpx.Response(
            200,
            json=bootstrap
            if request.url.path.endswith("bootstrap-static/")
            else fixtures
            if request.url.path.endswith("/fixtures/")
            else history,
        )

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    return store, provider, history, requests


def test_unstarted_provider_placeholder_is_not_an_observed_zero(tmp_path):
    store, provider, _, _ = setup_collection(tmp_path, unstarted=True)
    result = collect_football(store, provider, [1])
    row = result["labels"][0]
    assert row["label_status"] == "pending_fixture"
    assert row["minutes"] is None and row["total_points"] is None
    assert row["statistics"]["minutes"] == 0  # Original provider bytes remain inspectable.
    assert result["coverage"][0]["pending_history_fixture_ids"] == [1]
    assert result["coverage"][0]["status"] == "pending_fixture_rows"
    assert load_collection(store, result["collection_id"]) == result


@pytest.mark.parametrize("before", [True, False])
def test_deadline_missing_double_blank_and_no_silent_zeros(tmp_path, before):
    store, provider, _, requests = setup_collection(tmp_path, before=before)
    result = collect_football(store, provider, [1])
    assert result["before_deadline"] is before
    assert result["evidence_mode"] == ("prospective_capture" if before else "retrospective_capture")
    assert result["labels"][0]["minutes"] == 0
    assert result["labels"][0]["statistics"]["defensive_contribution"] is None
    assert result["labels"][0]["original_timing"] == "unknown_original_timing"
    assert result["labels"][0]["strict_historical_replay_eligible"] is False
    assert len(result["labels"]) == 1
    assert result["coverage"][0]["missing_history_fixture_ids"] == [2]
    assert result["coverage"][0]["scheduled_fixture_ids"] == [1, 2]
    assert result["coverage"][2]["status"] == "blank_event"
    assert len(result["schedule_exposures"]) == 3
    assert collection_coverage(store, result["collection_id"])["coverage"] == result["coverage"]
    assert load_collection(store, result["collection_id"]) == result
    assert len(requests) == 3


def test_revised_labels_preserve_old_sources_and_current_manager(tmp_path):
    store, provider, history, _ = setup_collection(tmp_path, final=True)
    store.put("current", "live", {"snapshot_id": "sentinel"})
    store.put("state", 12, {"private_sentinel": "unchanged"})
    first = collect_football(store, provider, [1])
    history["history"][0]["total_points"] = 2
    second = collect_football(store, provider, [1])
    assert first["labels"][0]["label_status"] == "final_revision"
    assert first["labels"][0]["revision_sha256"] != second["labels"][0]["revision_sha256"]
    assert first["collection_id"] != second["collection_id"]
    assert load_collection(store, first["collection_id"])["labels"][0]["total_points"] == 0
    assert store.get("current", "live") == {"snapshot_id": "sentinel"}
    assert store.get("state", 12) == {"private_sentinel": "unchanged"}
    assert (
        store.snapshot(first["sources"][2]["id"])["raw"]
        != store.snapshot(second["sources"][2]["id"])["raw"]
    )


@pytest.mark.parametrize("ids", [[True], [0], [-1], ["https://evil.test"], list(range(1, 102))])
def test_bounded_validated_ids_before_network(tmp_path, ids):
    store, provider, _, requests = setup_collection(tmp_path)
    with pytest.raises(ValueError):
        collect_football(store, provider, ids)
    assert requests == []


def test_bootstrap_only_and_cached_source_timing(tmp_path):
    store, provider, _, requests = setup_collection(tmp_path)
    first = collect_football(store, provider)
    second = collect_football(store, provider, force=False)
    assert len(requests) == 2
    assert second["sources"] == first["sources"]
    assert second["labels"] == []
    assert second["player_ids"] == []


def test_unknown_player_duplicate_and_schema_failure_preserve_collections(tmp_path):
    store, provider, history, _ = setup_collection(tmp_path)
    with pytest.raises(ValueError, match="absent"):
        collect_football(store, provider, [3])
    good = collect_football(store, provider, [1])
    history["history"].append(history["history"][0].copy())
    with pytest.raises(ValueError, match="Duplicate"):
        collect_football(store, provider, [1])
    assert len(store.list("football_collection")) == 1
    assert load_collection(store, good["collection_id"]) == good
    history["history"] = [{"fixture": 1}]
    with pytest.raises(ValueError, match="schema invalid"):
        collect_football(store, provider, [1])
    assert load_collection(store, good["collection_id"]) == good


def test_read_helper_detects_envelope_tampering(tmp_path):
    store, provider, _, _ = setup_collection(tmp_path)
    result = collect_football(store, provider, [1])
    result["labels"][0]["total_points"] = 900
    store.put("football_collection", result["collection_id"], result)
    with pytest.raises(ValueError, match="checksum"):
        load_collection(store, result["collection_id"])


def test_no_backdated_cache_availability(tmp_path):
    store, provider, _, _ = setup_collection(tmp_path)
    good = collect_football(store, provider, [1])
    assert all(source["source_published_at"] is None for source in good["sources"])
    assert all(
        label["available_at"] == good["sources"][2]["available_at"] for label in good["labels"]
    )
    assert json.dumps(good)


def test_parquet_export_is_optional_and_repeatable(tmp_path, monkeypatch):
    import pandas as pd

    import fpl_app.providers.collection as module

    store, provider, _, _ = setup_collection(tmp_path)
    result = collect_football(store, provider, [1])
    monkeypatch.setattr(module, "__file__", str(tmp_path / "a/b/c/d/collection.py"))
    assert not (tmp_path / "data/collections").exists()
    first = module.export_collection_parquet(store, result["collection_id"])
    second = module.export_collection_parquet(store, result["collection_id"])
    assert first == second
    frame = pd.read_parquet(first["artifacts"][0]["path"])
    assert frame.iloc[0]["minutes"] == 0
    assert json.loads(frame.iloc[0]["statistics"])["defensive_contribution"] is None
    assert load_collection(store, result["collection_id"]) == result


def test_empty_collection_export(tmp_path, monkeypatch):
    import fpl_app.providers.collection as module

    store, provider, _, _ = setup_collection(tmp_path)
    result = collect_football(store, provider)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "a/b/c/d/collection.py"))
    assert len(module.export_collection_parquet(store, result["collection_id"])["artifacts"]) == 3
