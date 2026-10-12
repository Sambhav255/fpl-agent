"""Financial-state dynamic programming over a declared bounded squad universe.

Unlike fixed-ownership candidates, every edge buys/sells at that event's prices,
keeps acquisition basis and replays chip inventory. Exhaustion certifies the
specified deterministic universe only. Budget exhaustion never claims optimality.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations, product
from math import comb, prod
from time import monotonic
from typing import Any

from fpl_app.contracts import ManagerState, Player, ProjectionRun, Settings
from fpl_app.domain.plans import _check_inputs, _week, allowed_chips, event_players
from fpl_app.domain.rules import RULES, advance_event, apply_transfers, readiness, validate_chip
from fpl_app.optimisation.oracle import funding_moves


@dataclass
class SequenceResult:
    weeks: list[dict[str, Any]]
    net_points: float
    evaluated_edges: int
    complete: bool
    status: str
    search_scope: str = "all_declared_squads"


def bounded_squads(
    current: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    deadline: float,
    offset: int,
) -> Iterator[set[int]]:
    """Lazy roll/one/two-replacement edges over the entire supplied catalogue.

    The two-replacement cap is a search restriction, including on chip weeks.
    Ranking uses unconditional forecast means only; legality/finances are checked
    by the existing transition engine. No Cartesian full-squad materialization.
    """
    owned = {pick.player_id for pick in current.picks}
    locks, exclusions = set(settings.locked_player_ids), set(settings.excluded_player_ids)
    by_id = {player.player_id: player for player in players}
    value = dict.fromkeys(by_id, 0.0)
    for row in run.projections:
        if row.player_id in value and row.event >= current.next_event:
            value[row.player_id] += row.expected_points
    if locks <= owned and not owned & exclusions:
        yield owned
    maximum = 2
    if offset == 0 and settings.max_transfers_this_event is not None:
        maximum = min(maximum, settings.max_transfers_this_event)
    outgoing = sorted(owned - locks, key=lambda i: (value[i], i))
    incoming = {
        pos: sorted(
            [
                p.player_id
                for p in players
                if p.position == pos and p.player_id not in owned | exclusions
            ],
            key=lambda i: (-value[i], by_id[i].market_price_units, i),
        )
        for pos in range(1, 5)
    }
    for number in range(1, maximum + 1):
        for sold in combinations(outgoing, number):
            counts = {pos: sum(by_id[i].position == pos for i in sold) for pos in range(1, 5)}
            positions = [pos for pos, n in counts.items() if n]
            # Keep same-position pairs lazy; product pools only single-player
            # lists when the two outgoing positions differ.
            bought_sets = (
                ((group,) for group in combinations(incoming[positions[0]], number))
                if len(positions) == 1
                else product(*(combinations(incoming[pos], 1) for pos in positions))
            )
            for bought in bought_sets:
                if monotonic() >= deadline:
                    return
                squad = (owned - set(sold)) | {i for group in bought for i in group}
                if locks <= squad and not squad & exclusions:
                    yield squad


def state_key(state: ManagerState, hits: int) -> tuple[Any, ...]:
    def picks_key(picks):
        return tuple(
            sorted(
                (
                    p.player_id,
                    p.purchase_price_units,
                    p.selling_price_units,
                    p.selling_price_market_units,
                    p.selling_price_provenance,
                )
                for p in picks
            )
        )

    return (
        state.next_event,
        picks_key(state.picks),
        state.bank_units,
        state.free_transfers_at_event_start,
        state.transfers_made_this_event,
        state.confirmed_hit_points,
        tuple(sorted(state.chips.items())),
        state.current_chip,
        state.previous_free_hit_event,
        picks_key(state.persistent_picks or []),
        picks_key(state.event_start_picks or []),
        state.event_start_bank_units,
        hits,
    )


def solve_sequence(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    max_edges: int = 100_000,
) -> SequenceResult:
    _check_inputs(state, players, run, settings)
    if not readiness(state, players)["transfers_ready"]:
        raise ValueError("Sequence search requires confirmed finances")
    count = prod(
        comb(sum(p.position == pos for p in players), n)
        for pos, n in enumerate(RULES.squad_counts, 1)
    )
    restricted = count > max_edges
    groups = (
        []
        if restricted
        else [
            [
                tuple(p.player_id for p in chosen)
                for chosen in combinations([p for p in players if p.position == pos], n)
            ]
            for pos, n in enumerate(RULES.squad_counts, 1)
        ]
    )
    squads = (
        []
        if restricted
        else [{i for group in choice for i in group} for choice in product(*groups)]
    )
    locks, exclusions = set(settings.locked_player_ids), set(settings.excluded_player_ids)
    squads = [s for s in squads if locks <= s and not s & exclusions]
    deadline = monotonic() + settings.solver_time_limit_seconds
    evaluated = 0
    complete = not restricted
    best: SequenceResult = SequenceResult([], float("-inf"), 0, False, "no_legal_path")
    # DFS with exact dominance on full financial/chip states. Explore roll first
    # so a complete incumbent exists before the expensive alternatives.
    seen: dict[tuple[Any, ...], float] = {}

    def visit(current: ManagerState, weeks: list[dict[str, Any]], net: float, hits: int):
        nonlocal evaluated, complete, best
        offset = len(weeks)
        if offset == settings.horizon_events:
            if net > best.net_points:
                best = SequenceResult(weeks, net, evaluated, False, "valid_incumbent")
            return
        if evaluated >= max_edges or monotonic() >= deadline:
            complete = False
            return
        key = state_key(current, hits)
        if seen.get(key, float("-inf")) >= net:
            return
        seen[key] = net
        catalogue = event_players(players, settings, current.next_event)
        owned = {p.player_id for p in current.picks}
        for chip in allowed_chips(current, settings, offset):
            if validate_chip(current, chip):
                continue
            choices = (
                bounded_squads(current, catalogue, run, settings, deadline, offset)
                if restricted
                else iter(sorted(squads, key=lambda s: (len(s - owned), tuple(sorted(s)))))
            )
            for squad in choices:
                if evaluated >= max_edges or monotonic() >= deadline:
                    complete = False
                    return
                evaluated += 1
                try:
                    moves = funding_moves(current, catalogue, squad)
                    if (
                        offset == 0
                        and settings.max_transfers_this_event is not None
                        and len(moves) > settings.max_transfers_this_event
                    ):
                        continue
                    changed, ledger = apply_transfers(current, catalogue, moves, chip)
                    week = _week(changed, catalogue, run, chip, ledger)
                    extra = hits + max(
                        0,
                        week["total_hits"]
                        - ((state.confirmed_hit_points or 0) if offset == 0 else 0),
                    )
                    if extra > settings.max_additional_hit_points:
                        continue
                    next_state = (
                        advance_event(changed) if offset + 1 < settings.horizon_events else changed
                    )
                    visit(next_state, weeks + [week], net + week["net_points"], extra)
                except ValueError:
                    continue

    visit(state.model_copy(deep=True), [], 0.0, 0)
    best.evaluated_edges = evaluated
    best.complete = complete
    if restricted:
        best.search_scope = "at_most_two_replacements_per_event_including_chips"
        best.status = "bounded_no_incumbent"
    if best.weeks:
        best.status = (
            "bounded_catalogue_incumbent"
            if restricted
            else "optimal_declared_universe"
            if complete
            else "budget_valid_incumbent"
        )
    return best
