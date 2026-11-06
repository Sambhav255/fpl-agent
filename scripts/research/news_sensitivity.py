"""Freeze an additional official-zero scenario without changing a registered parent."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend/src"))
from fpl_app.models.news_sensitivity import freeze_news_sensitivity
from fpl_app.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-id", required=True)
    args = parser.parse_args()
    store = Store()
    value = freeze_news_sensitivity(store, args.benchmark_id)
    try:
        store.get("forecast_benchmark", value["benchmark_id"])
    except KeyError:
        store.put("forecast_benchmark", value["benchmark_id"], value, expected=0)
    print(
        json.dumps(
            {
                "benchmark_id": value["benchmark_id"],
                "zeroed_players": value["protocol"]["zeroed_player_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
