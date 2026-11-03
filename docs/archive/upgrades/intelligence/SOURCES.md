# Sources and evidence

Research date: 10 October 2026. Repository findings are pinned to `e759bcfb299d3f818d2e80ebb017796874cf8019`. External sources can change. Verify provider access, pricing and season rules when enabling features.

## Repository evidence

| Evidence | Pinned source |
| --- | --- |
| Current status and recorded verification | [BUILD_STATUS.md](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/docs/BUILD_STATUS.md) |
| Advanced model integration gaps | [ML_INTEGRATION.md](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/docs/ML_INTEGRATION.md) |
| Baseline only worker route | [Worker.compute](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/jobs/__init__.py#L305-L345) |
| Approximate active model | [baseline.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/baseline.py) |
| Actual training feature list | [pipeline.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/features/pipeline.py#L41-L52) |
| Historical assumptions | [archive.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/features/archive.py) |
| CatBoost training and evaluation | [training.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/training.py) |
| Model registry | [registry.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/registry.py) |
| CatBoost and common inference | [inference.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/inference.py) |
| Bayesian scenarios | [bayesian.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/bayesian.py) |
| TFT model | [tft.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/tft.py) |
| Strict inactive adapters | [strategy_adapters.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/models/strategy_adapters.py) |
| Metrics and ensemble utility | [metrics.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/evaluation/metrics.py) |
| Ownership proxy and beam search | [planner.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/optimisation/planner.py) |
| Chip timing limitations | [advice.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/optimisation/advice.py) |
| Real scoring and legal lineup selection | [rules.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/domain/rules.py) |
| Current event product emphasis | [optimum-card.tsx](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/apps/web/src/components/planner/optimum-card.tsx) |
| Financial and model contracts | [contracts.py](https://github.com/Sambhav255/fpl-agent/blob/e759bcfb299d3f818d2e80ebb017796874cf8019/backend/src/fpl_app/contracts.py) |

## External sources

### S01. Official season changes

[Premier League: all changes for 2026/27](https://www.premierleague.com/en/news/4679873). Supports retaining defensive contribution scoring, new BPS considerations, two chip sets, free transfer inventory and later event score finalisation. These changes matter to labels, target regimes and chip expiration planning.

[Official FPL Rules Copilot](https://www.premierleague.com/en/news/4661029) and [official rules entry point](https://fantasy.premierleague.com/help/rules). The rules entry point returned no readable content in this retrieval, so it was not used as sole proof of a detailed rule. Reverify the exact rules and archive their version during implementation.

[Premier League: chips in 2026/27](https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627). Supports chip windows and the loss of unused first half chips.

### S02. Historical archive

[Vaastav FPL dataset](https://github.com/vaastav/Fantasy-Premier-League). Its current README states that weekly updates stopped after 2024/25 and warns about potential lookahead in xP. Use as historical material with audited limitations. The notice does not establish exact publication timing for each row or a complete present season feed.

### S03. Open FPL solver

[solioanalytics/open-fpl-solver](https://github.com/solioanalytics/open-fpl-solver). A public HiGHS based deterministic optimiser with configurable projections and constraints. It is a useful implementation and benchmark reference. Review its current constraints, source license and attribution before reusing code. Do not assume it implements this PRD's stochastic policy or current rules without checking.

### S04. Fantasy Football Fix

[Fix competitive comparison](https://www.fantasyfootballfix.com/competitive/). Describes squad planning, rotation, starting probabilities, expert team reveals and consensus. These are product references. Claims of superior forecasts or rankings are vendor assertions, not independently reproduced benchmarks and not proof of its proprietary model architecture.

### S05. Reddit access

[Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), updated 5 October 2026. Specifies explicit API approval and distinguishes developer, research and commercial routes.

[Data API Terms](https://redditinc.com/policies/data-api-terms) and [Developer Terms](https://redditinc.com/policies/developer-terms). These govern data access and additional use, including model training. Application approval should cover semantic analysis, storage, derived summaries and any intended model use.

### S06. X access and costs

[Official X API pricing](https://docs.x.com/x-api/getting-started/pricing). Current table lists $0.005 per post read and $0.010 per user read. Charges depend on returned resources, with spending controls and deduplication described separately. The planning arithmetic in this bundle uses that table and excludes other billable operations.

[Official search documentation](https://docs.x.com/x-api/posts/search/introduction). Documents recent search over seven days and separate archive search access. Supports a bounded collector and explicit historical coverage limitations.

### S07. X processing and retention

[Developer Agreement](https://docs.x.com/developer-terms/agreement), [Developer Policy](https://docs.x.com/developer-terms/policy) and [Developer Guidelines](https://docs.x.com/developer-guidelines). Relevant to model training restrictions, permitted access, public display, content changes, removal and identity matching. Configure capabilities from the applicable account terms rather than assuming API access grants unrestricted downstream rights.

### S08. Semantic analysis

[Sentence BERT paper](https://arxiv.org/abs/1908.10084) and [Sentence Transformers semantic similarity documentation](https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html). Support embeddings for comparing meaning and grouping related text. Similarity does not verify factual truth.

[Cardiff NLP tweet sentiment model card](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest). A general sentiment comparator; its task is not the FPL specific conditional stance extraction required here. Check model license and fit before use.

### S09. TFT

[Temporal Fusion Transformer paper](https://arxiv.org/abs/1912.09363). Describes a model for multiple forecasting horizons with static, observed and known future inputs. It motivates the architecture, but does not establish that the current one event FPL implementation has that capability or will outperform CatBoost.

### S10. Local NLP model candidates

[MiniLM sentence embedding model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [DeBERTa zero shot model card](https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33). Concrete candidate artifacts for local benchmarks. Neither provides measured FPL extraction quality out of the box.

## Recommendations versus established facts

The proposed models, risk objectives, feature groups, thresholds, milestones and source weighting schemes are design recommendations. They are not measured results from your team. The synthetic search miss and frozen availability behaviour were directly reproduced. Real FPL performance, source reliability and incremental social value remain to be measured.
