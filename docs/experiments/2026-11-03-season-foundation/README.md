# Prior-season archive foundation — 3 November 2026

A full **2024–25** archive was actually downloaded and normalized at pinned upstream commit `a59a43a8343d960a58cbe7a1f9fba2d2ce431856`. The four original CSV captures finished at **13:01:44 UTC** on 3 November. The source revision, URLs, original byte hashes, normalized artifact hashes, coverage and assumptions are retained in [manifest.json](manifest.json); [quality.json](quality.json) contains the measured quality report. A subsequent unchanged run verified every retained raw and derived artifact and reused the existing bundle without changing its manifest.

The bundle contains **27,283 player-fixture outcomes, 784 ordinary players, 380 fixtures, 38 events and 20 clubs**. Its 815 membership spans come from historical fixture sides, rather than the final player roster. All 115 negative point rows survive, including one disciplinary negative at zero minutes. Assistant Managers are excluded as a different scoring target. Every defensive-contribution value is missing; no modern score was fabricated. No duplicates were found. Archive completeness covers the listed fixtures and rows; omitted eligible players cannot be recovered as zero-minute records.

The new season tables extend the existing approximate archive path. They preserve original outcomes and era identity; player mappings are explicitly scoped to season, with provider codes retained only as clues and cross-season person mapping unresolved. Club codes receive explicit season mapping. Membership boundaries are observed fixture spans, not verified transfer dates. Current club metadata never rewrites historical observations.

League tables are derived from earlier finished fixture results under a declared seven-day publication lag, at an assumed earliest-event-kickoff-minus-48-hours origin. Final table positions are excluded. These are **development assumptions**, not verified historical publication times or deadlines. Final fixture revisions cannot supply historically known future schedules. The bundle is unsuitable for strict prospective replay or production activation. Upstream licensing still requires review before redistributing source data; only small audit manifests are committed.

Reproduction from retained bytes:

```sh
PYTHONPATH=backend/src backend/.venv/bin/python scripts/research/ingest_season.py \
  --source-directory /private/tmp/fpl-historical-source \
  --output data/research/season-foundation-2026-11-03/verified-retrieval \
  --season 2024-25 \
  --revision a59a43a8343d960a58cbe7a1f9fba2d2ce431856 \
  --retrieved-at 2026-11-03T13:01:44.610097+00:00
```

For a fresh acquisition, retrieve the four fixed source URLs in the manifest; save `gws/merged_gw.csv` as `gws_merged_gw.csv`. Supply the actual new retrieval time, never the example's historical time. Full original bytes and Parquet tables remain ignored under `data/research/season-foundation-2026-11-03/verified-retrieval/2024-25-76f655e61157525f`. An earlier local trial with a mistaken supplied retrieval timestamp is explicitly superseded by the canonical verified-retrieval run; its bytes are preserved and must not be used as evidence.

Four focused tests passed: delayed publication exclusion; immunity to later scores, final table changes and current membership; departed-player/signed-outcome/missing-statistic preservation; retry checksum checks and unpinned/duplicate rejection. Ruff lint/format and module mypy passed. No forecast was trained or promoted by this data task. Next: resolve independently evidenced cross-season person mappings and historical availability, then compare era-aware training on declared chronological folds.
