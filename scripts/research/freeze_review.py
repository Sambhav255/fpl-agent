"""Freeze a retained review's baseline, CatBoost, TFT, blends and team goals."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

import pandas as pd
from fpl_app.learning.forecast_benchmark import make_benchmark
from fpl_app.models.training import data_dir
from fpl_app.providers import Provider
from fpl_app.storage import Store, utcnow


def main():
    store = Store()
    directory = data_dir() / "analysis"
    baseline = json.loads((directory / "baseline-run.json").read_text())
    event = min(p["event"] for p in baseline["projections"])
    points = {}
    for p in baseline["projections"]:
        if p["event"] == event:
            points[p["player_id"]] = (
                points.get(p["player_id"], 0.0) + p["expected_points"]
            )
    artifact = Path(json.loads((directory / "catboost-path.json").read_text())["path"])
    catboost = pd.read_parquet(artifact / "future_predictions.parquet")
    tft = json.loads((directory / "tft-future.json").read_text())
    combined = pd.read_parquet(directory / "future-all-model-means.parquet")
    now = utcnow()

    def model(values):
        return {
            "published_at": now,
            "predictions": [
                {"player_id": int(p), "expected_points": float(v)} for p, v in values
            ],
        }

    models = {
        "baseline": model(points.items()),
        "football_catboost": model(zip(catboost.player_id, catboost.points_mean)),
        "tft_research": model(
            (p["player_id"], p["raw_research_mean"]) for p in tft["predictions"]
        ),
        "baseline_catboost_blend": model(
            zip(combined.player_id, combined.ensemble_reference)
        ),
        "three_family_research_blend": model(
            zip(combined.player_id, combined.ensemble_tft_sensitivity)
        ),
    }
    provider = Provider(store)
    bootstrap = provider.fetch("bootstrap-static/", force=True)
    fixtures = provider.fetch("fixtures/", force=True)
    elements = {p["id"]: p for p in json.loads(bootstrap["raw"])["elements"]}
    zero = {
        i for i, p in elements.items() if p.get("chance_of_playing_next_round") == 0
    }
    models.update(
        {
            name + "_news_zero": {
                "published_at": utcnow(),
                "predictions": [
                    {
                        **p,
                        "expected_points": 0.0
                        if p["player_id"] in zero
                        else p["expected_points"],
                    }
                    for p in m["predictions"]
                ],
                "adjustment": "Only explicit official 0% availability; no repeated appearance scaling",
            }
            for name, m in list(models.items())
        }
    )
    bayes = json.loads((directory / "bayesian-extended-report.json").read_text())
    team = {
        "bayesian_team_goals": [
            {k: p[k] for k in ["fixture_id", "home_mean_goals", "away_mean_goals"]}
            for p in bayes["future_team_predictions"]
            if p["event"] == event
        ]
    }
    benchmark = make_benchmark(
        store,
        bootstrap["id"],
        fixtures["id"],
        event,
        models,
        produced_at=utcnow(),
        protocol={
            "kind": "retained_review_forecasts",
            "research_timing_limits": "See retained review report; prospective event only is untouched",
            "source_artifacts": str(directory),
        },
        team_predictions=team,
    )
    store.put("forecast_benchmark", benchmark["benchmark_id"], benchmark, expected=0)
    output = directory / ("frozen-review-" + benchmark["benchmark_id"] + ".json")
    with output.open("x") as file:
        json.dump(benchmark, file, indent=2)
    # Paired known-news sensitivity for the new ablations is frozen separately.
    for original in store.list("forecast_benchmark"):
        if (
            original["benchmark_id"] == benchmark["benchmark_id"]
            or original["protocol"].get("version") != "deadline-ablation-v1"
        ):
            continue
        adjusted = {
            name + "_news_zero": {
                "published_at": utcnow(),
                "predictions": [
                    {
                        **p,
                        "expected_points": 0.0
                        if p["player_id"] in zero
                        else p["expected_points"],
                    }
                    for p in m["predictions"]
                ],
            }
            for name, m in original["models"].items()
        }
        paired = make_benchmark(
            store,
            bootstrap["id"],
            fixtures["id"],
            event,
            adjusted,
            produced_at=utcnow(),
            protocol={
                "kind": "known_news_sensitivity",
                "paired_raw_benchmark_id": original["benchmark_id"],
            },
        )
        store.put("forecast_benchmark", paired["benchmark_id"], paired, expected=0)
    print(
        json.dumps(
            {
                "benchmark_id": benchmark["benchmark_id"],
                "event": event,
                "model_streams": len(models),
                "automatic_check_after": benchmark["check_after"],
            }
        )
    )


if __name__ == "__main__":
    main()
