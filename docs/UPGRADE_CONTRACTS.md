# Intelligence upgrade integration contracts

Use the existing store and typed contracts. New fields are additive. The lead owns shared contracts and job/API changes. Current manager corrections, unknown money gates and independent replay remain controlling.

- Collection: `collect_football(store, provider=None, player_ids=None, force=True) -> dict`; immutable `football_collection` envelope, hashes, actual observation times, deadlines, explicit IDs, labels/revisions and coverage. Collection must not mutate current/live or manager state. CLI and worker wiring owned by lead.
- Forecast selection: requested provider is distinct from resolved provider. Baseline defaults; advanced selection requires explicit immutable artifact ID and experimental/shadow or recorded promotion mode. Queue freezes manifest checksum, origin, feature/mapping references and horizon; retries must reject changed artifacts, not resolve latest.
- ProjectionRun: additive provider/artifact/lifecycle/feature/mapping/origin/evaluation/evidence fields. Missing uncertainty remains null.
- Football CatBoost: model agent defines immutable manifest and future-origin forecast adapter in new module; same-season/cross-season mapping evidence stays explicit. Retrospective assumed evaluation may support an opt-in future-live challenger, never a claim of historical deployment or default superiority.
- Social: separate module-local records, capability gates and deletable lineage. Offline authored synthetic examples are labelled; live Reddit/X disabled. No points adjustments or training rights inferred.
- Search/replay: use existing domain transitions and validate every plan; exact oracle limited to declared small universes; proxy bounds never presented as full-plan optimality gaps.
