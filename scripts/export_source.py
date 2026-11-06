"""Export the current Git-visible source without repository history or local state."""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
]


def export_source(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    names = (
        subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .split("\0")
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"],
        check=False,
        input="\0".join(name for name in names if name).encode() + b"\0",
        cwd=root,
        capture_output=True,
    )
    if ignored.returncode not in (0, 1):
        raise RuntimeError(ignored.stderr.decode())
    excluded = set(ignored.stdout.decode().split("\0"))
    files = {}
    contents = {}
    forbidden_parts = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    for name in sorted(set(names)):
        if not name or name in excluded:
            continue
        source = root / name
        if not source.is_file() or source.is_symlink() or source.resolve() == output:
            continue
        parts = Path(name).parts
        if (
            forbidden_parts.intersection(parts)
            or any(p.startswith(".next") for p in parts)
            or parts[0] in {"data", "dist"}
            or parts[:2] == ("docs", "local")
            or (source.name.startswith(".env") and source.name != ".env.example")
            or source.suffix
            in {
                ".sqlite",
                ".sqlite3",
                ".db",
                ".parquet",
                ".log",
                ".ckpt",
                ".cbm",
                ".nc",
                ".joblib",
                ".pkl",
                ".pickle",
                ".pt",
                ".pth",
                ".onnx",
                ".safetensors",
                ".npy",
                ".npz",
            }
        ):
            raise ValueError(f"Private/generated source path is Git-visible: {name}")
        raw = source.read_bytes()
        if any(
            pattern.search(raw.decode("utf-8", errors="ignore"))
            for pattern in SECRET_PATTERNS
        ):
            raise ValueError(f"Potential credential pattern in source file: {name}")
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        contents[name] = raw
    preservation = contents.get("docs/archive/relocations.json")
    if preservation is not None:
        manifest = json.loads(preservation)
        referenced = [row["path"] for row in manifest.get("files", [])]
        referenced += list(manifest.get("preserved_experiment_sha256", {}))
        for name in referenced:
            if name not in files:
                raise ValueError(
                    f"Preserved document omitted from source export: {name}"
                )
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in contents.items():
            info = zipfile.ZipInfo(
                f"fpl-assistant/{name}", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (
                0o100755 if (root / name).stat().st_mode & 0o111 else 0o100644
            ) << 16
            archive.writestr(info, raw)
    audit = {
        "file_count": len(files),
        "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "files": files,
        "excluded_ignored_files": sorted(excluded - {""}),
        "git_history_included": False,
        "known_credential_pattern_matches": 0,
    }
    output.with_suffix(".audit.json").write_text(
        json.dumps(audit, sort_keys=True, indent=2) + "\n"
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "dist/fpl-assistant-source.zip"
    )
    args = parser.parse_args()
    audit = export_source(ROOT, args.output)
    print(
        f"Exported {audit['file_count']} audited source files to {args.output}; no Git history included."
    )


if __name__ == "__main__":
    main()
