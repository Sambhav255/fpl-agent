"""Exhaustive deterministic benchmark, deliberately bounded; never a live policy."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import comb, prod
from typing import Any

from fpl_app.contracts import ManagerState, Player, ProjectionRun, Settings
from fpl_app.domain.plans import _check_inputs, _week
from fpl_app.domain.rules import (
    RULES,
    advance_event,
    apply_transfers,
    player_map,
    readiness,
    sale_value,
)


def funding_moves(
    state: ManagerState, players: list[Player], selected: set[int]
) -> list[dict[str, int]]:
    """Pair same-position swaps and execute releases before spending (integer money)."""
    owned = {p.player_id: p for p in state.picks}
    by_id = player_map(players)
    moves: list[dict[str, int]] = []
    for position in range(1, 5):
        leaving = sorted(i for i in owned.keys() - selected if by_id[i].position == position)
        incoming = sorted(i for i in selected - owned.keys() if by_id[i].position == position)
        moves.extend({"out": o, "in": i} for o, i in zip(leaving, incoming, strict=True))
    return sorted(
        moves,
        key=lambda m: (
            by_id[m["in"]].market_price_units - sale_value(owned[m["out"]], by_id[m["out"]])
        ),
    )


@dataclass
class OracleResult:
    net_points: float
    weeks: list[dict[str, Any]]
    evaluated: int
    scope: str = (
        "exact bounded deterministic frozen-price universe; specified first-event chip only"
    )


def exact_oracle(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    max_universe: int = 22,
    max_nodes: int = 100000,
) -> OracleResult:
    _check_inputs(state, players, run, settings)
    if len(players) > max_universe or settings.horizon_events > 2:
        raise ValueError("Oracle supports only a small universe and at most two events")
    if not readiness(state, players)["transfers_ready"]:
        raise ValueError("Oracle requires confirmed finances")
    squad_count = prod(
        comb(sum(p.position == pos for p in players), count)
        for pos, count in enumerate(RULES.squad_counts, 1)
    )
    if squad_count > max_nodes:
        raise ValueError("Oracle node budget exhausted; no exact result")
    groups = [
        [
            tuple(p.player_id for p in chosen)
            for chosen in combinations([p for p in players if p.position == pos], count)
        ]
        for pos, count in enumerate(RULES.squad_counts, 1)
    ]
    squads = [{i for group in choice for i in group} for choice in product(*groups)]
    best = OracleResult(float("-inf"), [], 0)
    nodes = 0

    def visit(current: ManagerState, weeks: list[dict[str, Any]], extra: int) -> None:
        nonlocal nodes
        offset = len(weeks)
        chip = (
            (settings.chip_policy if settings.chip_policy != "none" else state.current_chip)
            if offset == 0
            else None
        )
        for selected in squads:
            nodes += 1
            if nodes > max_nodes:
                raise ValueError("Oracle node budget exhausted; no exact result")
            if not set(settings.locked_player_ids) <= selected or selected & set(
                settings.excluded_player_ids
            ):
                continue
            moves = funding_moves(current, players, selected)
            if (
                offset == 0
                and settings.max_transfers_this_event is not None
                and len(moves) > settings.max_transfers_this_event
            ):
                continue
            try:
                changed, ledger = apply_transfers(current, players, moves, chip)
                week = _week(changed, players, run, chip, ledger)
                new_extra = extra + max(
                    0, week["total_hits"] - (state.confirmed_hit_points or 0 if offset == 0 else 0)
                )
                if new_extra > settings.max_additional_hit_points:
                    continue
                path = weeks + [week]
                if len(path) == settings.horizon_events:
                    best.evaluated += 1
                    net = sum(w["net_points"] for w in path)
                    if net > best.net_points:
                        best.net_points, best.weeks = net, path
                else:
                    visit(advance_event(changed), path, new_extra)
            except ValueError as exc:
                if "budget exhausted" in str(exc):
                    raise

    visit(state.model_copy(deep=True), [], 0)
    if not best.weeks:
        raise ValueError("No legal oracle path")
    return best
