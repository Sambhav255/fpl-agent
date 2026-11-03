import copy
from datetime import UTC, datetime, timedelta

import pytest

from fpl_app.evaluation.selection import (
    SelectionProtocol,
    make_selection_plan,
    score_selection_plan,
    selection_evidence,
)
from fpl_app.storage import fingerprint


def plan_fixture(monkeypatch, *, minutes=None):
    now = datetime.now(UTC)
    cutoff = (now - timedelta(days=1)).isoformat()
    body = {
        "season": "2026/27",
        "event": 10,
        "deadline": (now + timedelta(days=1)).isoformat(),
        "published_at": cutoff,
        "models": {
            "baseline": {
                "predictions": [
                    {"player_id": p, "expected_points": v}
                    for p, v in ((1, 4.0), (2, 3.0), (3, -1.0))
                ]
            },
            "challenger": {
                "predictions": [
                    {"player_id": p, "expected_points": v}
                    for p, v in ((1, 3.0), (2, 4.0), (3, -2.0))
                ]
            },
        },
    }
    benchmark = {**body, "benchmark_id": fingerprint(body)}
    eligibility = [
        {
            "player_id": p,
            "position": 3,
            "prior_mean_minutes": (minutes or {}).get(p, 90.0),
            "decision_cutoff": cutoff,
        }
        for p in (1, 2, 3)
    ]
    source = {"available_at": cutoff, "sha256": "a" * 64}
    plan = make_selection_plan(
        [benchmark],
        eligibility,
        source,
        comparator="baseline",
        protocol=SelectionProtocol(position_top_k=2),
        study_id="study",
        method_regime="fixed-method",
        challenger="challenger",
    )
    return plan, benchmark, eligibility, source


def refs(time="2026-11-08T00:00:00Z"):
    return [{"resource": "event/10/live/", "available_at": time, "payload_sha256": "outcome"}]


def rehash(report):
    report["revision"] = fingerprint(
        {k: v for k, v in report.items() if k not in ("revision", "scored_at")}
    )
    return report


def test_selection_fixed_before_outcomes_and_missing_selected_player_never_backfilled(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch)
    outcomes = {2: {"total_points": 14}, 3: {"total_points": 20}}
    report = score_selection_plan(plan, outcomes, finalized=True, source_refs=refs())
    score = report["selections"]["baseline"]["attacking_top1"]
    assert score["selected_ids"] == [1]
    assert score["selected_sum"] is None
    assert score["missing_selected_ids"] == [1]
    assert report["status"] == "incomplete_outcome_coverage"
    assert report["selections"]["challenger"]["attacking_top1"]["selected_sum"] == 14
    outcomes[1] = {"total_points": -3}
    corrected = score_selection_plan(plan, outcomes, finalized=True, source_refs=refs())
    assert corrected["selections"]["baseline"]["attacking_top1"]["selected_ids"] == [1]
    assert corrected["selections"]["baseline"]["attacking_top1"]["selected_sum"] == -3
    assert corrected["selections"]["baseline"]["attacking_top1"]["selection_regret"] == 23


def test_eligibility_uses_prior_minutes_and_empty_position_pools_stay_explicit(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch, minutes={1: 0.0, 3: None})
    assert plan["eligible_ids"] == [2]
    report = score_selection_plan(
        plan, {2: {"total_points": -2}}, finalized=True, source_refs=refs()
    )
    scores = report["selections"]["baseline"]
    assert scores["position_GK"]["status"] == "empty_pool"
    assert scores["position_GK"]["selected_mean"] is None
    assert scores["position_MID"]["effective_k"] == 1
    assert scores["position_MID"]["selected_sum"] == -2
    assert scores["position_MID"]["selection_regret"] == 0


def test_tied_predictions_use_id_and_not_input_order(monkeypatch):
    _, benchmark, eligibility, source = plan_fixture(monkeypatch)
    for model in benchmark["models"].values():
        for row in model["predictions"]:
            row["expected_points"] = -1.0
        model["predictions"].reverse()
    benchmark["benchmark_id"] = fingerprint(
        {k: v for k, v in benchmark.items() if k != "benchmark_id"}
    )
    plan = make_selection_plan(
        [benchmark], list(reversed(eligibility)), source, comparator="baseline"
    )
    assert plan["selections"]["baseline"]["attacking_top1"]["selected_ids"] == [1]
    assert plan["selections"]["baseline"]["position_MID"]["selected_ids"] == [1, 2, 3]


def test_late_selection_is_retrospective_and_plan_mutation_rejected(monkeypatch):
    _, benchmark, eligibility, source = plan_fixture(monkeypatch)
    monkeypatch.setattr(
        "fpl_app.evaluation.selection.utcnow",
        lambda: (datetime.now(UTC) + timedelta(days=2)).isoformat(),
    )
    plan = make_selection_plan([benchmark], eligibility, source, comparator="baseline")
    assert plan["evidence_mode"] == "retrospective_frozen_forecast_diagnostic"
    plan["selections"]["baseline"]["attacking_top1"]["selected_ids"] = [2]
    with pytest.raises(ValueError, match="changed"):
        score_selection_plan(plan, {}, finalized=False, source_refs=refs())


def test_late_eligibility_and_mixed_events_fail(monkeypatch):
    _, benchmark, eligibility, source = plan_fixture(monkeypatch)
    source["available_at"] = benchmark["deadline"]
    with pytest.raises(ValueError, match="Eligibility source"):
        make_selection_plan([benchmark], eligibility, source, comparator="baseline")
    other = copy.deepcopy(benchmark)
    other["event"] = 11
    with pytest.raises(ValueError, match="Same-season/event"):
        make_selection_plan([benchmark, other], eligibility, source, comparator="baseline")


def test_duplicate_captures_count_as_one_week_and_provisional_events_excluded(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch)
    first = score_selection_plan(
        plan,
        {1: {"total_points": 0}, 2: {"total_points": 10}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs(),
    )
    correction = score_selection_plan(
        plan,
        {1: {"total_points": 0}, 2: {"total_points": -1}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs("2026-11-09T00:00:00Z"),
    )
    provisional = rehash({**first, "status": "provisional", "event": 11})
    evidence = selection_evidence(
        [first, correction, provisional],
        study_id="study",
        method_regime="fixed-method",
        challenger="challenger",
    )
    assert evidence["distinct_events"] == 1
    assert evidence["mean_selection_delta"] == -1
    assert evidence["status"] == "insufficient_evidence"
    assert evidence["descriptive_event_bootstrap_95_interval"] is None
    assert evidence["automatic_activation"] is False


def test_multiple_origins_of_same_week_cannot_supply_a_best_capture(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch)
    first = score_selection_plan(
        plan,
        {1: {"total_points": 1}, 2: {"total_points": 2}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs(),
    )
    other = rehash({**first, "plan_id": "another-origin", "revision": "other"})
    evidence = selection_evidence(
        [first, other], study_id="study", method_regime="fixed-method", challenger="challenger"
    )
    assert evidence["distinct_events"] == 0
    assert evidence["exclusions"]["ambiguous_canonical_plan"] == 1


def test_real_worker_attaches_registered_selection_review(monkeypatch, tmp_path):
    from test_post_event_review import captured_review

    from fpl_app.jobs import Queue, Worker
    from fpl_app.learning.selection_review import register_plan

    store, benchmark, source_ids = captured_review(monkeypatch, tmp_path, final=True)
    # Authored benchmark fixtures lack a 670-player immutable collection. Isolate
    # worker publication here; separate tests exercise collection binding.
    monkeypatch.setattr("fpl_app.learning.selection_review.verify_eligibility", lambda *_: None)
    cutoff = benchmark["published_at"]
    rows = [
        {"player_id": p, "position": 4, "prior_mean_minutes": 90.0, "decision_cutoff": cutoff}
        for p in (1, 2)
    ]
    plan = make_selection_plan([benchmark], rows, {"available_at": cutoff}, comparator="reference")
    register_plan(store, plan)
    sources = {store.snapshot(i)["resource"]: store.snapshot(i) for i in source_ids}

    class Retained:
        def fetch(self, resource, force=False):
            return sources[resource]

    queue = Queue(store)
    job = queue.enqueue(
        "forecast_benchmark_score", {"benchmark_id": benchmark["benchmark_id"], "check_slot": 1}
    )
    assert Worker(queue, provider=Retained()).run_once()
    assert queue.get(job["id"])["status"] == "succeeded"
    reports = store.list("forecast_selection_review")
    assert len(reports) == 1
    assert reports[0]["status"] == "final"
    assert reports[0]["evidence_mode"] == "retrospective_frozen_forecast_diagnostic"


def test_receipt_prevents_backdated_prospective_registration(monkeypatch, tmp_path):
    from test_post_event_review import captured_review

    from fpl_app.learning.selection_review import register_plan

    store, benchmark, _ = captured_review(monkeypatch, tmp_path, final=True)
    cutoff = benchmark["published_at"]
    rows = [
        {"player_id": p, "position": 4, "prior_mean_minutes": 90.0, "decision_cutoff": cutoff}
        for p in (1, 2)
    ]
    plan = make_selection_plan([benchmark], rows, {"available_at": cutoff}, comparator="reference")
    plan.update(evidence_mode="prospective_selection", registered_at=cutoff)
    plan["plan_id"] = fingerprint({k: v for k, v in plan.items() if k != "plan_id"})
    monkeypatch.setattr("fpl_app.learning.selection_review.verify_eligibility", lambda *_: None)
    with pytest.raises(ValueError, match="backdate"):
        register_plan(store, plan)
    assert not store.list("forecast_selection_plan")


def test_fresh_bootstrap_cannot_supersede_newer_live_outcome(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch)
    old = score_selection_plan(
        plan,
        {1: {"total_points": 0}, 2: {"total_points": 10}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs()
        + [{"resource": "bootstrap-static/", "available_at": "2026-11-10T00:00:00Z"}],
    )
    new = score_selection_plan(
        plan,
        {1: {"total_points": 0}, 2: {"total_points": -1}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs("2026-11-09T00:00:00Z"),
    )
    for reports in ([old, new], [new, old]):
        result = selection_evidence(
            reports, study_id="study", method_regime="fixed-method", challenger="challenger"
        )
        assert result["mean_selection_delta"] == -1


def test_forged_report_is_excluded(monkeypatch):
    plan, *_ = plan_fixture(monkeypatch)
    report = score_selection_plan(
        plan,
        {1: {"total_points": 1}, 2: {"total_points": 2}, 3: {"total_points": 0}},
        finalized=True,
        source_refs=refs(),
    )
    report["selections"]["challenger"]["attacking_top1"]["paired_selected_sum_delta"] = 100
    result = selection_evidence(
        [report], study_id="study", method_regime="fixed-method", challenger="challenger"
    )
    assert result["distinct_events"] == 0
    assert result["exclusions"]["invalid_report_identity"] == 1


def test_collection_eligibility_rejects_wrong_event_and_excludes_late_current_labels(monkeypatch):
    from fpl_app.learning.selection_review import collection_eligibility

    collection = {
        "collection_id": "source",
        "envelope_sha256": "a" * 64,
        "season": "2026/27",
        "captured_at": "2026-11-03T00:00:00Z",
        "available_at": "2026-11-02T23:00:00Z",
        "event_evidence": [
            {"event": 9, "actual_deadline": "2026-10-31T11:00:00Z"},
            {"event": 10, "actual_deadline": "2026-11-06T18:30:00Z"},
        ],
        "player_mappings": [{"provider_player_id": 1, "position": 4}],
        "schedule_exposures": [{"provider_player_id": 1, "event": 10}],
        "labels": [
            {
                "provider_player_id": 1,
                "label_status": status,
                "event": event,
                "available_at": at,
                "minutes": minutes,
                "statistics": {"kickoff_time": "2026-10-24T12:00:00Z"},
            }
            for status, event, at, minutes in [
                ("final_revision", 8, "2026-11-02T23:00:00Z", 90),
                ("preliminary", 9, "2026-11-02T23:00:00Z", 0),
                ("final_revision", 8, "2026-11-04T00:00:00Z", 0),
                ("final_revision", 10, "2026-11-02T23:00:00Z", 0),
            ]
        ],
    }
    monkeypatch.setattr("fpl_app.learning.selection_review.load_collection", lambda *_: collection)
    rows, source = collection_eligibility(None, "source", 10)
    assert rows[0]["prior_mean_minutes"] == 90
    assert source["collection_sha256"] == "a" * 64
    with pytest.raises(ValueError, match="different forecast event"):
        collection_eligibility(None, "source", 9)
