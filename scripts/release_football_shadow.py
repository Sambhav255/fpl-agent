"""Build immutable model/input release packets from retained football sources.

Uses existing confirmed state for --team-id. --research-portfolio explicitly
creates an isolated hypothetical portfolio; it never imports or repairs a team.
Run with DATA_DIR pointing at the isolated football experiment store.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from fpl_app.contracts import Fixture, ManagerState, Player
from fpl_app.models.advanced_serving import register_bundle
from fpl_app.models.baseline import baseline_run
from fpl_app.models.release_packets import (
    create_baseline_member,
    freeze_ensemble_inputs,
    freeze_football_inputs,
    produce_football_ensemble,
)
from fpl_app.models.router import create_serving_bundle
from fpl_app.providers import dataset
from fpl_app.providers.collection import load_collection
from fpl_app.storage import Store, utcnow


def release(
    store: Store, collection_id: str, artifact_id: str, team_id: int | None = None
):
    collection = load_collection(store, collection_id)
    research = team_id is None
    if research:
        # Only a store with no manager/current state may receive a research portfolio.
        # There is no inferred personal bank, purchase basis, transfer count or chip.
        if store.list("state") or store.list("current"):
            raise ValueError(
                "Research portfolio requires an empty isolated manager store"
            )
        bootstrap = store.snapshot(
            next(
                s["id"]
                for s in collection["sources"]
                if s["resource"] == "bootstrap-static/"
            )
        )
        fixtures = store.snapshot(
            next(s["id"] for s in collection["sources"] if s["resource"] == "fixtures/")
        )
        data = dataset(bootstrap, fixtures)
        store.put("dataset", data["snapshot_id"], data, expected=0)
        store.put("current", "live", {"snapshot_id": data["snapshot_id"]}, expected=0)
        from benchmark_season_planning import synthetic_start

        players = [Player.model_validate(p) for p in data["players"]]
        run = baseline_run(
            players,
            [Fixture.model_validate(f) for f in data["fixtures"]],
            data["snapshot_id"],
            data["source_cutoff"],
            "live",
            data["next_event"],
            1,
        )
        state = synthetic_start(players, run).model_copy(
            update={
                "team_id": 2_000_000_001,
                "warnings": [
                    "Hypothetical research portfolio using actual football sources; no personal manager state"
                ],
            }
        )
        store.put("state", state.team_id, state.model_dump(mode="json"), expected=0)
        store.put(
            "research_portfolio",
            state.team_id,
            {"synthetic_finances": True, "actual_manager": False},
            expected=0,
        )
    else:
        state = ManagerState.model_validate(store.get("state", team_id))
    before = store.get("state", state.team_id)
    ensemble_artifact = produce_football_ensemble(store, collection_id, artifact_id)
    origin = utcnow()
    input_id = freeze_football_inputs(store, collection_id, artifact_id, origin)
    football = create_serving_bundle(store, state, collection_id, artifact_id, input_id)
    baseline = create_baseline_member(store, state, football)
    ensemble_input = freeze_ensemble_inputs(
        store, state, ensemble_artifact, football, baseline
    )
    ensemble = register_bundle(
        store, state, "ensemble", ensemble_artifact, ensemble_input
    )
    if store.get("state", state.team_id) != before:
        raise ValueError("State changed during release construction")
    return {
        "team_id": state.team_id,
        "research_portfolio": research,
        "actual_manager": False if research else None,
        "football": football,
        "ensemble": ensemble,
        "champion_promoted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--team-id", type=int)
    choice.add_argument("--research-portfolio", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = release(Store(), args.collection_id, args.artifact_id, args.team_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        json.dump(packet, file, indent=2, sort_keys=True)
    print(
        json.dumps(
            {
                "packet": str(args.output),
                "team_id": packet["team_id"],
                "champion_promoted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
