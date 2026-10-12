"""Shared candidate scorer for real MaskablePPO, imported only by RL jobs."""

from __future__ import annotations

from typing import Any

import torch
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from torch import nn


def shared_inputs(obs):
    players = obs["players"].float()
    present = players[:, :, :1]
    pooled = (players * present).sum(dim=1) / present.sum(dim=1).clamp(min=1)
    context = torch.cat([obs["context"].float(), pooled], dim=1)
    candidates = obs["candidates"].float()
    mask = obs["mask"].float().unsqueeze(-1)
    pooled_candidates = (candidates * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
    state = torch.cat([context, pooled_candidates], dim=1)
    paired = torch.cat(
        [context.unsqueeze(1).expand(-1, candidates.shape[1], -1), candidates], dim=2
    )
    return paired, state


class SharedCandidatePolicy(MaskableActorCriticPolicy):
    """Each slot uses identical weights; masked pooling makes value invariant."""

    def _build(self, lr_schedule):
        # Base policy constructs spaces/distribution/extractor; no fixed-slot
        # action weights or learned player-ID embeddings are used.
        from gymnasium import spaces

        assert isinstance(self.observation_space, spaces.Dict)
        context_shape = self.observation_space["context"].shape
        player_shape = self.observation_space["players"].shape
        candidate_shape = self.observation_space["candidates"].shape
        assert (
            context_shape is not None and player_shape is not None and candidate_shape is not None
        )
        width = context_shape[0] + player_shape[1] + candidate_shape[1]
        self.action_net = nn.Sequential(
            nn.Linear(width, 64), nn.Tanh(), nn.Linear(64, 32), nn.Tanh(), nn.Linear(32, 1)
        )
        self.value_net = nn.Sequential(  # type: ignore[assignment]
            nn.Linear(width, 64), nn.Tanh(), nn.Linear(64, 1)
        )
        self.optimizer = self.optimizer_class(
            self.parameters(),
            lr=lr_schedule(1),  # type: ignore[call-arg]
            **self.optimizer_kwargs,
        )

    def _outputs(self, obs):
        paired, state = shared_inputs(obs)
        return self.action_net(paired).squeeze(-1), self.value_net(state)

    def get_distribution(self, obs, action_masks=None):
        logits, _ = self._outputs(obs)
        distribution = self.action_dist.proba_distribution(action_logits=logits)
        distribution.apply_masking(
            obs["mask"].detach().cpu().numpy().astype(bool)
            if action_masks is None
            else action_masks
        )
        return distribution

    def forward(self, obs, deterministic=False, action_masks=None):
        _, values = self._outputs(obs)
        distribution = self.get_distribution(obs, action_masks)
        actions = distribution.get_actions(deterministic=deterministic)
        return actions, values, distribution.log_prob(actions)

    def evaluate_actions(self, obs, actions, action_masks=None):
        _, values = self._outputs(obs)
        distribution = self.get_distribution(obs, action_masks)
        return values, distribution.log_prob(actions), distribution.entropy()

    def predict_values(self, obs):
        return self._outputs(obs)[1]

    def _get_constructor_parameters(self) -> dict[str, Any]:
        # Base constructor metadata is sufficient; all schema dimensions are
        # read from the frozen observation space when the model is reloaded.
        return super()._get_constructor_parameters()
