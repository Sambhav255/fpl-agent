"""Export the current Git-visible source without repository history or local state."""

import argparse
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/fpl-assistant-source.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    names = (
        subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
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
        cwd=ROOT,
        capture_output=True,
    )
    if ignored.returncode not in (0, 1):
        raise RuntimeError(ignored.stderr.decode())
    excluded = set(ignored.stdout.decode().split("\0"))
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(names)):
            if not name or name in excluded:
                continue
            source = ROOT / name
            if not source.is_file() or source.is_symlink() or source.resolve() == output:
                continue
            archive.write(source, arcname=f"fpl-assistant/{name}")
            count += 1
    print(f"Exported {count} source files to {output}; no Git history included.")


if __name__ == "__main__":
    main()
