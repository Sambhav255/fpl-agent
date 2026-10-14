"""Durable single-worker queue with fencing leases and independent input checks."""

import time
import uuid
from collections.abc import Callable
from threading import Event, Thread
from typing import Any

from sqlalchemy import insert, select, update

from fpl_app.contracts import (
    AnalysisRequest,
    ManagerState,
    Player,
    ProjectionRun,
    Recommendation,
)
from fpl_app.storage import Conflict, Store, entities, fingerprint, jobs, utcnow


def input_state(store: Store, team: int) -> tuple[ManagerState, dict[str, Any]]:
    state = ManagerState.model_validate(store.get("state", team))
    data = store.get("dataset", state.snapshot_id)
    current = store.get("current", state.data_mode)
    if data["data_mode"] != state.data_mode:
        raise Conflict("Dataset mode differs from manager state")
    if current["snapshot_id"] != state.snapshot_id:
        raise Conflict("Manager snapshot is stale; refresh and confirm state")
    if state.data_mode == "live" and state.next_event != data["next_event"]:
        raise Conflict("Manager gameweek changed; review current squad and private finances")
    return state, data


def projection_players(
    state: ManagerState, data: dict[str, Any], run: ProjectionRun
) -> list[Player]:
    players = [Player.model_validate(p) for p in data["players"]]
    if run.player_universe_ids is None:
        if run.model_family != "baseline":
            raise ValueError("Advanced forecast requires explicit player coverage")
        return players
    universe = set(run.player_universe_ids)
    if len(universe) != len(run.player_universe_ids) or not universe:
        raise ValueError("Invalid forecast player universe")
    if not {p.player_id for p in state.picks} <= universe:
        raise ValueError("Forecast universe must include every owned player")
    selected = [p for p in players if p.player_id in universe]
    if len(selected) != len(universe):
        raise ValueError("Forecast universe contains unknown players")
    expected = {
        (p.player_id, f["fixture_id"], f["event"])
        for p in selected
        for f in data["fixtures"]
        if f["event"] is not None
        and state.next_event <= f["event"] < state.next_event + run.horizon_events
        and p.club in (f["home_club"], f["away_club"])
    }
    actual = [(p.player_id, p.fixture_id, p.event) for p in run.projections]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Forecast coverage differs from scheduled exposures")
    return selected


def inputs(store: Store, kind: str, payload: dict[str, Any]) -> str:
    if kind == "strategy_training":
        from fpl_app.strategy.jobs import training_input

        return training_input(payload)
    if kind == "learning_review":
        from fpl_app.learning.review import review_inputs

        return review_inputs(store, payload)
    if kind == "outcome_review":
        journal = store.get("decision_journal", payload["decision_id"])
        source = store.snapshot(payload["finalization_snapshot_id"])
        if (
            source["resource"] != "bootstrap-static/"
            or source["validation_status"] != "valid"
            or source["payload_sha256"] != payload["finalization_sha256"]
        ):
            raise Conflict("Official finalization snapshot changed")
        return fingerprint(
            {
                "kind": kind,
                "decision_id": payload["decision_id"],
                "forecast_sha256": journal["forecast_sha256"],
                "finalization_sha256": payload["finalization_sha256"],
            }
        )
    if kind == "collection":
        ids = payload.get("player_ids", [])
        include_all = payload.get("include_all", False)
        if (
            not isinstance(ids, list)
            or len(ids) > 1_000
            or any(type(identifier) is not int or identifier <= 0 for identifier in ids)
            or type(include_all) is not bool
            or (include_all and ids)
        ):
            raise ValueError("Collection requires a valid bounded player universe")
        return fingerprint({"kind": kind, "payload": payload})
    if kind == "refresh":
        return fingerprint({"kind": kind, "payload": payload})
    state, data = input_state(store, payload["team_id"])
    horizon = (
        payload["horizon_events"] if kind == "projection" else payload["settings"]["horizon_events"]
    )
    if state.next_event + horizon - 1 > 38:
        raise ValueError("Requested horizon extends beyond season")
    value: dict[str, Any] = {
        "kind": kind,
        "state": state.model_dump(),
        "data": data,
        "payload": payload,
    }
    if kind == "projection" and payload.get("_forecast", {}).get("provider") == "baseline":
        frozen = dict(payload["_forecast"])
        frozen.pop("prediction_origin", None)
        value["payload"] = {**payload, "_forecast": frozen}
        if frozen.get("replay_capture_id"):
            from fpl_app.learning.packets import checked_capture

            capture = checked_capture(
                store,
                frozen["replay_capture_id"],
                state,
                data,
                frozen["replay_capture_sha256"],
            )
            if capture["horizon_events"] != horizon:
                raise Conflict("Queued replay capture horizon changed")
    if kind == "projection" and payload.get("_forecast", {}).get("provider") not in (
        None,
        "baseline",
    ):
        from fpl_app.models.router import verify_artifact

        reference = payload["_forecast"]
        verify_artifact(reference)
        bundle = store.get("forecast_bundle", reference["serving_bundle_id"])
        if fingerprint(bundle) != reference["bundle_fingerprint"]:
            raise Conflict("Frozen forecast bundle changed")
        from fpl_app.models.advanced_serving import FAMILIES, checked_inputs

        if reference["provider"] in FAMILIES:
            checked_inputs(store, state, data, reference)
    if kind == "recommendation":
        if state.state_version != payload["expected_state_version"]:
            raise Conflict("Manager version is stale")
        run = ProjectionRun.model_validate(store.get("projection", payload["projection_run_id"]))
        if run.snapshot_id != state.snapshot_id or run.data_mode != state.data_mode:
            raise Conflict("Projection snapshot or mode is stale")
        if run.horizon_events < payload["settings"]["horizon_events"]:
            raise Conflict("Projection horizon is too short")
        if run.source_cutoff != data["source_cutoff"]:
            raise Conflict("Projection cutoff is stale")
        projection_players(state, data, run)
        value["run"] = run.model_dump()
    return fingerprint(value)


class Queue:
    def __init__(self, store: Store, lease_seconds: float = 30, max_attempts: int = 3):
        self.store = store
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts

    def enqueue(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if kind == "projection" and "_forecast" not in payload:
            from fpl_app.models.router import resolve_forecast

            state, _ = input_state(self.store, payload["team_id"])
            payload = {**payload, "_forecast": resolve_forecast(self.store, payload, state)}
        digest = inputs(self.store, kind, payload)
        with self.store.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            # Recheck while holding the write lock before deduplicating/queuing.
            if inputs(self.store, kind, payload) != digest:
                raise Conflict("Inputs changed while queuing")
            existing = (
                connection.execute(
                    select(jobs).where(
                        jobs.c.fingerprint == digest,
                        jobs.c.status.in_(
                            ["queued", "running"]
                            if kind in {"refresh", "collection", "outcome_review"}
                            else ["queued", "running", "succeeded", "cancelled"]
                            if kind == "learning_review"
                            else ["queued", "running", "succeeded"]
                        ),
                    )
                )
                .mappings()
                .first()
            )
            if existing:
                return dict(existing)
            identifier = uuid.uuid4().hex
            connection.execute(
                insert(jobs).values(
                    id=identifier,
                    kind=kind,
                    payload=payload,
                    fingerprint=digest,
                    status="queued",
                    progress=0,
                    attempts=0,
                    owner=None,
                    lease_until=None,
                    heartbeat_at=None,
                    cancel_requested=False,
                    result=None,
                    error=None,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
        return self.get(identifier)

    def get(self, identifier: str) -> dict[str, Any]:
        with self.store.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == identifier)).mappings().first()
        if row is None:
            raise KeyError(identifier)
        return dict(row)

    def cancel(self, identifier: str) -> dict[str, Any]:
        with self.store.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(jobs.c.id == identifier, jobs.c.status.in_(["queued", "running"]))
                .values(
                    cancel_requested=True,
                    status="cancelled",
                    owner=None,
                    lease_until=None,
                    updated_at=utcnow(),
                )
            )
        return self.get(identifier)

    def claim(self, owner: str) -> dict[str, Any] | None:
        now = time.time()
        with self.store.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            expired = (jobs.c.status == "running") & (jobs.c.lease_until < now)
            connection.execute(
                update(jobs)
                .where(expired, jobs.c.attempts >= self.max_attempts)
                .values(
                    status="failed",
                    error={"code": "retry_exhausted", "message": "Worker lease expired"},
                    owner=None,
                    lease_until=None,
                    updated_at=utcnow(),
                )
            )
            connection.execute(
                update(jobs)
                .where(expired, jobs.c.attempts < self.max_attempts)
                .values(status="queued", owner=None, lease_until=None, updated_at=utcnow())
            )
            row = (
                connection.execute(
                    select(jobs)
                    .where(jobs.c.status == "queued", jobs.c.cancel_requested.is_(False))
                    .order_by(jobs.c.created_at)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            connection.execute(
                update(jobs)
                .where(jobs.c.id == row["id"])
                .values(
                    status="running",
                    owner=owner,
                    lease_until=now + self.lease_seconds,
                    heartbeat_at=now,
                    attempts=row["attempts"] + 1,
                    updated_at=utcnow(),
                )
            )
            result = dict(row)
            result.update(status="running", owner=owner, attempts=row["attempts"] + 1)
            return result

    def heartbeat(self, identifier: str, owner: str, progress: float = 0.1) -> bool:
        now = time.time()
        with self.store.engine.begin() as connection:
            result = connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == identifier,
                    jobs.c.owner == owner,
                    jobs.c.status == "running",
                    jobs.c.lease_until > now,
                    jobs.c.cancel_requested.is_(False),
                )
                .values(
                    heartbeat_at=now,
                    lease_until=now + self.lease_seconds,
                    progress=progress,
                    updated_at=utcnow(),
                )
            )
        return result.rowcount == 1

    def finish(
        self,
        identifier: str,
        owner: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> bool:
        with self.store.engine.begin() as connection:
            changed = connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == identifier,
                    jobs.c.owner == owner,
                    jobs.c.status == "running",
                    jobs.c.lease_until > time.time(),
                    jobs.c.cancel_requested.is_(False),
                )
                .values(
                    status="failed" if error else "succeeded",
                    result=result,
                    error=error,
                    progress=1,
                    owner=None,
                    lease_until=None,
                    updated_at=utcnow(),
                )
            )
        return changed.rowcount == 1

    def publish(
        self,
        job: dict[str, Any],
        owner: str,
        result: dict[str, Any],
        artifacts: list[tuple[str, str, dict[str, Any]]],
    ) -> bool:
        """Fence output persistence and completion together; no cancelled output leaks."""
        with self.store.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            current = (
                connection.execute(select(jobs).where(jobs.c.id == job["id"])).mappings().first()
            )
            if (
                current is None
                or current["owner"] != owner
                or current["status"] != "running"
                or current["cancel_requested"]
                or current["lease_until"] <= time.time()
            ):
                return False
            # The reserved write lock prevents state/current pointers changing between
            # this independent fingerprint check and output commit.
            if (
                job["kind"] != "refresh"
                and inputs(self.store, job["kind"], job["payload"]) != job["fingerprint"]
            ):
                raise Conflict("Inputs changed before publication")
            for kind, identifier, payload in artifacts:
                prior = connection.execute(
                    select(entities.c.payload).where(
                        entities.c.kind == kind, entities.c.id == identifier
                    )
                ).first()
                if prior is not None:
                    if prior[0] != payload:
                        raise Conflict("Immutable output identifier already exists")
                    continue
                connection.execute(
                    insert(entities).values(
                        kind=kind, id=identifier, version=1, payload=payload, updated_at=utcnow()
                    )
                )
            connection.execute(
                update(jobs)
                .where(jobs.c.id == job["id"])
                .values(
                    status="succeeded",
                    result=result,
                    error=None,
                    progress=1,
                    owner=None,
                    lease_until=None,
                    updated_at=utcnow(),
                )
            )
        return True


class Worker:
    def __init__(
        self,
        queue: Queue,
        provider: Any = None,
        handlers: dict[str, Callable[..., Any]] | None = None,
    ):
        self.queue = queue
        self.store = queue.store
        self.owner = uuid.uuid4().hex
        self.provider = provider
        self.handlers = handlers or {}

    def compute(self, job: dict[str, Any]) -> dict[str, Any]:
        kind, payload = job["kind"], job["payload"]
        if kind in self.handlers:
            return dict(self.handlers[kind](payload))
        if kind == "strategy_training":
            from fpl_app.strategy.jobs import train_job

            return train_job(payload, job, self.queue, self.owner)
        if kind == "learning_review":
            from fpl_app.learning.review import run_review
            from fpl_app.providers import Provider

            return run_review(self.store, self.provider or Provider(self.store), payload["tick_id"])
        if kind == "outcome_review":
            from fpl_app.learning.outcomes import collect_finalized_outcomes
            from fpl_app.providers import Provider

            outcome, scorecard = collect_finalized_outcomes(
                self.store,
                self.provider or Provider(self.store),
                payload["decision_id"],
                payload["finalization_sha256"],
            )
            revision = outcome["revision"]
            return {
                "decision_id": payload["decision_id"],
                "revision": revision,
                "metrics": scorecard["metrics"],
                "_artifacts": [
                    ("learning_outcome", f"{payload['decision_id']}:{revision}", outcome),
                    ("learning_scorecard", f"{payload['decision_id']}:{revision}", scorecard),
                ],
            }
        if kind == "refresh":
            from fpl_app.providers import Provider

            return dict(
                (self.provider or Provider(self.store)).refresh(payload.get("force", False))
            )
        if kind == "collection":
            from fpl_app.providers.collection import collect_football

            return collect_football(
                self.store,
                provider=self.provider,
                player_ids=payload.get("player_ids"),
                force=payload.get("force", True),
                include_all=payload.get("include_all", False),
            )
        state, data = input_state(self.store, payload["team_id"])
        players = [Player.model_validate(p) for p in data["players"]]
        if kind == "projection":
            from fpl_app.models.router import forecast_job

            return dict(forecast_job(self.store, state, data, payload).model_dump(mode="json"))
        if kind == "recommendation":
            from fpl_app.optimisation import recommend

            request = AnalysisRequest.model_validate(payload)
            run = ProjectionRun.model_validate(
                self.store.get("projection", request.projection_run_id)
            )
            players = projection_players(state, data, run)
            recommendation = recommend(
                state, players, run, request.settings, lineup_only=request.analysis_mode == "lineup"
            )
            return dict(recommendation.model_dump(mode="json"))
        raise ValueError("Unsupported job kind")

    def run_once(self) -> bool:
        job = self.queue.claim(self.owner)
        if job is None:
            return False
        stop = Event()

        def pulse() -> None:
            while not stop.wait(max(0.01, self.queue.lease_seconds / 3)):
                if not self.queue.heartbeat(job["id"], self.owner):
                    return

        thread = Thread(target=pulse, daemon=True)
        thread.start()
        try:
            if inputs(self.store, job["kind"], job["payload"]) != job["fingerprint"]:
                raise Conflict("Queued inputs changed")
            result = self.compute(job)
            if (
                job["kind"] != "refresh"
                and inputs(self.store, job["kind"], job["payload"]) != job["fingerprint"]
            ):
                raise Conflict("Inputs changed during computation")
            if not self.queue.heartbeat(job["id"], self.owner, 0.95):
                return True
            artifacts: list[tuple[str, str, dict[str, Any]]] = []
            if job["kind"] == "projection":
                run = ProjectionRun.model_validate(result)
                artifacts.append(("projection", run.projection_run_id, result))
            elif job["kind"] == "recommendation":
                recommendation = Recommendation.model_validate(result)
                artifacts.extend(
                    [
                        ("recommendation", recommendation.recommendation_id, result),
                        (
                            "recommendation_input",
                            recommendation.recommendation_id,
                            {"fingerprint": job["fingerprint"], "payload": job["payload"]},
                        ),
                    ]
                )
            elif job["kind"] in {"outcome_review", "learning_review"}:
                artifacts.extend(result.pop("_artifacts"))
            self.queue.publish(job, self.owner, result, artifacts)
        except Exception as exc:  # noqa: BLE001 - worker must persist arbitrary computation failures
            code = "STALE_INPUTS" if isinstance(exc, Conflict) else "COMPUTATION_FAILED"
            # Do not persist exception text containing provider URLs/private payloads.
            self.queue.finish(
                job["id"],
                self.owner,
                error={
                    "code": code,
                    "message": "Inputs are stale"
                    if code == "STALE_INPUTS"
                    else "Computation failed",
                    "exception_type": type(exc).__name__,
                },
            )
        finally:
            stop.set()
            thread.join(timeout=1)
        return True
