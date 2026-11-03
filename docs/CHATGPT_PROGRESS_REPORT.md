# Continuation summary

Start at [START_HERE](START_HERE.md), read [BUILD_STATUS](BUILD_STATUS.md), then follow [ROADMAP](ROADMAP.md). The next task is improving the existing CatBoost appearance/60-minute heads and chronological calibration; keep the experiment small and registered.

Completed: organized current specifications under `docs/specs/`; archived obsolete prompts/audits/status losslessly with a relocation manifest; preserved 33 prior experiment files, private data and all seven existing forecast bundles. `scripts/check_docs.py` verifies archive hashes and current links. The roadmap explains the top-10,000 goal, weekly operating routine, ordered milestones and acceptance criteria without promising rank.

Executed: a durable four-fold enriched-model rolling experiment, 2,671 outer rows/model across GW5–8. Multiscale RMSE 2.0890, full-context 2.0983, hurdle 2.1016, reconstructed baseline 2.3660. Historical evidence remains exploratory. The hurdle's tiny earlier split win does not consistently hold. GW9 ranking diagnostics show that better league-wide errors do not ensure better position shortlists.

Implemented source-bound frozen selection diagnostics, actual registration receipts, fixed study contracts, missing-outcome/no-backfill handling, canonical event plans and distinct-week evidence reporting. The GW9 analysis is retrospective/provisional. A GW10 prospective selection plan covers the existing 23 streams and 176 origin-eligible players; readiness is insufficient. No forecast was rewritten, no outcome was invented, and no champion was promoted.

Source map: `models/rolling_experiments.py` and its research CLI handle durable expanding fits/checkpoints; `evaluation/selection.py` and `learning/selection_review.py` handle ranking plans, source verification and evidence. Worker integration publishes final selection reviews; `score_forecasts.py --export` includes them. Documentation and research commands remain indexed in `scripts/README.md`.

Checks actually run this stage are in BUILD_STATUS; older test counts remain historical. The restarted local research worker uses current code and waits for official GW9 finalization, still pending at the latest check. It does not survive shutdown automatically. Current private finances remain unconfirmed, so transfer advice requires reconciliation. Production remains baseline plus the numerical optimiser; Bayesian full scoring/TFT qualification gates remain intact.
