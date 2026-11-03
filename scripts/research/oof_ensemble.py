"""Register and run a small prior-OOF-only weight fit; never refit base models."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))

from fpl_app.models.oof_ensemble import protocol, run_experiment
from fpl_app.storage import Store, fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simple-directory", type=Path, required=True)
    args = parser.parse_args()
    store = Store()
    spec = protocol(args.simple_directory)
    store.put("oof_ensemble_protocol", fingerprint(spec), spec, expected=0)
    print(json.dumps(run_experiment(store, spec)), flush=True)


if __name__ == "__main__":
    main()
