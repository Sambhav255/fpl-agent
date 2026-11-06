"""Verify archive preservation and local documentation links without private state."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^\s)]+)\)")


def verify_docs(root: Path) -> dict:
    manifest = json.loads((root / "docs/archive/relocations.json").read_text())
    moves = {r["previous_path"]: r["path"] for r in manifest["files"]}
    archived = 0
    active_revised = []
    for row in manifest["files"]:
        path = root / row["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["relocated_sha256"]:
            if row["path"].startswith("docs/specs/"):
                active_revised.append(row["path"])
                continue
            raise ValueError("Archived file changed: " + row["path"])
        if path.suffix == ".md":
            body = raw.decode()
            for patch in reversed(row["link_rewrites"]):
                shift = sum(
                    len(p["after"]) - len(p["before"])
                    for p in row["link_rewrites"]
                    if p["offset"] < patch["offset"]
                )
                offset = patch["offset"] + shift
                if body[offset : offset + len(patch["after"])] != patch["after"]:
                    raise ValueError(
                        "Archive link reconstruction failed: " + row["path"]
                    )
                body = (
                    body[:offset]
                    + patch["before"]
                    + body[offset + len(patch["after"]) :]
                )
            raw = body.encode()
        if (
            hashlib.sha256(raw).hexdigest() != row["original_sha256"]
            or len(raw) != row["original_size"]
        ):
            raise ValueError("Original bytes cannot be reconstructed: " + row["path"])
        archived += row["path"].startswith("docs/archive/")
    for name, digest in manifest.get("preserved_experiment_sha256", {}).items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Preserved experiment changed: " + name)
    broken = []
    redirects = []
    paths = [
        root / name
        for name in (
            "README.md",
            "AGENTS.md",
            "CONTRIBUTING.md",
            "backend/README.md",
            "scripts/README.md",
            "apps/web/README.md",
        )
    ]
    paths += [
        p
        for p in (root / "docs").rglob("*.md")
        if "local" not in p.relative_to(root / "docs").parts
    ]
    for path in paths:
        if not path.exists():
            continue
        for target in LINKS.findall(path.read_text()):
            local = target.split("#")[0]
            if not local or local.startswith(
                ("http:", "https:", "mailto:", "/", "app:", "plugin:")
            ):
                continue
            relative = os.path.normpath(str(path.relative_to(root).parent / local))
            if (root / relative).exists():
                continue
            if (
                relative in moves
                and (root / moves[relative]).exists()
                and path.is_relative_to(root / "docs/experiments")
            ):
                redirects.append(
                    {
                        "source": str(path.relative_to(root)),
                        "target": relative,
                        "relocated_to": moves[relative],
                    }
                )
            else:
                broken.append({"source": str(path.relative_to(root)), "target": target})
    if broken:
        raise ValueError("Broken documentation links: " + json.dumps(broken))
    return {
        "relocations": len(manifest["files"]),
        "archived_originals_verified": archived,
        "preserved_experiments_verified": len(
            manifest.get("preserved_experiment_sha256", {})
        ),
        "active_specs_revised_since_relocation": active_revised,
        "historical_reference_redirects": redirects,
        "broken_local_links": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(verify_docs(args.root), indent=2))


if __name__ == "__main__":
    main()
