"""Read-only selling-price estimates from published gameweek values."""

from __future__ import annotations

from typing import Any

from fpl_app.domain.rules import selling_price

PROVENANCE = "published_gameweek_price_estimate"


def suggest_selling_prices(
    squad_ids: list[int],
    market_prices: dict[int, int],
    transfers: list[dict[str, Any]],
    entry_history: dict[str, Any],
    element_histories: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Estimate purchase and sale prices. Do not infer free transfers from history."""
    current = entry_history.get("current")
    rows = current if isinstance(current, list) else []
    events = [
        row["event"]
        for row in rows
        if isinstance(row, dict) and type(row.get("event")) is int
    ]
    if not events:
        raise ValueError("Entry history has no current gameweeks")
    first_event = min(events)
    acquired: dict[int, int] = {}
    squad = set(squad_ids)
    for row in transfers:
        if not isinstance(row, dict):
            continue
        incoming = row.get("element_in")
        event = row.get("event")
        if type(incoming) is not int or type(event) is not int or incoming not in squad:
            continue
        if incoming not in acquired or event >= acquired[incoming]:
            acquired[incoming] = event
    suggestions: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for player_id in squad_ids:
        market = market_prices.get(player_id)
        if type(market) is not int:
            missing.append({"player_id": player_id, "reason": "Current market price is unavailable"})
            continue
        event = acquired.get(player_id, first_event)
        history = element_histories.get(player_id, [])
        values = [
            row["value"]
            for row in history
            if isinstance(row, dict)
            and row.get("round") == event
            and type(row.get("value")) is int
        ]
        if not values:
            missing.append(
                {"player_id": player_id, "reason": f"No published price for gameweek {event}"}
            )
            continue
        if len(set(values)) != 1:
            missing.append(
                {
                    "player_id": player_id,
                    "reason": f"Conflicting published prices for gameweek {event}",
                }
            )
            continue
        purchase = values[0]
        suggestions.append(
            {
                "player_id": player_id,
                "purchase_event": event,
                "purchase_price_units": purchase,
                "market_price_units": market,
                "selling_price_units": selling_price(purchase, market),
                "provenance": PROVENANCE,
                "estimate": True,
            }
        )
    return suggestions, missing
