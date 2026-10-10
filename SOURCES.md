# Sources and verification notes

Research date: 9 October 2026. Season discussed: standard FPL 2026/27.

These links ground the research and provide references for implementation. This kit does not claim that third party endpoints, authentication procedures, native package installation, or trained model performance have been tested in the user's project.

## Official FPL rules

| Reference | URL | Use |
|---|---|---|
| Full game rules | https://fantasy.premierleague.com/en/help/rules | Canonical rules; rendered content may require the website |
| Official rules explanation | https://www.premierleague.com/en/news/4661029 | Squad, transfers, selling prices, chips, scoring |
| Beginner guide | https://www.premierleague.com/en/news/1252542 | Formation, squad, deadline |
| Scoring explanation | https://www.premierleague.com/en/news/2174909/fpl-basics-explained-scoring-points | Fantasy scoring and assist cases |
| Defensive contributions | https://www.premierleague.com/en/news/4361991 | Position specific thresholds |
| 2026/27 updates | https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627 | Season changes and later score finalisation |
| Current chip explanation | https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627 | Two chip sets and restrictions |
| BPS changes | https://www.premierleague.com/en/news/4679946/whats-new-in-202627-fantasy-changes-to-bonus-points-system | Revised bonus inputs |
| Price predictor | https://www.premierleague.com/en/news/4680462/whats-new-in-202627-fantasy-price-change-predictor | Official price prediction feature |

Implementing agents should inspect current game configuration and rendered official rules, store a rule version, and verify difficult state transitions. Do not infer next season's rules from this document.

## Data and open implementations

| Reference | URL | Use and limitation |
|---|---|---|
| Official bootstrap | https://fantasy.premierleague.com/api/bootstrap-static/ | Current data endpoint opened during research |
| Official fixtures | https://fantasy.premierleague.com/api/fixtures/ | Current fixtures endpoint opened during research |
| Community endpoint catalogue | https://github.com/jakesmith1997-sfc/fpl-api/blob/main/README.md | Community documentation; not an official API contract |
| Vaastav archive | https://github.com/vaastav/Fantasy-Premier-League | Historical records; weekly updates stopped after 2024/25; xP timing warning |
| FPL Core Insights | https://github.com/olbauday/FPL-Core-Insights | Recent data and context; inspect field provenance and snapshot timing |
| Understat EPL | https://understat.com/league/EPL | Attacking metrics; keep provider identity |
| Understat adapter docs | https://soccerdata.readthedocs.io/en/stable/reference/understat.html | Retrieval interfaces; no guarantee of provider uptime |
| Football Data | https://football-data.co.uk/data.php | Historical results and odds; verify odds availability before deadlines |
| FBref data update | https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/ | Provider access and advanced table removal announcement |
| StatsBomb open data | https://github.com/hudl/open-data | Selected public competitions, not complete current EPL coverage |
| Open FPL solver | https://github.com/solioanalytics/open-fpl-solver | HiGHS based optimisation; audit current rules before adaptation |
| OpenFPL repository | https://github.com/daniegr/OpenFPL | Reproducible forecasting reference |

The Sports Reference announcement was supported by indexed content from its official site; direct retrieval returned a block during research. Historical repository snapshot descriptions do not by themselves prove strict feature availability before each deadline.

## Research papers

| Paper | URL | Relevance |
|---|---|---|
| OpenFPL | https://arxiv.org/abs/2508.09992 | Public data ensembles; prospective evaluation during 2024/25 |
| FPL selection framework | https://arxiv.org/abs/2505.02170 | Mixed integer optimisation and empirical comparisons |
| EPL player performance forecasting | https://arxiv.org/abs/2405.02412 | Numerical sequence models and news experiments |
| Temporal Fusion Transformer | https://arxiv.org/abs/1912.09363 | Multiple horizon architecture with known future covariates |
| Bayesian football results | https://discovery.ucl.ac.uk/id/eprint/16040/ | Hierarchical football modelling and shrinkage considerations |

OpenFPL reports competitive forecast accuracy on older season rules. That does not establish that this proposed app beats current commercial products or improves final rank. The Bayesian player event extension and TFT design in this kit are proposals to test.

## Product references

| Product | Reference |
|---|---|
| Fantasy Football Fix features | https://www.fantasyfootballfix.com/web_features/ |
| Fix team linking limitation | https://support.fantasyfootballfix.com/support/solutions/articles/202000056626-how-do-i-link-my-fpl-team- |
| Fix extension | https://www.fantasyfootballfix.com/extension/ |
| FPL Review model | https://docs.fplreview.com/the-model/projections/massive-data-model/ |
| FPL Review minutes | https://docs.fplreview.com/the-model/projections/xmins/ |
| FPL Review sync warning | https://docs.fplreview.com/the-model/planner-interface/sync_team/ |
| FPL Review solver differences | https://docs.fplreview.com/the-model/solvers/solver-comparison/ |
| Fantasy Football Hub | https://www.fantasyfootballhub.co.uk/ |
| Fantasy Football Scout | https://www.fantasyfootballscout.co.uk/2026/08/10/how-to-use-our-rate-my-team-tool-to-get-your-fpl-squad-rated |
| FPL Team planner | https://fpl.team/plan/ |
| LiveFPL | https://www.livefpl.net/ |
| Sportmonks expected lineups | https://www.sportmonks.com/football-api/expected-lineups-api/ |

Use functional ideas and public documentation. Do not represent a proprietary model as reproduced, copy branding, or assume access to a commercial data licence.

## Stack and coding workflow

| Reference | URL |
|---|---|
| Next.js setup | https://nextjs.org/docs/app/getting-started/installation |
| Node release support | https://nodejs.org/en/about/previous-releases |
| FastAPI dependency versions | https://fastapi.tiangolo.com/deployment/versions/ |
| uv | https://docs.astral.sh/uv/ |
| SQLAlchemy | https://docs.sqlalchemy.org/en/20/ |
| DuckDB | https://duckdb.org/docs/stable/ |
| TanStack Query | https://tanstack.com/query/latest/docs/framework/react/overview |
| CatBoost objectives | https://catboost.ai/docs/en/concepts/loss-functions-regression |
| PyMC | https://www.pymc.io/projects/docs/en/stable/ |
| PyTorch Forecasting | https://pytorch-forecasting.readthedocs.io/en/stable/ |
| HiGHS | https://highs.dev/ |
| Cursor rules | https://cursor.com/docs/rules |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md |
| Codex CLI | https://developers.openai.com/codex/cli |

The official Codex URLs redirected to ChatGPT Learn documentation during this research. AGENTS.md is intended as the shared project instruction file. The project still needs dependency resolution and installation checks; this kit intentionally avoids invented exact current package versions.

## Required implementation verification

1. Current FPL endpoint shapes and source availability.
2. Current private team access before attempting exact sync.
3. Saved transfer transitions during chips and the correct Free Hit restoration state.
4. Historical source timing, player mapping, and zero minute coverage.
5. Native dependency compatibility on the user's Mac.
6. Genuine training, chronological evaluation, calibration, and model activation.
7. Provider access and redistribution terms before a public commercial product.

Optional choices such as paid data, public deployment, and an LLM news parser remain outside the default implementation scope.
