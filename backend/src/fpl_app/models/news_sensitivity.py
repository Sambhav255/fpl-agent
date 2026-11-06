"""Explicit official-zero availability sensitivity; never rewrites parent forecasts."""

from __future__ import annotations

import copy
import json
from typing import Any

from fpl_app.learning.forecast_benchmark import checked_benchmark, make_benchmark
from fpl_app.storage import Store, fingerprint, utcnow


def freeze_news_sensitivity(
    store: Store, parent_id: str, parent: dict[str, Any] | None = None
) -> dict[str, Any]:
    existing = next(
        (
            b
            for b in store.list("forecast_benchmark")
            if b["protocol"].get("parent_benchmark_id") == parent_id
            and b["protocol"].get("version") == "official-zero-sensitivity-v1"
        ),
        None,
    )
    if existing is not None:
        return checked_benchmark(store, existing["benchmark_id"])
    parent = checked_benchmark(store, parent_id) if parent is None else parent
    if fingerprint({k: v for k, v in parent.items() if k != "benchmark_id"}) != parent_id:
        raise ValueError("Parent benchmark identity mismatch")
    source = next(r for r in parent["sources"] if r["resource"] == "bootstrap-static/")
    bootstrap = json.loads(store.snapshot(source["id"])["raw"])
    unavailable = {
        p["id"]
        for p in bootstrap["elements"]
        if p.get("chance_of_playing_next_round") == 0 or p.get("status") in {"u", "s"}
    }
    metadata = {p["id"]: p for p in bootstrap["elements"]}
    models = copy.deepcopy(parent["models"])
    now = utcnow()
    for model in models.values():
        model["published_at"] = now
        for row in model["predictions"]:
            p = metadata[row["player_id"]]
            row.update(
                official_status=p.get("status"),
                official_next_chance=p.get("chance_of_playing_next_round"),
            )
            if row["player_id"] in unavailable:
                for key in [
                    "expected_points",
                    "expected_minutes",
                    "appearance_probability",
                    "sixty_probability",
                    "q0.1",
                    "q0.5",
                    "q0.9",
                ]:
                    if key in row:
                        row[key] = 0.0
    fixtures = next(r for r in parent["sources"] if r["resource"] == "fixtures/")
    return make_benchmark(
        store,
        source["id"],
        fixtures["id"],
        parent["event"],
        models,
        produced_at=now,
        protocol={
            "version": "official-zero-sensitivity-v1",
            "study_id": parent["protocol"]["study_id"] + "-official-zero",
            "parent_benchmark_id": parent_id,
            "parent_forecast_published_at": parent["published_at"],
            "zeroed_player_count": len(unavailable),
            "zeroed_player_ids": sorted(unavailable),
            "policy": "One deterministic zero override for official 0%/unavailable/suspended; doubtful flags unchanged",
            "interpretation": "Sensitivity scenario, not a new fitted model or calibrated availability estimate",
            "promotion": False,
        },
    )
