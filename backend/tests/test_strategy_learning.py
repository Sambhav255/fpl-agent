from dataclasses import replace

import numpy as np
import pytest

pytest.importorskip("sb3_contrib")
pytest.importorskip("torch")

from sb3_contrib import MaskablePPO
from test_strategy_environment import episode

from fpl_app.contracts import Settings
from fpl_app.strategy.environment import FPLEnv
from fpl_app.strategy.policy import SharedCandidatePolicy
from fpl_app.strategy.training import train_challenger


def test_shared_policy_candidate_permutation_preserves_probabilities_and_value():
    env = FPLEnv([episode()], Settings(horizon_events=2))
    obs, _ = env.reset(seed=7)
    model = MaskablePPO(SharedCandidatePolicy, env, n_steps=32, batch_size=32, seed=7, device="cpu")
    perm = np.random.default_rng(7).permutation(env.k)
    altered = {k: v.copy() for k, v in obs.items()}
    altered["candidates"] = obs["candidates"][perm]
    altered["mask"] = obs["mask"][perm]
    left, _ = model.policy.obs_to_tensor(obs)
    right, _ = model.policy.obs_to_tensor(altered)
    p = model.policy.get_distribution(left).distribution.probs.detach().numpy()[0]
    q = model.policy.get_distribution(right).distribution.probs.detach().numpy()[0]
    np.testing.assert_allclose(q, p[perm], atol=1e-7)
    np.testing.assert_allclose(
        model.policy.predict_values(left).detach(),
        model.policy.predict_values(right).detach(),
        atol=1e-7,
    )
    a, _ = model.predict(obs, deterministic=True, action_masks=env.action_masks())
    b, _ = model.predict(altered, deterministic=True, action_masks=altered["mask"].astype(bool))
    assert perm[int(b)] == int(a)
    assert np.all(p[~env.action_masks()] == 0)


def test_real_five_seed_fit_save_reload_and_paired_masked_evaluation(tmp_path):
    train = [
        replace(
            episode(start=37, events=2, horizon=2, points_shift=1),
            episode_id="train",
            path_id="train-path",
            partition="train",
        )
    ]
    test = [
        replace(
            episode(start=37, events=2, horizon=2, points_shift=2),
            episode_id="test",
            path_id="test-path",
            partition="test",
        )
    ]
    meta, report = train_challenger(
        train,
        test,
        Settings(horizon_events=2, max_additional_hit_points=0),
        tmp_path / "experiment",
        timesteps=64,
        k=8,
    )
    assert len(meta["seeds"]) == 5
    assert len(report["episodes"]) == 5
    assert meta["active"] is False
    assert report["invalid_accepted_actions"] == 0
    assert report["distinct_test_paths"] == 1
    assert report["path_block_95_interval"] is None
    assert meta["fitted_value_transitions"] > 0
    assert all((tmp_path / "experiment" / f"ppo-{seed}.zip").is_file() for seed in meta["seeds"])
    assert report["promotion"] == "retain_champion_insufficient_prospective_evidence"
