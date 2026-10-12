# Engineering decisions

## Repository and storage — 2026-10-09

Preserve the original root specifications and maintain working copies in `docs/`. Use a shared checkout with explicit file ownership for authorized parallel implementation. Persist versioned JSON entities in SQLite through SQLAlchemy; keep immutable source bytes and analytical Parquet under ignored local data storage.

## Contracts and manager state — 2026-10-09

Generate frontend schemas from Pydantic contracts. Record financial provenance, confirmation timestamps, and the transfer ledger explicitly. Separate lineup analysis from transfer analysis so unknown finances do not prevent useful lineup recommendations. Unknown hit totals remain unavailable. A marked real-world club transfer exception may retain an existing squad; proposed transfer squads obey club limits.

## Forecast integrity — 2026-10-09

Missing minutes, points, goals, and assists remain missing rather than becoming zero. Drop unknown minute labels from availability training; genuine zero minutes remains a non-appearance. TFT encoders use only information published by the forecast deadline, masking unavailable history. Bind strict training to panel checksums and audited replay timing. Publish model runs atomically from staging directories after checksum validation. Synthetic optional-library tests are installation checks, not live training evidence.

## Planner semantics — 2026-10-10

Save manager corrections only from explicitly confirmed facts. Selling estimates remain unknown until accepted; acceptance never creates a purchase price. Compare marginal chip uplift across eligible weeks. Include a weekly HiGHS candidate alongside horizon candidates, independently validate saved plans, and label bounded search without claiming global optimality. Advanced model adapters enforce artifact eligibility; they do not authorize promotion.

## Repository hygiene — 2026-10-10

Use Ruff for Python and pinned Prettier for frontend formatting. Exclude generated API artifacts from formatting. Preserve private session notes under ignored `docs/local/` and maintain current public handoffs. CI uses offline fixtures and synthetic demo state with a production frontend. Preserve lockfiles and local data. Do not invent a license or remote, or push as part of repository preparation.

The dependency audit identified an unpatched development-only ESLint dependency advisory. Preserve the compatible framework rather than applying the suggested major downgrade; recheck upstream when updating dependencies. Advanced models remain inactive until genuine data and chronological evaluation meet release requirements.

## Personal workspace and model status — 2026-10-10

Keep the personal default in ignored local environment configuration. Loading a saved profile is a GET, never an automatic public reimport. Model registry display is independent of the manager workspace; diagnostic evaluation does not imply activation. Preserve private state on repeated same-event/same-ownership imports and reject ambiguous replacements. Conditional lineup watchlists may describe price thresholds but never substitute unknown selling values or enable blocked transfer recommendations.

## Intelligence upgrade — 2026-10-10

Apply the v2 intelligence kit without replacing the app or its data. Prioritise objective correctness, prospective collection, honest real-data experiments and operational serving over cosmetic changes. Keep default champion promotion strict while allowing explicit future-live experimental challenger selection with real availability timestamps. Capture football versions without silently advancing current manager snapshots. Social access remains disabled; implement and test authored offline examples independently.

## 2026-10-12: scoped experiments and stale manager state

Advanced projections carry an explicit player universe. Recommendation, lineup and saved-plan validation restrict candidates to that universe and reject missing scheduled exposures; unforecasted players are never zero-score candidates. Every owned player must be covered. Baseline retains the full catalogue.

Football collection is a separate recoverable job and CLI. It retains observations without refreshing the active dataset or editing manager state. Repeating a completed capture starts a new capture; simultaneous identical requests deduplicate. Live social capabilities are reported unavailable and influence remains zero.

Official data now identifies GW7. Refreshing fixtures and prices intentionally preserved the GW6 private corrections; those corrections cannot be silently carried into GW7. The saved deadline report is historical. Reconciliation is needed before new legal personal transfer recommendations.

Independent review fixes: rollover confirmation is explicit at the API boundary; unrelated selling rows retain their prior market anchors. Availability scenario endpoints use a separate typed projection field so scoring components still sum to the expected value. Unstarted fixture placeholders are pending observations with null normalised outcomes, not nonappearance labels; raw immutable source statistics remain unchanged.
