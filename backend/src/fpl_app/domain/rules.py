"""Season rules, deterministic scoring and state transitions; no provider I/O."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Any, NewType
from uuid import uuid4

from fpl_app.contracts import ManagerState, Pick, Player, Projection

Money = NewType("Money", int)
Points = NewType("Points", float)


@dataclass(frozen=True)
class SeasonRules:
    season: str = "2026/27"
    version: str = "2026-27-v1"
    verified_at: str = "2026-10-09T23:49:37Z"
    verification_precision: str = (
        "UTC verification completed; source URLs retained, raw HTML not archived"
    )
    sources: tuple[str, ...] = (
        "https://www.premierleague.com/en/news/4661029",
        "https://www.premierleague.com/en/news/2174900",
        "https://fantasy.premierleague.com/help/new",
    )
    squad_counts: tuple[int, ...] = (2, 5, 5, 3)
    club_limit: int = 3
    max_free_transfers: int = 5
    max_transfers: int = 20
    hit_cost: int = 4
    chip_windows: tuple[tuple[int, int], ...] = ((1, 19), (20, 38))
    goal_points: tuple[int, ...] = (10, 6, 5, 4)


RULES = SeasonRules()
CHIPS = {"wildcard", "free_hit", "bench_boost", "triple_captain"}


def selling_price(purchase: int, market: int) -> int:
    if type(purchase) is not int or type(market) is not int or min(purchase, market) < 0:
        raise ValueError("Prices must be nonnegative integer tenths")
    return min(purchase, market) if market <= purchase else purchase + (market - purchase) // 2


def player_map(players: list[Player]) -> dict[int, Player]:
    result = {p.player_id: p for p in players}
    if len(result) != len(players):
        raise ValueError("Duplicate player IDs")
    return result


def validate_formation(ids: list[int], players: list[Player]) -> list[str]:
    by_id = player_map(players)
    if len(ids) != 11 or len(set(ids)) != 11 or any(i not in by_id for i in ids):
        return ["Starting XI must contain eleven unique known players"]
    c = Counter(by_id[i].position for i in ids)
    return (
        []
        if c[1] == 1 and 3 <= c[2] <= 5 and 2 <= c[3] <= 5 and 1 <= c[4] <= 3
        else ["Illegal formation"]
    )


def validate_squad(
    state: ManagerState, players: list[Player], *, allow_club_exception: bool = True
) -> list[str]:
    by_id = player_map(players)
    ids = [p.player_id for p in state.picks]
    errors: list[str] = []
    if len(ids) != 15 or len(set(ids)) != 15:
        errors.append("Squad must contain fifteen unique players")
    if any(i not in by_id for i in ids):
        return errors + ["Unknown squad player"]
    counts: Counter[int] = Counter(by_id[i].position for i in ids)
    if tuple(counts[i] for i in range(1, 5)) != RULES.squad_counts:
        errors.append("Squad requires 2 GK, 5 DEF, 5 MID, 3 FWD")
    if max(Counter(by_id[i].club for i in ids).values(), default=0) > RULES.club_limit and not (
        allow_club_exception and state.club_limit_exception
    ):
        errors.append(
            "Club limit exceeded; reconcile real-world club transfer before next transfer"
        )
    if sorted(p.position for p in state.picks) != list(range(1, 16)):
        errors.append("Pick positions must be a permutation of 1 through 15")
    return errors


def sale_value(pick: Pick, player: Player) -> int:
    if pick.purchase_price_units is not None:
        derived = selling_price(pick.purchase_price_units, player.market_price_units)
        if (
            pick.selling_price_units is not None
            and pick.selling_price_market_units == player.market_price_units
            and pick.selling_price_units != derived
        ):
            raise ValueError(
                f"Confirmed selling price disagrees with acquisition: {pick.player_id}"
            )
        return derived
    if (
        pick.selling_price_units is not None
        and pick.selling_price_provenance in {"user_confirmed", "private_verified", "demo"}
        and pick.selling_price_market_units == player.market_price_units
        and pick.selling_price_units <= player.market_price_units
    ):
        return pick.selling_price_units
    raise ValueError(f"Unknown or stale selling price: {pick.player_id}")


def readiness(state: ManagerState, players: list[Player]) -> dict[str, Any]:
    errors = validate_squad(state, players)
    by_id = player_map(players)
    missing = [
        name
        for name in (
            "bank_units",
            "free_transfers_at_event_start",
            "transfers_made_this_event",
            "confirmed_hit_points",
        )
        if getattr(state, name) is None
    ]
    for pick in state.picks:
        if pick.player_id in by_id:
            try:
                sale_value(pick, by_id[pick.player_id])
            except ValueError as exc:
                missing.append(str(exc))
    if state.season != RULES.season:
        missing.append("Unverified season rules")
    if not state.current_chip_confirmed:
        missing.append("Current chip status is unconfirmed")
    if (
        state.transfers_made_this_event is not None
        and state.transfers_made_this_event > RULES.max_transfers
        and state.current_chip not in {"wildcard", "free_hit"}
    ):
        missing.append("Ordinary twenty-transfer event limit exceeded")
    if state.current_chip not in CHIPS | {None}:
        missing.append("Unknown current chip")
    if (
        state.current_chip not in {"wildcard", "free_hit"}
        and state.free_transfers_at_event_start is not None
        and state.transfers_made_this_event is not None
        and state.confirmed_hit_points is not None
    ):
        expected = RULES.hit_cost * max(
            0, state.transfers_made_this_event - state.free_transfers_at_event_start
        )
        if expected != state.confirmed_hit_points:
            missing.append("Committed hits disagree with transfer ledger count")
    return {
        "lineup_ready": not errors,
        "transfers_ready": not errors and not missing,
        "missing_fields": missing,
        "errors": errors,
    }


def transfer_accounting(
    free: int, made: int, additional: int = 0, chip: str | None = None
) -> dict[str, int]:
    if any(type(x) is not int or x < 0 for x in (free, made, additional)) or not 1 <= free <= 5:
        raise ValueError("Invalid transfer inventory")
    total = made + additional
    if chip not in CHIPS | {None}:
        raise ValueError("Unknown chip")
    if chip in {"wildcard", "free_hit"}:
        return {
            "total_hits": 0,
            "incremental_hits": 0,
            "free_transfers_next": free,
            "total_moves": total,
        }
    if total > RULES.max_transfers:
        raise ValueError("Twenty-transfer event limit exceeded")
    hit = RULES.hit_cost * max(0, total - free)
    return {
        "total_hits": hit,
        "incremental_hits": hit - RULES.hit_cost * max(0, made - free),
        "free_transfers_next": min(5, max(0, free - total) + 1),
        "total_moves": total,
    }


def validate_chip(state: ManagerState, chip: str | None) -> list[str]:
    if chip is None:
        return []
    if chip not in CHIPS:
        return ["Unknown chip"]
    if not state.current_chip_confirmed:
        return ["Current chip status is unconfirmed"]
    if state.season != RULES.season:
        return ["Season rules unverified"]
    if state.current_chip and state.current_chip != chip:
        return ["Only one chip per event"]
    if chip in {"wildcard", "free_hit"} and state.next_event == 1:
        return ["Wildcard and Free Hit unavailable in GW1"]
    window = 1 if state.next_event <= 19 else 2
    # A plain key denotes the user's confirmed inventory for the current window only.
    available = state.chips.get(f"{chip}_{window}", state.chips.get(chip))
    if state.current_chip != chip and available is not True:
        return ["Chip inventory unavailable or unknown for current window"]
    if chip == "free_hit":
        if state.previous_free_hit_event == state.next_event - 1:
            return ["Consecutive Free Hits forbidden"]
        if state.current_chip == "free_hit" and state.persistent_picks is None:
            return ["Active Free Hit requires persistent restore ownership"]
        if state.event_start_picks is None or state.event_start_bank_units is None:
            return ["Free Hit requires event-start ownership and bank"]
        if state.current_chip == "free_hit" and state.persistent_picks is None:
            return ["Active Free Hit requires persistent restore ownership"]
    return []


def apply_transfers(
    state: ManagerState, players: list[Player], moves: list[dict[str, int]], chip: str | None = None
) -> tuple[ManagerState, list[dict[str, int]]]:
    if not readiness(state, players)["transfers_ready"]:
        raise ValueError("Incomplete manager finances or invalid squad")
    active_chip = chip or state.current_chip
    errors = validate_chip(state, active_chip)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = player_map(players)
    result = state.model_copy(deep=True)
    if active_chip == "free_hit" and state.current_chip != "free_hit":
        result.persistent_picks = [p.model_copy(deep=True) for p in state.event_start_picks or []]
    result.current_chip = active_chip
    ledger = []
    bank = int(state.bank_units or 0)
    for move in moves:
        out, incoming = move["out"], move["in"]
        owned = {p.player_id: p for p in result.picks}
        if out not in owned or incoming in owned or incoming not in by_id:
            raise ValueError("Transfer ownership invalid")
        if by_id[out].position != by_id[incoming].position:
            raise ValueError("Transfers must preserve position")
        sold = sale_value(owned[out], by_id[out])
        bought = by_id[incoming].market_price_units
        bank += sold - bought
        if bank < 0:
            raise ValueError("Unaffordable transfer")
        result.picks = [
            Pick(
                player_id=incoming,
                purchase_price_units=bought,
                acquisition_id=str(uuid4()),
                selling_price_provenance="planned_acquisition",
                position=p.position,
                is_captain=p.is_captain,
                is_vice_captain=p.is_vice_captain,
            )
            if p.player_id == out
            else p
            for p in result.picks
        ]
        ledger.append(
            {
                "event": state.next_event,
                "out": out,
                "in": incoming,
                "sale_units": sold,
                "purchase_units": bought,
                "bank_units": bank,
            }
        )
    errors = validate_squad(result, players, allow_club_exception=False)
    if errors:
        raise ValueError("; ".join(errors))
    accounting = transfer_accounting(
        int(state.free_transfers_at_event_start or 0),
        int(state.transfers_made_this_event or 0),
        len(moves),
        active_chip,
    )
    result.bank_units = bank
    result.transfer_ledger.extend(ledger)
    result.transfers_made_this_event = accounting["total_moves"]
    result.confirmed_hit_points = accounting["total_hits"]
    return result, ledger


def advance_event(state: ManagerState) -> ManagerState:
    if state.next_event >= 38:
        raise ValueError("No event after GW38")
    result = state.model_copy(deep=True)
    if (
        state.free_transfers_at_event_start is not None
        and state.transfers_made_this_event is not None
    ):
        result.free_transfers_at_event_start = transfer_accounting(
            state.free_transfers_at_event_start,
            state.transfers_made_this_event,
            chip=state.current_chip,
        )["free_transfers_next"]
    if state.current_chip:
        window = 1 if state.next_event <= 19 else 2
        result.chips[f"{state.current_chip}_{window}"] = False
        result.chips.pop(state.current_chip, None)
    if state.current_chip == "free_hit":
        if state.persistent_picks is None or state.event_start_bank_units is None:
            raise ValueError("Missing Free Hit restore state")
        result.picks = [p.model_copy(deep=True) for p in state.persistent_picks]
        result.bank_units = state.event_start_bank_units
        result.previous_free_hit_event = state.next_event
        result.persistent_picks = None
    if state.next_event == 19:
        for chip in CHIPS:
            result.chips.pop(chip, None)
            result.chips[f"{chip}_1"] = False
    result.next_event += 1
    result.current_chip = None
    result.transfers_made_this_event = 0
    result.confirmed_hit_points = 0
    result.event_start_picks = [p.model_copy(deep=True) for p in result.picks]
    result.event_start_bank_units = result.bank_units
    return result


def projection_points(projections: list[Projection], event: int) -> dict[int, float]:
    totals: dict[int, float] = {}
    seen = set()
    for p in projections:
        key = (p.player_id, p.fixture_id)
        if key in seen:
            raise ValueError("Duplicate player-fixture projection")
        seen.add(key)
        if not isfinite(p.expected_points) or not isfinite(p.expected_minutes):
            raise ValueError("Nonfinite projection")
        for probability in (
            p.appearance_probability,
            p.start_probability,
            p.minutes_60_probability,
        ):
            if probability is not None and (not isfinite(probability) or not 0 <= probability <= 1):
                raise ValueError("Invalid projection probability")
        if p.point_quantiles and any(not isfinite(v) for v in p.point_quantiles.values()):
            raise ValueError("Nonfinite quantile")
        if any(v is not None and not isfinite(v) for v in p.components.values()):
            raise ValueError("Nonfinite component")
        if p.event == event:
            totals[p.player_id] = totals.get(p.player_id, 0.0) + p.expected_points
    return totals


def validate_lineup(
    lineup: dict[str, Any], state: ManagerState, players: list[Player]
) -> list[str]:
    starters = lineup.get("starters", [])
    bench = lineup.get("bench", [])
    errors = validate_formation(starters, players)
    if (
        len(bench) != 4
        or set(starters + bench) != {p.player_id for p in state.picks}
        or len(set(starters + bench)) != 15
    ):
        errors.append("Lineup must partition squad")
    if (
        lineup.get("captain") not in starters
        or lineup.get("vice_captain") not in starters
        or lineup.get("captain") == lineup.get("vice_captain")
    ):
        errors.append("Captain and vice must be distinct starters")
    by_id = player_map(players)
    if (
        len(bench) == 4
        and all(i in by_id for i in bench)
        and (by_id[bench[0]].position != 1 or any(by_id[i].position == 1 for i in bench[1:]))
    ):
        errors.append("Reserve goalkeeper must occupy separate first bench slot")
    return errors


def select_lineup(
    state: ManagerState,
    players: list[Player],
    projections: list[Projection],
    event: int,
    chip: str | None = None,
) -> dict[str, Any]:
    errors = validate_squad(state, players)
    if errors:
        raise ValueError("; ".join(errors))
    if chip not in CHIPS | {None}:
        raise ValueError("Unknown chip")
    by_id = player_map(players)
    xp = projection_points(projections, event)
    groups = {
        pos: sorted(
            [p.player_id for p in state.picks if by_id[p.player_id].position == pos],
            key=lambda i: (-xp.get(i, 0), i),
        )
        for pos in range(1, 5)
    }
    best: tuple[float, list[int]] | None = None
    for d in range(3, 6):
        for m in range(2, 6):
            f = 10 - d - m
            if not 1 <= f <= 3:
                continue
            ids = groups[1][:1] + groups[2][:d] + groups[3][:m] + groups[4][:f]
            gross = sum(xp.get(i, 0) for i in ids) + (2 if chip == "triple_captain" else 1) * max(
                xp.get(i, 0) for i in ids
            )
            if best is None or gross > best[0]:
                best = gross, ids
    assert best is not None
    starters = best[1]
    captains = sorted(starters, key=lambda i: (-xp.get(i, 0), i))
    remaining = [p.player_id for p in state.picks if p.player_id not in starters]
    bench = sorted(remaining, key=lambda i: (by_id[i].position != 1, -xp.get(i, 0), i))
    gross = best[0]
    if chip == "bench_boost":
        gross += sum(xp.get(i, 0) for i in bench)
    result = {
        "starters": starters,
        "bench": bench,
        "captain": captains[0],
        "vice_captain": captains[1],
        "formation": "-".join(
            str(sum(by_id[i].position == pos for i in starters)) for pos in (2, 3, 4)
        ),
        "expected_points": gross,
        "assumptions": [
            "Unconditional fixture means summed; no extra availability multiplier",
            "No calibrated joint autosub or captain-fallback expectation; absent fixture rows treated as zero (blank or missing)",
        ],
    }
    if validate_lineup(result, state, players):
        raise ValueError("Generated illegal lineup")
    return result


@dataclass(frozen=True)
class MatchStats:
    minutes: int = 0
    goals: int = 0
    assists: int = 0
    goals_conceded_on_pitch: int = 0
    goals_conceded_after_red: int = 0
    saves: int = 0
    penalty_saves: int = 0
    penalty_misses: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0
    bonus: int = 0
    clearances: int = 0
    blocks: int = 0
    interceptions: int = 0
    tackles: int = 0
    recoveries: int = 0


def score_match(position: int, stats: MatchStats) -> int:
    if position not in range(1, 5) or any(
        type(v) is not int or v < 0 for v in vars(stats).values()
    ):
        raise ValueError("Invalid match stats")
    minutes = stats.minutes
    points = (
        (2 if minutes >= 60 else int(minutes > 0))
        + RULES.goal_points[position - 1] * stats.goals
        + 3 * stats.assists
    )
    conceded = stats.goals_conceded_on_pitch + (
        stats.goals_conceded_after_red if stats.red_cards else 0
    )
    if minutes >= 60 and conceded == 0:
        points += (4, 4, 1, 0)[position - 1]
    if position <= 2:
        points -= conceded // 2
    if position == 1:
        points += stats.saves // 3 + 5 * stats.penalty_saves
    points -= 2 * stats.penalty_misses
    points -= 3 * stats.red_cards if stats.red_cards else stats.yellow_cards
    points += stats.bonus - 2 * stats.own_goals
    actions = stats.clearances + stats.blocks + stats.interceptions + stats.tackles
    if position == 2 and actions >= 10 or position in (3, 4) and actions + stats.recoveries >= 12:
        points += 2
    return points


def bonus_points(bps: dict[int, int]) -> dict[int, int]:
    return {i: max(0, 3 - sum(v > score for v in bps.values())) for i, score in bps.items()}


def score_lineup(
    lineup: dict[str, Any],
    state: ManagerState,
    players: list[Player],
    outcomes: dict[int, list[MatchStats]],
    chip: str | None = None,
) -> dict[str, Any]:
    errors = validate_lineup(lineup, state, players)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = player_map(players)
    played = {
        i: any(s.minutes > 0 or s.yellow_cards or s.red_cards for s in rows)
        for i, rows in outcomes.items()
    }
    minutes = {i: sum(s.minutes for s in rows) for i, rows in outcomes.items()}
    starters = list(lineup["starters"])
    bench = list(lineup["bench"])
    substitutions = []
    if chip != "bench_boost":
        # Find the maximum legal substitutions, then lexicographically prefer bench priority.
        missing = [i for i in starters if not played.get(i, False)]
        candidates = [i for i in bench if played.get(i, False)]
        choices = []
        for n in range(min(len(missing), len(candidates)) + 1):
            for ins in combinations(candidates, n):
                for outs in combinations(missing, n):
                    ids = [i for i in starters if i not in outs] + list(ins)
                    if not validate_formation(ids, players):
                        choices.append(((-n, tuple(bench.index(i) for i in ins)), outs, ins, ids))
        if choices:
            _, outs, ins, starters = min(choices, key=lambda c: c[0])
            substitutions = [{"out": o, "in": i} for o, i in zip(outs, ins, strict=True)]
    scoring_ids = lineup["starters"] + bench if chip == "bench_boost" else starters
    scores = {
        i: sum(score_match(by_id[i].position, s) for s in outcomes.get(i, [])) for i in scoring_ids
    }
    captain = (
        lineup["captain"]
        if minutes.get(lineup["captain"], 0) > 0
        else lineup["vice_captain"]
        if minutes.get(lineup["vice_captain"], 0) > 0
        else None
    )
    total = sum(scores.values())
    if captain is not None:
        total += (2 if chip == "triple_captain" else 1) * scores.get(captain, 0)
    return {
        "points": total,
        "scoring_players": scoring_ids,
        "substitutions": substitutions,
        "effective_captain": captain,
    }
