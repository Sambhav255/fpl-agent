# Social intelligence: next implementation stage

The current subsystem is a useful conservative starting point. It is not a trained semantic model and does not collect real Reddit/X content. Do not rebuild its capability, reviewed source or deletion infrastructure unnecessarily.

## Build semantics before consensus claims

Retain the grammar extractor as a precision comparator. Add entity linking and a structured semantic extractor with player ID, action, topic, horizon, condition, funding relation, attribution, fact/opinion/question status, evidence span and abstention. Preserve source text only where permitted. A claim must be supported by its span.

Examples for the benchmark are authored fixtures, not real posts:

| Text | Required interpretation |
| --- | --- |
| Palmer looks great but I would sell him to fund Salah | Palmer sell, Salah buy, funding relation; positive sentiment is not a hold vote |
| Captain Haaland only if the manager confirms he starts | Conditional captain; separate from unconditional captain consensus |
| Is Watkins worth a hit? | Question; no buy vote |
| Reporter says Saka trained, but no decision on Saturday | Attributed report and unresolved availability; not confirmed starting |
| Sold Jackson last week, now holding | Historical sell versus current hold |
| Nice cameo again, clearly captain material | Potential sarcasm; abstain if unsupported |

Build an initial 200 to 300 varied authored/permissioned examples, with a frozen test subset, source family and temporal separation. The number is an engineering target, not proof of accuracy. Independently double review a subset and record disagreements. Do not manufacture a human reviewed label by asking the same model to grade itself.

Compare grammar, compact embedding/entity models and a permitted structured language model extractor if available. Small pretrained sentence embeddings help entity resolution and rumour similarity; they do not directly solve stance or conditional recommendations. Benchmark entity accuracy, action/topic/horizon F1, conditional and attribution accuracy, report precision, abstention coverage and evidence span fidelity. Calibrate any confidence scores on held out labels.

## Expert and crowd separation

Use reviewed, versioned roles: official football source, specialist club reporter, FPL analyst, established manager, crowd and unknown. A reviewed expert label is not a guarantee of accuracy. Keep topic assignments explicit. A reporter may be credible about training without being strong at FPL transfer strategy.

Factual reliability can learn from timestamped claims with verifiable resolutions. Separate confirmed out/available, actual start and uncertain wording. Use shrinkage toward a topic prior and uncertainty intervals; sparse source histories stay close to the prior. Do not translate “might play” into an invented numerical probability or mark it wrong because the player did not play.

For FPL strategic opinion, evaluate comparable forecasted or recommended actions with explicit horizon, costs and uncertainty. Points gained by a single recommendation are noisy and depend on the starting squad. Avoid a leaderboard based on hindsight picking the one expert who happened to captain the week's highest scorer.

Freeze source inclusion and reliability as of each origin. Reviewing today's best performing pundit cannot retroactively make them part of last month's expert sample. Followers, verified badges and retweets are not the primary weighting signal.

## Aggregation and use

Show expert and crowd buy/sell/hold/captain distributions separately, by horizon and topic. Conditional views are separate rather than discarded permanently. Display disagreements, distinct authors, independent rumour families, coverage and recency.

Extend exact text deduplication to linked article and semantic evidence families with reviewed thresholds. Reposted reports are amplification, not independent confirmation. Cap author repetition and preserve conflicting claims. Missing live coverage stays unavailable.

Initially use reports to trigger review and opinions to explain agreement/disagreement. Structured availability evidence can create scenario branches when its provenance supports that use. No fixed expert bonus to player expected points. RL reward remains football points after hits.

Before any social derived training feature, verify permission for that derived use and run a football only versus social ablation on chronological origins. Also compare minutes improvement, strategy gain and false alarm costs. Engagement and hype often describe popular players rather than new football information.

## Access and retention

Current Reddit policy requires explicit approval for API access and places separate restrictions on training and commercial use. X developer guidance requires official permitted access and has explicit ML training restrictions. Reading, storing, semantic inference, exporting and training are separate capabilities; a token does not grant them all.

Use authored fixtures now and permitted data when available. No scrape fallback, identity matching of anonymous Reddit accounts to X accounts, or platform limit evasion. Provider deletion/edits must remove affected text, embeddings, claims, consensus caches and any permitted derived training artifacts under their retention rules. Keep numerical model results only when permitted and traceable.

Live collection remains an optional adapter. A missing Reddit or X configuration cannot stop football model and planner operation. Record sampling bias: a subreddit or curated X list is not the general FPL population.
