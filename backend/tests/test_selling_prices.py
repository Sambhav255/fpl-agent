"""Published gameweek selling-price estimates stay unconfirmed."""

import json

import httpx
from fastapi.testclient import TestClient

from fpl_app.api import create_app
from fpl_app.providers import demo
from fpl_app.providers.prices import suggest_selling_prices
from fpl_app.storage import Store

PURCHASES = {
    496: 45,
    8: 55,
    334: 50,
    4: 80,
    124: 55,
    40: 76,
    154: 95,
    565: 55,
    557: 65,
    346: 60,
    411: 155,
    109: 45,
    165: 75,
    259: 40,
    173: 40,
}
ARRIVALS = {40: 4, 173: 4}


def _history(player_id, purchase):
    rows = [
        {
            "fixture": 1,
            "round": 1,
            "minutes": 0,
            "total_points": 0,
            "value": 75 if player_id == 40 else purchase,
        }
    ]
    if player_id in ARRIVALS:
        rows.append({"fixture": 4, "round": 4, "minutes": 0, "total_points": 0, "value": purchase})
    return rows


def test_estimates_use_published_gameweek_value_not_transfer_cost():
    markets = {player_id: purchase for player_id, purchase in PURCHASES.items()}
    markets[8] = 56
    markets[259] = 39
    transfers = [
        {"element_in": 40, "element_out": 1, "event": 4, "time": "t", "element_in_cost": 75},
        {"element_in": 173, "element_out": 2, "event": 4, "time": "t", "element_in_cost": 39},
    ]
    history = {
        "current": [{"event": 1, "event_transfers": 0, "bank": 100, "value": 1000}],
        "past": [],
        "chips": [{"name": "bboost", "event": 1}],
    }
    histories = {
        player_id: _history(player_id, purchase) for player_id, purchase in PURCHASES.items()
    }
    suggestions, missing = suggest_selling_prices(
        list(PURCHASES), markets, transfers, history, histories
    )
    assert missing == []
    by_id = {row["player_id"]: row for row in suggestions}
    assert by_id[40]["purchase_event"] == 4
    assert by_id[40]["purchase_price_units"] == 76
    assert by_id[173]["purchase_event"] == 4
    assert by_id[173]["purchase_price_units"] == 40
    assert by_id[8]["purchase_price_units"] == 55
    assert by_id[8]["selling_price_units"] == 55
    assert by_id[259]["selling_price_units"] == 39
    assert all(row["provenance"] == "published_gameweek_price_estimate" for row in suggestions)
    assert all(row["estimate"] is True for row in suggestions)
    changed = json.loads(json.dumps(history))
    changed["current"][0]["event_transfers"] = 4
    changed["current"][0]["bank"] = 7
    again, _missing = suggest_selling_prices(
        list(PURCHASES), markets, transfers, changed, histories
    )
    assert again == suggestions
    assert "free_transfers" not in json.dumps(suggestions)


def test_suggestion_endpoint_does_not_store_or_fetch_arbitrary_urls(tmp_path):
    from fpl_app.providers import Provider

    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    state = demo(store)
    state.team_id = 15
    state.picks = state.picks[:1]
    store.put("state", 15, state.model_dump(mode="json"))
    urls = []

    def respond(request):
        urls.append(str(request.url))
        path = request.url.path
        if path.endswith("/history/"):
            body = {"current": [{"event": 1}], "past": [], "chips": []}
        elif path.endswith("/transfers/"):
            body = []
        else:
            body = {
                "history": [
                    {"fixture": 1, "round": 1, "minutes": 1, "total_points": 1, "value": 50}
                ],
                "fixtures": [],
                "history_past": [],
            }
        return httpx.Response(200, json=body)

    provider = Provider(store, httpx.MockTransport(respond))
    provider.minimum_interval = 0
    client = TestClient(create_app(store, provider))
    assert client.get("/api/v1/teams/0/selling-price-suggestions").status_code == 422
    before = client.get("/api/v1/teams/15/state").json()
    response = client.get(
        "/api/v1/teams/15/selling-price-suggestions?url=https://evil.example/secret"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["estimate"] is True
    assert payload["suggestions"][0]["provenance"] == "published_gameweek_price_estimate"
    after = client.get("/api/v1/teams/15/state").json()
    assert after["state_version"] == before["state_version"]
    assert after["picks"] == before["picks"]
    assert all(url.startswith("https://fantasy.premierleague.com/api/") for url in urls)
    assert all("evil.example" not in url for url in urls)
