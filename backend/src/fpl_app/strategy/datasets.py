"""Validated local replay files, explicit outcomes and immutable partition labels."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from fpl_app.contracts import ManagerState, Player, ProjectionRun
from fpl_app.domain.rules import MatchStats
from fpl_app.evaluation.strategy import ReplayOrigin


def load_episodes(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 50_000_000:
        raise ValueError("Invalid bounded episode file")
    return episodes_from_payload(json.loads(path.read_text()))


def episodes_from_payload(payload):
    from fpl_app.strategy.environment import Episode

    episodes = []
    for e in payload["episodes"]:
        origins = []
        for o in e["origins"]:
            mode = o["evidence_mode"]
            if mode not in {"synthetic_mechanics", "historical_reconstructed"}:
                raise ValueError("Research episode mode must be explicit")
            if mode != "synthetic_mechanics" and any(
                set(row) != {f.name for f in fields(MatchStats)}
                for rows in o["outcomes"].values()
                for row in rows
            ):
                raise ValueError("Missing real scoring components cannot default to zero")
            origins.append(
                ReplayOrigin(
                    deadline=o["deadline"],
                    information_available_at=o["information_available_at"],
                    players=[Player.model_validate(p) for p in o["players"]],
                    forecasts=ProjectionRun.model_validate(o["forecasts"]),
                    outcomes={
                        int(i): [MatchStats(**s) for s in rows] for i, rows in o["outcomes"].items()
                    },
                    evidence_mode=mode,
                    financial_coverage=o["financial_coverage"],
                    fitting_labels_available_at=o.get("fitting_labels_available_at"),
                )
            )
        if e["partition"] not in {"train", "validation", "test"}:
            raise ValueError("Explicit episode partition required")
        episodes.append(
            Episode(
                e["episode_id"],
                ManagerState.model_validate(e["initial"]),
                tuple(origins),
                e["partition"],
                e["path_id"],
            )
        )
    if not 1 <= len(episodes) <= 1000:
        raise ValueError("Episode count outside budget")
    return episodes
