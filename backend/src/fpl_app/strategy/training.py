"""Optional fitted-Q and MaskablePPO research with immutable evidence artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np

from fpl_app.contracts import Settings
from fpl_app.domain.rules import RULES
from fpl_app.storage import fingerprint, utcnow
from fpl_app.strategy.candidates import CANDIDATE_VERSION

POLICY_VERSION = "shared-candidate-maskable-ppo-v1"


def implementation_digest():
    from hashlib import sha256

    return fingerprint(
        {
            name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ("candidates.py", "environment.py", "policy.py", "training.py")
        }
    )


def q_features(obs):
    players = obs["players"]
    present = players[:, :1]
    pooled = (players * present).sum(axis=0) / max(1, float(present.sum()))
    context = np.concatenate([obs["context"], pooled])
    candidate = obs["candidates"]
    return np.concatenate(
        [
            np.ones((len(candidate), 1)),
            np.broadcast_to(context, (len(candidate), len(context))),
            candidate,
        ],
        axis=1,
    )


@dataclass
class FittedQ:
    weights: np.ndarray

    def predict(self, obs, mask):
        if not np.any(mask):
            raise ValueError("No legal actions")
        values = q_features(obs) @ self.weights
        return int(np.argmax(np.where(mask, values, -np.inf)))

    def save(self, path: Path):
        np.savez(path, weights=self.weights)

    @classmethod
    def load(cls, path: Path):
        with np.load(path, allow_pickle=False) as data:
            weights = data["weights"]
        if weights.ndim != 1 or not np.isfinite(weights).all():
            raise ValueError("Invalid fitted value artifact")
        return cls(weights)


def fit_value(episodes, settings: Settings, *, k=32, iterations=4, ridge=1.0):
    """Fitted Bellman Q on valid actions, using only training path outcomes.

    Transitions use full simulator replay including acquisition/chips/hits.
    Natural terminals have zero continuation; artificial cutoffs require a
    supported observation for bootstrapping. Fixed scales are not fitted on test.
    """
    from fpl_app.strategy.environment import FPLEnv

    records = []
    for episode in episodes:
        env = FPLEnv([episode], settings, k=k)
        obs, _ = env.reset(seed=0)
        done = False
        trajectory: list[int] = []
        while not done:
            for a in np.flatnonzero(env.action_masks()):
                # Recreate the same observable state before trying each action;
                # this mutates a private paper environment only.
                branch = FPLEnv([episode], settings, k=k)
                branch.reset(seed=0)
                for previous in trajectory:
                    branch.step(previous)
                next_obs, reward, terminated, truncated, info = branch.step(int(a))
                if truncated and not info["bootstrap_forecast_supported"]:
                    raise ValueError("Unsupported truncated value target")
                records.append((q_features(obs)[a], reward, next_obs, terminated))
            valid = np.flatnonzero(env.action_masks())
            chosen = int(valid[np.argmax(obs["candidates"][valid, 1])])
            trajectory.append(chosen)
            obs, _reward, terminated, truncated, _info = env.step(chosen)
            done = terminated or truncated
    if not records:
        raise ValueError("No fitted value transitions")
    x = np.stack([r[0] for r in records])
    weights = np.zeros(x.shape[1])
    for _ in range(iterations):
        targets = []
        for _, reward, next_obs, terminated in records:
            valid = next_obs["mask"].astype(bool)
            continuation = (
                0.0 if terminated else float(np.max((q_features(next_obs) @ weights)[valid]))
            )
            targets.append(reward + continuation)
        penalty = np.eye(x.shape[1]) * ridge
        weights = np.linalg.solve(x.T @ x + penalty, x.T @ np.array(targets))
    return FittedQ(weights), len(records)


def evaluate(env, chooser):
    started = perf_counter()
    obs, info = env.reset(seed=0)
    rows = []
    while True:
        mask = env.action_masks()
        decision_started = perf_counter()
        action = int(chooser(obs, mask))
        inference_seconds = perf_counter() - decision_started
        if not mask[action]:
            raise ValueError("Policy selected an invalid action")
        obs, reward, terminated, truncated, info = env.step(action)
        rows.append(
            {
                "event": info["event"],
                "net_points": reward,
                "hits": info["total_hits"],
                "semantic_action": info["semantic_action"],
                "candidate_count": len(info["candidate_ids"]),
                "candidate_truncated": info["candidate_truncated"],
                "inference_seconds": inference_seconds,
            }
        )
        if terminated or truncated:
            break
    return {
        "net_points": sum(r["net_points"] for r in rows),
        "rows": rows,
        "invalid_accepted_actions": 0,
        "episode_seconds": perf_counter() - started,
        "worst_event_net_points": min(r["net_points"] for r in rows),
        "total_hits": sum(r["hits"] for r in rows),
        "candidate_truncated_events": sum(r["candidate_truncated"] for r in rows),
    }


def _split_check(train, test):
    if not train or not test:
        raise ValueError("Separate train and test paths required")
    if any(e.partition != "train" for e in train) or any(e.partition != "test" for e in test):
        raise ValueError("Episode partition labels required")
    if {e.path_id for e in train} & {e.path_id for e in test}:
        raise ValueError("Shared train/test outcome paths")

    def outcome_key(e):
        return fingerprint(
            [
                {
                    "deadline": o.deadline,
                    "official_outcomes": None
                    if o.official_outcomes is None
                    else {str(i): vars(row) for i, row in o.official_outcomes.items()},
                    "outcomes": {
                        str(i): [vars(row) for row in rows] for i, rows in o.outcomes.items()
                    },
                }
                for o in e.origins
            ]
        )

    if {outcome_key(e) for e in train} & {outcome_key(e) for e in test}:
        raise ValueError("Shared train/test outcomes under different path labels")
    modes = {o.evidence_mode for e in [*train, *test] for o in e.origins}
    if "prospective_strict" in modes:
        # Strict serving policy artifacts must already exist at an origin. A
        # new research fit cannot inherit keep_policy's historical provenance.
        raise ValueError(
            "New policy training uses reconstructed/synthetic research paths, not prior deployment claims"
        )
    if "historical_reconstructed" in modes:
        from fpl_app.evaluation.provenance import replay_time

        if max(replay_time(o.deadline) for e in train for o in e.origins) >= min(
            replay_time(o.deadline) for e in test for o in e.origins
        ):
            raise ValueError("Reconstructed development/test blocks must be chronological")
    for e in [*train, *test]:
        end = e.initial.next_event + len(e.origins) - 1
        if end < 38 and e.bootstrap_origin is None and e.origins[-1].forecasts.horizon_events < 2:
            raise ValueError("Training/evaluation cutoff requires bootstrap support")
    return modes


def train_challenger(
    train,
    test,
    settings: Settings,
    output: Path,
    *,
    seeds=(0, 1, 2, 3, 4),
    timesteps=512,
    k=32,
    progress=None,
):
    import torch
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.evaluation import evaluate_policy

    from fpl_app.strategy.environment import ENV_VERSION, OBSERVATION_VERSION, FPLEnv
    from fpl_app.strategy.policy import SharedCandidatePolicy

    if len(set(seeds)) < 5 or timesteps < 64:
        raise ValueError("At least five unique training seeds and 64 steps required")
    modes = _split_check(train, test)
    implementation_sha256 = implementation_digest()
    torch.set_num_threads(1)
    output.mkdir(parents=True, exist_ok=False)
    data_hash = fingerprint([_episode_payload(e) for e in [*train, *test]])
    fitted, n = fit_value(train, settings, k=k)
    fitted.save(output / "fitted_q.npz")
    loaded_q = FittedQ.load(output / "fitted_q.npz")
    evaluation = []
    seed_rows = []
    from fpl_app.evaluation.strategy import planner_policy, replay_policy

    numerical = {}
    for ep in test:
        started = perf_counter()
        numerical[ep.episode_id] = replay_policy(
            ep.initial, list(ep.origins), planner_policy, settings
        )
        numerical[ep.episode_id]["episode_seconds"] = perf_counter() - started
    for index, seed in enumerate(seeds):
        if progress:
            progress(index / len(seeds))
        env = FPLEnv(train, settings, k=k)
        model = MaskablePPO(
            SharedCandidatePolicy,
            env,
            seed=seed,
            n_steps=32,
            batch_size=32,
            n_epochs=2,
            gamma=1.0,
            device="cpu",
            verbose=0,
        )
        model.learn(total_timesteps=timesteps, use_masking=True)
        path = output / f"ppo-{seed}.zip"
        model.save(path)
        reloaded = MaskablePPO.load(path, device="cpu")
        per_seed = []
        for ep in test:
            test_env = FPLEnv([ep], settings, k=k)
            obs, _ = test_env.reset(seed=0)
            a, _ = model.predict(obs, deterministic=True, action_masks=test_env.action_masks())
            b, _ = reloaded.predict(obs, deterministic=True, action_masks=test_env.action_masks())
            if int(a) != int(b) or fitted.predict(obs, test_env.action_masks()) != loaded_q.predict(
                obs, test_env.action_masks()
            ):
                raise ValueError("Reload semantic action changed")
            # Official masked evaluator as well as detailed masked trajectories.
            official_mean, _ = evaluate_policy(
                reloaded,
                test_env,
                n_eval_episodes=1,
                deterministic=True,
                warn=False,
                use_masking=True,
            )
            ppo = evaluate(
                FPLEnv([ep], settings, k=k),
                lambda o, m, policy=reloaded: policy.predict(o, deterministic=True, action_masks=m)[
                    0
                ],
            )
            keep = evaluate(FPLEnv([ep], settings, k=k), lambda o, m: 0)
            greedy = evaluate(
                FPLEnv([ep], settings, k=k),
                lambda o, m: int(np.argmax(np.where(m, o["candidates"][:, 0], -np.inf))),
            )
            planner = evaluate(
                FPLEnv([ep], settings, k=k),
                lambda o, m: int(np.argmax(np.where(m, o["candidates"][:, 1], -np.inf))),
            )
            value = evaluate(FPLEnv([ep], settings, k=k), loaded_q.predict)
            if not np.isclose(official_mean, ppo["net_points"]):
                raise ValueError("Mask-aware evaluator mismatch")
            row = {
                "episode_id": ep.episode_id,
                "path_id": ep.path_id,
                "seed": seed,
                "ppo": ppo,
                "keep": keep,
                "greedy": greedy,
                "menu_planner": planner,
                "fitted_q": value,
                "numerical_planner": numerical[ep.episode_id],
                "paired_incremental_vs_numerical_planner": ppo["net_points"]
                - numerical[ep.episode_id]["realised_net_points"],
                "paired_incremental_vs_menu_planner": ppo["net_points"] - planner["net_points"],
            }
            evaluation.append(row)
            per_seed.append(row["paired_incremental_vs_numerical_planner"])
        seed_rows.append({"seed": seed, "mean_incremental": float(np.mean(per_seed))})
    path_means = [
        float(
            np.mean(
                [
                    r["paired_incremental_vs_numerical_planner"]
                    for r in evaluation
                    if r["path_id"] == path
                ]
            )
        )
        for path in sorted({e.path_id for e in test})
    ]
    actual_seasons = sorted(
        {
            e.initial.season
            for e in test
            if any(o.evidence_mode == "historical_reconstructed" for o in e.origins)
        }
    )
    interval = None
    if len(path_means) >= 2 and "historical_reconstructed" not in modes:
        from scipy.stats import t

        mean = float(np.mean(path_means))
        se = float(np.std(path_means, ddof=1) / np.sqrt(len(path_means)))
        span = float(t.ppf(0.975, len(path_means) - 1) * se)
        interval = [mean - span, mean + span]
    report = {
        "status": "evaluated_research",
        "seeds": seed_rows,
        "episodes": evaluation,
        "distinct_test_paths": len(path_means),
        "independent_actual_seasons": len(actual_seasons),
        "actual_seasons": actual_seasons,
        "seed_selection": "first seed preselected; all seeds reported; no test selection",
        "worst_paired_event_vs_numerical": min(
            p["net_points"] - n["realised_net_points"]
            for r in evaluation
            for p, n in zip(r["ppo"]["rows"], r["numerical_planner"]["rows"], strict=True)
        ),
        "paired_event_path_mean": float(np.mean(path_means)),
        "path_block_95_interval": interval,
        "invalid_accepted_actions": 0,
        "promotion": "retain_champion_insufficient_prospective_evidence",
        "limitations": [
            "Synthetic/reconstructed paths are research evidence, not live edge",
            "Candidate menu and frozen-price hold continuation are bounded",
            "Numerical planner may choose actions outside the bounded RL menu; same-menu comparator also reported",
            "No hyperparameter tuning or winning-seed selection on held-out paths",
            "Repeated starts and training seeds are not independent actual seasons; historical intervals unavailable",
        ],
    }
    (output / "evaluation.json").write_text(json.dumps(report, sort_keys=True, indent=2))
    hashes = {
        p.name: __import__("hashlib").sha256(p.read_bytes()).hexdigest()
        for p in output.iterdir()
        if p.is_file()
    }
    manifest = {
        "artifact_id": f"maskable_ppo/{uuid4().hex}",
        "policy_version": POLICY_VERSION,
        "model_family": "maskable_ppo",
        "mode": "shadow",
        "status": "trained_evaluated_research",
        "available_at": utcnow(),
        "data_sha256": data_hash,
        "evidence_modes": sorted(modes),
        "observation_version": OBSERVATION_VERSION,
        "environment_version": ENV_VERSION,
        "candidate_version": CANDIDATE_VERSION,
        "rules_version": RULES.version,
        "settings": settings.model_dump(),
        "candidate_count": k,
        "seeds": list(seeds),
        "timesteps_per_seed": timesteps,
        "preselected_serving_seed": seeds[0],
        "implementation_sha256": implementation_sha256,
        "fitted_value_transitions": n,
        "artifacts": hashes,
        "active": False,
        "promotion": report["promotion"],
    }
    if implementation_digest() != implementation_sha256:
        raise ValueError("Strategy implementation changed during training")
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2))
    if progress:
        progress(1.0)
    return manifest, report


def _episode_payload(e):
    return {
        "episode_id": e.episode_id,
        "path_id": e.path_id,
        "partition": e.partition,
        "initial": e.initial.model_dump(),
        "bootstrap_origin": None
        if e.bootstrap_origin is None
        else {
            "deadline": e.bootstrap_origin.deadline,
            "information_available_at": e.bootstrap_origin.information_available_at,
            "players": [p.model_dump() for p in e.bootstrap_origin.players],
            "forecasts": e.bootstrap_origin.forecasts.model_dump(),
            "evidence_mode": e.bootstrap_origin.evidence_mode,
            "fitting_labels_available_at": e.bootstrap_origin.fitting_labels_available_at,
            "financial_coverage": e.bootstrap_origin.financial_coverage,
            "outcomes": {},
            "official_outcomes": {},
        },
        "origins": [
            {
                "deadline": o.deadline,
                "information_available_at": o.information_available_at,
                "players": [p.model_dump() for p in o.players],
                "forecasts": o.forecasts.model_dump(),
                "outcomes": {str(i): [vars(s) for s in stats] for i, stats in o.outcomes.items()},
                "official_outcomes": None
                if o.official_outcomes is None
                else {str(i): vars(row) for i, row in o.official_outcomes.items()},
                "evidence_mode": o.evidence_mode,
                "financial_coverage": o.financial_coverage,
                "fitting_labels_available_at": o.fitting_labels_available_at,
            }
            for o in e.origins
        ],
    }
