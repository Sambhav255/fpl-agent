"""Scoring must commit before reuse, including changed observation receipts."""

import json
from datetime import UTC, datetime

import pytest
from test_forecast_benchmark import RetainedProvider, fixture

from fpl_app.jobs import Queue
from fpl_app.learning.forecast_benchmark import checked_benchmark
from fpl_app.learning.review import score_collection_benchmarks
from fpl_app.models.training_eligibility import require_scored_collection
from fpl_app.storage import fingerprint


def collection_for(frozen, receipt):
    return {
        "season": frozen["season"],
        "envelope_sha256": receipt,
        "labels": [
            {
                "event": frozen["event"],
                "label_status": "final_revision",
                "available_at": datetime.now(UTC).isoformat(),
            }
        ],
    }


def test_collection_rescores_before_reuse_without_claiming_unrelated_work(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    provider = RetainedProvider(store, bootstrap, fixtures, finalized=True)
    original = fingerprint(checked_benchmark(store, frozen["benchmark_id"]))
    unrelated = Queue(store).enqueue("refresh", {})
    collection = collection_for(frozen, "first-capture")
    with pytest.raises(ValueError, match="Score finalized"):
        require_scored_collection(store, collection)
    first = score_collection_benchmarks(store, provider, collection)
    require_scored_collection(store, collection)
    assert first[0]["status"] == "final"
    assert Queue(store).get(unrelated["id"])["status"] == "queued"
    assert score_collection_benchmarks(store, provider, collection) == first
    before = store.list("forecast_benchmark_outcome")
    assert len(before) == 1
    recapture = collection_for(frozen, "new-capture")
    with pytest.raises(ValueError, match="current revision required"):
        require_scored_collection(store, recapture)
    second = score_collection_benchmarks(store, provider, recapture)
    assert second[0]["revision"] != first[0]["revision"]
    assert len(store.list("forecast_benchmark_outcome")) == 2
    assert before[0] in store.list("forecast_benchmark_outcome")
    assert fingerprint(checked_benchmark(store, frozen["benchmark_id"])) == original

    class Corrected(RetainedProvider):
        def fetch(self, resource, force=False):
            snapshot = super().fetch(resource, force=force)
            if resource.startswith("event/"):
                value = json.loads(snapshot["raw"])
                value["elements"][0]["stats"]["total_points"] = 9
                return self.store.snapshot(self.store.archive(json.dumps(value).encode(), resource))
            return snapshot

    third = score_collection_benchmarks(
        store,
        Corrected(store, bootstrap, fixtures, finalized=True),
        collection_for(frozen, "corrected-capture"),
    )
    scored = store.get(
        "forecast_benchmark_outcome", frozen["benchmark_id"] + ":" + third[0]["revision"]
    )
    assert scored["metrics"]["reference"]["mae"] == 2.75
    assert before[0] in store.list("forecast_benchmark_outcome")


def test_incomplete_scoring_blocks_training_and_can_recover(tmp_path):
    store, frozen, bootstrap, fixtures = fixture(tmp_path)
    collection = collection_for(frozen, "missing-capture")
    with pytest.raises(ValueError, match="incomplete"):
        score_collection_benchmarks(
            store,
            RetainedProvider(store, bootstrap, fixtures, finalized=True, missing=True),
            collection,
        )
    with pytest.raises(ValueError, match="Score finalized"):
        require_scored_collection(store, collection)
    score_collection_benchmarks(
        store,
        RetainedProvider(store, bootstrap, fixtures, finalized=True),
        collection_for(frozen, "recovered-capture"),
    )
    assert len([r for r in store.list("forecast_benchmark_outcome") if r["status"] == "final"]) == 1
