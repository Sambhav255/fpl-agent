"""Deterministic legal first-action menus, independent of realized outcomes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations
from threading import RLock
from typing import Any

import numpy as np

from fpl_app.contracts import ManagerState, Plan, Player, ProjectionRun, Settings
from fpl_app.domain.plans import _check_inputs, _week, input_fingerprint, validate_plan
from fpl_app.domain.rules import (
    CHIPS,
    advance_event,
    apply_transfers,
    projection_points,
    readiness,
    validate_chip,
)
from fpl_app.optimisation.oracle import funding_moves
from fpl_app.optimisation.planner import _plan
from fpl_app.storage import fingerprint

CANDIDATE_VERSION = "legal-first-actions-v1"
CANDIDATE_FEATURES = 14
DEFAULT_K = 32


@dataclass(frozen=True)
class Candidate:
    semantic_id: str
    plan: Plan
    settings: Settings
    features: tuple[float, ...]


@dataclass(frozen=True)
class CandidateMenu:
    candidates: tuple[Candidate, ...]
    input_fingerprint: str
    considered: int
    truncated: bool
    version: str = CANDIDATE_VERSION


def semantic_key(week: dict[str, Any]) -> str:
    # Transfer execution order is not policy meaning; financial records remain in plan.
    return fingerprint(
        {
            "event": week["event"],
            "moves": sorted((a["out"], a["in"]) for a in week["actions"]),
            "chip": week["chip"],
            "lineup": {
                k: week["lineup"][k] for k in ("starters", "bench", "captain", "vice_captain")
            },
        }
    )


def apply_candidate(state, players, moves, chip):
    changed, ledger = apply_transfers(state, players, moves, chip)
    # Stable paper acquisition identities make seeded trajectories reproducible;
    # the live domain retains unique acquisition identities.
    for pick in changed.picks:
        for move in ledger:
            if pick.player_id == move["in"]:
                pick.acquisition_id = fingerprint(
                    {"event": state.next_event, "state": state.model_dump(), "move": move}
                )
    return changed, ledger


def _candidate(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    moves: list[dict[str, int]],
    chip: str | None,
) -> Candidate:
    local = settings.model_copy(deep=True)
    local.chip_policy = chip or "none"  # type: ignore[assignment]
    local.chip_schedule = {state.next_event: chip} if chip else {}  # type: ignore[dict-item]
    local.future_chip_policy = "none"
    local.price_scenario = {}  # Candidate continuation is explicitly frozen-price.
    changed, ledger = apply_candidate(state, players, moves, chip)
    weeks = [_week(changed, players, run, chip, ledger)]
    current = changed
    for _ in range(1, local.horizon_events):
        current = advance_event(current)
        weeks.append(_week(current, players, run, None, []))
    prior = state.confirmed_hit_points or 0
    extra = sum(w["total_hits"] for w in weeks) - prior
    if extra > settings.max_additional_hit_points:
        raise ValueError("Candidate hit budget exceeded")
    plan = _plan(
        state,
        run,
        input_fingerprint(state, players, run, local),
        weeks,
        "Research first action; hold continuation",
        {"search": "deterministic menu"},
        sum(w["total_hits"] for w in weeks),
    )
    errors = validate_plan(plan, state, players, run, local)
    if errors:
        raise ValueError("; ".join(errors))
    week = weeks[0]
    features = (
        float(week["net_points"]) / 100,
        plan.net_points / (100 * local.horizon_events),
        len(moves) / 15,
        float(week["total_hits"]) / 80,
        float(week["bank_units"]) / 1000,
        float(week["free_transfers_next"]) / 5,
        float(not moves),
        *(
            float(chip == c)
            for c in (None, "wildcard", "free_hit", "bench_boost", "triple_captain")
        ),
        float(week["gross_points"]) / 100,
        local.horizon_events / 8,
    )
    return Candidate(semantic_key(week), plan, local, features)


def _build_menu(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    k: int = DEFAULT_K,
    template_budget: int = 256,
) -> CandidateMenu:
    _check_inputs(state, players, run, settings)
    if not readiness(state, players)["transfers_ready"]:
        raise ValueError("Candidate menu requires confirmed finances")
    if not 2 <= k <= 128 or template_budget < k:
        raise ValueError("Invalid candidate budget")
    own = {p.player_id for p in state.picks}
    locked, excluded = set(settings.locked_player_ids), set(settings.excluded_player_ids)
    # Slot zero is an unmodified legal roll. It may be masked by hard exclusions,
    # in which case this research environment rejects an incompatible initial state.
    if own & excluded:
        raise ValueError("Roll violates exclusions; reconcile initial research squad")
    xp = projection_points(run.projections, state.next_event)
    singles = [
        dict(out=o.player_id, **{"in": p.player_id})
        for o in sorted(state.picks, key=lambda x: x.player_id)
        if o.player_id not in locked
        for p in sorted(players, key=lambda x: (-xp.get(x.player_id, 0), x.player_id))
        if p.player_id not in own | excluded
        and p.position == next(q.position for q in players if q.player_id == o.player_id)
    ]
    singles.sort(key=lambda m: (-(xp.get(m["in"], 0) - xp.get(m["out"], 0)), m["out"], m["in"]))
    recipes: list[list[dict[str, int]]] = [[]] + [[m] for m in singles[: template_budget // 2]]
    # Funding pairs use cost-releasing order before applying the financial transition.
    for left, right in combinations(singles[:64], 2):
        if left["out"] == right["out"] or left["in"] == right["in"]:
            continue
        selected = own - {left["out"], right["out"]} | {left["in"], right["in"]}
        recipes.append(funding_moves(state, players, selected))
        if len(recipes) >= template_budget:
            break
    chip_options = [state.current_chip] if state.current_chip else [None, *sorted(CHIPS)]
    candidates: dict[str, Candidate] = {}
    considered = 0
    for moves in recipes:
        if (
            settings.max_transfers_this_event is not None
            and len(moves) > settings.max_transfers_this_event
        ):
            continue
        for chip in chip_options:
            if validate_chip(state, chip):
                continue
            considered += 1
            try:
                item = _candidate(state, players, run, settings, moves, chip)
            except ValueError:
                continue
            candidates.setdefault(item.semantic_id, item)
    roll = _candidate(state, players, run, settings, [], state.current_chip)
    ordered = [roll] + sorted(
        (c for c in candidates.values() if c.semantic_id != roll.semantic_id),
        key=lambda c: (-c.plan.net_points, c.semantic_id),
    )
    return CandidateMenu(
        tuple(ordered[:k]),
        input_fingerprint(state, players, run, settings),
        considered,
        len(ordered) > k or len(singles) > template_budget // 2 or len(recipes) >= template_budget,
    )


_MENU_CACHE: dict[str, CandidateMenu] = {}
_MENU_LOCK = RLock()


def build_menu(
    state: ManagerState,
    players: list[Player],
    run: ProjectionRun,
    settings: Settings,
    *,
    k=DEFAULT_K,
    template_budget=256,
):
    key = fingerprint(
        {
            "inputs": input_fingerprint(state, players, run, settings),
            "k": k,
            "template_budget": template_budget,
        }
    )
    with _MENU_LOCK:
        cached = _MENU_CACHE.get(key)
    if cached is None:
        cached = _build_menu(state, players, run, settings, k=k, template_budget=template_budget)
        with _MENU_LOCK:
            if len(_MENU_CACHE) >= 256:
                _MENU_CACHE.pop(next(iter(_MENU_CACHE)))
            _MENU_CACHE[key] = cached
    return deepcopy(cached)


def candidate_matrix(menu: CandidateMenu, k: int = DEFAULT_K) -> tuple[np.ndarray, np.ndarray]:
    if len(menu.candidates) > k:
        raise ValueError("Menu exceeds action space")
    matrix = np.zeros((k, CANDIDATE_FEATURES), dtype=np.float32)
    mask = np.zeros(k, dtype=np.bool_)
    for i, c in enumerate(menu.candidates):
        matrix[i] = c.features
        mask[i] = True
    return matrix, mask
