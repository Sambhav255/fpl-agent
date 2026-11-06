# Master-plan continuation — 6 November 2026

This continuation implements remaining code gaps and expands measured historical
research. The [acceptance checklist](../../MASTER_PLAN_STATUS.md) distinguishes
engineering delivery from qualification. The **full plan is not complete**:
M18/M19 and scientific/personal evidence requirements remain open. Previous source
changes, private state and immutable experiments were preserved.

## Delivered and actually exercised

- New enriched/direct/archive fits use `days_since_last_fixture` to describe elapsed
  time to origin. The enriched builder retains `rest_days` as a legacy manifest
  alias. Neither is represented as scheduled rest before the target match.
- The existing promotion module now offers registered, type-specific candidate
  gates: forecast loss reductions in declared units, deterministic planner net
  points per event, stochastic policy seeds and simulator bindings. Eight distinct
  prospective events, matched coverage, exact metric/protocol bindings and review
  remain required. The old v1 policy gate and receipts are unchanged. The operator
  CLI refuses overwriting an assessment and never activates a model.
- New fixed-provider acquisition captures four pinned source files with observation
  times/checksums and verifies retries offline. **2022–23: 26,505 rows; 2023–24:
  29,725 rows**, both covering all 380 fixtures. Together with the retained 2024–25
  bundle this provides three complete archive seasons. The pinned 2025–26 source
  only covers **80 played fixtures / 5,821 rows** and is explicitly incomplete.
- Source-verified cross-season mapping emitted **800 provider-code/full-name research
  links**, with **857 unresolved records**. Names alone never join players;
  duplicate codes and conflicting names stay unresolved. Source bundles are not
  rewritten. These links do not verify historical news availability.
- The existing archive runner now scopes player IDs and rules to the declared
  season rather than forcing 2024–25. Two additional actual experiments fit five
  fixed CatBoost ablations, calibration-partition blend weights and a separate
  latest research refit, through lead 8. A further 2023–24 run exercised the updated
  pre-fit implementation/lock/runtime snapshot publication in the patched environment.

## Measured results

The selected method was registered as `role_permitted_advanced`, not selected by
these test results. [Metrics](metrics.json) retain each experiment and lead.

| Season | Test rows | Selected RMSE | Reconstructed baseline RMSE | Rolling comparator RMSE | Selected / rolling MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022–23 | 44,333 | 2.042567 | 2.287811 | 2.107851 | 1.150485 / 1.105487 |
| 2023–24 | 46,053 | 1.974486 | 2.256052 | 2.048388 | 1.029920 / 1.004994 |

RMSE improves against these comparators; MAE is worse than rolling in both seasons.
Rows repeat players and leads with overlapping outcomes. Each run uses its own
season's scoring era and seven held-out origin blocks; these are separate models,
not a pooled cross-season production model. Deadlines, availability, schedules and
membership retain reconstruction assumptions. These historical studies do not
qualify current-season long-lead serving, calibrated joint scenarios, strict TFT,
complete Bayesian scoring or prospective legal-policy benefit. No champion changed.

The first two runs used the existing research publication contract. The follow-up
2023–24 run additionally retains exact pre-fit implementation bytes, dependency
lock and package identities in its registered protocol; do not retroactively claim
that the first runs had that stronger registration. Full CSV/Parquet/native model
artifacts and source receipts remain ignored under
`data/research/master-plan-2026-11-06/`.

## Dependency and runtime recovery

An actual installed-backend audit found **61 advisory records across five packages**:
certifi, filelock, Pillow, pytest and setuptools. Resolved patched versions are
2026.10.23, 4.2.9, 13.0.0, 9.2.0 and 84.2.1 respectively. Constraints preserve optional
extras; the environment was synced with all existing extras. The follow-up installed
package audit found **zero known vulnerabilities**. This is an advisory-database
result, not proof of security or a new frontend audit.

The old default API/worker were restarted with the same confirmed absolute DATA_DIR.
The updated API reports healthy heartbeat and actual finality. The worker then
completed a scheduled learning review and published a successful refit at
**04:08:25 UTC**. The normal production interface was started and returned HTTP 200.
No OS service was installed; these remain local processes requiring machine uptime.
Seven original benchmark hashes and both registered selection-plan hashes were
checked against the retained inventory and remain unchanged.

## Verification actually run

- Final patched backend suite: **627 passed, 3 skipped**, 335.23 seconds. A prior
  627-test pass preceded dependency synchronization; it is not substituted for this run.
- Operator suite: **21 passed**; Ruff and mypy passed (101 source files).
- Frontend lint/typecheck, **13 unit tests**, normal and isolated production builds passed.
- Isolated current API/worker smoke passed persistence, independent recommendation
  processing, stale rejection and unknown-finance lineup-only behavior.
- Isolated production desktop/mobile browser suite: **12 passed, 10 optional skipped**.
- Original freeze checks and `git diff --check` passed. No personal E2E scenario
  was enabled. Test stores and generated artifacts remain separate from private state.

## What still cannot be marked complete

The [acceptance checklist](../../MASTER_PLAN_STATUS.md) records every task. Actual
private committed transfer/chip reconciliation remains required before a personal
prospective study. Permitted, timestamped, labelled real social claims are missing
for M18. A credible independently evaluated simulator and held-out continuation
comparison are missing for M19. Historical observation-time/component coverage and
future prospective event outcomes remain prerequisites for stricter qualifications.
No invented posts, missing-as-zero components, retrospective prospective claims,
transfer/chip execution, account integration, publication or automatic promotion
were used to close those gaps.
