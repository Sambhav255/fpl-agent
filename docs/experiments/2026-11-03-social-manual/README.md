# Manual social evidence — 3 November 2026

M17 now has an operator path through the existing social records, structured validator, reviewed source registry and deletable SQLite store. It accepts operator-supplied **self-authored, permissioned, or explicitly synthetic** text. It does not collect Reddit/X material or contact external models.

The JSON manifest declares local storage/inference/derived-claim rights with finite retention, permission evidence, reviewer, canonical player IDs and their mapping reference. Claims explicitly resolve a player and exact evidence span, horizon, action/topic, attribution, conditions and any factual availability assertion. Unknown players and unsupported spans fail. Availability assertions must be report-type availability claims. The importer does not claim that a supplied annotation has been independently adjudicated.

Publication time and source reference are retained separately from **actual import-time observation and review**. A newly imported old report cannot enter an earlier origin. Source profiles use the existing topic-specific expert/crowd/unknown categories and as-of review windows; a later review cannot upgrade old claims. Unreviewed authors remain unknown. Source reliability stays at the existing broad Beta prior unless separate verified resolutions are available; manual import does not fit reliability or turn wording into an appearance probability.

Imports are atomic, including source reviews and the content-free receipt. Identical retries do not duplicate claims or shift the first observation. Exact-text evidence families and repeated author/family/assertion qualifications are deduplicated. Conditions and contradictions remain visible. Context references support deletion of dependent posts and claims. Source text lives in the existing deletable post records; receipts keep hashes, rights, timestamps and identifiers rather than a second text archive. Retention applies on queries and retries. Deletion does not allow receipt replay to resurrect text.

Availability output is **review-only evidence**: out/available/start/training/uncertain branches, conditions, source group and prior-only reliability. It never changes a forecast; direct points adjustment remains **zero**. A training report does not become a confirmed start. Live coverage, calibrated availability probabilities, extraction-quality claims, trained semantic models and social forecast ablations remain unavailable.

## Commands

Use the dedicated social database, separate from private app state:

```sh
backend/.venv/bin/python scripts/social_manual.py --database data/social.sqlite import reviewed.json
backend/.venv/bin/python scripts/social_manual.py --database data/social.sqlite scenarios --horizon GW10
backend/.venv/bin/python scripts/social_manual.py --database data/social.sqlite delete permissioned:post-id
```

[The authored example](authored-example.json) demonstrates the schema. It is an engineering fixture about a fictional player, not a real post, independently reviewed label, or football recommendation. For authored/permissioned imports set `material` to `self_authored`/`permissioned`, use provider `permissioned`, and namespaced `permissioned:` post IDs. Set `source_reference` when an original reference exists; it is retained as text, never fetched. Restrict claims to explicit IDs in the declared mapping. Optional `profiles` use the existing `SourceProfile` contract with author, group, topic scope, review evidence/reviewer/version, and aware reviewed/effective/expiry timestamps. External processing and model training flags are deliberately refused by this importer.

Actual CLI exercise on 3 November at 13:13 UTC imported the synthetic fixture, produced one review-only availability branch with unknown source category/prior-only reliability, deleted it, and returned unavailable coverage afterward. No real social content or personal state was used. Focused verification: **35 social tests passed**, including ten new manual-import cases; changed Python files passed Ruff. Social mypy checks are recorded in the final integrated build status.
