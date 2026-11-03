"""Forecast ranking diagnostics; these are not legal squad or transfer replays."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

import numpy as np

from fpl_app.features.pipeline import utc
from fpl_app.storage import fingerprint, utcnow


@dataclass(frozen=True)
class SelectionProtocol:
    minimum_prior_mean_minutes: float = 60.0
    position_top_k: int = 5
    version: str = "forecast-selection-v1"

    def __post_init__(self):
        if (
            isinstance(self.minimum_prior_mean_minutes, bool)
            or not isfinite(self.minimum_prior_mean_minutes)
            or not 0 <= self.minimum_prior_mean_minutes <= 90
            or type(self.position_top_k) is not int
            or self.position_top_k < 1
        ):
            raise ValueError("Valid prior-minutes threshold and positive integer K required")


def make_selection_plan(
    benchmarks: list[dict[str, Any]],
    eligibility: list[dict[str, Any]],
    eligibility_source: dict[str, Any],
    *,
    comparator: str,
    protocol: SelectionProtocol | None = None,
    study_id: str | None = None,
    method_regime: str | None = None,
    challenger: str | None = None,
) -> dict[str, Any]:
    """Select exclusively from frozen forecasts and origin-available player metadata.

    Registration time is always now. A late analysis never becomes a prospective
    decision merely because its underlying forecasts existed before the deadline.
    """
    protocol = protocol or SelectionProtocol()
    if not benchmarks or len({(b["season"], b["event"], b["deadline"]) for b in benchmarks}) != 1:
        raise ValueError("Same-season/event/deadline frozen benchmarks required")
    deadline = benchmarks[0]["deadline"]
    if utc(eligibility_source["available_at"]) >= utc(deadline):
        raise ValueError("Eligibility source must have been available before deadline")
    rows: dict[int, dict[str, Any]] = {}
    for row in eligibility:
        identifier = row["player_id"]
        if type(identifier) is not int or identifier <= 0 or row["position"] not in (1, 2, 3, 4):
            raise ValueError("Known positive IDs and FPL positions required")
        if utc(row["decision_cutoff"]) >= utc(deadline):
            raise ValueError("Eligibility must describe predeadline information")
        if identifier in rows and row != rows[identifier]:
            raise ValueError("Conflicting player eligibility rows")
        rows[identifier] = row
    names = Counter(name for b in benchmarks for name in b["models"])
    streams: dict[str, dict[int, float]] = {}
    for benchmark in benchmarks:
        if (
            fingerprint({k: v for k, v in benchmark.items() if k != "benchmark_id"})
            != benchmark["benchmark_id"]
        ):
            raise ValueError("Frozen benchmark changed")
        if utc(benchmark["published_at"]) >= utc(deadline):
            raise ValueError("Forecast published after deadline")
        for name, model in benchmark["models"].items():
            if names[name] > 1:
                name += "@" + benchmark["benchmark_id"][:12]
            predictions = model["predictions"]
            values = {r["player_id"]: float(r["expected_points"]) for r in predictions}
            if len(values) != len(predictions) or not all(isfinite(v) for v in values.values()):
                raise ValueError("Unique finite forecast means required")
            streams[name] = values
    if comparator not in streams:
        raise ValueError("Named comparator stream absent")
    if challenger is not None and challenger not in streams:
        raise ValueError("Named challenger stream absent")
    common = set.intersection(*(set(v) for v in streams.values()))
    if common - rows.keys():
        raise ValueError("Every common forecast player needs explicit eligibility metadata")
    eligible = {
        p
        for p in common
        if type(rows[p].get("prior_mean_minutes")) in (int, float)
        and isfinite(rows[p]["prior_mean_minutes"])
        and rows[p]["prior_mean_minutes"] >= protocol.minimum_prior_mean_minutes
    }
    groups: dict[str, dict[str, Any]] = {
        "position_" + name: {
            "ids": sorted(p for p in eligible if rows[p]["position"] == position),
            "k": protocol.position_top_k,
        }
        for position, name in ((1, "GK"), (2, "DEF"), (3, "MID"), (4, "FWD"))
    }
    groups["attacking_top1"] = {
        "ids": sorted(p for p in eligible if rows[p]["position"] in (3, 4)),
        "k": 1,
    }
    selections = {
        name: {
            group: {
                "selected_ids": sorted(pool["ids"], key=lambda p: (-values[p], p))[: pool["k"]],
                "predicted_sum": sum(
                    values[p]
                    for p in sorted(pool["ids"], key=lambda p: (-values[p], p))[: pool["k"]]
                ),
            }
            for group, pool in groups.items()
        }
        for name, values in streams.items()
    }
    now = utcnow()
    body = {
        "version": "frozen-selection-plan-v1",
        "season": benchmarks[0]["season"],
        "event": benchmarks[0]["event"],
        "deadline": deadline,
        "registered_at": now,
        "evidence_mode": "prospective_selection"
        if utc(now) < utc(deadline)
        else "retrospective_frozen_forecast_diagnostic",
        "protocol": asdict(protocol),
        "comparator": comparator,
        "study_id": study_id,
        "method_regime": method_regime,
        "benchmark_hashes": {b["benchmark_id"]: fingerprint(b) for b in benchmarks},
        "eligibility_source": eligibility_source,
        "eligibility_sha256": fingerprint([rows[p] for p in sorted(rows)]),
        "comparison_contract": {
            "comparator": comparator,
            "challenger": challenger,
            "primary_group": "attacking_top1",
            "metric": "selected_sum",
        },
        "common_forecast_ids": sorted(common),
        "eligible_ids": sorted(eligible),
        "groups": groups,
        "selections": selections,
        "interpretation": "Unconstrained ranking diagnostics; no ownership, prices, formation, hits, autosubs or captain/vice fallback",
        "tie_break": "descending predicted mean then ascending player ID",
    }
    return {**body, "plan_id": fingerprint(body)}


def score_selection_plan(
    plan: dict[str, Any],
    outcomes: dict[int, dict[str, Any]],
    *,
    finalized: bool,
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    if fingerprint({k: v for k, v in plan.items() if k != "plan_id"}) != plan["plan_id"]:
        raise ValueError("Selection plan changed")
    valid = {
        p: s["total_points"] for p, s in outcomes.items() if type(s.get("total_points")) is int
    }
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for name, selections in plan["selections"].items():
        result[name] = {}
        for group, choice in selections.items():
            pool, selected = plan["groups"][group]["ids"], choice["selected_ids"]
            missing_selected = sorted(set(selected) - valid.keys())
            missing_pool = sorted(set(pool) - valid.keys())
            # Never remove or backfill a selected player after inspecting outcomes.
            selected_sum = (
                sum(valid[p] for p in selected) if selected and not missing_selected else None
            )
            oracle = (
                sum(sorted((valid[p] for p in pool), reverse=True)[: len(selected)])
                if pool and not missing_pool
                else None
            )
            result[name][group] = {
                **choice,
                "requested_k": plan["groups"][group]["k"],
                "effective_k": len(selected),
                "eligible_n": len(pool),
                "missing_selected_ids": missing_selected,
                "missing_eligible_ids": missing_pool,
                "status": "empty_pool"
                if not pool
                else "incomplete_selection"
                if missing_selected
                else "complete_selection",
                "selected_sum": selected_sum,
                "selected_mean": selected_sum / len(selected) if selected_sum is not None else None,
                "hindsight_best_sum": oracle,
                "selection_regret": oracle - selected_sum
                if oracle is not None and selected_sum is not None
                else None,
            }
    for name, groups in result.items():
        for group, values in groups.items():
            baseline = result[plan["comparator"]][group]["selected_sum"]
            values["paired_selected_sum_delta"] = (
                values["selected_sum"] - baseline
                if values["selected_sum"] is not None and baseline is not None
                else None
            )
    body = {
        "plan_id": plan["plan_id"],
        "study_id": plan["study_id"],
        "method_regime": plan["method_regime"],
        "season": plan["season"],
        "event": plan["event"],
        "evidence_mode": plan["evidence_mode"],
        "protocol_sha256": fingerprint(plan["protocol"]),
        "comparison_contract": plan["comparison_contract"],
        "comparator": plan["comparator"],
        "status": "provisional"
        if not finalized
        else "incomplete_outcome_coverage"
        if any(v["missing_eligible_ids"] for g in result.values() for v in g.values())
        else "final",
        "selections": result,
        "source_refs": source_refs,
        "interpretation": plan["interpretation"],
        "promotion": False,
    }
    return {**body, "revision": fingerprint(body), "scored_at": utcnow()}


def selection_evidence(
    reports: list[dict[str, Any]],
    *,
    study_id: str,
    method_regime: str,
    challenger: str,
    group: str = "attacking_top1",
    minimum_events: int = 8,
) -> dict[str, Any]:
    """Distinct weekly ranking evidence, never the strategy promotion gate."""
    if type(minimum_events) is not int or minimum_events < 2:
        raise ValueError("At least two distinct event blocks required")
    by_event: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    exclusions: Counter[str] = Counter()
    for report in reports:
        if fingerprint(
            {k: v for k, v in report.items() if k not in ("revision", "scored_at")}
        ) != report.get("revision"):
            exclusions["invalid_report_identity"] += 1
        elif report.get("study_id") != study_id or report.get("method_regime") != method_regime:
            exclusions["different_study_or_method"] += 1
        elif (
            report.get("comparison_contract", {}).get("challenger") != challenger
            or report.get("comparison_contract", {}).get("primary_group") != group
        ):
            exclusions["different_primary_hypothesis"] += 1
        elif report["status"] != "final" or report["evidence_mode"] != "prospective_selection":
            exclusions["not_final_prospective_selection"] += 1
        else:
            by_event[(report["season"], report["event"])].append(report)
    rows = []
    protocols = set()
    comparators = set()
    for (season, event), captures in sorted(by_event.items()):
        if len({r["plan_id"] for r in captures}) != 1:
            exclusions["ambiguous_canonical_plan"] += 1
            continue

        # Exact same-plan source corrections use the latest retained capture,
        # never the revision with the most favorable score.
        def live_time(row, event=event):
            return max(
                utc(s["available_at"])
                for s in row["source_refs"]
                if s["resource"] == f"event/{event}/live/"
            )

        latest = max(live_time(row) for row in captures)
        corrections = [row for row in captures if live_time(row) == latest]
        if len({fingerprint(row["selections"]) for row in corrections}) > 1:
            exclusions["ambiguous_outcome_revision"] += 1
            continue
        report = max(corrections, key=lambda row: row["revision"])
        metric = report["selections"].get(challenger, {}).get(group, {})
        delta = metric.get("paired_selected_sum_delta")
        if delta is None:
            exclusions["missing_comparable_selection"] += 1
            continue
        protocols.add(report["protocol_sha256"])
        comparators.add(report["comparator"])
        rows.append(
            {
                "season": season,
                "event": event,
                "plan_id": report["plan_id"],
                "revision": report["revision"],
                "delta": delta,
            }
        )
    deltas = np.array([r["delta"] for r in rows], dtype=float)
    interval = None
    if len(deltas) >= minimum_events and len(protocols) == 1:
        samples = (
            np.random.default_rng(43)
            .choice(deltas, size=(4000, len(deltas)), replace=True)
            .mean(axis=1)
        )
        interval = [float(v) for v in np.quantile(samples, [0.025, 0.975])]
    reasons = []
    if len(rows) < minimum_events:
        reasons.append("Too few distinct finalized prospective gameweeks")
    if len(protocols) > 1:
        reasons.append("Evaluation protocol changed within study")
    if len(comparators) > 1:
        reasons.append("Comparator changed within study")
    if interval is not None and interval[0] <= 0:
        reasons.append("Weekly selection gain is inconclusive")
    return {
        "status": "insufficient_evidence" if reasons else "ready_for_method_review",
        "study_id": study_id,
        "method_regime": method_regime,
        "challenger": challenger,
        "group": group,
        "distinct_events": len(rows),
        "minimum_events": minimum_events,
        "paired_event_differences": rows,
        "exclusions": dict(exclusions),
        "reasons": reasons,
        "mean_selection_delta": float(deltas.mean()) if len(deltas) else None,
        "descriptive_event_bootstrap_95_interval": interval,
        "limitations": [
            "Few weekly blocks give unstable uncertainty estimates",
            "Ranking results omit legal squad transitions and do not meet strategy promotion requirements",
            "Calibration and full policy evidence still require separate review",
        ],
        "automatic_activation": False,
        "rank_target_probability": None,
    }
