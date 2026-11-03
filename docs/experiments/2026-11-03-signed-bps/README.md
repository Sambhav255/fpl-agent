# Signed BPS and Bayesian component audit — 3 November 2026

The real pinned 2024/25 archive contains **772 negative BPS observations among
27,283 ordinary player-fixture rows**, ranging from **−25 to 97 BPS** overall.
Negative observations: 450 defender, 167 midfielder, 94 forward and 61 goalkeeper
rows. One negative BPS observation has zero recorded minutes. The source also has
322 assistant-manager rows; these were excluded from the ordinary player audit.
Checksums of every retained source and normalized artifact were verified, and the
canonical BPS labels were reconciled to the original archive rows.
[Full audit and source hashes](audit.json).

BPS is a signed performance score. The official Premier League explanation lists
both rewards and deductions in its [BPS table](https://www.premierleague.com/en/news/106533).
This audit does not revise the domain's bonus ranking/tie rules or transplant the
2024/25 scoring coefficients into current-season predictions.

The existing research profile fitter incorrectly required nonnegative BPS and
modeled it with Gamma-Poisson count rates. Profile **v2** now validates BPS as a
finite signed integer independently of nonnegative event counts. It retains
empirical whole-fixture BPS observations by minutes/start category, with explicit
player/position fallback provenance, and samples their signed values directly.
BPS is neither converted to an absolute value nor scaled again by minutes.
Scenario outputs expose the sampled BPS for diagnosis. Event count components
retain their nonnegative count model.

Old v1 profile files remain unchanged. Complete scenario execution and the
Bayesian strategy adapter deliberately refuse them with a request to refit signed
v2 profiles; their old count interpretation cannot silently acquire new semantics.
Stored historical forecasts remain preserved.

An actual BPS-only support check fitted category pools from this prior season and
drew **40,000 scores per position**, preserving signed support. This is a partial
research diagnostic, with no held-out accuracy or calibration claim. Its full
pools and audit are under ignored `data/research/bayesian-components-2026-11-03/`.
BPS remains independently sampled from simulated goals/cards; this does not create
a calibrated joint football simulator.

**Full player scoring remains unavailable.** The archive lacks independently
identified on-pitch/after-red-card concessions, clearances, blocks, interceptions,
tackles and recoveries. Provider total concessions do not resolve the separate
temporal components. Original publication timing is also not verified. No missing
count was manufactured as zero, and the complete-profile fitting/qualification
requirements were retained. Baseline football remains champion.

Reproduce the read-only audit into a new directory from the repository root:

```sh
PYTHONPATH=backend/src backend/.venv/bin/python \
  docs/experiments/2026-11-03-signed-bps/audit.py \
  --archive data/research/season-foundation-2026-11-03/verified-retrieval/2024-25-76f655e61157525f \
  --output data/research/NEW-bps-audit
```

The next useful step is an explicit partial-component player-point experiment
with a separately evaluated residual, or obtaining the missing component lineage.
This signed-score fix by itself supplies neither full Bayesian qualification nor
evidence of improved player-point predictions.

New checks: **40 focused tests passed / 1 opt-in check skipped**, with one
dependency warning. The skipped ArviZ contract check was then explicitly enabled
and **passed** separately; its initial user-cache permission failure was corrected
by using test-local caches. Changed-file Ruff lint/format and mypy for both source
modules passed. The real audit and BPS-only support outputs reproduced byte for
byte. No Bayesian team or full player-point model was newly trained.
[Verification](verification.json).
