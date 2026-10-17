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
from fpl_app.domain.rules import (
    RULES,
    advance_event,
    apply_transfers,
    readiness,
    sale_value,
    validate_chip,
)
from fpl_app.optimisation.chip_candidates import complete_chip_squads
from fpl_app.optimisation.oracle import funding_moves


@dataclass
class SequenceResult:
    weeks: list[dict[str, Any]]
    net_points: float
    evaluated_edges: int
    complete: bool
    status: str
    search_scope: str = "all_declared_squads"
    root_actions_considered: int = 0
    root_actions_seeded: int = 0
    incumbent_source: str = "none"
    elapsed_seconds: float = 0.0


def _root_seed_squads(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
) -> Iterator[set[int]]:
    """Prioritise varied immediate singles and funding pairs before deep search.

    This is a bounded incumbent menu, not a claim that these are all legal roots.
    The normal catalogue remains the source of exhaustive small-universe search.
    """
    owned = {pick.player_id for pick in state.picks}
    locks, exclusions = set(settings.locked_player_ids), set(settings.excluded_player_ids)
    by_id = {player.player_id: player for player in players}
    by_pick = {pick.player_id: pick for pick in state.picks}
    current = dict.fromkeys(by_id, 0.0)
    future = dict.fromkeys(by_id, 0.0)
    for row in run.projections:
        if (
            row.player_id in by_id
            and state.next_event <= row.event < state.next_event + settings.horizon_events
        ):
            target = current if row.event == state.next_event else future
            target[row.player_id] += row.expected_points
    swaps: list[tuple[float, int, int, int]] = []
    for outgoing in owned - locks:
        old = by_id[outgoing]
        try:
            sale = sale_value(by_pick[outgoing], old)
        except ValueError:
            continue
        for incoming in players:
            if incoming.position != old.position or incoming.player_id in owned | exclusions:
                continue
            gain = (
                2 * (current[incoming.player_id] - current[outgoing])
                + future[incoming.player_id]
                - future[outgoing]
            )
            cost = incoming.market_price_units - sale
            swaps.append((gain, cost, outgoing, incoming.player_id))
    ranked = sorted(swaps, key=lambda row: (-row[0], row[1], row[2], row[3]))
    seen: set[frozenset[int]] = set()
    if locks <= owned and not owned & exclusions:
        seen.add(frozenset(owned))
        yield owned
    maximum = settings.max_transfers_this_event
    singles = (
        [frozenset((owned - {outgoing}) | {incoming}) for _, _, outgoing, incoming in ranked[:24]]
        if maximum is None or maximum >= 1
        else []
    )
    if maximum is not None and maximum < 2:
        for squad in singles:
            if squad not in seen:
                seen.add(squad)
                yield set(squad)
        return
    # A low-scoring reserve downgrade may fund an otherwise unaffordable XI gain.
    # Include both high-gain and high-saving swaps so this case is seeded early.
    donors = sorted(swaps, key=lambda row: (row[1], -row[0], row[2], row[3]))[:16]
    pairs: list[tuple[float, int, frozenset[int]]] = []
    for first in ranked[:20]:
        for second in donors:
            if first[2] == second[2] or first[3] == second[3]:
                continue
            squad = frozenset((owned - {first[2], second[2]}) | {first[3], second[3]})
            if squad not in seen:
                pairs.append((first[0] + second[0], first[1] + second[1], squad))
    ranked_pairs = sorted(pairs, key=lambda row: (-row[0], row[1], tuple(sorted(row[2]))))
    affordable_funding = [
        row
        for row in ranked_pairs
        if row[1] <= (state.bank_units or 0)
        and any(
            first[1] > (state.bank_units or 0)
            and second[1] < 0
            and frozenset((owned - {first[2], second[2]}) | {first[3], second[3]}) == row[2]
            for first in ranked[:20]
            for second in donors
            if first[2] != second[2] and first[3] != second[3]
        )
    ]
    paired = [squad for _, _, squad in (affordable_funding[:8] + ranked_pairs[:8])]
    for index in range(max(len(singles), len(paired))):
        for candidate_squad in (
            singles[index] if index < len(singles) else None,
            paired[index] if index < len(paired) else None,
        ):
            if candidate_squad is None:
                continue
            if candidate_squad not in seen:
                seen.add(candidate_squad)
                yield set(candidate_squad)


def bounded_squads(
    current: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    deadline: float,
    offset: int,
) -> Iterator[set[int]]:
    """Lazy roll/one/two-replacement edges over the entire supplied catalogue.

    The two-replacement cap applies to this local menu. Chip weeks also receive
    independently generated complete ownership/XI/captain replacement squads.
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
    started = monotonic()
    deadline = started + settings.solver_time_limit_seconds
    evaluated = 0
    complete = not restricted
    best: SequenceResult = SequenceResult([], float("-inf"), 0, False, "no_legal_path")
    root_seen: set[tuple[str | None, frozenset[int]]] = set()
    root_seeded = 0
    # Establish a complete legal roll path before optional solver imports and
    # candidate fitting consume the budget. A requested chip can also keep its
    # squad, with inventory and Free Hit restoration replayed normally.
    if locks <= {p.player_id for p in state.picks} and not exclusions & {
        p.player_id for p in state.picks
    }:
        held = state.model_copy(deep=True)
        hold_weeks = []
        try:
            for offset in range(settings.horizon_events):
                chip = next(
                    choice
                    for choice in allowed_chips(held, settings, offset)
                    if not validate_chip(held, choice)
                )
                catalogue = event_players(players, settings, held.next_event)
                held, ledger = apply_transfers(held, catalogue, [], chip)
                hold_weeks.append(_week(held, catalogue, run, chip, ledger))
                if offset + 1 < settings.horizon_events:
                    held = advance_event(held)
        except (ValueError, StopIteration):
            pass
        else:
            best = SequenceResult(
                hold_weeks,
                sum(week["net_points"] for week in hold_weeks),
                0,
                False,
                "valid_incumbent",
                incumbent_source="keep_seed",
            )
            root_seen.add((hold_weeks[0]["chip"], frozenset(p.player_id for p in state.picks)))
    if restricted and max_edges >= 16 and monotonic() < deadline:
        # Reserve most of the edge budget for deeper search. Every seeded root is
        # extended to a complete legal roll continuation before comparison.
        seed_limit = min(max_edges // 2, 256)
        catalogue = event_players(players, settings, state.next_event)
        for chip in allowed_chips(state, settings, 0):
            if validate_chip(state, chip):
                continue
            choices = (
                complete_chip_squads(state, catalogue, run, settings, deadline, 0, chip)
                if chip in {"wildcard", "free_hit"}
                else _root_seed_squads(state, catalogue, run, settings)
            )
            for squad in choices:
                if evaluated + settings.horizon_events > seed_limit or monotonic() >= deadline:
                    break
                root = (chip, frozenset(squad))
                if root in root_seen:
                    continue
                root_seen.add(root)
                evaluated += 1
                try:
                    moves = funding_moves(state, catalogue, squad)
                    if (
                        settings.max_transfers_this_event is not None
                        and len(moves) > settings.max_transfers_this_event
                    ):
                        continue
                    changed, ledger = apply_transfers(state, catalogue, moves, chip)
                    first = _week(changed, catalogue, run, chip, ledger)
                    extra = max(0, first["total_hits"] - (state.confirmed_hit_points or 0))
                    if extra > settings.max_additional_hit_points:
                        continue
                    weeks = [first]
                    held = changed
                    for offset in range(1, settings.horizon_events):
                        if evaluated >= seed_limit or monotonic() >= deadline:
                            break
                        held = advance_event(held)
                        future_chip = next(
                            choice
                            for choice in allowed_chips(held, settings, offset)
                            if not validate_chip(held, choice)
                        )
                        future_players = event_players(players, settings, held.next_event)
                        held, future_ledger = apply_transfers(held, future_players, [], future_chip)
                        weeks.append(_week(held, future_players, run, future_chip, future_ledger))
                        evaluated += 1
                    if len(weeks) == settings.horizon_events:
                        root_seeded += 1
                        score = sum(week["net_points"] for week in weeks)
                        if score > best.net_points:
                            best = SequenceResult(
                                weeks,
                                score,
                                evaluated,
                                False,
                                "valid_incumbent",
                                incumbent_source="root_seed",
                            )
                except (ValueError, StopIteration):
                    continue
            if evaluated + settings.horizon_events > seed_limit or monotonic() >= deadline:
                break
    # DFS with exact dominance on full financial/chip states. Explore roll first
    # so a complete incumbent exists before the expensive alternatives.
    seen: dict[tuple[Any, ...], float] = {}

    def visit(current: ManagerState, weeks: list[dict[str, Any]], net: float, hits: int):
        nonlocal evaluated, complete, best
        offset = len(weeks)
        if offset == settings.horizon_events:
            if net > best.net_points:
                best = SequenceResult(
                    weeks, net, evaluated, False, "valid_incumbent", incumbent_source="depth_search"
                )
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
        chips = allowed_chips(current, settings, offset)
        if restricted:
            # Reach complete replacement alternatives before the much larger local
            # subtree consumes the shared budget. This remains a bounded ordering.
            chips.sort(key=lambda chip: chip not in {"wildcard", "free_hit"})
        for chip in chips:
            if validate_chip(current, chip):
                continue
            choices = (
                complete_chip_squads(current, catalogue, run, settings, deadline, offset, chip)
                if restricted and chip in {"wildcard", "free_hit"}
                else bounded_squads(current, catalogue, run, settings, deadline, offset)
                if restricted
                else iter(sorted(squads, key=lambda s: (len(s - owned), tuple(sorted(s)))))
            )
            for squad in choices:
                if evaluated >= max_edges or monotonic() >= deadline:
                    complete = False
                    return
                if offset == 0:
                    root_seen.add((chip, frozenset(squad)))
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
    best.root_actions_considered = len(root_seen)
    best.root_actions_seeded = root_seeded
    best.elapsed_seconds = monotonic() - started
    if restricted:
        best.search_scope = "ordinary_events_at_most_two_replacements_complete_chip_milp_candidates"
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
