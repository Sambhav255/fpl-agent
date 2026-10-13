# Audited local advanced shadows

Implemented 2026-10-12. The Models page can load registered Bayesian, TFT, multilead TFT and mean-ensemble bundles for the current team/source snapshot and run an explicit shadow through the recoverable worker. The baseline remains default. Errors, progress, experimental status and approximations are visible. No transfer, chip or promotion is submitted.

## Reviewed artifact copy

Keep original training artifacts unchanged. A local operator review lives in ignored `DATA_DIR/model_reviews/<review-id>.json`. Its approved-shadow record binds the original manifest SHA256, current rules, held-out evaluation filename/checksum, retained training source IDs/checksums and `input_provenance_reviewed: true`. See `qualify_shadow` in `backend/src/fpl_app/models/qualification.py` for the exact contract.

Use `backend/.venv/bin/python scripts/prepare_advanced_forecast.py --provider <family> --artifact-id <original-id> --review-id <review-id>`. The command verifies the review and publishes a deterministic new `qualified-*` artifact with the actual current publication time, original training manifest, copied evaluation and checksum-bound release audit. It cannot backdate a fit or turn an unaudited research manifest into live evidence. Repeating the same valid review reuses the immutable copy.

Eligible metadata requires verified live provenance, current rules, exact family, known fitting-label cutoff and publication timing, complete genuine model payloads and untouched test coverage. Bayesian requires posterior, diagnostics and full scoring profiles; legacy TFT requires checkpoints and dataset plus matching run/dataset evaluation identity; multilead evaluation binds the original training manifest and lead metrics; ensemble evaluation binds validation-fitted weights and untouched later test origins. Retained official source bytes must still match their receipts.

Current research producers are not automatically release qualified. Complete audited producer metadata, full Bayesian profiles/evaluation, real-data calibration and adequate chronological targets remain necessary. Local approval is operator evidence, not independent attestation or proof of model advantage. Load only locally trusted checkpoints: checksums bind bytes but do not make arbitrary serialized Python/Torch models safe.

## Frozen serving packet

Prepare ignored `DATA_DIR/serving_inputs/<input-id>/manifest.json` and its checksum-bound Parquet inputs. IDs accept only letters, digits, underscores and hyphens; paths and symlinks are rejected. `InputManifest` in `backend/src/fpl_app/models/advanced_serving.py` is the authoritative schema:

- `schema_version: 1`, `review_status: reviewed_local`, family and qualified artifact ID/manifest SHA256.
- Current snapshot/rules, source cutoff, input availability, forecast origin, next event, horizon and all complete scheduled events, including blanks.
- Canonical player and club maps, retained official bootstrap/fixture source receipts, exact file checksums and optional frozen fixture times.
- Bayesian `exposures.parquet`; TFT `panel.parquet` and unconditional `minutes.parquet`; ensemble registered child bundle IDs for positively weighted members.

The source cutoff must precede input availability and prediction origin; models must have been published by that origin. Scheduled fixtures must be unplayed at the origin. Coverage includes the current and persistent owned squads. Legacy TFT supports one lead; multilead TFT must match its declared horizon. Means are unconditional on appearance and are never availability-scaled twice.

Register with `backend/.venv/bin/python scripts/prepare_advanced_forecast.py --provider <family> --artifact-id <qualified-id> --team-id <team-id> --input-bundle-id <input-id>`. Add `--enqueue` to request a shadow immediately, or select the registered bundle in Models. Qualifying and constructing the packet are normally separate steps so its manifest binds the newly published ID and checksum. No source data is fetched by this command and no manager state is edited.

Registration validates before publishing a team/snapshot-bound immutable bundle. Queue references freeze the packet, artifact, implementation digest and active ensemble members. The worker checks these before inference and again before output publication. Mutations fail visibly; missing coverage never becomes zero. Ensemble identities are deterministic and zero-weight absent families may be omitted. Worker ensembles now also support frozen app-baseline members and validated Football CatBoost bundles. Positive members bind their origin, horizon, universe, source receipts and immutable payload; a zero-weight family may be omitted. No probability or quantile mixture is invented.

## Actual verification and limits

Seventeen offline contract tests cover registration/API/worker publication, mutation fences, source timing, coverage, qualification copies, actual authored NetCDF Bayesian sampling and genuine authored validation-fit ensemble blending. TFT serving uses a mocked checkpoint predictor; separate real fit/reload tests exercise its installed library. Full backend: 400 passed / 3 optional skips. Frontend: 13 unit tests, lint/typecheck/format/build and 12 browser checks passed; 6 personal-state cases are explicitly skipped.

The browser verified complete baseline flows and missing-reviewed-input shadow gates. A positive real CatBoost/ensemble browser run is now verified on desktop/mobile, including queued worker inference, 667 displayed forecasts, independently validated analysis and pre-deadline paper freezing. See the current experiment report below; the original authored tests remain mechanics evidence. Authored fixtures are mechanics evidence; they are not trained live football releases, calibration, independent review or a prospective advantage.

## Reproducible real football producers (13 October 2026)

Read [the finalized experiment report](../experiments/2026-10-13-real-football-finalized/README.md) for actual results and commands. `scripts/train_current_football.py` evaluates retained official final labels and fits a separate latest artifact without manager state or network capture. `scripts/release_football_shadow.py` constructs new checksum-bound Parquet/origin inputs, freezes the actual baseline on identical coverage, fits mean weights from genuine earlier held-out fold predictions, evaluates later untouched origins, writes a model release audit and registers shadow inputs. Manual JSON/Parquet assembly is unnecessary for these real football paths. The optional Bayesian/TFT review contract above remains gated until its complete real producer/evaluation evidence is available.

Historical evaluation stays `retrospective_assumed`; the ensemble producer uses an explicitly distinct `historical_assumed_shadow` timing mode with retained training-manifest/receipt bytes and a `shadow_only` restriction. It never changes an assumed historical publication timestamp into verified evidence. All actual retained training source availability and model publication times precede the serving information cutoff, and covered fixtures/deadline must still be future. A forecast information cutoff differs from the later computation/publication time: the football packet records actual `input_produced_at`, the baseline member records actual `produced_at`, worker completion records publication, and the paper journal records actual decision time. These do not become backdated prospective predictions.

`--research-portfolio` creates a declared hypothetical portfolio only in a manager/current-empty isolated store. `--team-id` requires the existing exact state and current source snapshot; stale personal state remains blocked. No bank, selling values, transfers or chips are inferred. The public report records dataset/source hashes, chronological partitions, ablations, scores by position/event/lead and artifacts. Calibration, source timing and scoring-era limits remain visible; baseline stays champion. Fresh final verification: base413/11, RL429/7, mypy78 sources, 14 CLI tests, 13 frontend units, production build and14 production browser passes/6 personal-state skips. Earlier counts above are historical.
