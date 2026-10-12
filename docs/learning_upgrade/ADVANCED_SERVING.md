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

Registration validates before publishing a team/snapshot-bound immutable bundle. Queue references freeze the packet, artifact, implementation digest and active ensemble members. The worker checks these before inference and again before output publication. Mutations fail visibly; missing coverage never becomes zero. Ensemble identities are deterministic and zero-weight absent families may be omitted. Current worker ensemble members support audited Bayesian/TFT families; baseline/CatBoost member integration remains unfinished. No probability or quantile mixture is invented.

## Actual verification and limits

Seventeen offline contract tests cover registration/API/worker publication, mutation fences, source timing, coverage, qualification copies, actual authored NetCDF Bayesian sampling and genuine authored validation-fit ensemble blending. TFT serving uses a mocked checkpoint predictor; separate real fit/reload tests exercise its installed library. Full backend: 400 passed / 3 optional skips. Frontend: 13 unit tests, lint/typecheck/format/build and 12 browser checks passed; 6 personal-state cases are explicitly skipped.

The browser verified complete baseline flows and missing-reviewed-input shadow gates. A positive advanced real-data browser run is not yet available. Authored fixtures are mechanics evidence; they are not trained live football releases, calibration, independent review or a prospective advantage.
