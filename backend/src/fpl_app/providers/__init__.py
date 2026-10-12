"""Fixed-origin official ingestion and a separate, explicitly synthetic demo."""

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from fpl_app.contracts import Fixture, ManagerState, Pick, Player
from fpl_app.storage import Store


class Element(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = Field(gt=0)
    web_name: str
    team: int = Field(gt=0)
    element_type: int = Field(ge=1, le=4)
    now_cost: int = Field(ge=0)
    points_per_game: float
    minutes: int = Field(ge=0)
    goals_scored: int = Field(ge=0)
    assists: int = Field(ge=0)
    clean_sheets: int = Field(ge=0)
    status: str
    chance_of_playing_next_round: int | None = Field(default=None, ge=0, le=100)


class Bootstrap(BaseModel):
    elements: list[Element] = Field(min_length=1)
    events: list[dict[str, Any]] = Field(min_length=1)
    teams: list[dict[str, Any]] = Field(min_length=1)


def team_id(value: int | str) -> int:
    if isinstance(value, bool):
        raise ValueError("Invalid team ID")  # noqa: TRY004 - API validation contract
    text = str(value)
    if text.isdecimal():
        number = int(text)
    else:
        match = re.fullmatch(
            r"https://fantasy\.premierleague\.com/entry/([0-9]+)/event/([0-9]+)/?", text
        )
        if not match or not 1 <= int(match[2]) <= 38:
            raise ValueError("Use a numeric team ID or official Points page URL")
        number = int(match[1])
    if not 1 <= number <= 2_147_483_647:
        raise ValueError("Team ID out of range")
    return number


def parse(resource: str, value: Any) -> Any:
    if resource == "bootstrap-static/":
        parsed = Bootstrap.model_validate(value)
        ids = [p.id for p in parsed.elements]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate player IDs")
        for e in parsed.events:
            if not isinstance(e.get("id"), int) or "deadline_time" not in e:
                raise ValueError("Invalid event schema")
        return value
    if resource == "fixtures/":
        if not isinstance(value, list):
            raise ValueError("Invalid fixture schema")
        converted = [
            Fixture(
                fixture_id=p["id"],
                event=p["event"],
                home_club=p["team_h"],
                away_club=p["team_a"],
                kickoff=p.get("kickoff_time"),
                home_difficulty=p["team_h_difficulty"],
                away_difficulty=p["team_a_difficulty"],
            )
            for p in value
        ]
        if len({f.fixture_id for f in converted}) != len(converted):
            raise ValueError("Duplicate fixtures")
        return value
    if resource.endswith("/picks/"):
        picks = value["picks"]
        if len(picks) != 15 or len({p["element"] for p in picks}) != 15:
            raise ValueError("Invalid public squad")
        converted_picks = [
            Pick(
                player_id=p["element"],
                position=p["position"],
                is_captain=p["is_captain"],
                is_vice_captain=p["is_vice_captain"],
            )
            for p in picks
        ]
        if sorted(p.position for p in converted_picks) != list(range(1, 16)):
            raise ValueError("Invalid lineup positions")
        return value
    if re.fullmatch(r"element-summary/[1-9][0-9]*/", resource):
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("history"), list)
            or not isinstance(value.get("fixtures"), list)
            or not isinstance(value.get("history_past"), list)
        ):
            raise ValueError("Invalid player history schema")
        for row in value["history"]:
            if not all(
                isinstance(row.get(k), int) for k in ("fixture", "round", "minutes", "total_points")
            ):
                raise ValueError("Invalid history row")
        return value
    if resource.endswith("/history/"):
        if not isinstance(value, dict) or not all(
            isinstance(value.get(k), list) for k in ("current", "past", "chips")
        ):
            raise ValueError("Invalid manager history schema")
        return value
    if resource.endswith("/transfers/"):
        if not isinstance(value, list) or not all(
            all(k in row for k in ("element_in", "element_out", "event", "time")) for row in value
        ):
            raise ValueError("Invalid transfer schema")
        return value
    if re.fullmatch(r"event/[1-9][0-9]*/live/", resource):
        if not isinstance(value, dict) or not isinstance(value.get("elements"), list):
            raise ValueError("Invalid live event results schema")
        identifiers: list[int] = []
        for element in value["elements"]:
            stats = element.get("stats")
            if (
                not isinstance(element.get("id"), int)
                or element["id"] < 1
                or not isinstance(stats, dict)
                or type(stats.get("total_points")) is not int
                or type(stats.get("minutes")) is not int
                or not isinstance(element.get("explain"), list)
            ):
                raise ValueError("Invalid live event player result")
            identifiers.append(element["id"])
            for match in element["explain"]:
                if (
                    type(match.get("fixture")) is not int
                    or match["fixture"] < 1
                    or not isinstance(match.get("stats"), list)
                    or any(type(line.get("points")) is not int for line in match["stats"])
                ):
                    raise ValueError("Invalid fixture-level live event result")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Duplicate player in live event results")
        return value
    raise ValueError("Unsupported resource")


class Provider:
    def __init__(self, store: Store, transport: httpx.BaseTransport | None = None):
        self.store = store
        self.transport = transport
        self.last_request_at = 0.0
        self.minimum_interval = 0.1

    def fetch(self, resource: str, force: bool = False) -> dict[str, Any]:
        if (
            resource not in ("bootstrap-static/", "fixtures/")
            and not re.fullmatch(
                r"(?:entry/[1-9][0-9]*/(?:event/([1-9]|[12][0-9]|3[0-8])/picks/|history/|transfers/)|element-summary/[1-9][0-9]*/)",
                resource,
            )
            and not re.fullmatch(r"event/[1-9][0-9]*/live/", resource)
        ):
            raise ValueError("Unsupported provider path")
        cached = self.store.latest(resource)
        if cached and not force:
            age = (
                datetime.now(UTC) - datetime.fromisoformat(cached["captured_at"])
            ).total_seconds()
            if age < 21600:
                return cached
        with httpx.Client(transport=self.transport, timeout=15, follow_redirects=False) as client:
            import time
            from email.utils import parsedate_to_datetime

            for attempt in range(3):
                time.sleep(
                    max(0, self.minimum_interval - (time.monotonic() - self.last_request_at))
                )
                self.last_request_at = time.monotonic()
                try:
                    response = client.get("https://fantasy.premierleague.com/api/" + resource)
                except httpx.TransportError:
                    if attempt == 2:
                        raise
                    time.sleep(0.2 * 2**attempt)
                    continue
                if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                    response.raise_for_status()
                    break
                retry = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = (parsedate_to_datetime(retry) - datetime.now(UTC)).total_seconds()
                    except (ValueError, TypeError):
                        delay = 0.2 * 2**attempt
                if delay > 30:
                    response.raise_for_status()
                time.sleep(max(0, min(delay, 30)))
            raw = response.content
        try:
            value = json.loads(raw)
            parse(resource, value)
        except (ValueError, KeyError, TypeError) as exc:
            self.store.archive(raw, resource, valid=False)
            raise ValueError("Provider schema invalid; prior valid snapshot preserved") from exc
        identifier = self.store.archive(raw, resource)
        return self.store.snapshot(identifier)

    def refresh(self, force: bool = False) -> dict[str, Any]:
        bootstrap = self.fetch("bootstrap-static/", force)
        fixtures = self.fetch("fixtures/", force)
        data = dataset(bootstrap, fixtures)
        envelope = {
            "bootstrap_snapshot_id": bootstrap["id"],
            "fixture_snapshot_id": fixtures["id"],
            "available_at": data["source_cutoff"],
            "synthetic": False,
        }
        # Composite dataset is immutable, even when only fixtures change.
        from fpl_app.storage import fingerprint

        key = fingerprint(envelope)
        try:
            data = self.store.get("dataset_key", key)
        except KeyError:
            identifier = self.store.archive(
                json.dumps(envelope, sort_keys=True).encode(), "dataset"
            )
            data["snapshot_id"] = identifier
            self.store.put("dataset", identifier, data, expected=0)
            self.store.put("dataset_key", key, data, expected=0)
        self.store.put("current", "live", {"snapshot_id": data["snapshot_id"]})
        return data

    def player_history(self, player_id: int, force: bool = False) -> dict[str, Any]:
        identifier = team_id(player_id)
        snapshot = self.fetch(f"element-summary/{identifier}/", force)
        value = json.loads(snapshot["raw"])
        return {
            "snapshot_id": snapshot["id"],
            "history": value["history"],
            "appearances": sum(row["minutes"] > 0 for row in value["history"]),
            "source_cutoff": snapshot["available_at"],
        }

    def import_team(self, value: int | str) -> ManagerState:
        identifier = team_id(value)
        data = self.refresh()
        event = data["next_event"] - 1
        if event < 1:
            raise ValueError("No completed public deadline squad available")
        source = self.fetch(f"entry/{identifier}/event/{event}/picks/")
        picks = json.loads(source["raw"])["picks"]
        return ManagerState(
            team_id=identifier,
            snapshot_id=data["snapshot_id"],
            data_mode="live",
            next_event=data["next_event"],
            public_source_event=event,
            financial_provenance={
                k: "unknown"
                for k in (
                    "bank_units",
                    "free_transfers_at_event_start",
                    "transfers_made_this_event",
                    "confirmed_hit_points",
                )
            },
            chips={c: None for c in ("wildcard", "free_hit", "bench_boost", "triple_captain")},
            picks=[
                Pick(
                    player_id=p["element"],
                    position=p["position"],
                    is_captain=p["is_captain"],
                    is_vice_captain=p["is_vice_captain"],
                )
                for p in picks
            ],
            warnings=[
                "Public deadline squad; may miss recent transfers and lineup changes.",
                "Finances, transfers already made, persistent Free Hit squad and chips are unknown.",
                f"Public picks source snapshot: {source['id']}",
            ],
        )


def dataset(bootstrap: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    b = Bootstrap.model_validate(json.loads(bootstrap["raw"]))
    next_event = next((e["id"] for e in b.events if e.get("is_next")), None)
    if next_event is None:
        raise ValueError("Next event unavailable; season may be complete")
    return {
        "snapshot_id": bootstrap["id"],
        "fixture_snapshot_id": fixtures["id"],
        "bootstrap_snapshot_id": bootstrap["id"],
        "warnings": [
            "Appearance counts unavailable without selected player history; minutes estimates approximate."
        ],
        "data_mode": "live",
        "source_cutoff": max(bootstrap["available_at"], fixtures["available_at"]),
        "next_event": next_event,
        "events": b.events,
        "players": [
            Player(
                player_id=p.id,
                name=p.web_name,
                club=p.team,
                position=cast(Literal[1, 2, 3, 4], p.element_type),
                market_price_units=p.now_cost,
                points_per_game=p.points_per_game,
                minutes=p.minutes,
                availability=None
                if p.chance_of_playing_next_round is None
                else p.chance_of_playing_next_round / 100,
                appearances=0,
                goals=p.goals_scored,
                assists=p.assists,
                clean_sheets=p.clean_sheets,
                status=p.status,
            ).model_dump()
            for p in b.elements
        ],
        "fixtures": [
            Fixture(
                fixture_id=p["id"],
                event=p["event"],
                home_club=p["team_h"],
                away_club=p["team_a"],
                kickoff=p.get("kickoff_time"),
                home_difficulty=p["team_h_difficulty"],
                away_difficulty=p["team_a_difficulty"],
            ).model_dump()
            for p in json.loads(fixtures["raw"])
        ],
    }


def demo(store: Store) -> ManagerState:
    players = [
        Player(
            player_id=i + 1,
            name=f"Synthetic Player {i + 1}",
            club=i % 10 + 1,
            position=cast(Literal[1, 2, 3, 4], position),
            market_price_units=45 + i % 8 * 3,
            points_per_game=3 + i % 5 * 0.4,
            minutes=540,
            appearances=6,
            availability=1,
            goals=i % 3,
            assists=i % 2,
        )
        for i, position in enumerate([1] * 4 + [2] * 10 + [3] * 10 + [4] * 6)
    ]
    fixtures = [
        Fixture(fixture_id=event * 10 + club, event=event, home_club=club, away_club=club + 1)
        for event in range(8, 16)
        for club in range(1, 11, 2)
    ]
    demo_clock = datetime.now(UTC)
    events = [
        {
            "id": event,
            "deadline_time": (demo_clock + timedelta(days=1 + 7 * (event - 8))).isoformat(),
            "deadline_provenance": "authored_synthetic",
            "finished": False,
            "data_checked": False,
        }
        for event in range(1, 39)
    ]
    raw = json.dumps(
        {
            "synthetic": True,
            "events": events,
            "players": [p.model_dump() for p in players],
            "fixtures": [f.model_dump() for f in fixtures],
        }
    ).encode()
    snapshot = store.archive(raw, "demo", "demo")
    data = {
        "snapshot_id": snapshot,
        "data_mode": "demo",
        "source_cutoff": store.snapshot(snapshot)["available_at"],
        "next_event": 8,
        "events": events,
        "players": [p.model_dump() for p in players],
        "fixtures": [f.model_dump() for f in fixtures],
    }
    store.put("dataset", snapshot, data)
    store.put("current", "demo", {"snapshot_id": snapshot})
    chosen = [players[i] for i in [0, 1, 4, 5, 6, 7, 8, 14, 15, 16, 17, 18, 24, 25, 26]]
    # Legal 3-4-3 XI, reserve goalkeeper followed by outfield reserves.
    order = [0, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14, 1, 5, 6, 11]
    picks = [
        Pick(
            player_id=chosen[i].player_id,
            purchase_price_units=chosen[i].market_price_units,
            selling_price_units=chosen[i].market_price_units,
            selling_price_market_units=chosen[i].market_price_units,
            position=pos + 1,
            is_captain=pos == 4,
            is_vice_captain=pos == 5,
        )
        for pos, i in enumerate(order)
    ]
    for pick in picks:
        pick.selling_price_provenance = "synthetic"
        pick.acquisition_id = f"synthetic-{pick.player_id}"
    return ManagerState(
        current_chip_confirmed=True,
        financial_provenance={
            k: "synthetic"
            for k in (
                "bank_units",
                "free_transfers_at_event_start",
                "transfers_made_this_event",
                "confirmed_hit_points",
            )
        },
        team_id=0,
        snapshot_id=snapshot,
        bank_units=100,
        free_transfers_at_event_start=2,
        transfers_made_this_event=0,
        confirmed_hit_points=0,
        picks=picks,
        chips={c: True for c in ("wildcard", "free_hit", "bench_boost", "triple_captain")},
        event_start_picks=picks,
        event_start_bank_units=100,
        persistent_picks=picks,
        warnings=[
            "Entire dataset and manager are synthetic. No trained model or evaluation metrics."
        ],
    )
