import hashlib

import httpx
import pytest

from fpl_app.providers import Provider, demo, team_id
from fpl_app.storage import Store


def payloads(store):
    state = demo(store)
    data = store.get("dataset", state.snapshot_id)
    bootstrap = {
        "elements": [
            {
                "id": p["player_id"],
                "web_name": p["name"],
                "team": p["club"],
                "element_type": p["position"],
                "now_cost": p["market_price_units"],
                "points_per_game": "3.1",
                "minutes": 500,
                "goals_scored": 1,
                "assists": 2,
                "clean_sheets": 1,
                "status": "a",
            }
            for p in data["players"]
        ],
        "teams": [{"id": 1}],
        "events": [{"id": 8, "is_next": True, "deadline_time": "2026-10-10T10:00:00Z"}],
    }
    fixtures = [
        {
            "id": f["fixture_id"],
            "event": f["event"],
            "team_h": f["home_club"],
            "team_a": f["away_club"],
            "team_h_difficulty": 3,
            "team_a_difficulty": 3,
        }
        for f in data["fixtures"]
    ]
    picks = {
        "picks": [
            {
                "element": p.player_id,
                "position": p.position,
                "is_captain": p.is_captain,
                "is_vice_captain": p.is_vice_captain,
                "multiplier": 0,
            }
            for p in state.picks
        ]
    }
    return bootstrap, fixtures, picks


def test_public_import_unknown_and_immutable(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    bootstrap, fixtures, picks = payloads(store)
    requests = []

    def respond(request):
        requests.append(str(request.url))
        value = (
            bootstrap
            if request.url.path.endswith("bootstrap-static/")
            else picks
            if request.url.path.endswith("picks/")
            else fixtures
        )
        return httpx.Response(200, json=value)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    state = provider.import_team("https://fantasy.premierleague.com/entry/123/event/7/")
    assert state.team_id == 123 and state.public_source_event == 7
    assert (
        state.bank_units
        is state.confirmed_hit_points
        is state.free_transfers_at_event_start
        is None
    )
    assert all(p.purchase_price_units is p.selling_price_units is None for p in state.picks)
    assert all(v is None for v in state.chips.values())
    old = store.get("dataset", state.snapshot_id)
    raw = store.snapshot(old["bootstrap_snapshot_id"])
    assert hashlib.sha256(raw["raw"]).hexdigest() == raw["payload_sha256"]
    fixtures[0]["event"] = 9
    provider.fetch("fixtures/", force=True)
    new = provider.refresh()
    assert new["snapshot_id"] != state.snapshot_id
    assert store.get("dataset", state.snapshot_id) == old
    assert all(url.startswith("https://fantasy.premierleague.com/api/") for url in requests)


def test_bad_schema_preserves_cache(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    bootstrap, _, _ = payloads(store)
    valid = True

    def respond(request):
        return httpx.Response(200, json=bootstrap if valid else {"elements": []})

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    good = provider.fetch("bootstrap-static/")
    valid = False
    with pytest.raises(ValueError, match="prior valid"):
        provider.fetch("bootstrap-static/", force=True)
    assert store.latest("bootstrap-static/")["id"] == good["id"]
    assert store.snapshot(good["id"])["raw"] == good["raw"]


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.com/1",
        "https://fantasy.premierleague.com.evil/entry/1/event/1/",
        0,
        -1,
        True,
        "1;curl",
        "https://fantasy.premierleague.com/entry/1/event/39/",
    ],
)
def test_invalid_team_identifier(value):
    with pytest.raises(ValueError):
        team_id(value)


def test_retry_and_history(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    count = 0

    def respond(request):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "history": [
                    {"fixture": 1, "round": 1, "minutes": 90, "total_points": 2},
                    {"fixture": 2, "round": 2, "minutes": 0, "total_points": 0},
                ],
                "fixtures": [],
                "history_past": [],
            },
        )

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    assert provider.player_history(1)["appearances"] == 1
    assert count == 2
    assert provider.player_history(1)["appearances"] == 1
    assert count == 2
