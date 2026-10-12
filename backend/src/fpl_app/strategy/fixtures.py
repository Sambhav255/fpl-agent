"""Authored synthetic season endings for mechanics smoke; no live/model evidence."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal, cast

import numpy as np

from fpl_app.contracts import ManagerState, Pick, Player, Projection, ProjectionRun
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.strategy import ReplayOrigin
from fpl_app.strategy.environment import Episode


def synthetic_episode(seed: int, partition: str) -> Episode:
    rng = np.random.default_rng(seed)
    positions = [1] * 2 + [2] * 5 + [3] * 5 + [4] * 3 + [1, 3, 3]
    players = [
        Player(
            player_id=i + 1,
            name=f"Synthetic player {i + 1}",
            club=i // 3 + 1,
            position=cast(Literal[1, 2, 3, 4], pos),
            market_price_units=50,
        )
        for i, pos in enumerate(positions)
    ]
    picks = [
        Pick(player_id=p.player_id, position=i + 1, purchase_price_units=50)
        for i, p in enumerate(players[:15])
    ]
    state = ManagerState(
        team_id=1,
        next_event=37,
        snapshot_id="synthetic-37",
        bank_units=20,
        free_transfers_at_event_start=2,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        current_chip_confirmed=True,
        picks=picks,
        event_start_picks=picks,
        event_start_bank_units=20,
        chips={"triple_captain_2": True, "bench_boost_2": True},
    )
    origins = []
    for event in (37, 38):
        projections = [
            Projection(
                player_id=p.player_id,
                fixture_id=e * 100 + p.club,
                event=e,
                expected_points=3 + (p.player_id % 5) * 0.7,
                expected_minutes=75,
                appearance_probability=0.9,
            )
            for e in range(event, 39)
            for p in players
        ]
        run = ProjectionRun(
            projection_run_id=f"synthetic-{event}",
            snapshot_id=f"synthetic-{event}",
            source_cutoff=f"2027-05-{event - 20:02d}T00:00:00Z",
            data_mode="demo",
            horizon_events=39 - event,
            projections=projections,
        )
        outcomes = {
            p.player_id: [
                MatchStats(
                    minutes=90 if rng.random() < 0.9 else 0,
                    goals=int(rng.poisson(0.3)),
                    goals_conceded_on_pitch=int(rng.poisson(1.3)),
                )
            ]
            for p in players
        }
        # Nonappearance cannot score impossible authored goals.
        outcomes = {
            i: [replace(rows[0], goals=0) if rows[0].minutes == 0 else rows[0]]
            for i, rows in outcomes.items()
        }
        origins.append(
            ReplayOrigin(
                deadline=f"2027-05-{event - 19:02d}T00:00:00Z",
                information_available_at=run.source_cutoff,
                players=players,
                forecasts=run,
                outcomes=outcomes,
                evidence_mode="synthetic_mechanics",
            )
        )
    return Episode(f"{partition}-{seed}", state, tuple(origins), partition, f"authored-path-{seed}")
