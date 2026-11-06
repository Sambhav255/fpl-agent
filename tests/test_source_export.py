import importlib.util
import subprocess
import zipfile
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/export_source.py"
spec = importlib.util.spec_from_file_location("export_source", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def repository(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("data/\n.env\ndist/\n")
    (root / "README.md").write_text("# Source\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    return root


def test_export_excludes_even_tracked_ignored_state_and_is_reproducible(tmp_path):
    root = repository(tmp_path)
    (root / "data").mkdir()
    (root / "data/private.sqlite").write_text("private state")
    (root / ".env").write_text("private configuration")
    subprocess.run(
        ["git", "add", "--force", "data/private.sqlite", ".env"], cwd=root, check=True
    )
    output = root / "dist/source.zip"
    first = module.export_source(root, output)
    with zipfile.ZipFile(output) as archive:
        assert "fpl-assistant/README.md" in archive.namelist()
        assert not any(
            "private.sqlite" in n or n.endswith("/.env") or "/.git/" in n
            for n in archive.namelist()
        )
    assert not first["git_history_included"]
    assert (
        first["archive_sha256"] == module.export_source(root, output)["archive_sha256"]
    )


def test_export_rejects_a_credential_pattern_without_printing_its_value(tmp_path):
    root = repository(tmp_path)
    key = "AKIA" + "A" * 16
    (root / "credentials.txt").write_text(key)
    with pytest.raises(ValueError, match="credentials.txt") as error:
        module.export_source(root, root / "dist/source.zip")
    assert key not in str(error.value)
    assert not (root / "dist/source.zip").exists()


@pytest.mark.parametrize("suffix", [".joblib", ".pkl", ".pt", ".onnx"])
def test_export_rejects_git_visible_native_artifacts(tmp_path, suffix):
    root = repository(tmp_path)
    (root / ("unexpected" + suffix)).write_bytes(b"local trained model")
    with pytest.raises(ValueError, match="Private/generated source path"):
        module.export_source(root, root / "dist/source.zip")


def test_export_rejects_missing_preserved_evidence(tmp_path):
    import json

    root = repository(tmp_path)
    archive = root / "docs/archive"
    archive.mkdir(parents=True)
    (archive / "relocations.json").write_text(
        json.dumps(
            {
                "files": [],
                "preserved_experiment_sha256": {
                    "docs/experiments/missing.json": "unavailable"
                },
            }
        )
    )
    with pytest.raises(ValueError, match="Preserved document omitted"):
        module.export_source(root, root / "dist/source.zip")
