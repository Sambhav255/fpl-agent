# Sources and evidence

Reviewed 12 October 2026. Repository findings are derived from pinned source and local synthetic probes. External implementation guidance uses primary sources. Proposed architecture and gates are recommendations, not claims that the repository already implements them.

## Repository

1. [Pinned repository](https://github.com/Sambhav255/fpl-agent/tree/840c1185d005270717c7453fb278dc30a03c05f3).
2. [Changes since previous audit](https://github.com/Sambhav255/fpl-agent/compare/e759bcfb299d3f818d2e80ebb017796874cf8019...840c1185d005270717c7453fb278dc30a03c05f3).
3. [Current build status](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/docs/BUILD_STATUS.md).
4. [Football CatBoost experiments](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/docs/experiments/CATBOOST_FOOTBALL.md). Reported metrics; ignored binary artifacts were not retrieved.
5. [Strategy replay](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/evaluation/strategy.py).
6. [Planner](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/optimisation/planner.py).
7. [Forecast router](https://github.com/Sambhav255/fpl-agent/blob/840c1185d005270717c7453fb278dc30a03c05f3/backend/src/fpl_app/models/router.py).
8. [Hosted verification](https://github.com/Sambhav255/fpl-agent/actions/runs/38207057987). Relevant checks succeeded; overall cleanup remained in progress at the recorded audit observation.

## Reinforcement learning

1. [Gymnasium environment tutorial](https://gymnasium.farama.org/introduction/create_custom_env/). Custom environment interfaces and explicit episode endings.
2. [Stable Baselines3 guidance](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html). Practical training and evaluation guidance; verify stable package versions when installing.
3. [MaskablePPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html). Mask aware evaluation utilities required; standard implementation does not support recurrent policies. This supports the proposed masked candidate policy mechanics, not an FPL performance claim.
4. [Competing with Humans at Fantasy Football](https://ojs.aaai.org/index.php/AAAI/article/view/8259). Research precedent for sequential team selection under partial observability. It is not a current 2026/27 FPL benchmark for this app.

## Forecasting research

1. [OpenFPL paper](https://arxiv.org/abs/2508.09992), [full text](https://arxiv.org/html/2508.09992v1). A useful public data forecasting benchmark candidate, with position specific ensembles and prospectively tested short horizons. Published author results are not independently reproduced here. Scoring era, source access, code licensing and data timestamp differences must be checked before implementation or comparison.
2. [Temporal Fusion Transformer paper](https://arxiv.org/abs/1912.09363). Supports the model family concept; the app still requires an implemented and evaluated multilead decoder.
3. [Sentence BERT paper](https://arxiv.org/abs/1908.10084). Supports semantic embedding comparison, not automatic FPL recommendation understanding.

## Official FPL and platform sources

1. [FPL API bootstrap](https://fantasy.premierleague.com/api/bootstrap-static/). Current event metadata and universe; future implementation must retain source bytes and observed timestamps.
2. [2026/27 FPL changes](https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627).
3. [2026/27 chip windows](https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627). Two chip sets and one chip per event; verify actual deadline timestamps from current official data.
4. [Official rules](https://fantasy.premierleague.com/en/help/rules). Retain verified rules evidence before changing domain transitions.
5. [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy). API approval and processing/training restrictions.
6. [X Developer Guidelines](https://docs.x.com/developer-guidelines), [X Developer Policy](https://docs.x.com/developer-terms/policy). Permitted access, ML restrictions and retained content requirements must be checked before enabling adapters.

No paper, vendor claim or social popularity measure proves that a complex model will improve this specific team's decisions. The new journal and policy evaluation are how that question becomes testable.
