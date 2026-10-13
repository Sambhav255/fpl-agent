"""Official football replay reconstruction, with explicit unverified historical timing.

No manager state is read. Initial portfolios are paper squads bought at a declared
reconstructed price. Actual source capture times never become historical evidence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from fpl_app.contracts import Fixture, ManagerState, Pick, Player
from fpl_app.domain.rules import CHIPS, RULES, OfficialEventPoints, readiness
from fpl_app.evaluation.strategy import ReplayOrigin
from fpl_app.models.baseline import baseline_run
from fpl_app.storage import fingerprint, utcnow

ADAPTER_VERSION = "official-history-reconstructed-v2"
LABEL_LAG_HOURS = 27


def reconstruct_collection(
    collection: dict[str, Any],
    *,
    train_events: list[int],
    test_events: list[int],
    universe_size: int = 40,
    starting_squads: int = 1,
):
    """Build chronological episodes from finalized official rows, never guessed zeros.

    Schedule and current-club membership are retrospective reconstructions. The
    declared +27h label delay is an assumption, separate from actual capture time.
    Prices carry forward the last available earlier history value, not the target
    event's price. Selection uses development forecasts and coverage, never test
    points. All policies receive this same restricted covered universe.
    """
    from fpl_app.strategy.environment import Episode

    body = {k: v for k, v in collection.items() if k != "envelope_sha256"}
    if collection.get("envelope_sha256") != fingerprint(body):
        raise ValueError("Collection checksum mismatch")
    if collection.get("season", "").replace("-", "/") != RULES.season:
        raise ValueError("Historical collection requires its compatible season rules")
    if not 20 <= universe_size <= 100 or not 1 <= starting_squads <= 5:
        raise ValueError("Reconstruction outside declared CPU/universe budget")
    blocks = [train_events, test_events]
    if any(not events or events != list(range(min(events), max(events) + 1)) for events in blocks):
        raise ValueError("Contiguous explicit development/test blocks required")
    if max(train_events) >= min(test_events) or min(train_events) < 2 or max(test_events) >= 38:
        raise ValueError("Chronological blocks and forecast-only bootstrap event required")
    deadlines = {int(e["event"]): str(e["actual_deadline"]) for e in collection["event_evidence"]}
    fixtures = {int(f["id"]): f for f in collection["fixture_versions"]}
    rows: dict[int, list[dict[str, Any]]] = {}
    for row in collection["labels"]:
        rows.setdefault(int(row["provider_player_id"]), []).append(row)
    finalized = {r["event"] for r in collection["labels"] if r["label_status"] == "final_revision"}
    if not set(train_events + test_events) <= finalized:
        raise ValueError("Requested outcome block is not provider-finalized")
    if any(
        not f.get("finished_provisional")
        for f in fixtures.values()
        if f.get("event") in train_events + test_events
    ):
        raise ValueError("Incomplete event fixture finalization")
    required_events = sorted(
        set(train_events + test_events + [max(train_events) + 1, max(test_events) + 1])
    )
    mappings = {int(m["provider_player_id"]): m for m in collection["player_mappings"]}
    rejected: Counter[str] = Counter()
    eligible = []
    for identifier, mapping in mappings.items():
        history = rows.get(identifier, [])
        try:
            for event in required_events:
                _origin_player(identifier, mapping, history, fixtures, deadlines[event], event)
                if event in train_events + test_events:
                    _outcome(identifier, mapping, history, fixtures, event)
        except (ValueError, KeyError) as exc:
            rejected[str(exc)] += 1
            continue
        eligible.append(identifier)
    # Prospectively fixed selection recipe, ranked exclusively at first development origin.
    first = min(train_events)
    ranking = {
        i: _origin_player(i, mappings[i], rows[i], fixtures, deadlines[first], first)
        for i in eligible
    }
    quotas = {
        1: max(3, universe_size * 2 // 15),
        2: universe_size * 5 // 15,
        3: universe_size * 5 // 15,
        4: universe_size * 3 // 15,
    }
    quotas[3] += universe_size - sum(quotas.values())
    selected = []
    for position, quota in quotas.items():
        choices = sorted(
            (i for i in eligible if mappings[i]["position"] == position),
            key=lambda i: (-ranking[i].points_per_game / max(1, ranking[i].market_price_units), i),
        )
        if len(choices) < RULES.squad_counts[position - 1] + 1:
            raise ValueError("Insufficient covered players for legal position alternatives")
        selected.extend(choices[:quota])
    selected.sort()
    produced = utcnow()
    origins = {}
    for event in required_events:
        players = [
            _origin_player(i, mappings[i], rows[i], fixtures, deadlines[event], event)
            for i in selected
        ]
        known_fixtures = [
            Fixture(
                fixture_id=f["id"],
                event=event,
                home_club=f["team_h"],
                away_club=f["team_a"],
                kickoff=f["kickoff_time"],
                home_difficulty=3,
                away_difficulty=3,
            )
            for f in fixtures.values()
            if f.get("event") == event
        ]
        run = baseline_run(
            players,
            known_fixtures,
            f"reconstructed-{collection['envelope_sha256'][:12]}-{event}",
            deadlines[event],
            "live",
            event,
            1,
        )
        run.prediction_origin = produced
        run.evidence_mode = "historical_reconstructed"
        run.warnings += [
            "Captured schedule/current membership reconstructed; historical publication unavailable",
            "Neutral fixture difficulty; historical availability unknown and assumed available",
        ]
        origins[event] = ReplayOrigin(
            deadlines[event],
            deadlines[event],
            players,
            run,
            {},
            evidence_mode="historical_reconstructed",
            financial_coverage="reconstructed_prior_history_prices_paper_purchase_basis",
            fitting_labels_available_at=deadlines[event],
            official_outcomes={
                i: _outcome(i, mappings[i], rows[i], fixtures, event) for i in selected
            }
            if event in train_events + test_events
            else {},
        )
    episodes: dict[str, list[Episode]] = {"train": [], "test": []}
    for partition, events in zip(("train", "test"), blocks, strict=True):
        origin = origins[min(events)]
        for seed in range(starting_squads):
            initial = _paper_squad(origin, min(events), seed)
            episodes[partition].append(
                Episode(
                    f"{partition}-paper-{seed}",
                    initial,
                    tuple(origins[e] for e in events),
                    partition,
                    f"official-{collection['season']}-events-{'-'.join(map(str, events))}",
                    replace(origins[max(events) + 1], outcomes={}, official_outcomes={}),
                )
            )
    audit = {
        "adapter_version": ADAPTER_VERSION,
        "adapter_implementation_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "collection_id": collection["collection_id"],
        "collection_sha256": collection["envelope_sha256"],
        "actual_produced_at": produced,
        "source_receipts": collection["sources"],
        "rules_version": RULES.version,
        "season": collection["season"],
        "independent_actual_seasons": 1,
        "train_events": train_events,
        "test_events": test_events,
        "forecast_horizon": 1,
        "eligible_complete_players": len(eligible),
        "selected_player_ids": selected,
        "universe_selection": "position-balanced development-only points/price rank on common coverage",
        "coverage_rejections": dict(rejected),
        "starting_squads_per_block": starting_squads,
        "assumed_label_lag_hours": LABEL_LAG_HOURS,
        "original_label_publication": "unverified; actual retained availability stays in source receipts",
        "price_mode": "last earlier assumed-available history value, synthetic purchase at initial origin",
        "limitations": [
            "One actual season segment; seeds and paper starts are not independent seasons",
            "Retrospective complete-case coverage and current-club membership restrict generalisation",
            "Historical schedule publication and label finalization times are assumed, not verified",
            "One-lead baseline forecasts only; no repeated one-lead predictions used as a longer forecast",
            "No actual manager inputs, account actions or policy promotion",
        ],
    }
    return episodes["train"], episodes["test"], audit


def _scheduled(mapping, fixtures, event):
    return [
        f
        for f in fixtures.values()
        if f.get("event") == event and mapping["provider_club_id"] in (f["team_h"], f["team_a"])
    ]


def _outcome(identifier, mapping, history, fixtures, event):
    expected = {f["id"] for f in _scheduled(mapping, fixtures, event)}
    actual = [r for r in history if r["event"] == event]
    if {r["fixture_id"] for r in actual} != expected or len(actual) != len(expected):
        raise ValueError("Missing or mismatched historical fixture coverage")
    if any(
        r["label_status"] != "final_revision"
        or type(r["minutes"]) is not int
        or type(r["total_points"]) is not int
        for r in actual
    ):
        raise ValueError("Unfinalized or missing official outcome")
    for r in actual:
        if r["minutes"] == 0:
            cards = [r["statistics"].get(key) for key in ("yellow_cards", "red_cards")]
            if any(type(value) is not int or value < 0 for value in cards):
                raise ValueError("Missing official participation coverage")
            if any(cards) or r["total_points"] != 0:
                raise ValueError(
                    "Zero-minute cards/points require reconciled participation coverage"
                )
        f = fixtures[r["fixture_id"]]
        if type(r["statistics"].get("was_home")) is not bool:
            raise ValueError("Missing historical club membership evidence")
        inferred = f["team_h"] if r["statistics"].get("was_home") is True else f["team_a"]
        if inferred != mapping["provider_club_id"]:
            raise ValueError("Historical club membership mismatch")
    return OfficialEventPoints(
        sum(r["total_points"] for r in actual),
        sum(r["minutes"] for r in actual),
        any(r["minutes"] > 0 for r in actual),
    )


def _origin_player(identifier, mapping, history, fixtures, deadline, event):
    origin = pd.Timestamp(deadline)
    prior = [
        r
        for r in history
        if r["event"] < event
        and r["label_status"] == "final_revision"
        and fixtures.get(r["fixture_id"], {}).get("kickoff_time") is not None
        and pd.Timestamp(fixtures[r["fixture_id"]]["kickoff_time"])
        + timedelta(hours=LABEL_LAG_HOURS)
        < origin
    ]
    if not prior:
        raise ValueError("No earlier assumed-available price/history")
    if any(type(r["minutes"]) is not int or type(r["total_points"]) is not int for r in prior):
        raise ValueError("Missing earlier official points/minutes")
    prior.sort(key=lambda r: fixtures[r["fixture_id"]]["kickoff_time"])
    price = prior[-1]["statistics"].get("value")
    if type(price) is not int or price <= 0:
        raise ValueError("Missing historical price")
    keys = ["goals_scored", "assists", "clean_sheets"]
    if any(type(r["statistics"].get(k)) is not int for r in prior for k in keys):
        raise ValueError("Missing earlier baseline statistics")
    appearances = sum(r["minutes"] > 0 for r in prior)
    return Player(
        player_id=identifier,
        name=f"Official player {identifier}",
        club=mapping["provider_club_id"],
        position=cast(Literal[1, 2, 3, 4], mapping["position"]),
        market_price_units=price,
        points_per_game=sum(r["total_points"] for r in prior) / max(1, appearances),
        minutes=sum(r["minutes"] for r in prior),
        appearances=appearances,
        goals=sum(r["statistics"]["goals_scored"] for r in prior),
        assists=sum(r["statistics"]["assists"] for r in prior),
        clean_sheets=sum(r["statistics"]["clean_sheets"] for r in prior),
        availability=None,
    )


def _paper_squad(origin, event, seed):
    players = origin.players
    n = len(players)
    xp = {
        p.player_id: sum(
            r.expected_points for r in origin.forecasts.projections if r.player_id == p.player_id
        )
        for p in players
    }
    rng = np.random.default_rng(seed)
    objective = np.array([-xp[p.player_id] + rng.uniform(-0.1, 0.1) for p in players])
    vectors = [np.array([float(p.position == pos) for p in players]) for pos in range(1, 5)]
    lower = list(RULES.squad_counts)
    upper = list(RULES.squad_counts)
    vectors.append(np.array([p.market_price_units for p in players]))
    lower.append(0)
    upper.append(1000)
    for club in sorted({p.club for p in players}):
        vectors.append(np.array([float(p.club == club) for p in players]))
        lower.append(0)
        upper.append(3)
    result = milp(
        objective,
        integrality=np.ones(n),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(np.stack(vectors), lower, upper),
        options={"time_limit": 2},
    )
    if result.x is None:
        raise ValueError("No legal paper starting squad in covered universe")
    chosen = [p for p, value in zip(players, result.x, strict=True) if value > 0.5]
    picks = [
        Pick(
            player_id=p.player_id,
            position=j + 1,
            purchase_price_units=p.market_price_units,
            acquisition_id=f"paper-{seed}-{event}-{p.player_id}",
        )
        for j, p in enumerate(chosen)
    ]
    bank = 1000 - sum(p.market_price_units for p in chosen)
    state = ManagerState(
        team_id=1,
        season=RULES.season,
        next_event=event,
        data_mode="live",
        snapshot_id=origin.forecasts.snapshot_id,
        bank_units=bank,
        free_transfers_at_event_start=1,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        current_chip_confirmed=True,
        picks=picks,
        event_start_picks=picks,
        event_start_bank_units=bank,
        chips={f"{c}_{w}": False for c in CHIPS for w in (1, 2)},
        financial_provenance={"all": "paper initial purchase; not actual manager state"},
    )
    if not readiness(state, players)["transfers_ready"]:
        raise ValueError("Independently invalid paper starting squad")
    return state
