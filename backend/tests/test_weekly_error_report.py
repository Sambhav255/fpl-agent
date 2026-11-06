import copy
import json
from datetime import timedelta

import pytest
from test_post_event_review import captured_review

from fpl_app.features.pipeline import utc
from fpl_app.learning.error_report import weekly_error_report
from fpl_app.storage import fingerprint


def opportunity_fixture(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path, final=True)
    changed = copy.deepcopy(frozen)
    changed["models"]["reference"]["method_id"] = "fixed-method"
    changed["models"]["reference"]["predictions"][0].update(
        expected_minutes=60, appearance_probability=0.8, minutes_60_probability=0.6
    )
    changed["models"]["reference"]["predictions"][1].update(
        expected_minutes=20, appearance_probability=0.4, minutes_60_probability=0.2
    )
    changed["benchmark_id"] = fingerprint({k: v for k, v in changed.items() if k != "benchmark_id"})
    store.put("forecast_benchmark", changed["benchmark_id"], changed)
    return store, changed, sources


def test_source_bound_points_opportunity_and_unknown_execution(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    report = weekly_error_report(store, [frozen["benchmark_id"]], *sources)
    opportunity = report["models"]["reference"]["opportunity"]
    assert report["status"] == "final"
    assert opportunity["appearance"]["n"] == 2
    assert opportunity["appearance"]["brier"] == pytest.approx(0.1)
    assert opportunity["minutes_60"]["brier"] == pytest.approx(0.1)
    assert opportunity["minutes"]["mae"] == 25
    assert opportunity["minutes"]["bias"] == -5
    assert sum(b["n"] for b in opportunity["appearance"]["bins"]) == 2
    assert report["models"]["reference"]["points"]["full_coverage"]["mae"] == 1.25
    assert report["decisions_and_execution"]["execution_error_points"] is None
    assert report["decisions_and_execution"]["status"] == "unavailable"
    assert report["training_eligible"] is report["promotion"] is False
    assert not store.list("forecast_weekly_error_report")


def test_legacy_missing_opportunity_is_never_filled_with_zero(monkeypatch, tmp_path):
    store, frozen, sources = captured_review(monkeypatch, tmp_path)
    report = weekly_error_report(store, [frozen["benchmark_id"]], *sources)
    assert report["status"] == "provisional"
    opportunity = report["models"]["reference"]["opportunity"]
    assert opportunity["appearance"]["brier"] is None
    assert opportunity["minutes_60"]["n"] == 0
    assert opportunity["minutes"]["mae"] is None
    assert opportunity["missingness"]["appearance_missing_or_non_single_fixture"] == 2
    assert report["drift"]["reference"]["status"] == "insufficient_prior_blocks"


def test_double_event_minutes_do_not_invent_fixture_appearance_or_sixty(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    changed = copy.deepcopy(frozen)
    changed["fixtures"].append({"id": 82, "event": 9, "team_h": 1, "team_a": 2})
    changed["exposures"]["1"].append(82)
    changed["models"]["reference"]["predictions"][0].update(
        expected_minutes=120, minutes_semantics="event_total"
    )
    changed["benchmark_id"] = fingerprint({k: v for k, v in changed.items() if k != "benchmark_id"})
    store.put("forecast_benchmark", changed["benchmark_id"], changed)
    fixtures = json.loads(store.snapshot(sources[1])["raw"])
    fixtures.append({**fixtures[0], "id": 82})
    sources[1] = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    live = json.loads(store.snapshot(sources[2])["raw"])
    live["elements"][0]["stats"]["minutes"] = 150
    sources[2] = store.archive(json.dumps(live).encode(), "event/9/live/")
    report = weekly_error_report(store, [changed["benchmark_id"]], *sources)
    opportunity = report["models"]["reference"]["opportunity"]
    assert opportunity["appearance"]["n"] == opportunity["minutes_60"]["n"] == 1
    assert opportunity["minutes"]["n"] == 2
    assert opportunity["minutes"]["mae"] == 25


def rehash(report):
    report["report_id"] = fingerprint({k: v for k, v in report.items() if k != "report_id"})
    return report


def test_drift_uses_only_earlier_finalized_same_method_blocks_and_deduplicates_revisions(
    monkeypatch, tmp_path
):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    report = weekly_error_report(store, [frozen["benchmark_id"]], *sources)
    old = copy.deepcopy(report)
    old["event"] = 8
    old["reviewed_at"] = (utc(old["reviewed_at"]) - timedelta(minutes=1)).isoformat()
    old["models"]["reference"]["points"]["full_coverage"]["bias"] = 2.0
    rehash(old)
    revised = copy.deepcopy(old)
    revised["reviewed_at"] = report["reviewed_at"]
    revised["models"]["reference"]["points"]["full_coverage"]["bias"] = 1.0
    rehash(revised)
    ignored = copy.deepcopy(old)
    ignored["event"] = 7
    ignored["status"] = "provisional"
    rehash(ignored)
    result = weekly_error_report(
        store,
        [frozen["benchmark_id"]],
        *sources,
        previous_reports=[old, revised, ignored],
    )
    drift = result["drift"]["reference"]
    assert drift["prior_finalized_event_blocks"] == 1
    assert drift["event_equal_weight_mean_point_bias"] == 1
    assert drift["current_minus_prior_point_bias"] == -2.25
    assert drift["opportunity"]["appearance"]["prior_finalized_event_blocks"] == 1
    assert drift["opportunity"]["appearance"]["current_minus_prior"] == 0
    wrong = copy.deepcopy(old)
    wrong["models"]["reference"]["method_identity"] = "different"
    rehash(wrong)
    assert (
        weekly_error_report(store, [frozen["benchmark_id"]], *sources, previous_reports=[wrong])[
            "drift"
        ]["reference"]["prior_finalized_event_blocks"]
        == 0
    )


def test_mutated_previous_report_and_future_report_rejected(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    report = weekly_error_report(store, [frozen["benchmark_id"]], *sources)
    report["event"] = 10
    with pytest.raises(ValueError, match="contents changed"):
        weekly_error_report(store, [frozen["benchmark_id"]], *sources, previous_reports=[report])
    rehash(report)
    with pytest.raises(ValueError, match="Future report"):
        weekly_error_report(store, [frozen["benchmark_id"]], *sources, previous_reports=[report])


def test_execution_selected_and_unknown_remain_separate_from_confirmed(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    for decision, status in (
        ("unknown", "execution_unknown"),
        ("selected", "user_selected"),
    ):
        store.put(
            "decision_journal",
            decision,
            {
                "decision_id": decision,
                "season": frozen["season"],
                "event": 9,
                "recommended_action_id": "keep",
                "execution_status": status,
                "execution_action_id": None if status == "execution_unknown" else "move",
            },
        )
    report = weekly_error_report(store, [frozen["benchmark_id"]], *sources)
    execution = report["decisions_and_execution"]
    assert execution["frozen_decisions"] == 2
    assert execution["execution_status_counts"] == {
        "execution_unknown": 1,
        "user_selected": 1,
    }
    assert execution["selected_actions_different_from_recommendation"] == 1
    assert execution["confirmed_actions_different_from_recommendation"] == 0
    assert execution["realized_policy_gain"] is None


def test_invalid_source_bytes_rejected(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    original = store.snapshot

    def changed(identifier):
        row = original(identifier)
        if identifier == sources[2]:
            row["raw"] = b"{}"
        return row

    monkeypatch.setattr(store, "snapshot", changed)
    with pytest.raises(ValueError, match="Verified official source"):
        weekly_error_report(store, [frozen["benchmark_id"]], *sources)


def test_missing_point_target_excludes_opportunity_and_sixty_alias_is_supported(
    monkeypatch, tmp_path
):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    changed = copy.deepcopy(frozen)
    row = changed["models"]["reference"]["predictions"][0]
    row["sixty_probability"] = row.pop("minutes_60_probability")
    changed["benchmark_id"] = fingerprint({k: v for k, v in changed.items() if k != "benchmark_id"})
    store.put("forecast_benchmark", changed["benchmark_id"], changed)
    live = json.loads(store.snapshot(sources[2])["raw"])
    live["elements"][1]["stats"].pop("total_points")
    sources[2] = store.archive(json.dumps(live).encode(), "event/9/live/")
    report = weekly_error_report(store, [changed["benchmark_id"]], *sources)
    opportunity = report["models"]["reference"]["opportunity"]
    assert opportunity["minutes_60"]["n"] == 1
    assert opportunity["minutes_60"]["brier"] == pytest.approx(0.16)
    assert opportunity["missingness"]["excluded_from_verified_point_coverage"] == 1


def test_changed_schedule_cannot_enter_weekly_opportunity_diagnostics(monkeypatch, tmp_path):
    store, frozen, sources = opportunity_fixture(monkeypatch, tmp_path)
    fixtures = json.loads(store.snapshot(sources[1])["raw"])
    fixtures[0]["team_h"] = 99
    sources[1] = store.archive(json.dumps(fixtures).encode(), "fixtures/")
    with pytest.raises(ValueError, match="Schedule changed"):
        weekly_error_report(store, [frozen["benchmark_id"]], *sources)
