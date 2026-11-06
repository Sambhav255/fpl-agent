"""Generate an optional launchd user-agent template; never load or install it."""

from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path


def worker_template(project_root: Path, data_dir: Path) -> dict:
    if not project_root.is_absolute() or not data_dir.is_absolute():
        raise ValueError("Project root and DATA_DIR must be absolute")
    project_root, data_dir = project_root.resolve(), data_dir.resolve()
    python = project_root / "backend/.venv/bin/python"
    if not python.is_file():
        raise ValueError(
            "Install the backend environment before generating a worker template"
        )
    return {
        "Label": "local.fpl.worker",
        "ProgramArguments": [str(python), "-m", "fpl_app.jobs.worker"],
        "WorkingDirectory": str(project_root / "backend"),
        "EnvironmentVariables": {
            "DATA_DIR": str(data_dir),
            "DATABASE_URL": f"sqlite:///{data_dir / 'app.sqlite'}",
            "PYTHONUNBUFFERED": "1",
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 30,
        "ProcessType": "Background",
        "StandardOutPath": str(data_dir / "runtime/logs/worker.stdout.log"),
        "StandardErrorPath": str(data_dir / "runtime/logs/worker.stderr.log"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    template = worker_template(args.project_root, args.data_dir)
    # Refuse accidental replacement of an earlier reviewed configuration.
    with args.output.open("xb") as stream:
        plistlib.dump(template, stream, sort_keys=False)
    (args.data_dir / "runtime/logs").mkdir(parents=True, exist_ok=True)
    print(
        json.dumps({"template": str(args.output), "installed": False, "started": False})
    )


if __name__ == "__main__":
    main()
