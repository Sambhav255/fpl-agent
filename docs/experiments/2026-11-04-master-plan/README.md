# Master-plan continuation — 4 November 2026

Started at `9130066429e27494c7883dd94a4a91295949f277` with substantial uncommitted
3 November work already present. The [previous ledger](../2026-11-03-master-plan/README.md)
records that work and its negative opportunity/ensemble results. Nothing was reset.
One integration editor used three isolated agent checkouts for M12, M15 and runtime
health. The original plan and prior experiment reports remain unchanged.

## What actually ran

Fresh official capture now reports **GW9 finished and data checked**, with GW10
at **6 November 2026, 18:30 UTC**. Three original GW9 benchmark bundles were scored
and their registered reviews published before new label reuse. All seven original
benchmark hashes and both selection-plan hashes were verified unchanged afterward.
The old registered GW10 comparison was not expanded.

An isolated SQLite backup received a new full-bootstrap collection:
`c6bbb35e50154cdda728d4e40e3f33f3`, **670 players, 5,890 final player-fixture
labels across GW1–9**, captured at **06:39:20 UTC**. After collection, the new
coordinator rescored its three consumed benchmark bundles into durable fenced jobs.
The shared training guard passed. An unchanged retry reused those scoring jobs.
A separately evaluated CatBoost serving refit then froze actual GW10 predictions
at artifact completion. Its serving probabilities remain explicitly uncalibrated;
no model was promoted. This was a manually exercised real-data cycle, not proof
that an unattended scheduled full cycle has run or that a background service exists.

A new direct-lead experiment registered [its protocol](protocol.json) before
fitting and retained [actual measurements](metrics.json). Source bytes, code,
lockfile, package versions, features, coverage, native model files, checkpoint
checksums and predictions remain under ignored
`data/research/master-plan-2026-11-04/`. Experiment directory prefix:
`38e06464809835ed4fbc55e4`; the complete input identity is retained in
[metrics.json](metrics.json) and the original report. An actual unchanged retry
verified the completed report and reused it without refitting.

| Lead / outer events | Rows | Point RMSE: rolling → direct | Point MAE: rolling → direct | Minutes MAE: rolling → direct |
| --- | ---: | ---: | ---: | ---: |
| 1 / GW5–9 | 3,341 | 2.212931 → 2.047680 | 1.210142 → 1.194235 | 13.878938 → 14.460056 |
| 2 / GW8–9 | 1,339 | 2.240677 → 2.044775 | 1.259273 → 1.274353 | 15.727433 → 18.940843 |

Lead-two RMSE improved against this fixed rolling comparator, while its MAE and
minutes MAE regressed. Lead-one minutes MAE also regressed. This comparison does
not establish superiority to every existing CatBoost method. The separate existing
collection trainer measured point RMSE **2.086358** on its own same-era GW5–9 folds;
its feature contract and fitting procedure differ. No outer-driven tuning followed.
Leads 3, 4, 6 and 8 lack complete current-season training/validation/outer blocks
after both target-completion embargoes. They remain explicitly unavailable. The
older prior-season eight-lead research adapter is separate, with a different era
and historical assumptions; it is not current-season serving qualification.

All direct features stay frozen at the original deadline, including every fixture
of a double. Intervening outcomes cannot update player statistics. Missing outcomes
and captured blanks remain distinct; incomplete doubles are excluded as complete
player-event targets. Historical schedule/membership/universe/position and kickoff
plus one-day label timing are reconstructed assumptions. These already-inspected,
dependent event blocks are exploratory, not prospective confirmation or rank gains.

The new weekly report actually reviewed **28 GW9 point streams**. The retained
baseline/CatBoost 669-player streams had RMSE **1.94712 / 1.86313** respectively.
Frozen opportunity fields and decision journals are absent in these old bundles,
so their calibration and execution sections remain unavailable. The report does
not infer injuries, rotation, finishing luck or execution losses from residuals.
New final scoring jobs also publish weekly diagnostics when review evidence permits.

## Task disposition

| Task | Current disposition |
| --- | --- |
| M01 | Refreshed finality, deadline, runtime inventory and original freeze hashes; GW9 now scored |
| M02–M05 | Prior typed heads/eligibility/calibration work preserved; correction and fresh-receipt recovery extended/tested |
| M06–M09 | Prior pinned 2024–25 ingestion and actual Ridge/LightGBM measurements retained; cross-season persons and strict historical availability still unresolved |
| M10–M11 | Prior independently validated replay and wider transfer search preserved; screenshot-based provisional options separately checked, with no claim of realized policy gain |
| M12 | Actual origin-frozen direct point/minute fits and lead-specific measurements; longer current-season leads and future probabilities gated |
| M13 | Prior earlier-OOF blend negative result retained; no post-result retuning |
| M14 | Collection → targeted durable rescore → shared guard → refit; final bundles rechecked each six-hour slot; health API/CLI and optional launchd template; actual manual real-data cycle exercised |
| M15 | Source-bound points/opportunity/minutes/freshness/revision diagnostics, earlier-event descriptive drift and separate execution records; actual final report run |
| M16 | Prior signed BPS/component audit and team-goal scores retained; seven missing full-scoring components remain unavailable |
| M17 | Prior reviewed manual social path retained; no invented posts |
| M18 | Real extraction evaluation/chronological social ablation needs permitted, timestamped, labelled real claims; direct point adjustment remains zero |
| M19 | Qualified continuation/RL evidence needs a credible independently evaluated simulator and held-out policy comparison; old experimental RL remains a challenger |
| M20 | Health now exposes actual downtime/recovery through the existing API; no model API schema change or unrelated UI added |
| M21 | Consolidated checks and this measured report completed |

## Verification actually executed

- Backend full suite: **608 passed, 3 skipped**; later health API addition and
  scoring changes checked in **27 focused tests**. The full suite preceded that
  one additive health test; do not call this a rerun of a 609-test full suite.
- Operator tests: **18 passed**. Backend Ruff lint/format and mypy passed.
- Frontend format, lint, typecheck and **13 unit tests** passed; production build
  passed. OpenAPI regenerated with no schema diff (health remains an open dictionary).
- Isolated production frontend/API/current worker: **12 browser tests passed,
  10 optional tests skipped**, desktop and mobile; complete API/worker demo smoke
  passed, including persistence, stale rejection and unknown-finance lineup-only.
- Worker heartbeat observed healthy during QA. Optional launchd template generated
  and `plutil -lint` passed in isolation; it was not installed or started.
- Frontend production dependency audit: **zero vulnerabilities**. This is not a
  backend or full optional-package security audit.
- Documentation link/archive verification passed before this report and was rerun
  afterward. Prior immutable experiment bytes were not edited.

The pre-existing default-store API/worker were left running; they predate these
changes. QA used separate stores and ports. A stale/missing heartbeat can mean an
older process; restart the intended worker with the exact exported DATA_DIR to
load updated code. A configured schedule never proves uptime.

## Reproduction and next action

The [operator index](../../../scripts/README.md) documents the actual commands.
The current research directory retains the source database backup, inventory,
collection summary, scoring-stage receipts, `current-refit.json`, multilead job
receipt and full model directories. Register a new protocol only for a genuinely
new experiment; retries use its original retained protocol/payload and verify files.

Next: freeze a **new** same-state prospective paper comparison once the manager's
full committed transfer/chip state is reconciled, without altering the older GW10
study; evaluate longer current-season leads only as eligible history accumulates.
Resolve the actual historical mapping/component/social inputs before claiming those
gated tasks complete. Baseline football and the numerical planner remain champions.
No transfer/chip submission, account integration, promotion, push or deployment occurred.
