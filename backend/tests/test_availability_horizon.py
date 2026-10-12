"""Unknown future availability must not become eight weeks of confirmed absence."""

import pytest

from fpl_app.contracts import Fixture, Player
from fpl_app.models.baseline import baseline_run


def forecast(availability=0.0, status="i", appearances=7, fixtures=None):
    player = Player(
        player_id=1,
        name="Flagged",
        club=1,
        position=3,
        market_price_units=50,
        availability=availability,
        status=status,
        points_per_game=6,
        minutes=630,
        appearances=appearances,
    )
    schedule = (
        fixtures
        if fixtures is not None
        else [Fixture(fixture_id=e, event=e, home_club=1, away_club=2) for e in range(8, 16)]
    )
    return baseline_run([player], schedule, "s", "2026-10-01T10:00:00Z", "demo", 8, 8)


def test_injury_flag_is_current_only_future_is_explicit_unknown_scenario():
    run = forecast()
    current, *future = run.projections
    assert (
        current.expected_points == current.expected_minutes == current.appearance_probability == 0
    )
    assert len(future) == 7
    assert all(p.expected_points > 0 and p.expected_minutes == 90 for p in future)
    assert all(p.appearance_probability is None for p in future)
    assert all(
        any("not an appearance probability or recovery forecast" in a for a in p.assumptions)
        for p in future
    )
    assert any("Future availability unknown" in w for w in run.warnings)
    assert all(p.point_quantiles is None for p in run.projections)


@pytest.mark.parametrize("availability", [0, 0.25, 0.5, 0.75, 1, None])
def test_future_scenario_independent_of_current_probability(availability):
    run = forecast(availability)
    reference = forecast(1)
    for actual, expected in zip(run.projections[1:], reference.projections[1:], strict=True):
        assert actual.expected_points == expected.expected_points
        assert actual.expected_minutes == expected.expected_minutes
    if availability is not None:
        assert run.projections[0].expected_points == pytest.approx(
            reference.projections[0].expected_points * availability
        )


def test_future_numeric_points_are_conditional_available_not_averaged():
    run = forecast(0)
    # Match venue/difficulty so a later available-player baseline is comparable.
    later = baseline_run(
        [
            Player(
                player_id=1,
                name="A",
                club=1,
                position=3,
                market_price_units=50,
                availability=1,
                points_per_game=6,
                minutes=630,
                appearances=7,
            )
        ],
        [Fixture(fixture_id=9, event=9, home_club=1, away_club=2)],
        "s",
        "2026-10-01T10:00:00Z",
        "demo",
        9,
        1,
    )
    assert run.projections[1].expected_points == pytest.approx(later.projections[0].expected_points)
    assert sum(v for v in run.projections[1].components.values() if v is not None) == pytest.approx(
        run.projections[1].expected_points
    )


@pytest.mark.parametrize("status", ["s", "u"])
def test_status_does_not_assert_permanent_future_absence(status):
    run = forecast(None, status)
    assert run.projections[0].expected_points == 0
    assert run.projections[1].expected_points > 0
    assert run.projections[1].appearance_probability is None
    assert any(
        "Current-event status implies nonappearance" in a for a in run.projections[0].assumptions
    )


def test_blank_does_not_shift_current_flag_and_double_has_consistent_scenario():
    fixtures = [Fixture(fixture_id=i, event=9, home_club=1, away_club=2) for i in (1, 2)]
    run = forecast(fixtures=fixtures)
    assert len(run.projections) == 2
    assert all(
        p.event == 9 and p.expected_points > 0 and p.appearance_probability is None
        for p in run.projections
    )
    assert run.projections[0].expected_points == run.projections[1].expected_points


def test_missing_exposure_warning_and_policy_identity(monkeypatch):
    from fpl_app.models import baseline

    run = forecast(appearances=0)
    assert any("elapsed-event exposure proxy" in w for w in run.warnings)
    assert any("Missing appearance count" in a for a in run.projections[0].assumptions)
    assert forecast().projection_run_id == forecast().projection_run_id
    original = forecast().projection_run_id
    monkeypatch.setattr(baseline, "AVAILABILITY_POLICY_VERSION", "different-policy")
    assert forecast().projection_run_id != original


def test_flagged_future_exposes_scenario_endpoints_not_calibrated_intervals():
    run = forecast()
    for row in run.projections[1:]:
        assert row.availability_scenario_points is not None
        assert row.availability_scenario_points["nonappearance"] == 0
        assert row.availability_scenario_points["available"] == row.expected_points
        assert row.point_quantiles is None and row.appearance_probability is None
        assert any("future return UNKNOWN" in a for a in row.assumptions)
    assert any("Future injury/status return UNKNOWN" in warning for warning in run.warnings)
    assert run.projections[0].availability_scenario_points is None


def test_healthy_future_is_not_halved_and_does_not_claim_injury():
    run = forecast(1, status="a")
    assert run.projections[1].expected_points == run.projections[0].expected_points
    assert run.projections[1].expected_minutes == run.projections[0].expected_minutes
    assert run.projections[1].appearance_probability is None
    assert run.projections[1].availability_scenario_points is None
    assert not any("Future injury/status return UNKNOWN" in warning for warning in run.warnings)
