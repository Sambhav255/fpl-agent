# Data and model specification

This is the implementation contract for observations, features, forecasts, and decisions. The three advanced model families are CatBoost, Bayesian events, and Temporal Fusion Transformer. A transparent baseline is required for development and comparison.

## 1. Source strategy

| Source | Priority | Access and intended use |
|---|---|---|
| Official FPL JSON endpoints | Required | Current player universe, fixtures, events, player histories, public squads |
| Vaastav historical FPL archive | Required historical audit | Past player observations; no assumption of weekly current updates |
| Understat | Optional initial enrichment | Player and team attacking metrics and shot information |
| FPL Core Insights | Supplementary | Recent history, defensive actions, fixture context; audit field provenance |
| Football Data | Optional benchmark | Results and odds with a verified availability cutoff |
| Official club news | Later | Concrete availability information with timestamped source evidence |
| Licensed provider | Later | Structured expected lineups, injury history, detailed match events |

References and timing warnings are in SOURCES.md. Do not depend on FBref advanced tables as a current feed. Do not assume StatsBomb open data is a full current EPL dataset.

Use adapters that validate responses and preserve original bytes. Parse fields explicitly; tolerate new unrelated fields but reject missing required fields. Check that an API response is JSON with the expected structure rather than an HTML error document.

## 2. Official endpoints

Base URL: `https://fantasy.premierleague.com/api/`.

| Resource | Path |
|---|---|
| Bootstrap | `bootstrap-static/` |
| Fixtures | `fixtures/` |
| Player history | `element-summary/{element_id}/` |
| Public manager | `entry/{entry_id}/` |
| Manager history | `entry/{entry_id}/history/` |
| Public picks | `entry/{entry_id}/event/{event_id}/picks/` |
| Public transfers | `entry/{entry_id}/transfers/` |
| Live scores | `event/{event_id}/live/` |
| Private current team | `my-team/{entry_id}/`, deferred until current access is verified |

These are website endpoints with community documentation. During implementation, probe the required public endpoints without authentication, store schema fixtures, and document any changed shape. Never assume old authentication examples still work.

Initial refresh defaults: bootstrap and fixtures every six hours while the collector is running, manual refresh before solving, and additional capture shortly before deadlines. These are proposed schedules, not provider service guarantees. Implement configuration and graceful throttling. Capture exact timestamps rather than pretending every scheduled attempt ran on time.

Player histories can be cached after ingestion and refreshed after finalised matches. A failure preserves the last good snapshot. Avoid repeatedly requesting every player summary for each dashboard visit.

## 3. Immutable snapshot envelope

Required fields: `snapshot_id`, `provider`, `resource`, `captured_at`, `source_published_at` when supplied, `available_at`, `payload_sha256`, `schema_version`, `season`, `storage_path`, and `validation_status`.

Use UTC timestamps internally. The UI displays local time with a timezone label; deadline logic remains UTC. Unknown original publication time is null. For a newly captured live response, `available_at` is at least the capture time; never invent an earlier availability date.

Historical match dates establish when football happened, not necessarily when every revised statistic became available. Mark sources with uncertain information timing as unsuitable for strict replay of those fields. A conservative audit may still permit lagged completed match statistics while excluding historical injury flags, roles, odds, or price snapshots of unclear timing.

Archive fixture versions too. A final season fixture list does not establish which doubles or blanks were known earlier.

## 4. Identifiers and money

Maintain a canonical person ID and a mapping keyed by provider, provider player ID, and season. FPL element IDs can change between seasons. FPL `code` is a useful matching clue, not permission to skip mapping validation. Use names, club history, and available stable metadata to review unresolved matches; do not join solely on a display name.

Team identity also needs a season mapping. A player can change club or FPL position. Keep the historically applicable club and position on each observation.

Store all FPL money as integer tenths of a million. For an owned player:

```python
if current_price_units <= purchase_price_units:
    selling_price_units = current_price_units
else:
    selling_price_units = purchase_price_units + (current_price_units - purchase_price_units) // 2
```

Prefer a current verified private selling price or user confirmed selling price when purchase history is incomplete. Record which market snapshot the confirmed price belongs to. After a later market price change, recompute from known acquisition price or mark the confirmed selling price for review. Do not silently reuse a stale confirmation.

The sell and rebuy case creates a new acquisition record. Wildcard purchases use their actual acquisition price. Free Hit acquisitions do not replace the original persistent acquisition records.

## 5. Manager state reconciliation

An import creates a new version of a manager state. Public picks identify a deadline squad, not an exact current private team. Public history can support reconstruction, but cannot reveal every change made since the most recent deadline.

Each financial field has provenance: `private_verified`, `public_reconstructed`, `user_confirmed`, or `unknown`. Add a confirmation timestamp and supporting source. A reconstructed value remains distinguishable from a confirmed current value.

Track `free_transfers_at_event_start`, `transfers_made_this_event`, `confirmed_hit_points`, `current_chip`, `persistent_squad`, and `active_squad`. Keep a start of event state and a transfer ledger. If the start state cannot be established, require the missing information before offering a chip that depends on it.

A public picks response may contain final multipliers and automatic substitution information. Use documented lineup positions and captain flags appropriately, and do not mistake a final scoring multiplier for the manager's original starting selection. Verify the payload on a week with an automatic substitution.

For an ordinary event, with `f` free transfers at event start and `t` total transfers in that event:

```python
total_hit_points = 4 * max(0, t - f)
next_event_free_transfers = min(5, max(0, f - t) + 1)
```

Proposed moves add to already made moves. Compute the incremental cost relative to Keep so committed hits are not charged a second time in the recommendation delta. If current chip rules cancel hits or preserve transfer inventory, route through a separate chip transition function. Under the cited current rule, Wildcard or Free Hit preserves the saved transfer count rather than applying the ordinary transition; verify this against live game state before activating chip solving.

Free Hit requires the correct persistent squad from before the event's temporary moves. On the following event, restore its acquisition records and apply current market prices; do not restore outdated market prices. The precise bank and transfer transition must match verified official behaviour.

## 6. Canonical observation table

Primary key: season, canonical player, fixture ID. A Gameweek may have zero, one, or more fixtures for a player.

Store league, event assignment version, kickoff, club, opponent, venue, position, minutes, start flag where known, goals, FPL assists, clean sheet result, conceded goals, saves, penalties, cards, own goals, bonus, BPS, defensive actions, xG, xA, and final FPL points.

Use official FPL results as the final fantasy scoring target. External assists and defensive action definitions can differ. Retain provider labels and map definitions deliberately.

Represent eligible players who do not appear as zero minute outcomes when source coverage permits. Distinguish no appearance, no scheduled fixture, missing record, and missing statistic. Missing defensive actions are not zero actions.

Deduplicate player fixture rows, especially in Double Gameweeks. Avoid cumulative season statistics being treated as per match values. If differencing cumulative records, handle data revisions and transfers and validate against fixture level records.

## 7. Feature timing and feature groups

Every forecast has a `decision_cutoff`. Features must be built only from information available at or before it. For all fixtures in a Gameweek, use the FPL deadline cutoff, not each individual kickoff.

Recommended features:

| Group | Features |
|---|---|
| Opportunity | Starts, minutes, substitutions, absence frequency, recent return from injury |
| Attacking rates | xG and xA per 90, shots, key passes, longer term rate priors |
| Team strength | Recency weighted goals and xG for and against, venue effects |
| Defensive involvement | Position appropriate action distributions and threshold frequency |
| Goalkeeping | Save rates, expected concession environment, historical bonus patterns |
| Context | Rest days, European and cup minutes, fixture congestion, role changes |
| Future schedule | Known opponents, venue, event assignment, blank and double scenarios |
| Availability | Timestamped status and concrete news; null remains unknown |
| Roles | Penalty and set piece rank, with historical timing verified |

Use candidate windows of 3, 5, 10, and 20 matches, plus recency weighting. Select windows on training and validation data. Rate features must handle small exposures with shrinkage or longer term priors; a substitute's one shot should not establish an elite true rate.

Exclude the potentially updated historical `xP` field initially. Exclude same fixture realised minutes, xG, BPS, points, and closing odds unavailable at the FPL deadline from input features. Standardisation, imputation, feature selection, and encoding are fitted on training partitions only.

For future horizons, never insert future realised injury, minutes, or match outcomes. During a six week forecast, subsequent weeks use assumptions or simulated future state. Weekly replay may update the policy when that future week actually arrives.

## 8. Common forecast contract

Every model emits the same logical fields:

```json
{
  "projection_run_id": "example_run",
  "model_family": "baseline",
  "model_status": "evaluated",
  "player_id": "example_player",
  "fixture_id": 501,
  "event": 7,
  "decision_cutoff": "2026-10-01T12:00:00Z",
  "expected_points": 4.3,
  "expected_minutes": 72.0,
  "appearance_probability": 0.93,
  "start_probability": 0.84,
  "minutes_60_probability": 0.78,
  "point_quantiles": null,
  "components": null,
  "assumptions": ["illustrative payload, not a real forecast"]
}
```

Expected points are unconditional on appearance. If a component model predicts conditional returns, combine availability once. Never multiply an already unconditional prediction by appearance probability again. Quantiles and component breakdowns are optional and must be unavailable rather than fabricated.

FPL points can be negative. Do not clip all forecasts, samples, or intervals to zero. Poisson or negative binomial distributions are suitable for event counts, not a total FPL score with negative outcomes.

Fixture forecasts aggregate to Gameweek forecasts. Means sum, but quantiles and variances require joint samples or an explicit dependence assumption. Do not sum player percentiles to create a squad percentile.

## 9. Baseline

Implement an explainable component baseline with recent minutes distributions, shrunk attacking rates, venue and team adjustment, clean sheet probabilities, and a labelled approximate bonus contribution. If defensive data is absent, mark the defensive component unavailable or use an explicitly documented prior.

Also keep a simple recent points average baseline for evaluation. These are references for model quality, not the planned advanced product.

## 10. Model 1: CatBoost

Use structured features to predict unconditional expected fixture points. Begin with an RMSE mean objective; evaluate position specific models or position aware pooled models. Train auxiliary appearance, start, and minutes threshold predictions when labels are available. Keep auxiliary outputs coherent and calibrate probabilities.

Quantile heads can later estimate point percentiles. A quantile model targets a percentile, not the mean used by a points maximiser. Address quantile crossing and assess coverage. Do not apply Poisson directly to potentially negative total points.

Use chronological tuning, early stopping on a later validation block, regularisation, and reproducible seeds. Compare performance for starters, low minutes players, new players, and high expected return candidates. Store feature importance; describe it as model attribution rather than causal proof.

## 11. Model 2: Bayesian events

Build a hierarchical model of team attack and defence, with venue and time effects. Model player contribution and exposure, sharing information by position or role. Test Poisson and overdispersed event count assumptions. Use an identifiable parameterisation and check posterior convergence.

Generate coherent match scenarios: shared team goals, player scoring and assist allocation, minutes, saves, defensive thresholds, cards, and bonus. Account for changing roles and small samples through priors.

Exact BPS reconstruction requires many event inputs. When they are unavailable, use a validated approximate bonus model and label the component. Do not claim full Opta scoring replication from summary statistics.

Check posterior predictive fit and convergence diagnostics. Start with small datasets for installation and execution checks, then use the real audited training panel. Preserve posterior or predictive samples and seeds. Avoid presenting posterior parameter uncertainty as the full range of possible match outcomes.

## 12. Model 3: Temporal Fusion Transformer

Use a compact global model across player sequences. Include historical observations, known future fixture information, and static role information. Unknown future minutes, injury, xG, and points cannot be supplied as future inputs.

Use a padded and masked event representation or an equivalent fixture sequence representation that preserves multiple fixtures and zero fixture events. Define sequence indexing explicitly and test Double Gameweeks. A single averaged opponent for a double is insufficient.

Start with limited depth and embedding size, regularisation, and early stopping. Separate a mean target used for expected points from quantile targets; a median is not automatically an expected score. Keep CPU execution feasible for inference and document any accelerator needed for training.

Activation requires chronological held out performance. Architecture suitability is a hypothesis. Do not ship a placeholder neural model with synthetic outputs labelled trained.

## 13. Ensemble and scenario evaluation

Learn nonnegative weights summing to one from forecasts produced on validation folds, without training contamination. Use one global blend first; add position or horizon specific weights only with enough evidence. Weight zero is valid.

Compare the blend against its best individual model. Do not learn weights on the final test period. Track model disagreement as one indication of uncertainty, not a calibrated confidence score.

A mixture of predictive distributions has quantiles different from averaged quantiles. Preserve joint football relationships when combining forecasts with a scenario engine. If only independent marginal estimates exist, explicitly state that squad risk metrics are approximate and avoid strong rank claims.

## 14. Decision engine

Use HiGHS to generate feasible plans under budget, position, club, transfer, chip, and state transition constraints. Default horizon six events. Include Keep and transfer saving. Score net points and maintain terminal value for bank, squad quality, and saved transfers so the final planning week does not create an artificial spending spree. Fit or sensitivity test those terminal values.

Persist market and purchase prices separately. Candidate squad ownership evolves with transfers. Support player locks and exclusions. Handle solver limits and report the best valid incumbent plus gap when available.

Evaluate leading candidates with shared match scenarios, captain fallback, formation preserving bench substitutions, and chip effects. Approximate linear bench weights can generate candidates, but must be labelled and reranked using the fuller evaluator when available.

A mathematical optimum is conditional on forecasts, assumptions, candidate universe, horizon, and solver formulation. It is not a guarantee of maximum realised points.

## 15. Evaluation protocol

Use expanding chronological folds across complete Gameweeks. Purge training targets that cross a validation cutoff for overlapping future horizons. Choose hyperparameters and ensemble weights on validation folds, then evaluate once on the held out period.

Evaluate mean forecast MAE and RMSE, ranking quality among plausible picks, probability calibration for appearances and thresholds, quantile pinball loss and interval coverage, and full policy points after hits. Bootstrap or otherwise assess differences with Gameweek blocks; player rows from one match are not independent experiments.

A full policy replay needs historical bank, acquisition prices, free transfers, chips, and candidate availability. If those are incomplete, label the result as lineup evaluation or partial transfer replay instead of a complete season backtest.

Publish separate results by position, horizon, minutes category, new versus established players, and ordinary versus double or blank events. Compare every policy from the same initial state and the same information access.

## 16. Model registry and fallbacks

States: `not_installed`, `not_trained`, `trained`, `evaluated`, `active`, `disabled`.

If a model is unavailable, omit it and show the reason. If enrichment fails, fall back only to a model trained for that reduced feature set. Do not substitute zeros into a rich model and hope its outputs remain calibrated.

Before a deadline, freeze the source and prediction versions used for the recommendation. Evaluate outcomes only after the event is finalised. Compare real and demo runs separately.
