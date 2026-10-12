import hashlib
import json

from fpl_app.models.registry import registry


def test_real_artifact_schema_exposes_experiment_without_promotion(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    directory = tmp_path / "models" / "football_catboost" / "contract_fixture"
    directory.mkdir(parents=True)
    evaluation = json.dumps(
        {
            "evaluation_kind": "retrospective_assumed",
            "comparators": {"football_catboost": {"mae": 4.0, "rmse": 5.0}},
        }
    ).encode()
    (directory / "evaluation.json").write_bytes(evaluation)
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "artifact_id": "contract_fixture",
                "family": "football_catboost",
                "files": {"evaluation.json": hashlib.sha256(evaluation).hexdigest()},
            }
        )
    )
    entry = next(e for e in registry() if e["model_family"] == "football_catboost")
    assert entry["status"] == "evaluated_experimental"
    assert entry["metrics"]["mae"] == 4.0
    assert not entry["active"] and not entry["strict_release_eligible"]
    (directory / "evaluation.json").write_text("{}")
    entry = next(e for e in registry() if e["model_family"] == "football_catboost")
    assert entry["status"] == "disabled"
    assert entry["metrics"] is None
