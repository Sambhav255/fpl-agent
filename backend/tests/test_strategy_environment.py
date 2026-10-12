import copy

import numpy as np
import pytest

pytest.importorskip("gymnasium")

from test_upgrade_optimisation import funding_fixture

from fpl_app.contracts import Settings
from fpl_app.domain.rules import MatchStats, advance_event, apply_transfers, score_lineup
from fpl_app.evaluation.strategy import ReplayOrigin
from fpl_app.strategy.candidates import build_menu
from fpl_app.strategy.environment import Episode, FPLEnv


def episode(events=2, start=8, horizon=2, points_shift=0):
    state, players, run = funding_fixture(horizon)
    state.next_event = start
    for p in run.projections:
        p.event += start - 8
    origins = []
    for offset in range(events):
        forecasts = run.model_copy(deep=True)
        forecasts.projection_run_id = f"run-{offset}"
        for p in forecasts.projections:
            p.event += offset
        origins.append(
            ReplayOrigin(
                deadline=f"2026-10-{10 + offset:02d}T00:00:00Z",
                information_available_at="2026-10-09T00:00:00Z",
                players=players,
                forecasts=forecasts,
                outcomes={
                    p.player_id: [
                        MatchStats(minutes=90, goals=int(p.player_id == 1) + points_shift)
                    ]
                    for p in players
                },
                evidence_mode="synthetic_mechanics",
            )
        )
    return Episode("authored", state, tuple(origins), path_id="authored-season")


def test_environment_step_matches_domain_and_never_mutates_episode():
    data = episode()
    original = copy.deepcopy(data)
    env = FPLEnv([data], Settings(horizon_events=2))
    obs, info = env.reset(seed=42)
    assert env.observation_space.contains(obs)
    assert env.action_masks()[0]
    assert len(set(info["candidate_ids"])) == len(info["candidate_ids"])
    action = 1
    item = env._menu.candidates[action]
    week = item.plan.weeks[0]
    changed, _ = apply_transfers(
        data.initial, data.origins[0].players, week["actions"], week["chip"]
    )
    scored = score_lineup(
        week["lineup"], changed, data.origins[0].players, data.origins[0].outcomes, week["chip"]
    )
    next_obs, reward, terminated, truncated, after = env.step(action)
    assert reward == scored["points"] - week["total_hits"]
    expected = advance_event(changed)
    assert env._state.bank_units == expected.bank_units
    assert env._state.free_transfers_at_event_start == expected.free_transfers_at_event_start
    assert not terminated and not truncated
    assert env.observation_space.contains(next_obs)
    assert "outcomes" not in info and "outcomes" not in after
    assert data == original


def test_future_outcome_mutation_cannot_change_current_observation_or_menu():
    left = episode()
    right = episode(points_shift=3)
    a, b = FPLEnv([left], Settings(horizon_events=2)), FPLEnv([right], Settings(horizon_events=2))
    oa, ia = a.reset(seed=7)
    ob, ib = b.reset(seed=7)
    for name in oa:
        np.testing.assert_array_equal(oa[name], ob[name])
    assert ia == ib
    assert a.step(0)[1] != b.step(0)[1]


def test_padded_action_rejected_without_state_change_and_same_seed_repeats():
    data = episode()
    data = Episode(data.episode_id, data.initial, data.origins)
    env = FPLEnv([data], Settings(horizon_events=2, locked_player_ids=list(range(1, 16))))
    a, info = env.reset(seed=9)
    before = env._state.model_dump()
    with pytest.raises(ValueError, match="padded"):
        env.step(31)
    assert env._state.model_dump() == before
    b, again = env.reset(seed=9)
    assert info == again
    for name in a:
        np.testing.assert_array_equal(a[name], b[name])


def test_natural_end_and_artificial_cutoff_are_distinct_and_bootstrap_supported():
    natural = FPLEnv([episode(events=1, start=38, horizon=1)], Settings(horizon_events=1))
    natural.reset(seed=1)
    assert natural.step(0)[2:4] == (True, False)
    cutoff = FPLEnv([episode(events=1, horizon=2)], Settings(horizon_events=2))
    cutoff.reset(seed=1)
    terminal, _reward, terminated, truncated, info = cutoff.step(0)
    assert (terminated, truncated) == (False, True)
    assert info["bootstrap_forecast_supported"]
    assert terminal["context"][4] == pytest.approx(9 / 38)
    assert terminal["mask"][0] == 1
    with pytest.raises(ValueError, match="reset"):
        cutoff.step(0)


def test_missing_coverage_and_unknown_finances_reject_without_live_writes():
    data = episode()
    data.origins[0].outcomes.pop(1)
    env = FPLEnv([data], Settings(horizon_events=2))
    env.reset(seed=1)
    original = env._state.model_dump()
    with pytest.raises(ValueError, match="Missing outcomes"):
        env.step(0)
    assert env._state.model_dump() == original
    data.initial.bank_units = None
    with pytest.raises(ValueError, match="finances"):
        FPLEnv([data], Settings(horizon_events=2)).reset()


def test_candidate_masks_deduplicate_and_bound_the_first_action():
    state, players, run = funding_fixture(2)
    menu = build_menu(
        state, players, run, Settings(horizon_events=2, max_additional_hit_points=0), k=8
    )
    assert len(menu.candidates) <= 8
    assert not menu.candidates[0].plan.weeks[0]["actions"]
    assert len({c.semantic_id for c in menu.candidates}) == len(menu.candidates)
    assert any(len(c.plan.weeks[0]["actions"]) == 2 for c in menu.candidates)
