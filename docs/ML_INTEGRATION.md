# Standalone ML adapter handoff

Owned files: `backend/src/fpl_app/models/strategy_adapters.py`,
`backend/tests/test_strategy_adapters.py`, and this document only. No changes to
contracts, jobs, manifests, registry, frontend, or BUILD_STATUS. Ownership is
released after the scoped checks below; lead owns integration/status updates.

`bayesian_run` loads the local ArviZ posterior and calls the actual shared football
scenario sampler for each frozen fixture. It emits unconditional sample means,
minutes, appearance/60-minute probabilities and fixture marginal quantiles. Start
probability is unavailable. Partial scoring and heuristic minutes are explicit;
these outputs are **not evaluated or activated recommendations**.

`tft_run` calls the actual checkpoint predictor and joins returned series/time
indices to decoder fixtures. It preserves the separate RMSE mean and quantile
heads, negative points and doubles. It rejects horizons beyond one event and
requires separately sourced unconditional minutes. It requires as-of panels,
masked decoder outcomes, earlier encoder events, explicit canonical-player and
club mappings, exact opponent/venue checks and independent fixture coverage.
Encoder publication provenance remains the upstream slot builder's responsibility:
a flattened panel alone cannot establish original source publication timestamps.

Both adapters are read-only and require a verified, live, trained local manifest,
all required artifact checksums, `training_cutoff` and `available_at` at or before
the forecast cutoff. Availability cannot precede training. Current training
manifests do **not** supply these two timestamps and are deliberately rejected.
There is no retrospective override. Checksums establish integrity, not trust of
pickle: TFT checkpoint/dataset files must come from trusted local training.
Returned status remains `trained`, never `active` or `evaluated`.

## Exact blockers and next contract

1. Obtain genuinely deadline-verified historical source versions, fixture versions
   and FPL deadlines; ingest a checksum-bound audited panel. The current Vaastav
   retrospective diagnostic is not an eligible substitute.
2. Training publication must record `training_cutoff` as the latest information
   used by fitting/preprocessing/model selection, and `available_at` as actual
   completed artifact availability. Do not backdate or patch historical manifests
   to manufacture eligibility. Future training can add these fields under lead
   ownership. Timestamp evidence alone does not prove training quality.
3. Supply season-reviewed canonical-player→current-ID and current-club→training
   club mappings, deadline-sourced exposure aggregates, and fixture time indices
   in the Bayesian model's training scale. Unseen/promoted clubs fail rather than
   silently inheriting a team's posterior. Require posterior convergence.
4. Bayesian still lacks calibrated minutes, full scoring components and genuine
   held-out forecast evaluation. TFT needs genuine training and evaluation,
   persisted decoder provenance, separately validated minute estimates and a
   fixed multiweek decoder before longer-horizon support.
5. Before any registry/job/UI wiring, define an eligibility record binding model
   artifact hashes, panel audit, training/validation/test cutoffs, held-out metrics,
   mapping version, source snapshot and input fingerprint. Freeze these inputs in
   the recoverable worker. Promotion needs chronological held-out comparison;
   ensemble weights need eligible validation forecasts and untouched test data.
   An adapter producing a ProjectionRun is not promotion authorization.

## Verification

Tests use synthetic library-compatible contract fixtures, not fitted/registered
models. TFT tests substitute only the inference return boundary. Bayesian test
uses an ArviZ-shaped synthetic posterior and the real shared scenario sampler;
posterior file loading alone is substituted. Optional ArviZ absence skips that
case without preventing the baseline. No training or live-data claims.

Scoped commands from backend use `UV_CACHE_DIR=/private/tmp/fpl-adapter-uv` to
avoid the sandbox-protected shared uv cache: `uv run --offline pytest -q
 tests/test_strategy_adapters.py`, `uv run --offline ruff check
 src/fpl_app/models/strategy_adapters.py tests/test_strategy_adapters.py`, and
`uv run --offline mypy src/fpl_app/models/strategy_adapters.py`.

Scoped mypy passed (1 source file). Scoped Ruff passed after fixing eight
C408 findings. Initial pytest completed 11 cases before being interrupted during
the optional ArviZ import; the Bayesian optional case was not verified. That case
is now opt-in with `FPL_OPTIONAL_SMOKE=1`, consistent with existing model smokes.

Lead reports full pytest: 187 passed, 2 skipped; full mypy: 34 files passed.
Scoped adapter mypy passed (1 source file). Scoped Ruff passed after fixing eight
C408 findings. The Bayesian ArviZ contract test is opt-in via
`FPL_OPTIONAL_SMOKE=1`; it is synthetic and no real-model activation is claimed.
Ownership of all three new files is released to the lead.
