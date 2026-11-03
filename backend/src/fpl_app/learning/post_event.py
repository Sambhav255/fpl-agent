"""Offline, source-bound diagnostics of frozen forecasts, including provisional reviews.

Preview reports are deliberately separate from finalized benchmark outcomes and must
never be consumed as training labels or promotion evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from fpl_app.features.pipeline import utc
from fpl_app.learning.forecast_benchmark import checked_benchmark
from fpl_app.storage import Store, fingerprint, utcnow


def verified_source(store: Store, identifier: str, resource: str) -> tuple[dict, Any]:
    source = store.snapshot(identifier)
    if (
        source["provider"] != "official_fpl"
        or source["data_mode"] != "live"
        or source["resource"] != resource
        or source["validation_status"] != "valid"
        or hashlib.sha256(source["raw"]).hexdigest() != source["payload_sha256"]
    ):
        raise ValueError("Verified official source bytes and resource required")
    return source, json.loads(source["raw"])


def metrics(predicted: list[float], actual: list[int]) -> dict[str, Any]:
    if not actual:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "spearman": None}
    error = np.asarray(predicted) - np.asarray(actual)
    correlation = (
        float(spearmanr(predicted, actual).statistic)
        if len(set(predicted)) > 1 and len(set(actual)) > 1
        else None
    )
    return {
        "n": len(actual),
        "mae": float(np.abs(error).mean()),
        "rmse": float(np.sqrt(np.square(error).mean())),
        "bias": float(error.mean()),
        "spearman": correlation,
    }


def review_forecasts(
    store: Store,
    benchmark_ids: list[str],
    bootstrap_id: str,
    fixtures_id: str,
    live_id: str,
    *,
    analysis_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = [checked_benchmark(store, identifier) for identifier in benchmark_ids]
    if not frozen or len({b["event"] for b in frozen}) != 1:
        raise ValueError("Nonempty same-event benchmarks required")
    event = frozen[0]["event"]
    sources_and_values = [
        verified_source(store, identifier, resource)
        for identifier, resource in (
            (bootstrap_id, "bootstrap-static/"),
            (fixtures_id, "fixtures/"),
            (live_id, f"event/{event}/live/"),
        )
    ]
    sources = [s for s, _ in sources_and_values]
    if any(s["season"] != b["season"] for s in sources for b in frozen):
        raise ValueError("Mixed source seasons")
    if any(utc(s["available_at"]) <= utc(frozen[0]["deadline"]) for s in sources):
        raise ValueError("Post-deadline outcome captures required")
    bootstrap, fixtures, live = [v for _, v in sources_and_values]
    official = next(e for e in bootstrap["events"] if e["id"] == event)
    actual = {p["id"]: p["stats"] for p in live["elements"]}
    if len(actual) != len(live["elements"]):
        raise ValueError("Duplicate outcome IDs")
    current = {f["id"]: f for f in fixtures if f.get("event") == event}
    for b in frozen:
        saved = {f["id"]: f for f in b["fixtures"]}
        if set(saved) != set(current) or any(
            any(current[i].get(k) != f[k] for k in ("event", "team_h", "team_a"))
            for i, f in saved.items()
        ):
            raise ValueError("Schedule changed; original event targets need reconciliation")
    fixture_complete = bool(current) and all(
        f.get("finished") is True and f.get("finished_provisional") is True
        for f in current.values()
    )
    finalized = (
        official.get("finished") is True
        and official.get("data_checked") is True
        and fixture_complete
    )
    models: dict[str, dict[int, float]] = {}
    names = Counter(name for b in frozen for name in b["models"])
    for b in frozen:
        for name, model in b["models"].items():
            # Repeated experiments at distinct origins remain distinct streams.
            if names[name] > 1:
                name = name + "@" + b["benchmark_id"][:12]
            models[name] = {
                r["player_id"]: float(r["expected_points"]) for r in model["predictions"]
            }
    valid = {
        p
        for p, s in actual.items()
        if type(s.get("total_points")) is int
        and type(s.get("minutes")) is int
        and s["minutes"] >= 0
    }
    common = set.intersection(*(set(m) for m in models.values())) & valid
    first_bootstrap = json.loads(store.snapshot(frozen[0]["sources"][0]["id"])["raw"])
    positions = {p["id"]: p["element_type"] for p in first_bootstrap["elements"]}
    groups = {"all_common_players": common}
    plan_is_predeclared = False
    if analysis_plan:
        if analysis_plan["event"] != event:
            raise ValueError("Analysis plan event differs")
        plan_is_predeclared = utc(analysis_plan["registered_at"]) < utc(
            frozen[0]["deadline"]
        ) and set(analysis_plan["benchmark_ids"]) == set(benchmark_ids)
        groups.update({name: set(ids) & common for name, ids in analysis_plan["subgroups"].items()})
    for position, label in ((1, "GK"), (2, "DEF"), (3, "MID"), (4, "FWD")):
        groups["position_" + label] = {p for p in common if positions.get(p) == position}
    # These two strata describe realized outcomes, never eligibility at forecast time.
    groups["realized_minutes_zero_diagnostic"] = {p for p in common if actual[p]["minutes"] == 0}
    groups["realized_minutes_60_plus_diagnostic"] = {
        p for p in common if actual[p]["minutes"] >= 60
    }
    comparisons = {}
    for name, predictions in models.items():
        ids = sorted(set(predictions) & valid)
        comparisons[name] = {
            "full_coverage": metrics(
                [predictions[p] for p in ids], [actual[p]["total_points"] for p in ids]
            ),
            "forecast_n": len(predictions),
            "missing_or_invalid_ids": sorted(set(predictions) - valid),
            "groups": {
                label: metrics(
                    [predictions[p] for p in sorted(members)],
                    [actual[p]["total_points"] for p in sorted(members)],
                )
                for label, members in groups.items()
            },
            "largest_errors": [
                {
                    "player_id": p,
                    "predicted": predictions[p],
                    "actual": actual[p]["total_points"],
                    "minutes": actual[p]["minutes"],
                    "error": predictions[p] - actual[p]["total_points"],
                }
                for p in sorted(
                    ids, key=lambda p: abs(predictions[p] - actual[p]["total_points"]), reverse=True
                )[:10]
            ],
        }
    team_metrics = {}
    for b in frozen:
        for name, rows in b.get("team_predictions", {}).items():
            pairs = [
                (r[mean], current[r["fixture_id"]].get(score))
                for r in rows
                for mean, score in (
                    ("home_mean_goals", "team_h_score"),
                    ("away_mean_goals", "team_a_score"),
                )
            ]
            known = [(p, a) for p, a in pairs if type(a) is int]
            team_metrics[name] = {
                **metrics([p for p, _ in known], [a for _, a in known]),
                "expected_n": len(pairs),
            }
    body = {
        "event": event,
        "status": (
            "provisional"
            if not finalized
            else "incomplete_outcome_coverage"
            if any(m["missing_or_invalid_ids"] for m in comparisons.values())
            or any(m["n"] != m["expected_n"] for m in team_metrics.values())
            else "final"
        ),
        "official_finished": official.get("finished"),
        "official_data_checked": official.get("data_checked"),
        "finished_fixtures": sum(f.get("finished") is True for f in current.values()),
        "provisionally_finished_fixtures": sum(
            f.get("finished_provisional") is True for f in current.values()
        ),
        "scheduled_fixtures": len(current),
        "average_entry_score": official.get("average_entry_score"),
        "benchmarks": {b["benchmark_id"]: fingerprint(b) for b in frozen},
        "sources": [
            {k: s[k] for k in ("id", "resource", "payload_sha256", "available_at")} for s in sources
        ],
        "analysis_plan_sha256": fingerprint(analysis_plan) if analysis_plan else None,
        "subgroups_predeclared": plan_is_predeclared,
        "common_player_ids": sorted(common),
        "comparisons": comparisons,
        "team_goal_metrics": team_metrics,
        "training_eligible": False,
        "promotion": False,
        "limitations": [
            "Provisional scores can change, including bonus and substitutions",
            "One gameweek is not independent player-level evidence of general improvement",
            "Retrospective outcome strata are diagnostic only",
            "Player point errors and team goal errors have different units",
        ],
    }
    return {**body, "revision": fingerprint(body), "reviewed_at": utcnow()}


def registered_reviews(
    store: Store, scorecard: dict[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    """Finish registered cross-family diagnostics when official scoring becomes final."""
    if scorecard.get("status") != "final":
        return []
    refs = {r["resource"]: r["id"] for r in scorecard["source_refs"]}
    artifacts = []
    for retained in store.list("forecast_analysis_plan"):
        plan = retained["plan"]
        if fingerprint(plan) != retained["plan_sha256"]:
            raise ValueError("Retained analysis plan changed")
        if scorecard["benchmark_id"] not in plan["benchmark_ids"]:
            continue
        report = review_forecasts(
            store,
            plan["benchmark_ids"],
            refs["bootstrap-static/"],
            refs["fixtures/"],
            refs[f"event/{plan['event']}/live/"],
            analysis_plan=plan,
        )
        artifacts.append(("forecast_event_review", report["revision"], report))
    return artifacts
