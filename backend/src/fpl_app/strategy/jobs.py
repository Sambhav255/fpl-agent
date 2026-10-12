"""Recoverable, checksum-bound local policy fits; no arbitrary file requests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fpl_app.contracts import Settings
from fpl_app.models.training import data_dir
from fpl_app.storage import fingerprint


def training_input(payload):
    if set(payload) - {"synthetic_smoke", "episodes_data", "timesteps", "seeds", "settings"}:
        raise ValueError("Unknown strategy training inputs")
    smoke = payload.get("synthetic_smoke", False)
    if type(smoke) is not bool or smoke == ("episodes_data" in payload):
        raise ValueError("One explicit research dataset required")
    for field, lower, upper in [("timesteps", 64, 1_000_000), ("seeds", 5, 10)]:
        value = payload.get(field)
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError("Training configuration outside budget")
    if len(json.dumps(payload)) > 50_000_000:
        raise ValueError("Research payload exceeds budget")
    Settings.model_validate(payload["settings"])
    root = Path(__file__).parent
    digest = fingerprint(
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.py")}
    )
    return fingerprint({"kind": "strategy_training", "payload": payload, "implementation": digest})


def train_job(payload, job, queue, owner):
    from fpl_app.strategy.training import train_challenger

    if payload.get("synthetic_smoke"):
        from fpl_app.strategy.fixtures import synthetic_episode

        train = [synthetic_episode(i, "train") for i in range(100, 103)]
        test = [synthetic_episode(i, "test") for i in range(200, 203)]
    else:
        from fpl_app.strategy.datasets import episodes_from_payload

        episodes = episodes_from_payload(payload["episodes_data"])
        train = [e for e in episodes if e.partition == "train"]
        test = [e for e in episodes if e.partition == "test"]
    output = data_dir() / "models" / "strategy" / f"job-{job['id']}-attempt-{job['attempts']}"

    def progress(value):
        if not queue.heartbeat(job["id"], owner, min(float(value), 0.9)):
            raise ValueError("Training lease lost or job cancelled")

    meta, report = train_challenger(
        train,
        test,
        Settings.model_validate(payload["settings"]),
        output,
        seeds=tuple(range(payload["seeds"])),
        timesteps=payload["timesteps"],
        progress=progress,
    )
    meta["publication_job_id"] = job["id"]
    (output / "manifest.json").write_text(json.dumps(meta, sort_keys=True, indent=2))
    return {
        "artifact_id": meta["artifact_id"],
        "artifact_directory": str(output),
        "status": meta["status"],
        "promotion": report["promotion"],
        "active": False,
    }
