import pytest
from pydantic import ValidationError

from fpl_app.contracts import Pick, Player, Projection


@pytest.mark.parametrize("value", [75.5, 75.0, True, "75", -1])
def test_money_rejects_non_integer_or_negative(value):
    with pytest.raises(ValidationError):
        Pick(player_id=1, purchase_price_units=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_forecast_rejected(value):
    with pytest.raises(ValidationError):
        Projection(player_id=1, fixture_id=1, event=1, expected_points=value, expected_minutes=60)


def test_negative_points_allowed_but_probability_bounded():
    row = Projection(player_id=1, fixture_id=1, event=1, expected_points=-2, expected_minutes=0)
    assert row.expected_points == -2
    with pytest.raises(ValidationError):
        Projection(
            player_id=1,
            fixture_id=1,
            event=1,
            expected_points=2,
            expected_minutes=60,
            appearance_probability=1.1,
        )


def test_unknown_money_and_availability_remain_null():
    pick = Pick(player_id=1)
    player = Player(player_id=1, name="Example", club=1, position=1, market_price_units=45)
    assert pick.purchase_price_units is None and pick.selling_price_units is None
    assert player.availability is None
