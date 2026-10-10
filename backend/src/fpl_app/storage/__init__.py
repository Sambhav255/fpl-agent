"""SQLite schema v1.

schema_versions: applied migration numbers. entities: (kind,id) JSON envelope,
version, updated_at; manager state updates use compare-and-swap. snapshots:
immutable exact BLOB bytes, sha256, provider/resource, capture/availability,
validation status and schema. jobs: durable payload/result JSON, fingerprint,
attempts, progress, lease owner/expiry/heartbeat, cancellation and error.
Money remains integer units in contract JSON; unknown fields remain null.
Migration v1 is additive and transactional. No destructive automatic migrations.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    event,
    insert,
    select,
    update,
)
from sqlalchemy.pool import StaticPool

metadata = MetaData()
versions = Table("schema_versions", metadata, Column("version", Integer, primary_key=True))
entities = Table(
    "entities",
    metadata,
    Column("kind", String, primary_key=True),
    Column("id", String, primary_key=True),
    Column("version", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("updated_at", String, nullable=False),
)
snapshots = Table(
    "source_snapshots",
    metadata,
    Column("id", String, primary_key=True),
    Column("provider", String),
    Column("resource", String),
    Column("data_mode", String),
    Column("captured_at", String),
    Column("available_at", String),
    Column("source_published_at", String),
    Column("payload_sha256", String),
    Column("schema_version", Integer),
    Column("season", String),
    Column("validation_status", String),
    Column("storage_path", String),
    Column("raw", LargeBinary, nullable=False),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("kind", String),
    Column("payload", JSON),
    Column("fingerprint", String, index=True),
    Column("status", String, index=True),
    Column("progress", Float),
    Column("attempts", Integer),
    Column("owner", String),
    Column("lease_until", Float),
    Column("heartbeat_at", Float),
    Column("cancel_requested", Boolean),
    Column("result", JSON),
    Column("error", JSON),
    Column("created_at", String),
    Column("updated_at", String),
)


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class Conflict(ValueError):
    pass


def database_url() -> str:
    """Shared API/worker default independent of process working directory."""
    import os
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    data = Path(os.environ.get("DATA_DIR", str(root / "data")))
    if not data.is_absolute():
        data = root / "backend" / data
    configured = os.environ.get("DATABASE_URL", os.environ.get("FPL_DATABASE_URL"))
    if configured:
        if configured.startswith("sqlite:///") and ":memory:" not in configured:
            path = Path(configured.removeprefix("sqlite:///"))
            if not path.is_absolute():
                path = root / "backend" / path
            return f"sqlite:///{path.resolve()}"
        return configured
    return f"sqlite:///{data.resolve() / 'app.sqlite'}"


class Store:
    def __init__(self, url: str | None = None):
        url = url or database_url()
        if url.startswith("sqlite:///") and ":memory:" not in url:
            from pathlib import Path

            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        options: dict[str, Any] = {"connect_args": {"check_same_thread": False, "timeout": 10}}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
        self.engine = create_engine(url, **options)

        @event.listens_for(self.engine, "connect")
        def configure(connection: Any, record: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            applied: list[int] = list(
                connection.execute(select(versions.c.version)).scalars().all()
            )
            if any(version > 1 for version in applied):
                raise ValueError("Database schema newer than this application")
            if not applied:
                connection.execute(insert(versions).values(version=1))

    def get(self, kind: str, identifier: str | int) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(entities.c.payload).where(
                    entities.c.kind == kind, entities.c.id == str(identifier)
                )
            ).first()
        if row is None:
            raise KeyError(identifier)
        return dict(row[0])

    def put(
        self, kind: str, identifier: str | int, payload: dict[str, Any], expected: int | None = None
    ) -> int:
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            condition = (entities.c.kind == kind) & (entities.c.id == str(identifier))
            old = connection.execute(select(entities.c.version).where(condition)).first()
            if old is None:
                if expected not in (None, 0):
                    raise Conflict("Entity no longer matches expected version")
                version = 1
                connection.execute(
                    insert(entities).values(
                        kind=kind,
                        id=str(identifier),
                        version=version,
                        payload=payload,
                        updated_at=utcnow(),
                    )
                )
            else:
                if expected is not None and old[0] != expected:
                    raise Conflict("Entity version changed")
                version = old[0] + 1
                result = connection.execute(
                    update(entities)
                    .where(condition, entities.c.version == old[0])
                    .values(version=version, payload=payload, updated_at=utcnow())
                )
                if result.rowcount != 1:
                    raise Conflict("Concurrent edit")
        return version

    def put_checked(self, kind: str, identifier: str, payload: dict[str, Any], verify: Any) -> None:
        """Verify inputs and persist under a reserved SQLite write transaction."""
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            verify()
            existing = connection.execute(
                select(entities.c.payload).where(
                    entities.c.kind == kind, entities.c.id == identifier
                )
            ).first()
            if existing is not None:
                # Saving the same selected plan is idempotent.
                return
            connection.execute(
                insert(entities).values(
                    kind=kind, id=identifier, version=1, payload=payload, updated_at=utcnow()
                )
            )

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                dict(row[0])
                for row in connection.execute(
                    select(entities.c.payload).where(entities.c.kind == kind)
                )
            ]

    def delete_team(self, identifier: int) -> None:
        self.get("state", identifier)
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.execute(
                delete(entities).where(entities.c.kind == "state", entities.c.id == str(identifier))
            )
            for row in (
                connection.execute(
                    select(entities).where(entities.c.kind == "recommendation_input")
                )
                .mappings()
                .all()
            ):
                if row["payload"].get("payload", {}).get("team_id") == identifier:
                    connection.execute(
                        delete(entities).where(
                            entities.c.kind.in_(["recommendation", "recommendation_input"]),
                            entities.c.id == row["id"],
                        )
                    )
            connection.execute(
                delete(jobs).where(
                    jobs.c.id.in_(
                        [
                            row["id"]
                            for row in connection.execute(select(jobs)).mappings().all()
                            if row["payload"].get("team_id") == identifier
                        ]
                    )
                )
            )
            # State-bound plans are removed; public immutable sources stay archived.
            for row in connection.execute(
                select(entities).where(entities.c.kind == "plan")
            ).mappings():
                if row["payload"].get("team_id") == identifier:
                    connection.execute(
                        delete(entities).where(
                            entities.c.kind == "plan", entities.c.id == row["id"]
                        )
                    )
            for row in connection.execute(
                select(jobs).where(jobs.c.status.in_(["queued", "running"]))
            ).mappings():
                if row["payload"].get("team_id") == identifier:
                    connection.execute(
                        update(jobs)
                        .where(jobs.c.id == row["id"])
                        .values(status="cancelled", cancel_requested=True, owner=None)
                    )

    def archive(self, raw: bytes, resource: str, mode: str = "live", valid: bool = True) -> str:
        import uuid

        identifier = uuid.uuid4().hex
        timestamp = utcnow()
        with self.engine.begin() as connection:
            connection.execute(
                insert(snapshots).values(
                    id=identifier,
                    provider="synthetic" if mode == "demo" else "official_fpl",
                    resource=resource,
                    data_mode=mode,
                    captured_at=timestamp,
                    available_at=timestamp,
                    source_published_at=None,
                    payload_sha256=hashlib.sha256(raw).hexdigest(),
                    schema_version=1,
                    season="2026/27",
                    validation_status="valid" if valid else "invalid",
                    storage_path=f"sqlite:source_snapshots/{identifier}",
                    raw=raw,
                )
            )
        return identifier

    def snapshot(self, identifier: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(snapshots).where(snapshots.c.id == identifier))
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError(identifier)
        return dict(row)

    def latest(self, resource: str, mode: str = "live") -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(snapshots)
                    .where(
                        snapshots.c.resource == resource,
                        snapshots.c.data_mode == mode,
                        snapshots.c.validation_status == "valid",
                    )
                    .order_by(snapshots.c.captured_at.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None
