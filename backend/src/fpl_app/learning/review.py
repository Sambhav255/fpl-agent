"""Opt-in local recurring review. Durable ticks never edit private team state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fpl_app.jobs import Queue
from fpl_app.storage import Conflict, Store, fingerprint


def implementation_digest() -> str:
    from hashlib import sha256
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    names = [
        "learning/review.py",
        "learning/tournament.py",
        "models/weekly_tournament.py",
        "evaluation/tournament.py",
        "learning/outcomes.py",
        "learning/refit_cache.py",
        "learning/forecast_benchmark.py",
        "learning/post_event.py",
        "learning/selection_review.py",
        "models/training_eligibility.py",
        "models/opportunity.py",
        "features/football.py",
        "models/football_catboost.py",
        "domain/rules.py",
    ]
    return fingerprint({name: sha256((root / name).read_bytes()).hexdigest() for name in names})


def configure_review(
    store: Store,
    team_id: int,
    *,
    enabled=False,
    interval_minutes=360,
    collect=False,
    include_all=False,
    train=False,
    expected_version=0,
):
    store.get("state", team_id)
    if type(interval_minutes) is not int or not 60 <= interval_minutes <= 10080:
        raise ValueError("Review interval must be between one hour and one week")
    if train and not collect:
        raise ValueError("Refitting requires a freshly retained collection")
    version = expected_version + 1
    config = {
        "team_id": team_id,
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "collect": collect,
        "include_all": include_all,
        "train": train,
        "schedule_version": version,
    }
    store.put("review_schedule", team_id, config, expected=expected_version)
    return config


def review_inputs(store: Store, payload: dict[str, Any]) -> str:
    tick = store.get("review_tick", payload["tick_id"])
    config = store.get("review_schedule", tick["team_id"])
    store.get("state", tick["team_id"])
    if not config["enabled"] or fingerprint(config) != tick["schedule_sha256"]:
        raise Conflict("Review schedule changed or disabled")
    for decision_id, digest in tick["decision_sha256"].items():
        if fingerprint(store.get("decision_journal", decision_id)) != digest:
            raise Conflict("Frozen review journal changed")
    if tick["implementation_sha256"] != implementation_digest():
        raise Conflict("Review implementation changed; enqueue a new schedule version")
    return fingerprint({"kind": "learning_review", "tick": tick})


def enqueue_due_reviews(store: Store, now: str | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC).isoformat()
    clock = datetime.fromisoformat(now)
    if clock.tzinfo is None:
        raise ValueError("Scheduler clock requires timezone")
    results = []
    for config in store.list("review_schedule"):
        if not config["enabled"]:
            continue
        slot = int(clock.timestamp()) // (config["interval_minutes"] * 60)
        tick_id = fingerprint(
            {
                "team_id": config["team_id"],
                "schedule_version": config["schedule_version"],
                "slot": slot,
            }
        )
        try:
            tick = store.get("review_tick", tick_id)
        except KeyError:
            decisions = {
                d["decision_id"]: fingerprint(d)
                for d in store.list("decision_journal")
                if d["team_id"] == config["team_id"]
                and datetime.fromisoformat(d["frozen_at"]) <= clock
                and d["data_mode"] == "live"
            }
            tick = {
                "tick_id": tick_id,
                "team_id": config["team_id"],
                "slot": slot,
                "scheduled_for": datetime.fromtimestamp(
                    slot * config["interval_minutes"] * 60, UTC
                ).isoformat(),
                "schedule_sha256": fingerprint(config),
                "config": config,
                "implementation_sha256": implementation_digest(),
                "decision_sha256": decisions,
            }
            store.put_checked(
                "review_tick",
                tick_id,
                tick,
                lambda: None,
                same=lambda existing, new: existing["schedule_sha256"] == new["schedule_sha256"],
            )
        if tick["implementation_sha256"] != implementation_digest():
            # Preserve the old tick. A changed implementation resumes at the next
            # scheduled slot, rather than rewriting evidence or retry-spamming.
            continue
        results.append(
            Queue(store).enqueue(
                "learning_review", {"tick_id": tick_id, "team_id": config["team_id"]}
            )
        )
    return results


def score_collection_benchmarks(store: Store, provider, collection: dict[str, Any]) -> list[dict]:
    """Commit independent, fenced scoring stages before any new labels are reused.

    A scoring job remains useful even if its parent review is cancelled. Its key
    binds the collection receipt, so a later corrected capture cannot reuse an
    older completed scoring job. Targeted execution never claims unrelated work.
    """
    from fpl_app.jobs import Worker
    from fpl_app.models.training_eligibility import require_scored_collection

    events = {
        row["event"] for row in collection["labels"] if row["label_status"] == "final_revision"
    }
    queue = Queue(store)
    results = []
    for benchmark in store.list("forecast_benchmark"):
        if benchmark["event"] not in events or str(benchmark["season"]).replace(
            "-", "/"
        ) != collection["season"].replace("-", "/"):
            continue
        job = queue.enqueue(
            "forecast_benchmark_score",
            {
                "benchmark_id": benchmark["benchmark_id"],
                "collection_sha256": collection["envelope_sha256"],
            },
        )
        if job["status"] == "queued":
            Worker(queue, provider=provider).run_once(job["id"])
        finished = queue.get(job["id"])
        result = finished.get("result") or {}
        results.append(
            {
                "benchmark_id": benchmark["benchmark_id"],
                "job_id": job["id"],
                "status": result.get("status", finished["status"]),
                "revision": result.get("revision"),
            }
        )
        if finished["status"] != "succeeded" or result.get("status") != "final":
            raise ValueError("Collection benchmark scoring is incomplete; retry after recovery")
    require_scored_collection(store, collection)
    return results


def run_review(store: Store, provider, tick_id: str) -> dict[str, Any]:
    from fpl_app.learning.outcomes import collect_finalized_outcomes, event_status
    from fpl_app.models.football_catboost import train_collection_experiment
    from fpl_app.models.training import data_dir
    from fpl_app.providers.collection import collect_football

    tick = store.get("review_tick", tick_id)
    artifacts = []
    rows = []
    statuses = {}
    for decision_id in sorted(tick["decision_sha256"]):
        decision = store.get("decision_journal", decision_id)
        event = decision["event"]
        if event not in statuses:
            statuses[event] = event_status(provider, event)
        if not statuses[event]["ready"]:
            rows.append(
                {"decision_id": decision_id, "event": event, "status": "pending_finalization"}
            )
            continue
        outcome, scorecard = collect_finalized_outcomes(
            store, provider, decision_id, statuses[event]["finalization_sha256"]
        )
        revision = outcome["revision"]
        artifacts.extend(
            [
                ("learning_outcome", f"{decision_id}:{revision}", outcome),
                ("learning_scorecard", f"{decision_id}:{revision}", scorecard),
            ]
        )
        rows.append(
            {
                "decision_id": decision_id,
                "event": event,
                "status": "scored",
                "revision": revision,
                "metrics": scorecard["metrics"],
            }
        )
    collection = None
    challenger = None
    benchmark_scores = []
    config = tick["config"]
    if config["collect"]:
        collection = collect_football(
            store, provider=provider, include_all=config["include_all"], force=True
        )
    if config["train"] and collection is not None:
        import hashlib
        import json

        from fpl_app.learning.refit_cache import cached_refit, refit_identity

        bootstrap_source = next(
            s for s in collection["sources"] if s["resource"] == "bootstrap-static/"
        )
        bootstrap = json.loads(store.snapshot(bootstrap_source["id"])["raw"])
        try:
            # Scoring is independent of refit reuse: even unchanged labels need
            # an outcome receipt at least as recent as the new collection.
            benchmark_scores = score_collection_benchmarks(store, provider, collection)
            identity = refit_identity(collection, implementation_digest())
            challenger = cached_refit(store, identity)
            if challenger is None:
                path = train_collection_experiment(
                    collection,
                    data_dir() / "models" / "football_catboost",
                    "fpl-" + collection["season"].replace("/", "-"),
                    bootstrap,
                    store=store,
                )
                challenger = {
                    "artifact_directory": str(path),
                    "manifest_sha256": hashlib.sha256(
                        (path / "manifest.json").read_bytes()
                    ).hexdigest(),
                    "input_identity": identity,
                    "mode": "experimental",
                    "promoted": False,
                    "reused_unchanged_inputs": False,
                }
                artifacts.append(("learning_refit", identity, challenger))
        except (ValueError, ImportError) as exc:
            challenger = {
                "status": "unavailable_or_insufficient_data",
                "exception_type": type(exc).__name__,
                "promoted": False,
            }
    tournament = None
    if collection is not None:
        from fpl_app.learning.tournament import enqueue_tournament

        try:
            # The optional tournament enforces its own scoring guard at enqueue.
            tournament = enqueue_tournament(store, collection)
        except (ValueError, ImportError) as exc:
            tournament = {"status": "unavailable", "exception_type": type(exc).__name__}
    report = {
        "weekly_tournament": tournament,
        "review_id": tick_id,
        "team_id": tick["team_id"],
        "scheduled_for": tick["scheduled_for"],
        "decisions": rows,
        "collection_id": None if collection is None else collection["collection_id"],
        "challenger": challenger,
        "benchmark_scores": benchmark_scores,
        "football_champion": "baseline",
        "strategy_champion": "numerical_planner",
        "promotion": "retain_champions_insufficient_evidence",
        "limitations": [
            "A recurring refit is not proof of improvement",
            "Unknown execution remains unknown",
            "No private squad, finance or account action is changed",
        ],
    }
    artifacts.append(("learning_review", tick_id, report))
    return {**report, "_artifacts": artifacts}
