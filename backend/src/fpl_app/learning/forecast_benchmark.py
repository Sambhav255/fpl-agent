"""Immutable pre-deadline forecasts and automatic finalized-event scorecards."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from math import isfinite
from typing import Any

import numpy as np

from fpl_app.features.pipeline import utc
from fpl_app.storage import Store, fingerprint, utcnow


def make_benchmark(
    store: Store,
    bootstrap_id: str,
    fixtures_id: str,
    event: int,
    models: dict[str, dict[str, Any]],
    *,
    produced_at: str,
    protocol: dict[str, Any],
    team_predictions: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Freeze explicit unconditional event means; never infer missing predictions."""
    if type(event) is not int or not 1 <= event <= 38 or not models:
        raise ValueError("Explicit event and nonempty forecast families required")
    sources = [store.snapshot(i) for i in (bootstrap_id, fixtures_id)]
    for source, resource in zip(sources, ("bootstrap-static/", "fixtures/")):
        if (
            source["resource"] != resource
            or source["provider"] != "official_fpl"
            or source["data_mode"] != "live"
            or source["validation_status"] != "valid"
            or hashlib.sha256(source["raw"]).hexdigest() != source["payload_sha256"]
            or utc(source["available_at"]) > utc(produced_at)
        ):
            raise ValueError("Verified source identity, bytes and pre-forecast timing required")
    bootstrap, fixtures = (json.loads(s["raw"]) for s in sources)
    deadline = next(e["deadline_time"] for e in bootstrap["events"] if e["id"] == event)
    if utc(produced_at) >= utc(deadline) or utc(produced_at) > utc(utcnow()):
        raise ValueError("Forecast must actually be published before its deadline")
    elements = {p["id"]: p for p in bootstrap["elements"]}
    schedule = [f for f in fixtures if f.get("event") == event]
    if not schedule or any(f.get("started") is True for f in schedule):
        raise ValueError("Unstarted frozen event schedule required")
    for model in models.values():
        rows = model["predictions"]
        if not rows or len({r["player_id"] for r in rows}) != len(rows):
            raise ValueError("Distinct nonempty player forecast coverage required")
        if utc(model["published_at"]) > utc(produced_at):
            raise ValueError("Model forecast was not available at benchmark publication")
        for row in rows:
            if (
                type(row["player_id"]) is not int
                or row["player_id"] not in elements
                or type(row["expected_points"]) not in (float, int)
                or not isfinite(row["expected_points"])
            ):
                raise ValueError("Known player IDs and finite mean forecasts required")
    for rows in (team_predictions or {}).values():
        if len({r["fixture_id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate team-goal forecast fixtures")
        for row in rows:
            if row["fixture_id"] not in {f["id"] for f in schedule} or any(
                type(row[k]) not in (int, float) or not isfinite(row[k]) or row[k] < 0
                for k in ("home_mean_goals", "away_mean_goals")
            ):
                raise ValueError("Known fixture and finite nonnegative team-goal means required")
    exposures = {
        str(p): sorted(f["id"] for f in schedule if el["team"] in (f["team_h"], f["team_a"]))
        for p, el in elements.items()
    }
    last_kickoff = max(utc(f["kickoff_time"]) for f in schedule)
    body = {
        "version": "predeadline-event-means-v1",
        "season": sources[0]["season"],
        "event": event,
        "deadline": deadline,
        "published_at": produced_at,
        "check_after": (last_kickoff + timedelta(hours=16)).isoformat(),
        "sources": [
            {k: s[k] for k in ("id", "resource", "available_at", "payload_sha256")} for s in sources
        ],
        "models": models,
        "team_predictions": team_predictions or {},
        "exposures": exposures,
        "fixtures": [{k: f[k] for k in ("id", "event", "team_h", "team_a")} for f in schedule],
        "protocol": protocol,
        "execution_claim": "forecast benchmark only; no actual manager action inferred",
    }
    return {**body, "benchmark_id": fingerprint(body)}


def checked_benchmark(store: Store, identifier: str) -> dict[str, Any]:
    value = store.get("forecast_benchmark", identifier)
    if fingerprint({k: v for k, v in value.items() if k != "benchmark_id"}) != identifier:
        raise ValueError("Frozen benchmark contents changed")
    if utc(value["published_at"]) >= utc(value["deadline"]):
        raise ValueError("Late forecast cannot become a prospective benchmark")
    for ref in value["sources"]:
        source = store.snapshot(ref["id"])
        if hashlib.sha256(source["raw"]).hexdigest() != ref["payload_sha256"]:
            raise ValueError("Frozen benchmark source bytes changed")
    return value


def score_benchmark(store: Store, provider: Any, identifier: str) -> dict[str, Any]:
    frozen = checked_benchmark(store, identifier)
    event = frozen["event"]
    status = provider.fetch("bootstrap-static/", force=True)
    official = next(e for e in json.loads(status["raw"])["events"] if e["id"] == event)
    if official.get("finished") is not True or official.get("data_checked") is not True:
        return {"benchmark_id": identifier, "event": event, "status": "pending_finalization"}
    fixtures = provider.fetch("fixtures/", force=True)
    live = provider.fetch(f"event/{event}/live/", force=True)
    current_fixtures = {f["id"]: f for f in json.loads(fixtures["raw"])}
    changed = {
        f["id"]
        for f in frozen["fixtures"]
        if f["id"] not in current_fixtures
        or any(current_fixtures[f["id"]].get(k) != f[k] for k in ("event", "team_h", "team_a"))
    }
    if any(
        f.get("event") == event and f["id"] not in {x["id"] for x in frozen["fixtures"]}
        for f in current_fixtures.values()
    ):
        return {"benchmark_id": identifier, "event": event, "status": "schedule_changed"}
    elements = json.loads(live["raw"])["elements"]
    if len({p["id"] for p in elements}) != len(elements):
        raise ValueError("Duplicate official player outcome IDs")
    actual = {p["id"]: p for p in elements}
    metrics, outcomes = {}, []
    common = set.intersection(
        *[{r["player_id"] for r in m["predictions"]} for m in frozen["models"].values()]
    )
    for name, model in frozen["models"].items():
        errors, common_errors = [], []
        coverage: Counter[str] = Counter()
        for row in model["predictions"]:
            player = row["player_id"]
            state = "final"
            record = actual.get(player)
            stats = {} if record is None else record.get("stats", {})
            points, minutes = stats.get("total_points"), stats.get("minutes")
            if changed.intersection(frozen["exposures"][str(player)]):
                state = "schedule_changed"
            elif record is None:
                state = "missing_outcome"
            elif type(points) is not int or type(minutes) is not int or minutes < 0:
                state = "invalid_outcome"
            coverage[state] += 1
            outcomes.append({"model": name, "player_id": player, "status": state, "points": points})
            if state == "final":
                assert type(points) is int
                predicted = float(row["expected_points"])
                errors.append(predicted - points)
                if player in common:
                    common_errors.append(predicted - points)
        metrics[name] = {
            "n": len(errors),
            "forecast_n": len(model["predictions"]),
            "mae": float(np.abs(errors).mean()) if errors else None,
            "rmse": float(np.sqrt(np.square(errors).mean())) if errors else None,
            "bias": float(np.mean(errors)) if errors else None,
            "coverage": dict(coverage),
            "common_n": len(common_errors),
            "common_mae": float(np.abs(common_errors).mean()) if common_errors else None,
            "common_rmse": float(np.sqrt(np.square(common_errors).mean()))
            if common_errors
            else None,
        }
    team_metrics = {}
    for name, rows in frozen.get("team_predictions", {}).items():
        goal_errors = []
        for row in rows:
            fixture = current_fixtures.get(row["fixture_id"], {})
            if row["fixture_id"] in changed:
                continue
            for mean_key, actual_key in [
                ("home_mean_goals", "team_h_score"),
                ("away_mean_goals", "team_a_score"),
            ]:
                if type(fixture.get(actual_key)) is int:
                    goal_errors.append(row[mean_key] - fixture[actual_key])
        team_metrics[name] = {
            "n": len(goal_errors),
            "expected_n": 2 * len(rows),
            "mae": float(np.abs(goal_errors).mean()) if goal_errors else None,
            "rmse": float(np.sqrt(np.square(goal_errors).mean())) if goal_errors else None,
        }
    complete = all(m["n"] == m["forecast_n"] for m in metrics.values())
    complete = complete and all(m["n"] == m["expected_n"] for m in team_metrics.values())
    body = {
        "benchmark_id": identifier,
        "event": event,
        "status": "final" if complete else "incomplete_outcome_coverage",
        "scored_at": utcnow(),
        "forecast_sha256": fingerprint(frozen),
        "source_refs": [
            {k: s[k] for k in ("id", "resource", "payload_sha256", "available_at")}
            for s in (status, fixtures, live)
        ],
        "metrics": metrics,
        "team_goal_metrics": team_metrics,
        "outcomes": outcomes,
        "claim": "One prospective event; score before refitting, no automatic promotion",
    }
    revision = fingerprint({k: v for k, v in body.items() if k != "scored_at"})
    return {**body, "revision": revision}


def enqueue_due_benchmarks(store: Store, now: str | None = None) -> list[dict[str, Any]]:
    from fpl_app.jobs import Queue

    instant = utc(now or utcnow())
    scored = {
        r["benchmark_id"]
        for r in store.list("forecast_benchmark_outcome")
        if r["status"] == "final"
    }
    result = []
    for benchmark in store.list("forecast_benchmark"):
        if benchmark["benchmark_id"] in scored or instant < utc(benchmark["check_after"]):
            continue
        result.append(
            Queue(store).enqueue(
                "forecast_benchmark_score",
                {
                    "benchmark_id": benchmark["benchmark_id"],
                    "check_slot": int(instant.timestamp()) // (6 * 3600),
                },
            )
        )
    return result
