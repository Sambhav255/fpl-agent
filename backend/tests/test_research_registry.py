"""Authored registry contracts do not constitute training or real-data evidence."""

import hashlib
import json

import pytest

from fpl_app.models.registry import registry
from fpl_app.storage import fingerprint


def artifact(tmp_path, family):
    directory = tmp_path / "models" / family / "contract"
    directory.mkdir(parents=True)
    payloads = (
        {"mean.ckpt": b"mean", "quantiles.ckpt": b"quantiles", "dataset.pt": b"dataset"}
        if family == "tft_multilead"
        else {
            "weights.json": b'{"baseline": 1.0}',
            "evaluation.json": json.dumps(
                {"partition": "test", "blend": {"n": 4, "rmse": 2.0}}
            ).encode(),
        }
    )
    for name, raw in payloads.items():
        (directory / name).write_bytes(raw)
    meta = {
        "model_family": family,
        "horizon_events": 2,
        "active": True,  # Caller cannot self-promote through a manifest.
        "artifacts": {name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()},
    }
    (directory / "manifest.json").write_text(json.dumps(meta))
    return directory, meta


def entry(family):
    return next(r for r in registry() if r["model_family"] == family)


def evaluation(directory, **changes):
    report = {
        "model_family": "tft_multilead",
        "partition": "test",
        "manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "panel_sha256": "authored-test-panel",
        "lead_metrics": {"1": {"n": 4, "rmse": 2.0}, "2": None},
        **changes,
    }
    path = directory / f"evaluation-{fingerprint(report)}.json"
    path.write_text(json.dumps(report))
    return path


@pytest.mark.parametrize("family", ["tft_multilead", "ensemble"])
def test_discovery_never_promotes_or_imports_optional_dependencies(tmp_path, monkeypatch, family):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    directory, _ = artifact(tmp_path, family)
    if family == "tft_multilead":
        assert entry(family)["status"] == "trained_research"
        evaluation(directory)
    result = entry(family)
    assert result["status"] == "evaluated_research"
    assert result["active"] is False and result["strict_release_eligible"] is False
    assert result["metrics"] is None  # Do not collapse leads or pick a winning test artifact.
    assert result["artifacts"][0]["evaluations"][0]["partition"] == "test"
    payload = directory / ("mean.ckpt" if family == "tft_multilead" else "weights.json")
    payload.write_bytes(b"mutated")
    assert entry(family)["status"] == "disabled"


@pytest.mark.parametrize(
    "changes",
    [
        {"manifest_sha256": "different-model"},
        {"partition": "validation"},
        {"model_family": "tft"},
        {"lead_metrics": {"1": {"rmse": 1}}},
    ],
)
def test_unbound_evaluation_rejected(tmp_path, monkeypatch, changes):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    directory, _ = artifact(tmp_path, "tft_multilead")
    evaluation(directory, **changes)
    assert entry("tft_multilead")["status"] == "disabled"


def test_report_mutation_and_unsafe_payloads_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    directory, meta = artifact(tmp_path, "tft_multilead")
    path = evaluation(directory)
    report = json.loads(path.read_text())
    report["lead_metrics"]["1"]["rmse"] = 0.0
    path.write_text(json.dumps(report))
    assert entry("tft_multilead")["status"] == "disabled"
    path.unlink()
    outside = tmp_path / "outside.ckpt"
    outside.write_bytes(b"mean")
    (directory / "mean.ckpt").unlink()
    (directory / "mean.ckpt").symlink_to(outside)
    assert entry("tft_multilead")["status"] == "disabled"
    (directory / "mean.ckpt").unlink()
    (directory / "mean.ckpt").write_bytes(b"mean")
    meta["artifacts"]["../outside.ckpt"] = hashlib.sha256(b"mean").hexdigest()
    (directory / "manifest.json").write_text(json.dumps(meta))
    assert entry("tft_multilead")["status"] == "disabled"


def test_bad_manifest_cannot_break_baseline_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    directory, _ = artifact(tmp_path, "ensemble")
    (directory / "manifest.json").write_text("[]")
    assert entry("ensemble")["status"] == "disabled"
    assert entry("baseline")["status"] == "active"
