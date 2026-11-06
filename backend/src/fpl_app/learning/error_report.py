"""Source-bound weekly residual diagnostics; associations never imply a cause."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, TypeGuard

from fpl_app.features.pipeline import utc
from fpl_app.learning.journal import decision_view
from fpl_app.learning.post_event import metrics, review_forecasts
from fpl_app.storage import Store, fingerprint, utcnow

VERSION = "weekly-error-report-v1"


def _finite(value: Any) -> TypeGuard[float]:
    return type(value) in (int, float) and math.isfinite(value)


def _probability(value: Any) -> TypeGuard[float]:
    return _finite(value) and 0 <= value <= 1


def _calibration(pairs: list[tuple[float, int]]) -> dict[str, Any]:
    bins = []
    for low in range(5):
        selected = [(p, y) for p, y in pairs if min(4, int(p * 5)) == low]
        bins.append(
            {
                "lower": low / 5,
                "upper": (low + 1) / 5,
                "n": len(selected),
                "mean_probability": sum(p for p, _ in selected) / len(selected)
                if selected
                else None,
                "observed_frequency": sum(y for _, y in selected) / len(selected)
                if selected
                else None,
            }
        )
    return {
        "n": len(pairs),
        "brier": sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else None,
        "bias": sum(p - y for p, y in pairs) / len(pairs) if pairs else None,
        "log_loss": -sum(
            y * math.log(max(1e-15, p)) + (1 - y) * math.log(max(1e-15, 1 - p)) for p, y in pairs
        )
        / len(pairs)
        if pairs
        else None,
        "bins": bins,
    }


def _opportunity(
    rows: list[dict], actual: dict[int, dict], exposures: dict, eligible_ids: set[int]
) -> dict:
    appearances: list[tuple[float, int]] = []
    sixty: list[tuple[float, int]] = []
    predicted_minutes, actual_minutes = [], []
    missing: Counter[str] = Counter()
    residuals = []
    for row in rows:
        player = row["player_id"]
        if player not in eligible_ids:
            missing["excluded_from_verified_point_coverage"] += 1
            continue
        stats = actual.get(player, {})
        minutes = stats.get("minutes")
        scheduled = exposures[str(player)]
        if type(minutes) is not int or minutes < 0:
            missing["missing_or_invalid_outcome"] += 1
            continue
        # Frozen benchmark rows contain event means. Fixture probabilities cannot
        # be derived from DGW event minutes, nor combined without a joint model.
        single = len(scheduled) == 1
        p = row.get("appearance_probability")
        p60 = row.get("minutes_60_probability", row.get("sixty_probability"))
        expected = row.get("expected_minutes")
        if single and _probability(p):
            appearances.append((p, int(minutes > 0)))
        else:
            missing["appearance_missing_or_non_single_fixture"] += 1
        if single and _probability(p60):
            sixty.append((p60, int(minutes >= 60)))
        else:
            missing["sixty_missing_or_non_single_fixture"] += 1
        if (
            _finite(expected)
            and expected >= 0
            and (single or row.get("minutes_semantics") == "event_total")
        ):
            predicted_minutes.append(expected)
            actual_minutes.append(minutes)
            residuals.append(
                {
                    "player_id": player,
                    "forecast_minus_actual_minutes": expected - minutes,
                }
            )
        else:
            missing["minutes_missing_or_undeclared_event_total"] += 1
    return {
        "appearance": _calibration(appearances),
        "minutes_60": _calibration(sixty),
        "minutes": metrics(predicted_minutes, actual_minutes),
        "missingness": dict(missing),
        "largest_duration_residuals": sorted(
            residuals,
            key=lambda r: abs(r["forecast_minus_actual_minutes"]),
            reverse=True,
        )[:10],
        "semantics": "Minutes-based appearance; single-fixture probability metrics only",
        "causal_attribution": "unavailable; residuals alone do not identify injury, role or rotation",
    }


def _decisions(store: Store, season: str, event: int) -> dict:
    statuses: Counter[str] = Counter()
    different = confirmed_different = 0
    references = {}
    for journal in store.list("decision_journal"):
        if (
            journal.get("season", "").replace("-", "/") != season.replace("-", "/")
            or journal["event"] != event
        ):
            continue
        view = decision_view(store, journal["decision_id"])
        status = view["execution_status"]
        statuses[status] += 1
        changed = (
            view["execution_action_id"] is not None
            and view["execution_action_id"] != view["recommended_action_id"]
        )
        different += changed
        confirmed_different += changed and status == "confirmed_executed"
        references[journal["decision_id"]] = fingerprint(
            {"journal": journal, "action_history": view["action_history"]}
        )
    return {
        "frozen_decisions": sum(statuses.values()),
        "execution_status_counts": dict(statuses),
        "selected_actions_different_from_recommendation": different,
        "confirmed_actions_different_from_recommendation": confirmed_different,
        "references": references,
        "realized_policy_gain": None,
        "execution_error_points": None,
        "status": "unavailable" if not references else "execution_records_only",
        "limitations": [
            "Action disagreement is not an execution error or a measured point loss",
            "User selection does not establish execution; unknown execution remains unknown",
            "Legal policy gains require a separate source-bound same-state replay",
        ],
    }


def weekly_error_report(
    store: Store,
    benchmark_ids: list[str],
    bootstrap_id: str,
    fixtures_id: str,
    live_id: str,
    *,
    previous_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read verified frozen forecasts and observations without fetching or writing.

    Prior reports must retain their content hashes. Only earlier finalized event
    blocks with the same explicit method identity contribute to drift summaries.
    Provisional current results stay labelled and never become training evidence.
    """
    import json

    from fpl_app.learning.forecast_benchmark import checked_benchmark

    review = review_forecasts(store, benchmark_ids, bootstrap_id, fixtures_id, live_id)
    bundles = [checked_benchmark(store, b) for b in benchmark_ids]
    seasons = {b["season"] for b in bundles}
    if len(seasons) != 1:
        raise ValueError("Same-season report required")
    season = next(iter(seasons))
    actual = {
        row["id"]: row["stats"] for row in json.loads(store.snapshot(live_id)["raw"])["elements"]
    }
    names = Counter(name for b in bundles for name in b["models"])
    models = {}
    for bundle in bundles:
        ages = [
            (utc(bundle["published_at"]) - utc(s["available_at"])).total_seconds() / 3600
            for s in bundle["sources"]
        ]
        for name, method in bundle["models"].items():
            stream = name if names[name] == 1 else name + "@" + bundle["benchmark_id"][:12]
            method_identity = method.get("method_id") or fingerprint(
                {"name": name, "protocol": bundle["protocol"]}
            )
            models[stream] = {
                "method_identity": method_identity,
                "method_identity_status": "explicit"
                if method.get("method_id")
                else "protocol_bound_fallback",
                "points": review["comparisons"][stream],
                "opportunity": _opportunity(
                    method["predictions"],
                    actual,
                    bundle["exposures"],
                    {r["player_id"] for r in method["predictions"]}
                    - set(review["comparisons"][stream]["missing_or_invalid_ids"]),
                ),
                "input_age_hours_at_forecast": {
                    "minimum": min(ages),
                    "maximum": max(ages),
                },
                "freshness_semantics": "Source capture age, not feature publication latency",
                "feature_missingness": None,
                "component_error_attribution": {
                    "role": "unavailable_without_verified_role_targets",
                    "attacking_opportunity": "unavailable_without_frozen_component_forecasts",
                    "finishing_variance": "not_identifiable_from_one_realized_return",
                    "clean_sheet": "unavailable_without_frozen_component_forecasts",
                    "defensive_contribution": "unavailable_without_frozen_component_forecasts",
                    "bonus": "unavailable_without_frozen_component_forecasts",
                },
            }
    previous = []
    for report in previous_reports or []:
        if report.get("version") != VERSION or fingerprint(
            {k: v for k, v in report.items() if k != "report_id"}
        ) != report.get("report_id"):
            raise ValueError("Previous weekly report contents changed")
        if report["season"] != season:
            continue
        if report["event"] > review["event"] or utc(report["reviewed_at"]) > utc(utcnow()):
            raise ValueError("Future report cannot enter drift analysis")
        previous.append(report)
    drift = {}
    for name, model in models.items():
        blocks: dict[int, tuple[Any, dict]] = {}
        for report in previous:
            if report["event"] >= review["event"] or report["status"] != "final":
                continue
            for old in report["models"].values():
                if old["method_identity"] != model["method_identity"]:
                    continue
                # Revisions are one event block; never independent observations.
                candidate = (utc(report["reviewed_at"]), old)
                if report["event"] not in blocks or candidate[0] > blocks[report["event"]][0]:
                    blocks[report["event"]] = candidate
        old_bias = [
            old["points"]["full_coverage"]["bias"]
            for _, old in blocks.values()
            if old["points"]["full_coverage"]["bias"] is not None
        ]
        opportunity_drift = {}
        for label, field in (
            ("appearance", "brier"),
            ("minutes_60", "brier"),
            ("minutes", "bias"),
        ):
            prior_values = [
                old["opportunity"][label][field]
                for _, old in blocks.values()
                if old["opportunity"][label][field] is not None
            ]
            current_value = model["opportunity"][label][field]
            mean = sum(prior_values) / len(prior_values) if prior_values else None
            opportunity_drift[label] = {
                "metric": field,
                "prior_finalized_event_blocks": len(prior_values),
                "event_equal_weight_mean": mean,
                "current_minus_prior": current_value - mean
                if current_value is not None and mean is not None
                else None,
            }
        current_bias = model["points"]["full_coverage"]["bias"]
        prior_bias = sum(old_bias) / len(old_bias) if old_bias else None
        drift[name] = {
            "prior_finalized_event_blocks": len(blocks),
            "prior_events": sorted(blocks),
            "event_equal_weight_mean_point_bias": prior_bias,
            "current_minus_prior_point_bias": current_bias - prior_bias
            if current_bias is not None and prior_bias is not None
            else None,
            "status": "descriptive_only" if blocks else "insufficient_prior_blocks",
            "opportunity": opportunity_drift,
            "formal_drift_test": None,
        }
    same_event = [r for r in previous if r["event"] == review["event"]]
    body = {
        "version": VERSION,
        "season": season,
        "event": review["event"],
        "status": review["status"],
        "reviewed_at": utcnow(),
        "forecast_review_revision": review["revision"],
        "benchmark_sha256": review["benchmarks"],
        "source_refs": review["sources"],
        "models": models,
        "drift": drift,
        "decisions_and_execution": _decisions(store, season, review["event"]),
        "outcome_revision_observations": {
            "distinct_prior_source_revisions_for_same_event": len(
                {fingerprint(r["source_refs"]) for r in same_event}
            ),
            "current_sources_differ_from_prior": any(
                fingerprint(r["source_refs"]) != fingerprint(review["sources"]) for r in same_event
            ),
            "semantics": "Capture revision frequency; byte changes need not change football outcomes",
        },
        "training_eligible": False,
        "promotion": False,
        "limitations": [
            "Residual associations are diagnostics, not identified causes",
            "Missing opportunity and component forecasts remain unavailable",
            "Different method identities never pool; revisions count as one event block",
            "Player rows within an event are dependent; no player-level significance claim",
            "No automatic point adjustment, retraining, state edit or model promotion",
        ],
    }
    return {**body, "report_id": fingerprint(body)}
