# B03 bounded football collection

Owned files: `backend/src/fpl_app/providers/collection.py`, `backend/tests/test_collection.py`, and this document. Lead owns CLI/job integration and shared status updates.

## Integration contract

```python
from fpl_app.providers.collection import (
    collect_football, load_collection, collection_coverage, export_collection_parquet,
)
from fpl_app.storage import Store

store = Store()
collection = collect_football(store, player_ids=[4, 8], force=True)
reloaded = load_collection(store, collection["collection_id"])
coverage = collection_coverage(store, collection["collection_id"])
artifacts = export_collection_parquet(store, collection["collection_id"])
```

`collect_football(store, provider=None, player_ids: list[int] | None=None, force=True) -> dict` calls only Provider.fetch. None/empty collects bootstrap and fixtures without histories. IDs must be positive integers present in the bootstrap universe; duplicates are removed, maximum 100 distinct players. No URL arguments. Existing provider pacing/retries and verified TLS are retained. Capture failure raises without publishing an incomplete collection; successful individual source snapshots remain archived.

The returned JSON envelope is persisted under Store entity kind `football_collection`, key `collection_id`, using expected version zero. Every capture receives a new ID; no collection is updated by these helpers. Source checksum references retain actual capture/availability timestamps and exact bytes in Store snapshots. `load_collection` verifies the envelope checksum and source references and does not write. `collection_coverage` returns IDs, coverage, per-event deadline evidence and limitations.

Top-level fields include `collection_id`, `schema_version`, `provider`, `season`, `data_mode`, `captured_at`, `available_at`, `actual_deadline`, `before_deadline`, `evidence_mode`, `sources`, `event_evidence`, `player_ids`, `labels`, `schedule_exposures`, `coverage`, and `envelope_sha256`. Newly generated envelopes additionally expose `player_mappings` and raw `fixture_versions`; the initial real capture predates those conveniences, so use its source bootstrap/fixtures references for those values. `actual_deadline` is the next event's exact provider deadline. `before_deadline` requires source capture, source availability, and collection completion before the deadline. No next deadline yields null and `no_next_deadline`. Cached source timestamps are retained, never backdated.

## Model-agent label shape

Each `labels` row has:

- `provider="official_fpl"`, `season`, integer `provider_player_id`, `canonical_player_id="official_fpl:<season>:element:<id>"`, and `canonical_id_scope="season_local_unverified_cross_season"`.
- Integer `fixture_id`, `event`, `minutes`, and `total_points`, plus `statistics` retaining provider fields and nulls. Missing statistics remain absent/null; missing rows are not manufactured as zeros. A provider-reported zero minutes/points remains zero.
- `label_status="preliminary"` or `"final_revision"`. The latter requires fixture `finished_provisional=true` and event `data_checked=true`; it identifies the checked version captured, not a promise that later corrections cannot occur.
- `revision_sha256`, `snapshot_id`, `available_at`, `source_published_at=null`, `original_timing="unknown_original_timing"`, `actual_deadline`, and `strict_historical_replay_eligible=false`.

Repeated captures preserve prior revisions and checksums. Duplicate player/fixture rows fail explicitly. History-past season aggregates are preserved in raw source bytes and excluded from fixture-level labels. Historical xP remains raw provenance only; it is not a verified feature.

Coverage distinguishes `blank_event`, `rows_present`, and `missing_rows`, with explicit scheduled and missing fixture IDs. Schedule exposures retain both fixtures of a double, event assignment, kickoff, venue, opponent, club IDs and fixture snapshot availability. These use captured current club membership and are explicitly unsuitable for reconstructing historical transfers or proving past player eligibility. Canonical player/club IDs are season-local aliases; cross-season identity is unverified.

## Real bounded capture

Collection: `5ca9f12d261942b69ba6c69e693cb1bb`.

Actual capture: `2026-10-10T06:56:35.321477+00:00`; provider season `2026/27`; next deadline `2026-10-10T10:00:00Z`; before deadline true; evidence mode `prospective_capture`.

Thirty players: all 15 stored live owned IDs, plus candidates selected by current public total points. Only player IDs were projected from manager records in SQLite; no private financial values were read or printed. Existing Provider with 0.25-second minimum request spacing was used. The sandbox could not resolve the provider host; an authorized network escalation completed with default verified TLS. No TLS verification bypass was used.

The capture produced 150 historical fixture labels across GWs 1–5 and three optional Parquet artifacts under ignored `data/collections/5ca9f12d261942b69ba6c69e693cb1bb/`. The current/live pointer checksum was identical before and after. Collector code never reads or writes manager state, and never creates/updates current/live or dataset entities.

Newton can load this collection for a small retrospective current-regime experiment with GWs 1–3 training, GW4 validation, GW5 test. The selection of candidates uses current total points, so selection is retrospective and introduces selection bias. The historical labels do not establish deadline-available historical features. This is qualified diagnostic evidence, not strict replay or a broad performance claim.

## Verification and remaining work

Executed checks: `backend/.venv/bin/pytest tests/test_collection.py tests/test_providers.py -q` from backend: **24 passed**; targeted Ruff: **passed**; `mypy src/fpl_app/providers/collection.py`: **passed**. The real collection was subsequently loaded and all source/envelope checksums verified. Tests cover both sides of deadlines, missing rows/statistics, double/blank schedules, genuine zero outcomes, revised versions, checksum verification, ID bounds, duplicate/schema failures, cached source timing, immutable optional exports and preservation of current/manager entities.

Lead's next step: wire CLI/recoverable jobs to the function and record B03 status in shared build documentation. Optional Parquet export is separate from capture and does not change the immutable envelope. An export dependency/filesystem failure cannot invalidate the already persisted source collection. No model activation is performed here.
