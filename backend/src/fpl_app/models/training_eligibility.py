"""Shared embargo on reusing labels before retained forecasts are finally scored."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fpl_app.storage import Store, fingerprint


def require_scored_labels(store: Store, labels: list[dict[str, Any]], season: str | None) -> None:
    """Check all consumed final events, scoped by season and source revision time.

    A later label capture needs a score using outcomes observed at least that late.
    This conservative rule also catches corrections without pretending that an
    element-summary checksum equals an event-live checksum.
    """
    events = {r["event"] for r in labels if r.get("label_status") == "final_revision"}
    scores = store.list("forecast_benchmark_outcome")
    for bundle in store.list("forecast_benchmark"):
        event = bundle["event"]
        if event not in events or (
            season is not None and bundle.get("season") not in (None, season)
        ):
            continue
        observed = [
            datetime.fromisoformat(r["available_at"])
            for r in labels
            if r["event"] == event
            and r.get("label_status") == "final_revision"
            and r.get("available_at")
        ]
        matching = [
            s
            for s in scores
            if s.get("benchmark_id") == bundle["benchmark_id"]
            and s.get("status") == "final"
            and s.get("forecast_sha256") == fingerprint(bundle)
        ]
        if observed:
            matching = [
                s
                for s in matching
                if any(
                    ref.get("resource") == f"event/{event}/live/"
                    and datetime.fromisoformat(ref["available_at"]) >= max(observed)
                    for ref in s.get("source_refs", [])
                )
            ]
        if not matching:
            raise ValueError(
                "Score finalized frozen benchmarks before refitting their labels "
                f"(event {event}, benchmark {bundle['benchmark_id']}; current revision required)"
            )


def require_scored_collection(store: Store, collection: dict[str, Any]) -> None:
    require_scored_labels(store, collection["labels"], collection.get("season"))


def require_scored_panel(store: Store, frame: Any) -> None:
    """Apply the same boundary to audited CatBoost, Bayesian and TFT panels."""
    for season, group in frame.groupby("season"):
        labels = []
        for row in group.to_dict("records"):
            if row.get("target_points") is None:
                continue
            event = row.get("event")
            if event is None:
                # Some older audited panels identify origins by deadline only.
                matches = [
                    b["event"]
                    for b in store.list("forecast_benchmark")
                    if b.get("season") == str(season)
                    and b.get("deadline") == row["decision_cutoff"]
                ]
                if not matches:
                    continue
                event = matches[0]
            labels.append(
                {
                    "event": int(event),
                    "label_status": "final_revision",
                    "available_at": row.get("actual_label_available_at")
                    or row["target_available_at"],
                }
            )
        require_scored_labels(store, labels, str(season))
