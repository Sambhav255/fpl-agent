"""Bounded beam planner with optional HiGHS candidate generation and independent replay."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import monotonic
from typing import Any, Literal
from uuid import uuid4

from fpl_app.contracts import ManagerState, Plan, Player, ProjectionRun, Recommendation, Settings
from fpl_app.domain.plans import (
    _check_inputs,
    _week,
    allowed_chips,
    event_players,
    input_fingerprint,
    validate_plan,
)
from fpl_app.domain.rules import (
    RULES,
    advance_event,
    apply_transfers,
    player_map,
    projection_points,
    readiness,
    sale_value,
    validate_chip,
)
from fpl_app.optimisation.advice import chip_advice


def _plan(
    state: ManagerState,
    run: ProjectionRun,
    fingerprint: str,
    weeks: list[dict[str, Any]],
    name: str,
    metadata: dict[str, Any],
    baseline_hits: int,
) -> Plan:
    gross = sum(w["gross_points"] for w in weeks)
    hits = sum(w["total_hits"] for w in weeks)
    return Plan(
        plan_id=str(uuid4()),
        state_version=state.state_version,
        projection_run_id=run.projection_run_id,
        input_fingerprint=fingerprint,
        name=name,
        actions=[a for w in weeks for a in w["actions"]],
        weeks=weeks,
        gross_points=gross,
        total_hits=hits,
        incremental_hits=hits - baseline_hits,
        net_points=gross - hits,
        bank_units=weeks[0]["bank_units"],
        free_transfers_next=weeks[0]["free_transfers_next"],
        lineup=weeks[0]["lineup"],
        chip=weeks[0]["chip"],
        this_week_net=weeks[0]["net_points"],
        this_week_delta=0,
        assumptions=[
            "Frozen market prices over horizon; acquisition prices and selling profit retained",
            (
                "Beam search with original 15-player squad proxy comparator; no global optimality claim"
                if metadata.get("candidate_comparator") == "squad_proxy"
                else "Beam search with frozen-ownership lineup/captain MILP candidates; no global optimality claim"
            ),
            "Terminal tiebreak preserves free transfers and bank; terminal values are not fitted",
            "No calibrated joint scenario uncertainty or autosub expectation",
        ],
        solver=metadata,
    )


def squad_proxy_candidate(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    remaining: float,
    chip: str | None,
    max_moves: int,
) -> tuple[list[dict[str, int]], dict[str, Any]]:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    owned = {p.player_id: p for p in state.picks}
    n = len(players)
    prices = np.array(
        [
            sale_value(owned[p.player_id], p) if p.player_id in owned else p.market_price_units
            for p in players
        ],
        dtype=float,
    )
    budget = int(state.bank_units or 0) + sum(
        sale_value(p, player_map(players)[p.player_id]) for p in state.picks
    )
    future = [
        projection_points(run.projections, event)
        for event in range(
            state.next_event,
            min(39, state.next_event + (1 if chip == "free_hit" else settings.horizon_events)),
        )
    ]
    objective = np.array(
        [
            -sum(x.get(p.player_id, 0) for x in future) + (0.001 if p.player_id not in owned else 0)
            for p in players
        ]
    )
    rows, lower, upper = [], [], []
    for pos, count in enumerate(RULES.squad_counts, 1):
        rows.append([int(p.position == pos) for p in players])
        lower.append(count)
        upper.append(count)
    for club in sorted({p.club for p in players}):
        rows.append([int(p.club == club) for p in players])
        lower.append(0)
        upper.append(3)
    rows.append(prices.tolist())
    lower.append(0)
    upper.append(budget)
    rows.append([int(p.player_id not in owned) for p in players])
    lower.append(0)
    upper.append(max_moves)
    lo, hi = np.zeros(n), np.ones(n)
    for i, p in enumerate(players):
        if p.player_id in settings.locked_player_ids:
            lo[i] = 1
        if p.player_id in settings.excluded_player_ids:
            hi[i] = 0
    result = milp(
        objective,
        integrality=np.ones(n),
        bounds=Bounds(lo, hi),
        constraints=LinearConstraint(np.array(rows), np.array(lower), np.array(upper)),
        options={"time_limit": max(0.001, min(remaining, 1.0))},
    )
    metadata = {
        "engine": "scipy.milp/HiGHS",
        "candidate_status": int(result.status),
        "candidate_message": str(result.message),
        "candidate_gap": float(result.mip_gap)
        if getattr(result, "mip_gap", None) is not None and isfinite(result.mip_gap)
        else None,
    }
    if result.x is None:
        return [], metadata
    selected = {p.player_id for i, p in enumerate(players) if result.x[i] > 0.5}
    out = [p.player_id for p in players if p.player_id in owned and p.player_id not in selected]
    incoming = [
        p.player_id for p in players if p.player_id in selected and p.player_id not in owned
    ]
    by_id = player_map(players)
    moves: list[dict[str, int]] = []
    for pos in range(1, 5):
        leaving = sorted(
            [i for i in out if by_id[i].position == pos],
            key=lambda i: -sale_value(owned[i], by_id[i]),
        )
        entering = sorted(
            [i for i in incoming if by_id[i].position == pos],
            key=lambda i: by_id[i].market_price_units,
        )
        moves.extend({"out": o, "in": i} for o, i in zip(leaving, entering, strict=True))
    moves.sort(
        key=lambda m: (
            by_id[m["in"]].market_price_units - sale_value(owned[m["out"]], by_id[m["out"]])
        )
    )
    return moves, metadata


def _highs_candidate(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    remaining: float,
    chip: str | None,
    max_moves: int,
) -> tuple[list[dict[str, int]], dict[str, Any]]:
    """Frozen ownership candidate with legal XI/captain per event, not a horizon policy."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    owned = {p.player_id: p for p in state.picks}
    by_id = player_map(players)
    n = len(players)
    horizon = 1 if chip == "free_hit" else settings.horizon_events
    horizon = min(horizon, 39 - state.next_event)
    size = n * (1 + 2 * horizon)
    objective = np.zeros(size)
    rows, lower, upper = [], [], []

    def constraint(terms, lo, hi):
        row = np.zeros(size)
        for index, value in terms:
            row[index] = value
        rows.append(row)
        lower.append(lo)
        upper.append(hi)

    for position, count in enumerate(RULES.squad_counts, 1):
        constraint([(i, 1) for i, p in enumerate(players) if p.position == position], count, count)
    for club in sorted({p.club for p in players}):
        constraint([(i, 1) for i, p in enumerate(players) if p.club == club], 0, 3)
    budget = int(state.bank_units or 0) + sum(
        sale_value(p, by_id[p.player_id]) for p in state.picks
    )
    constraint(
        [
            (i, sale_value(owned[p.player_id], p) if p.player_id in owned else p.market_price_units)
            for i, p in enumerate(players)
        ],
        0,
        budget,
    )
    constraint([(i, 1) for i, p in enumerate(players) if p.player_id not in owned], 0, max_moves)
    for offset in range(horizon):
        start, captain = n * (1 + 2 * offset), n * (2 + 2 * offset)
        xp = projection_points(run.projections, state.next_event + offset)
        constraint([(start + i, 1) for i in range(n)], 11, 11)
        constraint([(captain + i, 1) for i in range(n)], 1, 1)
        for position, lo, hi in [(1, 1, 1), (2, 3, 5), (3, 2, 5), (4, 1, 3)]:
            constraint(
                [(start + i, 1) for i, p in enumerate(players) if p.position == position], lo, hi
            )
        for i, p in enumerate(players):
            constraint([(start + i, 1), (i, -1)], -np.inf, 0)
            constraint([(captain + i, 1), (start + i, -1)], -np.inf, 0)
            value = xp.get(p.player_id, 0)
            boost = offset == 0 and chip == "bench_boost"
            objective[i if boost else start + i] -= value
            objective[captain + i] = -value * (2 if offset == 0 and chip == "triple_captain" else 1)
    bound_lo, bound_hi = np.zeros(size), np.ones(size)
    for i, p in enumerate(players):
        if p.player_id in settings.locked_player_ids:
            bound_lo[i] = 1
        if p.player_id in settings.excluded_player_ids:
            bound_hi[i] = 0
    result = milp(
        objective,
        integrality=np.ones(size),
        bounds=Bounds(bound_lo, bound_hi),
        constraints=LinearConstraint(np.array(rows), np.array(lower), np.array(upper)),
        options={"time_limit": max(0.001, min(remaining, 1.0))},
    )
    metadata = {
        "engine": "scipy.milp/HiGHS",
        "candidate_objective": "frozen_ownership_lineup_captain",
        "candidate_status": int(result.status),
        "candidate_message": str(result.message),
        "candidate_gap": float(result.mip_gap)
        if getattr(result, "mip_gap", None) is not None and isfinite(result.mip_gap)
        else None,
        "candidate_gap_scope": "frozen ownership candidate only; excludes future transfers and hits",
    }
    if result.x is None:
        return [], metadata
    from fpl_app.optimisation.oracle import funding_moves

    selected = {p.player_id for i, p in enumerate(players) if result.x[i] > 0.5}
    return funding_moves(state, players, selected), metadata


@dataclass
class Node:
    state: ManagerState
    weeks: list[dict[str, Any]]
    net: float
    additional_hits: int


def _hold_weeks(state, players, run, first_week, horizon):
    weeks = [first_week]
    if horizon == 1:
        return weeks
    current = advance_event(state)
    for offset in range(1, horizon):
        weeks.append(_week(current, players, run, None, []))
        if offset + 1 < horizon:
            current = advance_event(current)
    return weeks


def recommend(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    lineup_only: bool = False,
    candidate_mode: Literal["lineup_captain", "squad_proxy"] = "lineup_captain",
) -> Recommendation:
    candidate_generator = (
        _highs_candidate if candidate_mode == "lineup_captain" else squad_proxy_candidate
    )
    started = monotonic()
    _check_inputs(state, players, run, settings)
    deadline = started + settings.solver_time_limit_seconds
    fingerprint = input_fingerprint(state, players, run, settings)
    warnings = list(run.warnings) + [
        "Lineup objective omits expected autosubs and vice fallback; deterministic scoring is available"
    ]
    if not run.fixtures:
        warnings.append(
            "Legacy run lacks frozen fixture schedule; wholly absent club events cannot be distinguished from blanks"
        )
    ready = readiness(state, players)
    current = state.model_copy(deep=True)
    weeks = []
    for offset in range(settings.horizon_events):
        weeks.append(
            _week(
                current,
                event_players(players, settings, current.next_event),
                run,
                current.current_chip,
                [],
            )
        )
        if offset + 1 < settings.horizon_events:
            current = advance_event(current)
    baseline_hits = sum(w["total_hits"] for w in weeks)
    metadata: dict[str, Any] = {
        "candidate_comparator": candidate_mode,
        "status": "feasible_heuristic",
        "time_limit_seconds": settings.solver_time_limit_seconds,
        "optimality_gap": None,
        "search": "beam_width_6, singles plus funding-aware lineup/captain HiGHS candidates",
        "terminal_policy": "net points then saved FT then bank; unfitted",
        "candidate_universe_size": len(players),
    }
    baseline = _plan(state, run, fingerprint, weeks, "Keep", metadata.copy(), baseline_hits)
    if settings.price_scenario:
        baseline.assumptions[0] = (
            "Conditional declared market-price path; purchase and selling basis retained"
        )
    errors = validate_plan(baseline, state, players, run, settings, enforce_preferences=False)
    if errors:
        raise ValueError("Invalid Keep plan: " + "; ".join(errors))
    if lineup_only or not ready["transfers_ready"]:
        if not ready["transfers_ready"]:
            warnings += ["Transfers blocked: " + "; ".join(ready["missing_fields"])]
        if state.confirmed_hit_points is None:
            warnings.append(
                "Committed hits unknown; net points and comparison delta are unavailable"
            )
        baseline.solver["status"] = "lineup_only"
        baseline.solver["search"] = "lineup selection only; transfer solver not run"
        baseline.solver["elapsed_seconds"] = monotonic() - started
        if state.confirmed_hit_points is None:
            baseline.solver["net_points_status"] = "unavailable_unknown_committed_hits"
            baseline.assumptions.append(
                "Net points and delta are unavailable because committed hit points are unknown; legacy numeric net/hit fields are provisional placeholders, not confirmed zero hits"
            )
        else:
            baseline.solver["net_points_status"] = "available"
        if not ready["transfers_ready"]:
            baseline.assumptions.append(
                "Financial state unconfirmed or incomplete: " + "; ".join(ready["missing_fields"])
            )
        return Recommendation(
            recommendation_id=str(uuid4()),
            baseline_plan=baseline,
            alternatives=[],
            gameweek_optimum=None,
            chip_advice=chip_advice(state, state, players, run, settings, baseline, None),
            source_cutoff=run.source_cutoff,
            rules_version=run.rules_version,
            state_version=state.state_version,
            projection_run_id=run.projection_run_id,
            warnings=warnings,
        )
    chip = allowed_chips(state, settings, 0)[0]
    chip_errors = validate_chip(state, chip)
    if chip_errors:
        warnings += chip_errors
        return Recommendation(
            recommendation_id=str(uuid4()),
            baseline_plan=baseline,
            alternatives=[],
            gameweek_optimum=None,
            chip_advice=chip_advice(state, state, players, run, settings, baseline, None),
            source_cutoff=run.source_cutoff,
            rules_version=run.rules_version,
            state_version=state.state_version,
            projection_run_id=run.projection_run_id,
            warnings=warnings,
        )
    if settings.planner_mode == "sequence":
        from fpl_app.optimisation.sequence import solve_sequence

        sequence_result = solve_sequence(
            state,
            players,
            run,
            settings.model_copy(
                update={"solver_time_limit_seconds": max(0.001, deadline - monotonic())}
            ),
        )
        sequence_meta = {
            **metadata,
            "search": "financial-state dynamic programming; full declared squad/chip path",
            "status": sequence_result.status,
            "evaluated_edges": sequence_result.evaluated_edges,
            "search_scope": sequence_result.search_scope,
            "optimality_gap": 0 if sequence_result.complete and sequence_result.weeks else None,
            "elapsed_seconds": monotonic() - started,
            "scope": "declared deterministic price and forecast path; budget bounded",
        }
        sequence_alternatives: list[Plan] = []
        if sequence_result.weeks:
            plan = _plan(
                state,
                run,
                fingerprint,
                sequence_result.weeks,
                "Financial sequence plan",
                sequence_meta,
                baseline_hits,
            )
            plan.delta_to_baseline = plan.net_points - baseline.net_points
            plan.this_week_delta = float(plan.weeks[0]["net_points"]) - float(
                baseline.weeks[0]["net_points"]
            )
            plan.assumptions = [
                "Complete financial-state path over the declared universe when search exhausts; bounded incumbents otherwise",
                "Large catalogues restrict ordinary events to at most two replacements; Wildcard/Free Hit admit complete ownership/XI/captain MILP squads; path search remains bounded",
                "Conditional declared price path"
                if settings.price_scenario
                else "Frozen prices; exact acquisition and selling basis",
                "Future chips subject to confirmed inventory, expiry and Free Hit restoration",
                "Forecast means; no joint uncertainty or fitted continuation value",
            ]
            errors = validate_plan(plan, state, players, run, settings, baseline)
            if errors:
                raise ValueError("Invalid sequence incumbent: " + "; ".join(errors))
            sequence_alternatives.append(plan)
        if not sequence_result.complete:
            warnings.append(
                "Sequence search is restricted or budget exhausted; only complete validated paths returned, no global optimality claim"
            )
        baseline.solver = sequence_meta
        return Recommendation(
            recommendation_id=str(uuid4()),
            baseline_plan=baseline,
            alternatives=sequence_alternatives,
            gameweek_optimum=None,
            chip_advice=chip_advice(state, state, players, run, settings, baseline, None),
            source_cutoff=run.source_cutoff,
            rules_version=run.rules_version,
            state_version=state.state_version,
            projection_run_id=run.projection_run_id,
            warnings=warnings,
        )
    beam = [Node(state.model_copy(deep=True), [], 0.0, 0)]
    by_id = player_map(players)
    timed_out = False
    this_week_best: tuple[tuple[float, int, int, int], ManagerState, dict[str, Any]] | None = None
    for offset in range(settings.horizon_events):
        expanded = []
        for node in beam:
            week_players = event_players(players, settings, node.state.next_event)
            for event_chip in allowed_chips(node.state, settings, offset):
                if validate_chip(node.state, event_chip):
                    continue
                candidates: list[list[dict[str, int]]] = [[]]
                owned = {p.player_id for p in node.state.picks}
                if monotonic() < deadline:
                    xp = projection_points(run.projections, node.state.next_event)
                    eligible = [
                        p
                        for p in week_players
                        if p.player_id not in owned
                        and p.player_id not in settings.excluded_player_ids
                    ]
                    eligible.sort(key=lambda p: (-xp.get(p.player_id, 0), p.player_id))
                    remaining_hits = settings.max_additional_hit_points - node.additional_hits
                    free = int(node.state.free_transfers_at_event_start or 1)
                    made = int(node.state.transfers_made_this_event or 0)
                    max_moves = (
                        15
                        if event_chip in {"wildcard", "free_hit"}
                        else min(20 - made, max(0, free - made) + remaining_hits // 4)
                    )
                    if offset == 0 and settings.max_transfers_this_event is not None:
                        max_moves = min(max_moves, settings.max_transfers_this_event)
                    # Full single-transfer universe, bounded by wall clock and this-week cap.
                    if max_moves >= 1:
                        for out in node.state.picks:
                            if out.player_id in settings.locked_player_ids:
                                continue
                            candidates.extend(
                                [{"out": out.player_id, "in": p.player_id}]
                                for p in eligible
                                if p.position == by_id[out.player_id].position
                            )
                    try:
                        if max_moves >= 1:
                            moves, solver_info = candidate_generator(
                                node.state,
                                week_players,
                                run,
                                settings,
                                deadline - monotonic(),
                                event_chip,
                                max_moves,
                            )
                            metadata.update(solver_info)
                            if moves and len(moves) <= max_moves:
                                candidates.insert(1, moves)
                            if offset == 0 and settings.horizon_events > 1:
                                weekly_moves, weekly_info = candidate_generator(
                                    node.state,
                                    week_players,
                                    run,
                                    settings.model_copy(update={"horizon_events": 1}),
                                    deadline - monotonic(),
                                    event_chip,
                                    max_moves,
                                )
                                metadata["this_week_candidate_status"] = weekly_info
                                if (
                                    weekly_moves
                                    and len(weekly_moves) <= max_moves
                                    and weekly_moves not in candidates
                                ):
                                    candidates.insert(1, weekly_moves)
                    except (ImportError, ValueError) as exc:
                        metadata["highs_unavailable_or_failed"] = str(exc)
                else:
                    timed_out = True
                for index, moves in enumerate(candidates):
                    if index > 0 and monotonic() >= deadline:
                        timed_out = True
                        break
                    try:
                        result, ledger = apply_transfers(
                            node.state, week_players, moves, event_chip
                        )
                        if {p.player_id for p in result.picks} & set(settings.excluded_player_ids):
                            continue
                        week = _week(result, week_players, run, event_chip, ledger)
                        extra = node.additional_hits + max(
                            0,
                            week["total_hits"]
                            - (baseline.weeks[offset]["total_hits"] if offset == 0 else 0),
                        )
                        if extra > settings.max_additional_hit_points:
                            continue
                        if (
                            offset == 0
                            and settings.max_transfers_this_event is not None
                            and len(ledger) > settings.max_transfers_this_event
                        ):
                            continue
                        if offset == 0:
                            rank = (
                                float(week["net_points"]),
                                int(week["free_transfers_next"] or 0),
                                int(result.bank_units or 0),
                                -len(ledger),
                            )
                            if this_week_best is None or rank > this_week_best[0]:
                                this_week_best = (rank, result, week)
                        next_state = (
                            advance_event(result)
                            if offset + 1 < settings.horizon_events
                            else result
                        )
                        expanded.append(
                            Node(
                                next_state,
                                node.weeks + [week],
                                node.net + week["net_points"],
                                extra,
                            )
                        )
                    except ValueError:
                        continue
        if not expanded:
            warnings.append("No complete legal plan satisfying preferences within search budget")
            beam = []
            break
        expanded.sort(
            key=lambda n: (n.net, n.weeks[-1]["free_transfers_next"] or 0, n.state.bank_units or 0),
            reverse=True,
        )
        unique = {}
        for n in expanded:
            key = (
                tuple(sorted((p.player_id, p.purchase_price_units) for p in n.state.picks)),
                n.state.bank_units,
                n.state.free_transfers_at_event_start,
                n.additional_hits,
                tuple(sorted(n.state.chips.items())),
                n.state.current_chip,
                n.state.previous_free_hit_event,
                tuple(
                    sorted(
                        (p.player_id, p.purchase_price_units)
                        for p in (n.state.persistent_picks or [])
                    )
                ),
            )
            if key not in unique:
                unique[key] = n
        beam = list(unique.values())[:6]
    metadata["status"] = "time_limit_valid_incumbent" if timed_out else "feasible_heuristic"
    metadata["elapsed_seconds"] = monotonic() - started
    alternatives: list[Plan] = []
    for node in beam:
        plan = _plan(
            state,
            run,
            fingerprint,
            node.weeks,
            "Transfer/chip plan",
            metadata.copy(),
            baseline_hits,
        )
        if settings.price_scenario:
            plan.assumptions[0] = (
                "Conditional declared price scenario; acquisition basis and sale rounding replayed at every event"
            )
        if settings.future_chip_policy == "optimise" or settings.chip_schedule:
            plan.assumptions.append(
                "Future chips searched under confirmed inventory and season windows; dates are conditional proposals"
            )
        plan.delta_to_baseline = plan.net_points - baseline.net_points
        plan.this_week_delta = float(plan.weeks[0]["net_points"]) - float(
            baseline.weeks[0]["net_points"]
        )
        errors = validate_plan(plan, state, players, run, settings, baseline)
        if (
            not errors
            and (
                plan.actions
                or any(
                    w["chip"] != b["chip"] for w, b in zip(plan.weeks, baseline.weeks, strict=True)
                )
            )
            and all(plan.weeks != p.weeks for p in alternatives)
        ):
            alternatives.append(plan)
        elif errors:
            warnings.append("Candidate rejected by independent replay: " + "; ".join(errors))
    baseline.solver = metadata.copy()
    if timed_out:
        warnings.append(
            "Time limit reached; Keep and complete validated incumbents only; global gap unavailable"
        )
    chosen = state
    scenario_net = None
    gameweek_optimum = None
    if this_week_best is not None:
        _rank, chosen_state, first_week = this_week_best
        if settings.chip_policy in {"wildcard", "free_hit"}:
            scenario_net = float(first_week["net_points"])
        if not first_week["actions"] and first_week.get("chip") == baseline.chip:
            gameweek_optimum = baseline.model_copy(deep=True)
            gameweek_optimum.plan_id = str(uuid4())
            gameweek_optimum.name = "Gameweek optimum"
        else:
            if first_week.get("chip") is None:
                chosen = chosen_state
            optimum_weeks = _hold_weeks(
                chosen_state, players, run, first_week, settings.horizon_events
            )
            gameweek_optimum = _plan(
                state,
                run,
                fingerprint,
                optimum_weeks,
                "Gameweek optimum",
                metadata.copy(),
                baseline_hits,
            )
            gameweek_optimum.delta_to_baseline = gameweek_optimum.net_points - baseline.net_points
            gameweek_optimum.this_week_delta = float(optimum_weeks[0]["net_points"]) - float(
                baseline.weeks[0]["net_points"]
            )
            optimum_errors = validate_plan(
                gameweek_optimum, state, players, run, settings, baseline
            )
            if optimum_errors:
                warnings.append(
                    "Gameweek optimum rejected by independent replay: " + "; ".join(optimum_errors)
                )
                gameweek_optimum = None
    return Recommendation(
        recommendation_id=str(uuid4()),
        baseline_plan=baseline,
        alternatives=alternatives[:3],
        gameweek_optimum=gameweek_optimum,
        chip_advice=chip_advice(state, chosen, players, run, settings, baseline, scenario_net),
        source_cutoff=run.source_cutoff,
        rules_version=run.rules_version,
        state_version=state.state_version,
        projection_run_id=run.projection_run_id,
        warnings=warnings,
    )
