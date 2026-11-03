# Expert and crowd intelligence specification

Date: 10 October 2026. Goal: extract football evidence and FPL recommendations from approved sources, show sampled consensus, and test whether those signals improve decisions.

## 1. Product principle

Semantic analysis should identify what someone means about a player, not merely whether a sentence sounds positive. An expert consensus is a description of a reviewed source sample, not proof of truth. A crowd consensus is not representative of every FPL manager.

Keep four distinct outputs: football facts, expert strategy stance, crowd strategy stance and model prediction. Do not compress these into one invented player rating.

## 2. Source access and implementation modes

| Provider | Current verified constraint | Product design |
| --- | --- | --- |
| Reddit | Explicit approval required for API access; intended use must be disclosed; training and other uses have separate restrictions | Build an adapter and apply for the exact external analytics use case; default disabled |
| X | Official API offers recent and archive search; reads are metered; training restrictions apply | Use official API with a spend cap; default disabled |
| Licensed or permissioned contributor material | Rights depend on the agreement | Accept only the processing and retention actually covered |
| Synthetic text examples | Created for testing | Exercise extraction and interface without implying live coverage |

Reddit's current Responsible Builder Policy says uses not supported by Devvit require a request, and commercial use requires explicit written approval. Do not assume that registering OAuth credentials or installing PRAW grants access to this analytics project. Research program access is a separate route and not a substitute for approval of a personal application.

X's official pages currently list post reads at $0.005 per returned resource and user reads at $0.010. Thus 5,000 new billable post reads cost approximately $25, excluding profiles, extra resources and inference. Treat that as a planning example, not a promised bill. Set both an app budget and the provider spending limit. Deduplication can reduce repeated read charges, but local caching and hard caps are still needed. Verify pricing when enabling the connector.

Recent X search covers seven days. Full archive access is separately available through the current paid access model. Starting a collector today cannot produce an honestly observed historical stream for previous deadlines.

Build provider capability flags for `allow_read`, `allow_store`, `allow_inference`, `allow_external_processing`, `allow_derived_features`, `allow_training`, and retention. Rights to fetch are not automatically rights to train a model. Initially prohibit fitting classifiers, points models or expert weights on restricted content unless the intended use is explicitly covered. Derived numeric features are not an automatic workaround.

Inference with an existing model is a separate activity from fitting or fine tuning. Verify that the intended inference, storage and any third party processing are allowed before activation. Prefer local processing when it fits the approved use case. Do not send source text to an external model by default.

Social content must support edits and removals. Do not copy the immutable forever retention policy of football snapshots. Retain tombstones and lineage sufficient to purge text, embeddings, derived claims and affected aggregates when required. Recompute affected summaries and record changes according to permitted retention.

These requirements come from current platform documentation in `SOURCES.md`. They do not require the product to stop functioning while access is pending: football forecasts and synthetic extraction tests remain usable.

## 3. What to collect

Reddit starting scope, if approved: r/FantasyPL and relevant analytical discussions; captain polls, injury threads, press conference discussion, transfer advice and team reveals. Other communities require the same access coverage and a clear reason to include them.

X starting scope: a reviewed registry of official club sources, specialist club reporters, FPL analysts and established managers, plus bounded keyword samples of ordinary FPL discussion. Resolve aliases, club names and ambiguous names through a football entity dictionary.

Prefer a small relevant sample to an expensive firehose. Track query, time range, language, source category, pagination, truncation, retrieval time and coverage. Do not present a top engagement sample as a population percentage.

Collect post ID, source author ID where permitted, creation time, first observation time, edit time, referenced original IDs and URLs, parent or quote context, language, permitted text, and engagement as observed at that time. Engagement collected tomorrow cannot be a feature of yesterday's forecast.

## 4. Author categories

| Category | How established | Useful for | Insufficient evidence |
| --- | --- | --- | --- |
| Official football source | Verified official publishing identity | Confirmed availability, schedule and quoted club information | A reposted claim without original context |
| Specialist reporter | Reviewed public role, beat and publishing record | Club team news and publicly reported rotation information | Follower count or a paid verification badge |
| FPL analyst | Reviewed forecasting or analytical work | Player comparisons, captaincy and strategy arguments | Popular content alone |
| Established manager | Explicitly supplied or publicly self linked history reviewed with consent where needed | FPL strategy and team reveal context | A single strong season or unverified rank claim |
| Crowd | Source has not met a reviewed specialist category | Sampled buy, sell, captain and hold sentiment | Upvotes treated as expertise |
| Unknown | Evidence is missing or ambiguous | Limited descriptive inclusion | Automatic promotion to expert |

Categories are versioned and reviewed. Allow overlapping expertise, such as reporter and analyst, without counting the same person twice. Do not link anonymous Reddit accounts to X identities by speculative matching. Use explicit consent or suitable publicly supplied identity evidence within the provider rules.

Expertise is topic specific. A manager with excellent historical rank does not automatically know who will start a particular club's next match. A reporter can be reliable about availability and poor at recommending FPL transfers.

Begin with a manual registry. Add evidence fields: source role, relevant clubs, claimed history, verification link, review date, category confidence, scope and uncertainty. Do not fabricate a list of vetted experts from memory.

## 5. Semantic extraction pipeline

1. Normalise permitted text while retaining quotations, negation and context.
2. Identify canonical player and club mentions, including aliases and ambiguous surname candidates.
3. Extract separate atomic claims for each player and topic.
4. Classify action: buy, sell, hold, captain, avoid, bench, no action or unclear.
5. Classify topic: availability, minutes, role, penalties, fixtures, performance, price, captaincy or chips.
6. Identify event horizon, conditions, certainty, negation, quotation, question, humour and promotional context.
7. Attach the evidence span and original attribution. Distinguish author opinion from someone else's quoted claim.
8. Cluster repeated claims and linked articles. Preserve contradictions.
9. Aggregate only claims with sufficient extraction quality and coverage.

Use a schema constrained extractor and a deterministic validator. An extraction model confidence score is not a calibrated probability unless it has been measured on labelled data. Low confidence entity or stance cases abstain.

Sentence embeddings are useful for semantic grouping and paraphrase detection. They do not establish truth or expertise. A general tweet sentiment model can be a secondary comparator, but cannot replace FPL stance extraction. Use independently permitted text or authored synthetic examples for labelled development fixtures.

| Text example, all synthetic | Required interpretation |
| --- | --- |
| “Palmer is brilliant, but sell him to fund Salah.” | Positive general sentiment; sell Palmer; buy Salah; funding dependency |
| “I would captain Haaland only if he starts.” | Conditional captain stance, not an unconditional recommendation |
| “Anyone selling Saka?” | Question; not a sell claim |
| “The reporter says he trained. That does not mean he starts.” | Quoted training report; no confirmed start |
| “Great, another one point cameo.” | Negative FPL exposure stance despite a positive word |
| “He is out for this match, should return after the break.” | Current absence report and uncertain later return; do not persist zero availability forever |

No injury diagnosis or private health inference belongs in this system. Public football availability reports can be recorded with their original attribution and permitted scope; do not infer sensitive attributes of source authors.

## 6. Evidence and reliability

Maintain reliability by source and topic, not a universal expert score. Suggested categories: factual availability, start prediction, probabilistic minutes forecast, player points forecast, strategy stance and price commentary.

For a resolvable factual claim, use a shrunk historical accuracy estimate with correct, incorrect and unresolved outcomes. A simple beta prior can illustrate uncertainty: `(correct + a) / (resolved + a + b)`. This is a proposal requiring permitted use and suitable labels, not evidence that an untested source has that reliability.

For stated probabilities, use proper scores and calibration against resolved outcomes. Do not convert “might start” into 70% without an evaluated extraction mapping. Strategy advice requires a defined comparator and horizon; outcome accuracy alone can reward lucky advice. Retain conditions and assess them only when they held.

Do not retroactively select experts using the same season that is being evaluated. Freeze the registry and reliability at each origin. Use shrinkage for small samples and penalise neither abstention nor unresolved claims as if they were false.

Authority, source track record, freshness, evidence quality and independence are distinct fields. The first version can show these separately instead of introducing an arbitrary composite score.

## 7. Expert and crowd consensus

Produce separate distributions across buy, sell, hold, captain, avoid and unclear actions for each player, horizon and source group. Do not force captain and transfer stances onto one axis: a strong captain candidate can still be a poor transfer for a particular budget.

For a binary stance within one topic, a proposed descriptive score is:

`C = sum(weight_i × stance_i) / sum(weight_i)`

Weights can include extraction quality, relevance, freshness and, for experts, permitted topic reliability. Aggregate repeated messages from one author before combining authors. Bound each author's contribution and reduce repeated evidence family contributions. Initial weights and half lives are configuration choices, not learned facts.

Effective sample size is `(sum(weight_i))² / sum(weight_i²)`. Report it alongside distinct authors and independent evidence families. Similar claims from many sources are not independent if all cite the same report. Thread and evidence family resampling can give more honest intervals than treating every comment as an independent vote.

Freshness depends on topic. Lineup information can become stale within hours; a chip strategy argument may remain relevant longer. Predeclare decay settings and measure their sensitivity. Do not infer an injury has resolved merely because an old report decayed.

Engagement can help locate material and indicate sampled attention. It should not dominate source authority. Saturate or omit engagement weights and compare results. Preserve balanced query samples instead of collecting only popular posts.

Show separate expert and crowd scores, disagreement, coverage status and momentum. Momentum needs comparable sampling windows; a wider search tomorrow must not be mistaken for increasing enthusiasm. A crowd versus expert gap is a discussion signal, not automatic evidence of a profitable differential.

## 8. Influence on forecasts and plans

Release 1: show claims and separate consensus beside football forecasts. Flag watchlist changes. No numerical points adjustment.

Release 2: where permitted, use independently supported public football facts to update a versioned availability or role scenario. Deduplicate information already present in official FPL data. Record the before and after assumptions and affected recommendation.

Release 3: evaluate permitted social features through chronological ablations: football only, plus factual reports, plus expert stance, plus crowd stance, and combined. Keep missingness and sampling scope explicit. Assess prediction quality and strategy points, not only extraction quality.

Fit influence only when rights cover it. The official X and Reddit training restrictions mean a functioning analytics view does not automatically permit training CatBoost on their derived signals. Until that is resolved, keep the social features out of fitted football models and expert weight learning.

Never add a fixed “expert bonus” to points. A bullish expert should not make a £5m player gain two expected points by decree. Credible evidence may alter minutes or a role distribution; social enthusiasm can remain useful context without moving the forecast.

## 9. Proposed records and API

`SocialPost`: provider and post IDs, permitted author reference, times, context IDs, query provenance, content state, retention and capability reference.

`SourceProfile`: reviewed category, evidence, topic scope, effective time, review version, optional permitted reliability summary.

`ExtractedClaim`: entity, topic, stance, condition, horizon, factual/opinion type, evidence span reference, origin source, quality and extractor version.

`EvidenceFamily`: original claim or URL, dependent reposts, contradictions and first observed time.

`ConsensusSnapshot`: entity and horizon, source group, action distribution, distinct authors, effective sample size, source families, sample coverage, freshness and aggregation version.

Proposed endpoints under `/api/v1`: social status, source registry, player claims, player consensus and permitted ingestion jobs. These are new contracts, not existing routes. Credentials remain server side. A disabled provider returns an explicit unavailable status and never fake live text.

## 10. Quality and release gates

Build a held out extraction set containing ambiguous surnames, quotes, sarcasm, conditional transfers, multiple players, conflicting updates, prices and chip timing. Require entity precision of at least 95% on the adjudicated fixture set and measure recall and action macro F1. This is an acceptance target, not a current result. Set a separately justified threshold for factual reports that may affect forecasts, and abstain below it.

Report reviewer agreement and errors by category. Require each factual update to retain source context. Test duplicate rumours, one prolific author, copied articles across platforms, pagination gaps, future engagement leakage, expired roles, edited text, deletions, budget exhaustion, unavailable credentials and source outages.

Provider access, extraction quality, consensus quality and predictive usefulness are four different release checks. Passing one does not establish the others.

## 11. Local implementation stack

Reuse Python, HTTPX, Pydantic, SQLite and the existing worker. Add optional `sentence-transformers` and `transformers` dependencies to an NLP extra rather than making every baseline installation download model weights.

Start semantic clustering experiments with `sentence-transformers/all-MiniLM-L6-v2`. Its model card describes a 384 dimensional embedding for short text and an Apache 2.0 license. Pin the downloaded model revision. Chunk longer threads without discarding quote context. Similarity thresholds must be measured on the FPL fixture set.

For a first stance comparison, evaluate a local zero shot NLI model such as `MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33` against deterministic rules. This is a candidate to benchmark, not an asserted accurate FPL classifier. It does not replace player resolution, conditions, attribution or evidence spans. A schema constrained extraction model can be added behind the same interface if it performs better under the permitted processing policy.

Store permitted embeddings with deletable source lineage. For a personal scale sample, use NumPy cosine comparisons and SQLite metadata. Add a separate vector database only if measured retrieval scale requires it. Keep forecasts and text processing in separate worker job types, with bounded batches, cancellation and budget accounting.
