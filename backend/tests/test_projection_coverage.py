import pytest

from fpl_app.contracts import Fixture, Player
from fpl_app.jobs import projection_players
from fpl_app.models.baseline import baseline_run
from fpl_app.providers import demo
from fpl_app.storage import Store


def fixture_run(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/app.sqlite")
    state = demo(store)
    data = store.get("dataset", state.snapshot_id)
    players = [Player.model_validate(p) for p in data["players"]]
    run = baseline_run(
        players,
        [Fixture.model_validate(f) for f in data["fixtures"]],
        state.snapshot_id,
        data["source_cutoff"],
        "demo",
        state.next_event,
        1,
    )
    selected = {p.player_id for p in state.picks}
    run = run.model_copy(
        update={
            "model_family": "football_catboost",
            "player_universe_ids": list(selected),
            "projections": [p for p in run.projections if p.player_id in selected],
        }
    )
    return state, data, run


def test_scoped_forecast_excludes_uncovered_transfer_candidates(tmp_path):
    state, data, run = fixture_run(tmp_path)
    assert {p.player_id for p in projection_players(state, data, run)} == set(
        run.player_universe_ids
    )


def test_missing_exposure_not_treated_as_blank(tmp_path):
    state, data, run = fixture_run(tmp_path)
    run.projections.pop()
    with pytest.raises(ValueError, match="scheduled exposures"):
        projection_players(state, data, run)


def test_owned_player_cannot_disappear_from_universe(tmp_path):
    state, data, run = fixture_run(tmp_path)
    run.player_universe_ids.pop()
    with pytest.raises(ValueError, match="every owned"):
        projection_players(state, data, run)
