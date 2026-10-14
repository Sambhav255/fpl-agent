"""Authored command flows; these checks never claim real football performance."""

import importlib.util
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_official_replay import payloads, persist
from test_replay_packets import freeze, prepared

from fpl_app.evaluation.strategy import keep_policy, planner_policy, proxy_planner_policy
from fpl_app.learning.packets import capture_replay_evidence, produce_journal_replay_packet
from fpl_app.learning.paper import evaluate_paper_journal
from fpl_app.storage import Conflict

ROOT = Path(__file__).resolve().parents[2]


def load_cli(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finalized(tmp_path, monkeypatch):
    store, state, client = prepared(tmp_path, monkeypatch)
    policies = {"keep": keep_policy, "planner": planner_policy, "proxy": proxy_planner_policy}
    captures = {
        name: capture_replay_evidence(store, state.team_id, 1, policy)
        for name, policy in policies.items()
    }
    journal, _ = freeze(client, captures["keep"]["capture_id"])
    for name, policy in policies.items():
        produce_journal_replay_packet(
            store, journal["decision_id"], captures[name]["capture_id"], policy
        )
    monkeypatch.setattr("fpl_app.storage.utcnow", lambda: "2026-10-11T20:00:00Z")
    fixtures, live = payloads(journal)
    key, _ = persist(store, journal, fixtures, live)
    return store, journal, key


def test_capture_cli_queues_real_worker_contract_and_seal_cli_is_idempotent(
    tmp_path, monkeypatch, capsys
):
    cli = load_cli("prepare_journal_replay")
    store, state, client = prepared(tmp_path, monkeypatch)
    before = deepcopy(store.get("state", state.team_id))
    assert cli.main(["capture", "--team-id", "0", "--horizon", "1", "--enqueue"], store=store) == 0
    result = json.loads(capsys.readouterr().out)
    assert set(result["captures"]) == {"keep", "planner", "proxy"}
    assert result["job"]["status"] == "queued"
    journal, _ = freeze(client, result["captures"]["keep"]["capture_id"])
    for name, capture in result["captures"].items():
        args = [
            "seal",
            "--decision-id",
            journal["decision_id"],
            "--capture-id",
            capture["capture_id"],
            "--policy",
            name,
        ]
        assert cli.main(args, store=store) == 0
        first = json.loads(capsys.readouterr().out)
        assert cli.main(args, store=store) == 0
        assert json.loads(capsys.readouterr().out) == first
    assert store.get("state", state.team_id) == before


def test_score_cli_full_pipeline_pins_revision_and_preserves_prior_reports(
    tmp_path, monkeypatch, capsys
):
    cli = load_cli("evaluate_journal_replay")
    store, journal, revision = finalized(tmp_path, monkeypatch)
    before = deepcopy(store.get("state", journal["team_id"]))
    args = ["--decision-id", journal["decision_id"], "--outcome-revision", revision]
    assert cli.main(args, store=store) == 0
    result = json.loads(capsys.readouterr().out)
    path = Path(result["report_path"])
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == result["report_sha256"]
    report = json.loads(raw)
    assert set(report["reports"]) == {"keep", "planner", "proxy"}
    assert report["outcome_revision_id"] == revision
    assert all(
        row["legal"] and row["realised_net_points"] == 24 for row in report["reports"].values()
    )
    assert report["covered_events"] == 1
    assert cli.main(args + ["--policy", "keep"], store=store) == 0
    assert Path(json.loads(capsys.readouterr().out)["report_path"]) != path
    assert path.read_bytes() == raw
    assert store.get("state", journal["team_id"]) == before
    assert store.decision_records(journal["decision_id"]) == []


@pytest.mark.parametrize("revision", ["latest", "0" * 64, "other:" + "0" * 64])
def test_score_cli_missing_or_unbound_revision_publishes_nothing(
    tmp_path, monkeypatch, capsys, revision
):
    cli = load_cli("evaluate_journal_replay")
    store, journal, _ = finalized(tmp_path, monkeypatch)
    assert (
        cli.main(
            ["--decision-id", journal["decision_id"], "--outcome-revision", revision], store=store
        )
        == 1
    )
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error"] == "PAPER_REPLAY_FAILED"
    assert not (tmp_path / "replay_reports").exists()


def test_concurrent_revision_change_is_fenced_before_report_publication(tmp_path, monkeypatch):
    store, journal, revision = finalized(tmp_path, monkeypatch)
    from fpl_app.learning import paper

    original = paper.replay_policy

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        row = store.get("learning_outcome", revision)
        row["captured_at"] = "2026-10-12T20:00:00Z"
        store.put("learning_outcome", revision, row)
        return result

    monkeypatch.setattr(paper, "replay_policy", changed)
    with pytest.raises(Conflict, match="outcome revision changed"):
        evaluate_paper_journal(store, journal["decision_id"], revision, {"keep": keep_policy})
    assert not (tmp_path / "replay_reports").exists()


def test_cli_errors_do_not_expose_private_state(tmp_path, monkeypatch, capsys):
    cli = load_cli("prepare_journal_replay")
    store, _, _ = prepared(tmp_path, monkeypatch)

    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE_SENTINEL")

    monkeypatch.setattr(cli, "capture_replay_evidence", fail)
    assert cli.main(["capture", "--team-id", "0"], store=store) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "PRIVATE_SENTINEL" not in output.err
    assert json.loads(output.err) == {
        "error": "REPLAY_PREPARATION_FAILED",
        "error_type": "RuntimeError",
    }
