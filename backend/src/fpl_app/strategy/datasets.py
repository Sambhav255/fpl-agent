"""Validated local replay files, explicit outcomes and immutable partition labels."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from fpl_app.contracts import ManagerState, Player, ProjectionRun
from fpl_app.domain.rules import MatchStats, OfficialEventPoints
from fpl_app.evaluation.strategy import ReplayOrigin


def load_episodes(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 50_000_000:
        raise ValueError("Invalid bounded episode file")
    return episodes_from_payload(json.loads(path.read_text()))


def _origin(o, *, bootstrap=False):
    mode = o["evidence_mode"]
    if mode not in {"synthetic_mechanics", "historical_reconstructed"}:
        raise ValueError("Research episode mode must be explicit")
    component = o.get("outcomes", {})
    official = o.get("official_outcomes")
    if component and official:
        raise ValueError("Choose exactly one outcome representation")
    if bootstrap and (component or official):
        raise ValueError("Bootstrap origin must remain outcome-free")
    if mode != "synthetic_mechanics" and any(
        set(row) != {f.name for f in fields(MatchStats)}
        for rows in component.values()
        for row in rows
    ):
        raise ValueError("Missing real scoring components cannot default to zero")
    if official is not None and any(
        set(row) != {f.name for f in fields(OfficialEventPoints)}
        or type(row["points"]) is not int
        or type(row["minutes"]) is not int
        or row["minutes"] < 0
        or type(row["participated"]) is not bool
        or row["minutes"] > 0
        and not row["participated"]
        for row in official.values()
    ):
        raise ValueError("Invalid official outcome coverage")
    return ReplayOrigin(
        deadline=o["deadline"],
        information_available_at=o["information_available_at"],
        players=[Player.model_validate(p) for p in o["players"]],
        forecasts=ProjectionRun.model_validate(o["forecasts"]),
        outcomes={int(i): [MatchStats(**s) for s in rows] for i, rows in component.items()},
        official_outcomes=None
        if official is None
        else {int(i): OfficialEventPoints(**r) for i, r in official.items()},
        evidence_mode=mode,
        financial_coverage=o.get("financial_coverage", "assumed_frozen_prices"),
        fitting_labels_available_at=o.get("fitting_labels_available_at"),
    )


def episodes_from_payload(payload):
    from fpl_app.strategy.environment import Episode

    episodes = []
    for e in payload["episodes"]:
        if e["partition"] not in {"train", "validation", "test"}:
            raise ValueError("Explicit episode partition required")
        episodes.append(
            Episode(
                e["episode_id"],
                ManagerState.model_validate(e["initial"]),
                tuple(_origin(o) for o in e["origins"]),
                e["partition"],
                e["path_id"],
                _origin(e["bootstrap_origin"], bootstrap=True)
                if e.get("bootstrap_origin")
                else None,
            )
        )
    if not 1 <= len(episodes) <= 1000:
        raise ValueError("Episode count outside budget")
    return episodes
