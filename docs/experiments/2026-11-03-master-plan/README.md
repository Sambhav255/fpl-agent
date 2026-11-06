# Master-plan execution — 3 November 2026

Started from `0e43ed8e8ce365a1bcf1aaaa3e1b218a23acba59` using Section 34 of the
[user-supplied master plan](../../../FPL_MODEL_IMPROVEMENT_MASTER_PLAN_2026_11_03.md).
One integration owner and three isolated local checkouts handled model, historical
and decision tasks; the integration checkout owned eligibility and worker changes.
Unrelated `PM_LOG.md` and existing ignored research/private state were preserved.

## Inventory and execution ledger

At **13:02 UTC**, fresh official bootstrap bytes still reported GW9
`finished=false`, `data_checked=false`; GW10 deadline was **6 November 2026 at
18:30 UTC**. The bootstrap SHA256 was
`113c6d41ae928e70833e8f2f0a50d7edc8b500d9b606dece905be903826950ef`;
380-fixture bytes hashed
`dc5b91b3360a84444a40fb51cff556a8115d25ebf54a47d69c376f57f599c3fd`.
Raw responses and the private before/after state/hash inventory remain ignored in
`data/research/master-plan-2026-11-03/inventory/`. Seven frozen benchmark bundles
were inventoried before training; GW9 remained outside new fitting targets.
The existing process inventory found the API and a worker on the default app
store, rather than an active research-store worker. No duplicate worker for that
store was started. QA used a separate disposable demo database.

| Task | Owner | Delivered or remaining condition |
| --- | --- | --- |
| M01 | Integration | Fresh official inventory and retained hashes; final GW9 scoring still externally gated |
| M02 | Integration | Shared scoring guard across collection/scheduled/audited/research entrypoints; corrected recaptures and ambiguous eventless panels covered |
| M03–M05 | Model | Typed binary heads, chronological calibration, coherent minutes, actual registered four-fold comparison |
| M06–M07 | Historical | Full pinned 2024–25 ingestion, identity/membership/era/coverage tables and prefix tests; strict historical timing/cross-season persons unresolved |
| M08–M09 | Historical | Actual same-fold Ridge and optional LightGBM fits with native checkpoints and retries |
| M10–M11 | Decision | Same-state multi-forecast replay and measured three-transfer search gap; synthetic trajectory run, real prospective policy comparison unavailable |
| M12 | Next | Direct multi-lead forecasting not implemented in this stage; current trained support stays one event |
| M13 | Historical | Actual earlier-OOF convex blend, negative result retained |
| M14 | Integration | Independent heartbeat and unchanged-input refit reuse; real post-GW9 eligible scoring/refit/freeze cycle still awaits finality |
| M15 | Partial | Opportunity, point, subgroup and policy-mechanics reports; integrated execution/drift review still pending |
| M16 | Decision | Signed BPS audit and profile support; complete player-scoring evidence remains gated |
| M17 | Model | Actual synthetic manual import/scenario/delete workflow; no real posts or point uplift |
| M18–M19 | Gated | Genuine social ablation and held-out RL continuation require measured inputs and simulator evidence; no claim of completion |
| M20 | Integration | Planner explanation aligned with real search coverage; no extra dashboard or account integration |
| M21 | Integration | Consolidated actual checks recorded in BUILD_STATUS and verification below |

## Measurements and interpretation

- [Opportunity comparison](../2026-11-03-opportunity/README.md): 2,671 outer
  rows/method, GW5–8. Appearance Brier **0.129059 → 0.129910**, 60-minute Brier
  **0.103395 → 0.104127** (both worse); minutes MAE **16.882671 → 16.845961**.
  Point RMSE was unchanged (**2.140505**) by design. The bundle failed the primary
  Brier objectives. Calibrated evaluation and uncalibrated latest-data refit are
  distinct methods.
- [Prior-season ingestion](../2026-11-03-season-foundation/README.md): **27,283**
  ordinary player-fixture rows, **784** players, all **380** fixtures, 115 negative
  point rows including one at zero minutes. Defensive contribution remains
  unmeasured. Historical availability/deadlines remain assumed.
- [Simple models](../2026-11-03-simple-models/README.md): 2,671 rows/method,
  GW5–8. Ridge RMSE **2.202751**, LightGBM **2.094006**, existing multiscale
  CatBoost **2.089037**. LightGBM improves slightly on original context CatBoost,
  but does not beat the best retained single comparator.
- [Earlier-OOF blend](../2026-11-03-oof-ensemble/README.md): **2,004 GW6–8** rows.
  Ensemble RMSE **2.078964**, multiscale **2.071538**, LightGBM **2.077180** on
  the identical window. Weights never consume their own current/future labels.
- [Paper policies](../2026-11-03-paper-policy/README.md): actual two-event,
  four-policy synthetic mechanics run; correct trajectories do not establish a
  football model advantage. The former two-transfer cap missed a beneficial
  third free transfer in an exact controlled case.
- [Manual social evidence](../2026-11-03-social-manual/README.md): synthetic
  import, availability branch and deletion exercised. Real source coverage,
  extraction accuracy and chronological ablation remain unavailable.

All model metrics above are exploratory measurements on already inspected,
reconstructed historical blocks. Player rows are dependent. No rank benefit or
prospective legal-policy improvement is established. **Baseline football and the
numerical optimiser remain champions.** Existing GW9/GW10 comparisons are not
expanded to include these later models. Original protocols, source bytes, model
files and executed implementation hashes remain with ignored artifacts; integrated
source/guard/lock changes intentionally invalidate a new run's old fingerprint.
An unchanged retry reported by an experiment refers to its exact executed source,
not a claim that different integrated code reused that identity.

The next substantive task is M12: register and evaluate supported direct leads
without intervening outcome leakage, alongside a genuinely new prospective
same-state comparison when financial evidence and final outcomes permit it.
