"""Optional Gymnasium deterministic replay environment. No Store or live writes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from fpl_app.contracts import ManagerState, Settings
from fpl_app.domain.plans import input_fingerprint, validate_plan
from fpl_app.domain.rules import (
    CHIPS,
    advance_event,
    projection_points,
    readiness,
    score_lineup,
)
from fpl_app.evaluation.provenance import replay_time
from fpl_app.evaluation.strategy import ReplayOrigin, _check_provenance, keep_policy
from fpl_app.strategy.candidates import (
    CANDIDATE_FEATURES,
    DEFAULT_K,
    apply_candidate,
    build_menu,
    candidate_matrix,
)

ENV_VERSION = "fpl-deterministic-replay-v1"
OBSERVATION_VERSION = "state-player-candidates-v1"
CONTEXT_SIZE = 14
PLAYER_FEATURES = 14
MAX_PLAYERS = 1000


@dataclass(frozen=True)
class Episode:
    episode_id: str
    initial: ManagerState
    origins: tuple[ReplayOrigin, ...]
    partition: str = "research"
    path_id: str = "synthetic"
    bootstrap_origin: ReplayOrigin | None = None


class FPLEnv(gym.Env):
    def __init__(self, episodes: list[Episode], settings: Settings, *, k: int = DEFAULT_K):
        if not episodes or not 2 <= k <= 128:
            raise ValueError("Episodes and valid candidate count required")
        self.metadata = {"render_modes": []}
        self._episodes = deepcopy(episodes)
        self.settings = settings.model_copy(deep=True)
        self.k = k
        self.action_space = spaces.Discrete(k)
        self.observation_space = spaces.Dict(
            {
                "context": spaces.Box(-np.inf, np.inf, (CONTEXT_SIZE,), np.float32),
                "players": spaces.Box(-np.inf, np.inf, (MAX_PLAYERS, PLAYER_FEATURES), np.float32),
                "candidates": spaces.Box(-np.inf, np.inf, (k, CANDIDATE_FEATURES), np.float32),
                "mask": spaces.MultiBinary(k),
            }
        )
        self._done = True

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        index = (options or {}).get("episode_index")
        if index is None:
            index = int(self.np_random.integers(len(self._episodes)))
        if type(index) is not int or not 0 <= index < len(self._episodes):
            raise ValueError("Invalid episode index")
        self._episode = deepcopy(self._episodes[index])
        if (
            not self._episode.origins
            or len(self._episode.origins) > 39 - self._episode.initial.next_event
        ):
            raise ValueError("Invalid episode length")
        self._state = self._episode.initial.model_copy(deep=True)
        self._offset = 0
        self._done = False
        return self._prepare(), self._info()

    def _prepare(self):
        origin = self._episode.origins[self._offset]
        if len(origin.players) > MAX_PLAYERS:
            raise ValueError("Universe exceeds observation schema")
        deadline, available = (
            replay_time(origin.deadline),
            replay_time(origin.information_available_at),
        )
        if available > deadline or replay_time(origin.forecasts.source_cutoff) > available:
            raise ValueError("Future origin observations")
        if self._offset and deadline <= replay_time(
            self._episode.origins[self._offset - 1].deadline
        ):
            raise ValueError("Noncontiguous episode origins")
        self._state.snapshot_id = origin.forecasts.snapshot_id
        if not readiness(self._state, origin.players)["transfers_ready"]:
            raise ValueError("Unknown or stale research finances")
        horizon = min(
            self.settings.horizon_events,
            origin.forecasts.horizon_events,
            39 - self._state.next_event,
        )
        self._local_settings = self.settings.model_copy(
            update={
                "horizon_events": horizon,
                "chip_schedule": {},
                "price_scenario": {},
                "chip_policy": "none",
            }
        )
        self._provenance = _check_provenance(
            origin, self._state.next_event, self._local_settings, keep_policy
        )
        self._menu = build_menu(
            self._state, origin.players, origin.forecasts, self._local_settings, k=self.k
        )
        matrix, mask = candidate_matrix(self._menu, self.k)
        self._mask = mask
        s = self._state
        assert s.bank_units is not None and s.free_transfers_at_event_start is not None
        assert s.transfers_made_this_event is not None and s.confirmed_hit_points is not None
        window = 1 if s.next_event <= 19 else 2
        chips = [s.chips.get(f"{c}_{window}", s.chips.get(c)) for c in sorted(CHIPS)]
        context = np.array(
            [
                s.bank_units / 1000,
                s.free_transfers_at_event_start / 5,
                s.transfers_made_this_event / 20,
                s.confirmed_hit_points / 80,
                s.next_event / 38,
                (39 - s.next_event) / 38,
                horizon / 8,
                *(-1 if c is None else float(c) for c in chips),
                window / 2,
                float(s.current_chip is not None),
                len(origin.players) / MAX_PLAYERS,
            ],
            dtype=np.float32,
        )
        tokens = np.zeros((MAX_PLAYERS, PLAYER_FEATURES), dtype=np.float32)
        owned = {p.player_id: p for p in s.picks}
        points = [
            projection_points(origin.forecasts.projections, e)
            for e in range(s.next_event, s.next_event + 8)
        ]
        for j, p in enumerate(sorted(origin.players, key=lambda p: p.player_id)):
            pick = owned.get(p.player_id)
            tokens[j] = [
                1,
                float(pick is not None),
                p.position / 4,
                p.market_price_units / 150,
                -1
                if pick is None or pick.purchase_price_units is None
                else pick.purchase_price_units / 150,
                -1 if p.availability is None else p.availability,
                *(xp.get(p.player_id, 0) / 20 for xp in points),
            ]
        return {
            "context": context,
            "players": tokens,
            "candidates": matrix,
            "mask": mask.astype(np.int8),
        }

    def _info(self):
        return {
            "episode_id": self._episode.episode_id,
            "path_id": self._episode.path_id,
            "event": self._state.next_event,
            "environment_version": ENV_VERSION,
            "observation_version": OBSERVATION_VERSION,
            "candidate_version": self._menu.version,
            "candidate_ids": [c.semantic_id for c in self._menu.candidates],
            "menu_input_fingerprint": self._menu.input_fingerprint,
            "candidate_truncated": self._menu.truncated,
            "evidence_mode": self._episode.origins[self._offset].evidence_mode,
        }

    def action_masks(self):
        if self._done:
            raise ValueError("Episode has ended; reset first")
        return self._mask.copy()

    def step(self, action):
        if self._done:
            raise ValueError("Episode has ended; reset first")
        if (
            not isinstance(action, (int, np.integer))
            or not 0 <= int(action) < self.k
            or not self._mask[int(action)]
        ):
            raise ValueError("Illegal or padded action; state unchanged")
        origin = self._episode.origins[self._offset]
        if self._menu.input_fingerprint != input_fingerprint(
            self._state, origin.players, origin.forecasts, self._local_settings
        ):
            raise ValueError("Stale candidate menu")
        candidate = self._menu.candidates[int(action)]
        errors = validate_plan(
            candidate.plan, self._state, origin.players, origin.forecasts, candidate.settings
        )
        if errors:
            raise ValueError("Invalid candidate: " + "; ".join(errors))
        week = candidate.plan.weeks[0]
        changed, _ = apply_candidate(self._state, origin.players, week["actions"], week["chip"])
        if not {p.player_id for p in changed.picks} <= origin.outcomes.keys():
            raise ValueError("Missing outcomes cannot be treated as nonappearance")
        scoring = score_lineup(
            week["lineup"], changed, origin.players, origin.outcomes, week["chip"]
        )
        reward = float(scoring["points"] - week["total_hits"])
        terminated = changed.next_event == 38
        truncated = not terminated and self._offset + 1 == len(self._episode.origins)
        info = self._info()
        info.update(
            {
                "semantic_action": candidate.semantic_id,
                "realised_net_points": reward,
                "total_hits": week["total_hits"],
                "scoring": scoring,
            }
        )
        self._state = advance_event(changed) if not terminated else changed
        self._done = terminated or truncated
        if self._done:
            # A truncated bootstrap uses a forecast-only next state, not a zero
            # value pretending the season ended. With no next origin, reuse this
            # origin's remaining frozen support or mark unsupported bootstrap.
            self._terminal_observation = self._terminal_state_observation(origin)
            info["bootstrap_forecast_supported"] = bool(
                self._episode.bootstrap_origin is not None or origin.forecasts.horizon_events > 1
            )
            return self._terminal_observation, reward, terminated, truncated, info
        self._offset += 1
        return self._prepare(), reward, False, False, info

    def _terminal_state_observation(self, origin):
        if self._state.next_event <= 38 and (
            self._episode.bootstrap_origin is not None or origin.forecasts.horizon_events > 1
        ):
            # Build a temporary, outcome-free origin for a supported continuation.
            saved = self._episode
            next_origin = deepcopy(saved.bootstrap_origin or origin)
            next_origin.outcomes = {}
            if saved.bootstrap_origin is None:
                next_origin.forecasts.horizon_events -= 1
            self._episode = Episode(
                saved.episode_id, self._state, (next_origin,), saved.partition, saved.path_id
            )
            previous = self._offset
            self._offset = 0
            try:
                return self._prepare()
            finally:
                self._episode = saved
                self._offset = previous
        # Unsupported truncation must never be used as a fitted value target.
        return {
            "context": np.zeros(CONTEXT_SIZE, np.float32),
            "players": np.zeros((MAX_PLAYERS, PLAYER_FEATURES), np.float32),
            "candidates": np.zeros((self.k, CANDIDATE_FEATURES), np.float32),
            "mask": np.zeros(self.k, np.int8),
        }
