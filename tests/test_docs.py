import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_docs", Path(__file__).resolve().parents[1] / "scripts/check_docs.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def tree(tmp_path):
    root = tmp_path / "project"
    archive = root / "docs/archive"
    archive.mkdir(parents=True)
    data = b"Historical evidence\n"
    (archive / "old.md").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (archive / "relocations.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "previous_path": "docs/old.md",
                        "path": "docs/archive/old.md",
                        "original_sha256": digest,
                        "relocated_sha256": digest,
                        "original_size": len(data),
                        "link_rewrites": [],
                    }
                ]
            }
        )
    )
    (root / "README.md").write_text("[Start](docs/archive/old.md)\n")
    return root


def test_archive_checksum_and_local_links_are_enforced(tmp_path):
    root = tree(tmp_path)
    assert module.verify_docs(root)["archived_originals_verified"] == 1
    (root / "docs/archive/old.md").write_text("silently changed")
    with pytest.raises(ValueError, match="Archived file changed"):
        module.verify_docs(root)


def test_broken_active_link_is_detected(tmp_path):
    root = tree(tmp_path)
    (root / "README.md").write_text("[Missing](docs/not-there.md)\n")
    with pytest.raises(ValueError, match="Broken documentation links"):
        module.verify_docs(root)


def test_package_guides_and_operator_reference_are_checked(tmp_path):
    root = tree(tmp_path)
    (root / "backend").mkdir()
    (root / "backend/README.md").write_text("[Missing guide](../docs/missing.md)\n")
    with pytest.raises(ValueError, match="backend/README.md"):
        module.verify_docs(root)
