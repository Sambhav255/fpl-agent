import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "collection_cli", ROOT / "scripts/collect_football.py"
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

from fpl_app.providers import Provider
from fpl_app.storage import Store


def fixture_store(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    store.put(
        "state",
        10,
        {
            "data_mode": "live",
            "picks": [{"player_id": 1}],
            "bank_units": "PRIVATE_SENTINEL",
        },
    )
    store.put("state", 11, {"data_mode": "demo", "picks": [{"player_id": 900}]})
    store.put("current", "live", {"snapshot_id": "KEEP_POINTER"})
    deadline = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    bootstrap = {
        "elements": [
            {
                "id": i,
                "team": 1,
                "element_type": 3,
                "web_name": "Public",
                "now_cost": 50,
                "points_per_game": "2",
                "minutes": 90,
                "goals_scored": 0,
                "assists": 0,
                "clean_sheets": 0,
                "status": "a",
            }
            for i in [1, 2]
        ],
        "teams": [{"id": 1}],
        "events": [
            {"id": 6, "deadline_time": deadline, "is_current": True},
            {"id": 7, "deadline_time": deadline, "is_next": True},
        ],
    }
    fixtures = [
        {
            "id": 1,
            "event": 6,
            "team_h": 1,
            "team_a": 2,
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
        }
    ]
    requests = []

    def respond(request):
        requests.append(request.url.path)
        value = (
            bootstrap
            if request.url.path.endswith("bootstrap-static/")
            else (
                fixtures
                if request.url.path.endswith("fixtures/")
                else {"history": [], "fixtures": [], "history_past": []}
            )
        )
        return httpx.Response(200, json=value)

    return store, Provider(store, httpx.MockTransport(respond)), requests


def test_capture_owned_union_summary_and_read_only_coverage(tmp_path, capsys):
    store, provider, requests = fixture_store(tmp_path)
    before = cli.guard_versions(store)
    assert (
        cli.main(
            ["--player-ids", "2", "2", "--include-owned"],
            store=store,
            provider=provider,
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["coverage"]["player_count"] == 2
    assert output["event_origin"]["current_event"] == 6
    assert output["event_origin"]["next_event"] == 7
    assert output["event_origin"]["before_deadline"] is True
    assert cli.guard_versions(store) == before
    assert len(requests) == 4
    assert cli.main(["--coverage", output["collection_id"]], store=store, provider=provider) == 0
    assert json.loads(capsys.readouterr().out) == output
    assert len(requests) == 4
    assert "PRIVATE_SENTINEL" not in json.dumps(output)
    assert "KEEP_POINTER" not in json.dumps(output)
    assert "player_ids" not in output
    assert (
        cli.main(
            ["--from-collection", output["collection_id"]],
            store=store,
            provider=provider,
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["coverage"]["player_count"] == 2
    assert len(requests) == 8  # Forced fresh capture, not cache reuse.


def test_full_bootstrap_universe_cli_freezes_membership_without_private_state(tmp_path, capsys):
    store, provider, requests = fixture_store(tmp_path)
    before = cli.guard_versions(store)
    assert cli.main(["--include-all"], store=store, provider=provider) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["coverage"]["player_count"] == 2
    assert output["player_universe"]["kind"] == "full_bootstrap_elements"
    assert output["player_universe"]["member_count"] == 2
    assert cli.guard_versions(store) == before
    assert len(requests) == 4
    with pytest.raises(SystemExit):
        cli.main(["--include-all", "--include-owned"], store=store, provider=provider)
    assert len(requests) == 4


@pytest.mark.parametrize("value", ["0", "-1", "true", "https://evil.test", "2147483648", "１"])
def test_invalid_ids_prevent_network(tmp_path, value):
    store, provider, requests = fixture_store(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--player-ids", value], store=store, provider=provider)
    assert not requests


def test_union_bounds_and_safe_errors(tmp_path, capsys):
    store, provider, requests = fixture_store(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--player-ids", *map(str, range(1, 1002))], store=store, provider=provider)
    assert not requests
    assert cli.main(["--from-collection", "missing"], store=store, provider=provider) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "PRIVATE_SENTINEL" not in captured.err
    assert not requests


def test_optional_export_and_bootstrap_only(tmp_path, capsys, monkeypatch):
    store, provider, requests = fixture_store(tmp_path)
    calls = []
    monkeypatch.setattr(
        cli,
        "export_collection_parquet",
        lambda store, identifier: calls.append(identifier),
    )
    assert cli.main(["--parquet"], store=store, provider=provider) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["coverage"]["player_count"] == 0
    assert len(requests) == 2
    assert calls == [output["collection_id"]]


def test_provider_error_does_not_leak_details(tmp_path, capsys, monkeypatch):
    store, provider, _ = fixture_store(tmp_path)
    before = cli.guard_versions(store)

    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE_SENTINEL")

    monkeypatch.setattr(cli, "collect_football", fail)
    assert cli.main([], store=store, provider=provider) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err) == {
        "error": "COLLECTION_FAILED",
        "error_type": "RuntimeError",
    }
    assert cli.guard_versions(store) == before


def test_combined_selection_bound_before_network(tmp_path, capsys, monkeypatch):
    store, provider, requests = fixture_store(tmp_path)
    monkeypatch.setattr(cli, "load_collection", lambda *args: {"player_ids": list(range(2, 1002))})
    assert (
        cli.main(
            ["--include-owned", "--from-collection", "example"],
            store=store,
            provider=provider,
        )
        == 1
    )
    assert not requests
    assert json.loads(capsys.readouterr().err)["error_type"] == "ValueError"


def test_concurrent_state_change_is_detected(tmp_path, capsys, monkeypatch):
    store, provider, _ = fixture_store(tmp_path)
    original = cli.collect_football

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        store.put("current", "live", {"snapshot_id": "CONCURRENT_EDIT"})
        return result

    monkeypatch.setattr(cli, "collect_football", changed)
    assert cli.main([], store=store, provider=provider) == 1
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err)["error_type"] == "RuntimeError"


def test_conflicting_read_only_arguments(tmp_path):
    store, provider, requests = fixture_store(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--coverage", "example", "--include-owned"], store=store, provider=provider)
    assert not requests
