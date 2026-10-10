import pytest
from test_rules import sample

from fpl_app.contracts import Fixture, Projection, ProjectionRun, Settings
from fpl_app.domain import recommend
from fpl_app.optimisation import validate_plan


def run_for(state, players, horizon=3):
    fixtures = [
        Fixture(fixture_id=e * 100 + c, event=e, home_club=c, away_club=100 + c)
        for e in range(state.next_event, state.next_event + horizon)
        for c in {p.club for p in players}
    ]
    forecasts = [
        Projection(
            player_id=p.player_id,
            fixture_id=e * 100 + p.club,
            event=e,
            expected_points=3 if p.player_id <= 15 else 10,
            expected_minutes=80,
        )
        for e in range(state.next_event, state.next_event + horizon)
        for p in players
    ]
    return ProjectionRun(
        projection_run_id="run",
        snapshot_id=state.snapshot_id,
        source_cutoff="2026-10-09T00:00:00Z",
        data_mode="demo",
        horizon_events=horizon,
        projections=forecasts,
        fixtures=fixtures,
    )


@pytest.mark.parametrize("horizon", [1, 2, 3, 4, 5, 6, 7, 8])
def test_full_horizon_and_independent_replay(horizon):
    state, players = sample()
    run = run_for(state, players, horizon)
    settings = Settings(horizon_events=horizon, solver_time_limit_seconds=0.4)
    recommendation = recommend(state, players, run, settings)
    assert len(recommendation.baseline_plan.weeks) == horizon
    assert not validate_plan(
        recommendation.baseline_plan, state, players, run, settings, enforce_preferences=False
    )
    for plan in recommendation.alternatives:
        assert len(plan.weeks) == horizon
        assert not validate_plan(plan, state, players, run, settings, recommendation.baseline_plan)
        assert plan.delta_to_baseline == pytest.approx(
            plan.net_points - recommendation.baseline_plan.net_points
        )
    assert recommendation.baseline_plan.solver["optimality_gap"] is None


def test_unknown_finances_keep_lineup_only():
    state, players = sample()
    state.bank_units = None
    result = recommend(state, players, run_for(state, players), Settings(horizon_events=3))
    assert not result.alternatives
    assert result.baseline_plan.solver["status"] == "lineup_only"
    assert result.baseline_plan.lineup["starters"]


def test_committed_hits_counted_once_and_tampered_plan_rejected():
    state, players = sample()
    state.free_transfers_at_event_start = 1
    state.transfers_made_this_event = 2
    state.confirmed_hit_points = 4
    run = run_for(state, players)
    settings = Settings(horizon_events=3, solver_time_limit_seconds=0.5)
    result = recommend(state, players, run, settings)
    assert result.baseline_plan.total_hits == 4
    assert result.baseline_plan.incremental_hits == 0
    for plan in result.alternatives:
        assert plan.incremental_hits == plan.total_hits - 4
    bad = result.baseline_plan.model_copy(deep=True)
    bad.weeks[0]["bank_units"] += 1
    assert validate_plan(bad, state, players, run, settings, enforce_preferences=False)
    bad = result.baseline_plan.model_copy(deep=True)
    bad.net_points += 1
    assert validate_plan(bad, state, players, run, settings, enforce_preferences=False)


def test_locks_exclusions_hits_and_highs_candidate():
    state, players = sample()
    run = run_for(state, players, 1)
    settings = Settings(
        horizon_events=1,
        locked_player_ids=[3],
        excluded_player_ids=[4],
        max_additional_hit_points=0,
        solver_time_limit_seconds=2,
    )
    result = recommend(state, players, run, settings)
    assert result.alternatives
    assert result.baseline_plan.solver["engine"] == "scipy.milp/HiGHS"
    for plan in result.alternatives:
        assert 3 in plan.weeks[0]["squad_ids"] and 4 not in plan.weeks[0]["squad_ids"]
        assert plan.incremental_hits == 0


@pytest.mark.parametrize("chip", ["wildcard", "free_hit", "bench_boost", "triple_captain"])
def test_chip_plans_and_replay(chip):
    state, players = sample()
    run = run_for(state, players, 2)
    settings = Settings(horizon_events=2, chip_policy=chip, solver_time_limit_seconds=0.6)
    result = recommend(state, players, run, settings)
    assert result.alternatives
    for plan in result.alternatives:
        assert plan.weeks[0]["chip"] == chip
        assert plan.weeks[1]["chip"] is None
        assert not validate_plan(plan, state, players, run, settings, result.baseline_plan)
        if chip == "free_hit":
            assert (
                plan.weeks[1]["squad_ids"] == [p.player_id for p in state.event_start_picks]
                or plan.weeks[1]["actions"]
            )


def test_missing_forecast_blanks_doubles_and_stale():
    state, players = sample()
    run = run_for(state, players, 2)
    settings = Settings(horizon_events=2, solver_time_limit_seconds=0.1)
    run.projections.pop()
    with pytest.raises(ValueError, match="Missing scheduled"):
        recommend(state, players, run, settings)
    run = run_for(state, players, 2)
    run.fixtures = [f for f in run.fixtures if f.event != 9]
    run.projections = [p for p in run.projections if p.event != 9]
    result = recommend(state, players, run, settings)
    assert result.baseline_plan.weeks[1]["gross_points"] == 0
    extra = Fixture(fixture_id=999, event=8, home_club=1, away_club=101)
    run.fixtures.append(extra)
    run.projections += [
        Projection(
            player_id=p.player_id, fixture_id=999, event=8, expected_points=4, expected_minutes=90
        )
        for p in players
        if p.club == 1
    ]
    assert recommend(state, players, run, settings).baseline_plan.gross_points > 0
    run.snapshot_id = "stale"
    with pytest.raises(ValueError, match="Stale"):
        recommend(state, players, run, settings)


def test_timeout_complete_incumbent_and_duplicates():
    state, players = sample()
    run = run_for(state, players, 8)
    result = recommend(
        state, players, run, Settings(horizon_events=8, solver_time_limit_seconds=0.001)
    )
    assert len(result.baseline_plan.weeks) == 8
    assert result.baseline_plan.solver["status"] == "time_limit_valid_incumbent"
    run.projections.append(run.projections[0])
    with pytest.raises(ValueError, match="Duplicate"):
        recommend(state, players, run, Settings(horizon_events=8))


def test_negative_unconditional_points_not_availability_squared():
    state, players = sample()
    run = run_for(state, players, 1)
    for p in run.projections:
        p.expected_points = -2
        p.appearance_probability = 0.1
    result = recommend(
        state, players, run, Settings(horizon_events=1, solver_time_limit_seconds=0.01)
    )
    assert result.baseline_plan.gross_points == -24


def test_terminal_no_indifferent_spending():
    state, players = sample()
    run = run_for(state, players, 2)
    for p in run.projections:
        p.expected_points = 3
    result = recommend(
        state,
        players,
        run,
        Settings(horizon_events=2, max_additional_hit_points=0, solver_time_limit_seconds=0.2),
    )
    assert result.baseline_plan.net_points == 72
    assert all(plan.net_points <= result.baseline_plan.net_points for plan in result.alternatives)


def test_chip_refund_does_not_fund_new_hits():
    state, players = sample()
    state.free_transfers_at_event_start = 1
    state.transfers_made_this_event = 2
    state.confirmed_hit_points = 4
    run = run_for(state, players, 3)
    settings = Settings(
        horizon_events=3,
        chip_policy="wildcard",
        max_additional_hit_points=0,
        solver_time_limit_seconds=0.4,
    )
    result = recommend(state, players, run, settings)
    assert result.alternatives
    assert all(all(w["total_hits"] == 0 for w in p.weeks) for p in result.alternatives)
    assert all(p.incremental_hits == -4 for p in result.alternatives)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_mutated_nonfinite_forecast_rejected(value):
    state, players = sample()
    run = run_for(state, players, 1)
    run.projections[0].expected_points = value
    with pytest.raises(ValueError, match="Nonfinite"):
        recommend(state, players, run, Settings(horizon_events=1))


def test_replay_rejects_forged_ledger_and_input_changes():
    state, players = sample()
    run = run_for(state, players, 1)
    settings = Settings(horizon_events=1, solver_time_limit_seconds=0.3)
    result = recommend(state, players, run, settings)
    assert result.alternatives
    plan = result.alternatives[0].model_copy(deep=True)
    plan.weeks[0]["actions"][0]["sale_units"] += 1
    assert validate_plan(plan, state, players, run, settings, result.baseline_plan)
    players[0].market_price_units += 1
    assert validate_plan(
        result.baseline_plan, state, players, run, settings, enforce_preferences=False
    )


def test_missing_whole_club_rows_rejected_using_frozen_fixtures():
    state, players = sample()
    run = run_for(state, players, 1)
    run.projections = [p for p in run.projections if p.player_id > 3]
    with pytest.raises(ValueError, match="Missing scheduled"):
        recommend(state, players, run, Settings(horizon_events=1))


def test_chip_unknown_restore_disables_only_chip_alternatives():
    state, players = sample()
    state.event_start_picks = None
    result = recommend(
        state,
        players,
        run_for(state, players, 1),
        Settings(horizon_events=1, chip_policy="free_hit"),
    )
    assert not result.alternatives
    assert any("event-start" in warning for warning in result.warnings)


def test_legacy_missing_schedule_disclosed():
    state, players = sample()
    run = run_for(state, players, 1)
    run.fixtures = []
    result = recommend(
        state, players, run, Settings(horizon_events=1, solver_time_limit_seconds=0.01)
    )
    assert any("Legacy run" in warning for warning in result.warnings)


@pytest.mark.parametrize("entry_point", ["domain", "optimisation"])
def test_explicit_lineup_mode_preserves_input_and_skips_solver(monkeypatch, entry_point):
    from fpl_app import domain, optimisation
    from fpl_app.optimisation import input_fingerprint, planner

    def fail_solver(*args, **kwargs):
        raise AssertionError("Lineup mode must not call the transfer solver")

    monkeypatch.setattr(planner, "_highs_candidate", fail_solver)
    state, players = sample()
    original = state.model_dump()
    run = run_for(state, players, 3)
    settings = Settings(horizon_events=3, chip_policy="wildcard")
    entry = domain.recommend if entry_point == "domain" else optimisation.recommend
    result = entry(state, players, run, settings, lineup_only=True)
    assert not result.alternatives
    assert result.baseline_plan.solver["status"] == "lineup_only"
    assert result.baseline_plan.solver["net_points_status"] == "available"
    assert "engine" not in result.baseline_plan.solver
    assert result.baseline_plan.input_fingerprint == input_fingerprint(
        state, players, run, settings
    )
    assert state.model_dump() == original
    assert len(result.baseline_plan.weeks) == 3
    assert all(not week["actions"] and week["chip"] is None for week in result.baseline_plan.weeks)


def test_unknown_committed_hits_saved_plan_retains_unavailable_net_marker():
    from fpl_app.contracts import Plan
    from fpl_app.optimisation import input_fingerprint

    state, players = sample()
    state.confirmed_hit_points = None
    state.bank_units = None
    original = state.model_dump()
    run = run_for(state, players, 2)
    settings = Settings(horizon_events=2)
    result = recommend(state, players, run, settings, lineup_only=True)
    saved = Plan.model_validate_json(result.baseline_plan.model_dump_json())
    assert saved.solver["status"] == "lineup_only"
    assert saved.solver["net_points_status"] == "unavailable_unknown_committed_hits"
    assert any("Net points and delta are unavailable" in a for a in saved.assumptions)
    assert any("Financial state unconfirmed" in a for a in saved.assumptions)
    assert any("Committed hits unknown" in w for w in result.warnings)
    assert saved.input_fingerprint == input_fingerprint(state, players, run, settings)
    assert state.model_dump() == original
    assert not result.alternatives


def test_implicit_financial_fallback_also_marks_unknown_net():
    state, players = sample()
    state.confirmed_hit_points = None
    result = recommend(state, players, run_for(state, players, 1), Settings(horizon_events=1))
    assert result.baseline_plan.solver["net_points_status"] == "unavailable_unknown_committed_hits"
    assert any(
        "Net points and delta are unavailable" in a for a in result.baseline_plan.assumptions
    )


@pytest.mark.parametrize("fault", ["consecutive", "missing_restore"])
def test_active_free_hit_keep_cannot_bypass_chip_validation(fault):
    state, players = sample()
    state.current_chip = "free_hit"
    state.persistent_picks = [p.model_copy(deep=True) for p in state.picks]
    if fault == "consecutive":
        state.previous_free_hit_event = state.next_event - 1
    else:
        state.persistent_picks = None
    with pytest.raises(ValueError, match="Free Hit"):
        recommend(
            state, players, run_for(state, players, 1), Settings(horizon_events=1), lineup_only=True
        )


def test_replay_rejects_invalid_active_chip_even_without_moves():
    state, players = sample()
    state.current_chip = "free_hit"
    state.persistent_picks = [p.model_copy(deep=True) for p in state.picks]
    run = run_for(state, players, 1)
    settings = Settings(horizon_events=1)
    plan = recommend(state, players, run, settings, lineup_only=True).baseline_plan
    state.previous_free_hit_event = state.next_event - 1
    assert any(
        "Free Hit" in error
        for error in validate_plan(plan, state, players, run, settings, enforce_preferences=False)
    )
