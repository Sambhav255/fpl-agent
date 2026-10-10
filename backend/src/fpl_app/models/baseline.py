from __future__ import annotations

import math
from typing import Literal

from fpl_app.contracts import Fixture, Player, Projection, ProjectionRun
from fpl_app.features.pipeline import fingerprint, utc


def baseline_run(
    players: list[Player],
    fixtures: list[Fixture],
    snapshot_id: str,
    cutoff: str,
    data_mode: Literal["demo", "live"],
    next_event: int,
    horizon: int,
) -> ProjectionRun:
    utc(cutoff)
    if not snapshot_id or not 1 <= next_event <= 38 or not 1 <= horizon <= 8:
        raise ValueError("invalid snapshot, event or horizon")
    if len({p.player_id for p in players}) != len(players):
        raise ValueError("duplicate player")
    if len({f.fixture_id for f in fixtures}) != len(fixtures):
        raise ValueError("duplicate fixture")
    projections = []
    for p in players:
        if not math.isfinite(p.points_per_game) or p.minutes < 0 or p.appearances < 0:
            raise ValueError("invalid player statistics")
        if p.availability is not None and not 0 <= p.availability <= 1:
            raise ValueError("availability must be probability in [0,1]")
        # Official PPG is conditional on appearance; availability is applied once.
        chance = (
            p.availability
            if p.availability is not None
            else (0.0 if p.status in {"u", "s"} else 1.0)
        )
        observed_games = p.appearances if p.appearances else max(1, next_event - 1)
        conditional_minutes = (
            min(90.0, p.minutes / p.appearances)
            if p.appearances
            else (min(90.0, p.minutes / observed_games) if p.minutes else 60.0)
        )
        exposure = p.minutes + 900
        goals90 = 90 * (p.goals + 0.2) / exposure
        assists90 = 90 * (p.assists + 0.2) / exposure
        for f in fixtures:
            if (
                f.event is None
                or not next_event <= f.event < next_event + horizon
                or p.club not in (f.home_club, f.away_club)
            ):
                continue
            difficulty = f.home_difficulty if p.club == f.home_club else f.away_difficulty
            adjustment = max(
                0.65,
                min(1.35, 1 + (3 - difficulty) * 0.08 + (0.03 if p.club == f.home_club else -0.03)),
            )
            minutes = conditional_minutes * chance
            appearance = chance * (1 + conditional_minutes / 90)  # approximate minutes distribution
            goal = goals90 * minutes / 90 * {1: 10, 2: 6, 3: 5, 4: 4}[p.position] * adjustment
            assist = assists90 * minutes / 90 * 3 * adjustment
            clean = (
                min(1.0, (p.clean_sheets + 1) / (observed_games + 4))
                * chance
                * (conditional_minutes / 90)
                * {1: 4, 2: 4, 3: 1, 4: 0}[p.position]
                * adjustment
            )
            bonus = 0.25 * chance
            component_mean = appearance + goal + assist + clean + bonus
            points_average = (
                (p.points_per_game * observed_games + 2.0 * 4)
                / (observed_games + 4)
                * chance
                * adjustment
            )
            points = 0.5 * component_mean + 0.5 * points_average
            projections.append(
                Projection(
                    player_id=p.player_id,
                    fixture_id=f.fixture_id,
                    event=f.event,
                    expected_points=points,
                    expected_minutes=minutes,
                    appearance_probability=chance,
                    components={
                        "appearance": 0.5 * appearance,
                        "goals": 0.5 * goal,
                        "assists": 0.5 * assist,
                        "clean_sheets": 0.5 * clean,
                        "bonus_approximate": 0.5 * bonus,
                        "defensive_contribution": None,
                        "points_average_reference": 0.5 * points_average,
                    },
                    assumptions=[
                        "Season aggregates stand in for recent match distributions; fixture difficulty adjustment is heuristic",
                        "Bonus, minutes distribution and clean sheet eligibility approximate; defensive actions, cards, saves and concessions unavailable",
                        "Weighted component contributions sum to expected points; PPG conditional on appearance; availability applied once",
                        "Missing appearance count uses elapsed event exposure proxy"
                        if not p.appearances
                        else "Appearance count supplied",
                        "Unknown availability assumes available"
                        if p.availability is None
                        else "Snapshot availability held constant across horizon",
                    ],
                )
            )
    identity = fingerprint(
        {
            "players": [p.model_dump() for p in players],
            "fixtures": [f.model_dump() for f in fixtures],
            "snapshot": snapshot_id,
            "cutoff": cutoff,
            "mode": data_mode,
            "event": next_event,
            "horizon": horizon,
        }
    )
    return ProjectionRun(
        projection_run_id=f"baseline-{identity[:24]}",
        snapshot_id=snapshot_id,
        source_cutoff=cutoff,
        data_mode=data_mode,
        horizon_events=horizon,
        projections=projections,
        fixtures=[
            f
            for f in fixtures
            if f.event is not None and next_event <= f.event < next_event + horizon
        ],
        warnings=[
            "Labelled approximate baseline; no trained model or calibrated intervals",
            "Snapshot aggregates require provenance at cutoff; historical replay must use the feature pipeline",
        ],
    )
