import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location(
        "expand_seasons", ROOT / "scripts/research/expand_seasons.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_archive_capture_retries_verify_bytes_without_network(tmp_path, monkeypatch):
    ops = module()
    revision = "a" * 40
    source = tmp_path / "sources" / revision / "2023-24"
    source.mkdir(parents=True)
    hashes = {}
    for name in ops.FILES:
        (source / name).write_bytes(b"retained")
        hashes[name] = hashlib.sha256(b"retained").hexdigest()
    (source / "capture.json").write_text(
        json.dumps({"sha256": hashes, "retrieved_at": "2026-11-06T00:00:00Z"})
    )
    dest = tmp_path / "normalized"
    dest.mkdir()
    (dest / "quality.json").write_text(
        json.dumps({"rows": 10, "fixtures_covered": 1, "fixtures_in_source": 380})
    )
    monkeypatch.setattr(ops, "ingest_season", lambda *a, **kw: dest)
    monkeypatch.setattr(
        ops.httpx, "Client", lambda **kw: pytest.fail("retry must remain offline")
    )
    assert (
        ops.capture("2023-24", revision, tmp_path)["complete_fixture_coverage"] is False
    )
    (source / ops.FILES[0]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        ops.capture("2023-24", revision, tmp_path)


def test_capture_rejects_arbitrary_urls_unpinned_revisions_and_partial_sources(
    tmp_path,
):
    ops = module()
    with pytest.raises(ValueError):
        ops.capture("https://example.com", "main", tmp_path)
    source = tmp_path / "sources" / ("a" * 40) / "2023-24"
    source.mkdir(parents=True)
    (source / ops.FILES[0]).write_bytes(b"partial")
    with pytest.raises(ValueError, match="Incomplete capture"):
        ops.capture("2023-24", "a" * 40, tmp_path)


def test_candidate_assessment_cli_keeps_missing_evidence_and_refuses_overwrite(
    tmp_path,
):
    import subprocess
    import sys

    request = tmp_path / "request.json"
    output = tmp_path / "assessment.json"
    request.write_text(
        json.dumps(
            {
                "gate": {
                    "kind": "forecast",
                    "primary_metric": "point_mae",
                    "metric_units": "FPL_points",
                },
                "evidence": {},
            }
        )
    )
    command = [
        sys.executable,
        str(ROOT / "scripts/research/assess_candidate.py"),
        "--input",
        str(request),
        "--output",
        str(output),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["decision"] == "retain_champion"
    assert report["automatic_activation"] is False
    original = output.read_bytes()
    assert subprocess.run(command, check=False, capture_output=True).returncode != 0
    assert output.read_bytes() == original


def test_weekly_competition_operator_config_is_explicit_and_reversible(tmp_path):
    import os
    import subprocess
    import sys

    command = [sys.executable, str(ROOT / "scripts/research/configure_tournament.py")]
    env = {**os.environ, "DATA_DIR": str(tmp_path)}
    assert (
        subprocess.run(
            command + ["--enable"], check=False, env=env, capture_output=True
        ).returncode
        != 0
    )
    enabled = subprocess.run(
        command + ["--enable", "--study-id", "research-v1"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    assert enabled.returncode == 0, enabled.stderr
    assert json.loads(enabled.stdout)["enabled"] is True
    disabled = subprocess.run(
        command + ["--disable"], check=False, env=env, capture_output=True, text=True
    )
    assert disabled.returncode == 0, disabled.stderr
    assert json.loads(disabled.stdout)["enabled"] is False
    assert json.loads(disabled.stdout)["study_id"] == "research-v1"
