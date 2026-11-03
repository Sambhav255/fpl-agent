from dataclasses import asdict

import pandas as pd
import pytest
from test_upgrade_optimisation import funding_fixture

from fpl_app.domain.rules import MatchStats
from fpl_app.models.bayesian_scoring import fit_scoring_profiles
from fpl_app.models.ensemble import blend_runs


def test_scoring_profiles_are_fitted_asof_and_missing_components_reject():
    rows = []
    for player, pos in enumerate([1, 2, 3, 4], 1):
        for event in range(6):
            rows.append(
                {
                    "player_id": player,
                    "position": pos,
                    "started": event % 2 == 0,
                    "bps": 20,
                    "available_at": f"2026-10-{event + 1:02d}T00:00:00Z",
                    **asdict(
                        MatchStats(
                            minutes=90 if event % 2 == 0 else 20,
                            goals=int(pos == 3),
                            saves=int(pos == 1) * 3,
                        )
                    ),
                }
            )
    frame = pd.DataFrame(rows)
    first = fit_scoring_profiles(frame, "2026-10-04T00:00:00Z")
    altered = frame.copy()
    altered.loc[altered.available_at > "2026-10-04T00:00:00Z", "goals"] = 999
    assert fit_scoring_profiles(altered, "2026-10-04T00:00:00Z") == first
    assert first["status"] == "fitted_research" and not first["calibrated"]
    assert len(first["profiles"]) == 4
    with pytest.raises(ValueError, match="Complete explicit"):
        fit_scoring_profiles(frame.drop(columns="saves"), "2026-10-04T00:00:00Z")


def test_eligible_mean_blend_omits_unvalidated_marginals_and_rejects_coverage_changes():
    _, _, first = funding_fixture()
    second = first.model_copy(deep=True)
    for p in second.projections:
        p.expected_points += 2
    blended = blend_runs(
        {"a": first, "b": second},
        {"a": 0.75, "b": 0.25},
        validated_artifact_id="registered",
        evaluation_reference="heldout-report",
    )
    by_key = {(p.player_id, p.fixture_id): p for p in first.projections}
    assert all(
        p.expected_points == by_key[(p.player_id, p.fixture_id)].expected_points + 0.5
        for p in blended.projections
    )
    assert all(
        p.point_quantiles is None and p.appearance_probability is None for p in blended.projections
    )
    second.projections.pop()
    with pytest.raises(ValueError, match="coverage"):
        blend_runs(
            {"a": first, "b": second},
            {"a": 0.5, "b": 0.5},
            validated_artifact_id="registered",
            evaluation_reference="report",
        )


def test_complete_scenarios_score_every_sample_with_domain_components():
    from types import SimpleNamespace

    import numpy as np

    xr = pytest.importorskip("xarray")
    from fpl_app.domain.rules import score_match
    from fpl_app.models.bayesian_scoring import complete_scenarios

    rows = [
        {
            "player_id": i,
            "position": pos,
            "started": True,
            "bps": -2 * i,
            "available_at": "2026-10-01T00:00:00Z",
            **asdict(
                MatchStats(
                    minutes=90, saves=4 if pos == 1 else 0, yellow_cards=1, tackles=12, own_goals=1
                )
            ),
        }
        for i, pos in enumerate([1, 2, 3, 4], 1)
    ]
    artifact = fit_scoring_profiles(pd.DataFrame(rows), "2026-10-02T00:00:00Z")
    posterior = xr.Dataset(
        {
            **{name: (("chain", "draw"), np.zeros((2, 8))) for name in ["base", "venue", "trend"]},
            "dispersion": (("chain", "draw"), np.ones((2, 8))),
            "attack": (("chain", "draw", "club"), np.zeros((2, 8, 2))),
            "defence": (("chain", "draw", "club"), np.zeros((2, 8, 2))),
        }
    )
    players = pd.DataFrame(
        [
            {
                "player_id": i,
                "position": pos,
                "club": 1 if i <= 2 else 2,
                "appearances": 6,
                "total_matches": 8,
                "minutes_per_appearance": 90,
                "goals": 2,
                "assists": 1,
                "total_minutes": 540,
            }
            for i, pos in enumerate([1, 2, 3, 4], 1)
        ]
    )
    result = complete_scenarios(
        SimpleNamespace(posterior=posterior),
        {
            "clubs": [1, 2],
            "limitations": ["Authored posterior contract fixture, never fitted team accuracy"],
        },
        1,
        2,
        players,
        artifact,
        samples=100,
    )
    again = complete_scenarios(
        SimpleNamespace(posterior=posterior),
        {
            "clubs": [1, 2],
            "limitations": ["Authored posterior contract fixture, never fitted team accuracy"],
        },
        1,
        2,
        players,
        artifact,
        samples=100,
    )
    np.testing.assert_array_equal(result["points"], again["points"])
    np.testing.assert_array_equal(result["bps"], again["bps"])
    assert np.any(result["bps"] < 0)
    for sample in range(100):
        for j, pos in enumerate([1, 2, 3, 4]):
            stats = MatchStats(
                **{k: int(v[sample, j]) for k, v in result["scored_components"].items()}
            )
            assert result["points"][sample, j] == score_match(pos, stats)
    np.testing.assert_allclose(result["expected_points"], result["points"].mean(axis=0))
    assert np.all(result["start_probability"] <= result["appearance_probability"])
    assert np.all(np.diff(result["point_quantiles"], axis=0) >= 0)


def test_fitted_ensemble_keeps_test_outcomes_out_of_weights_and_verifies_payloads(tmp_path):
    from fpl_app.models.ensemble import ensemble_run, fit_mean_ensemble
    from fpl_app.storage import utcnow

    def data(partition, start):
        return pd.DataFrame(
            [
                {
                    "partition": partition,
                    "event": day,
                    "decision_cutoff": f"2026-10-{day:02d}T00:00:00Z",
                    "target_available_at": f"2026-10-{day + 1:02d}T00:00:00Z",
                    "train_target_end": "2026-09-30T00:00:00Z",
                    "target_points": float(i + 1),
                    "good": float(i + 1),
                    "weak": 10.0,
                }
                for i, day in enumerate(range(start, start + 3))
            ]
        )

    validation, heldout = data("validation", 1), data("test", 6)
    meta, report = fit_mean_ensemble(validation, heldout, ["good", "weak"], tmp_path / "first")
    changed = heldout.copy()
    changed["target_points"] = 100.0
    _, other = fit_mean_ensemble(validation, changed, ["good", "weak"], tmp_path / "second")
    assert report["validation"]["weights"] == other["validation"]["weights"]
    assert report["blend"]["rmse"] < other["blend"]["rmse"]
    assert not meta["active"] and report["promotion"].startswith("retain_champion")
    with pytest.raises(ValueError, match="overlap"):
        fit_mean_ensemble(validation, data("test", 3), ["good", "weak"], tmp_path / "leak")
    _, _, first = funding_fixture()
    origin = utcnow()
    first = first.model_copy(update={"prediction_origin": origin, "source_cutoff": origin})
    blended = ensemble_run(tmp_path / "first", {"good": first, "weak": first})
    assert blended.artifact_id == meta["artifact_id"] and blended.artifact_manifest_sha256
    assert blended.lifecycle_state == "experimental"
    with pytest.raises(ValueError, match="unavailable"):
        ensemble_run(
            tmp_path / "first",
            {
                "good": first.model_copy(update={"prediction_origin": "2026-09-01T00:00:00Z"}),
                "weak": first.model_copy(update={"prediction_origin": "2026-09-01T00:00:00Z"}),
            },
        )
    (tmp_path / "first" / "weights.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        ensemble_run(tmp_path / "first", {"good": first, "weak": first})
    omitted = blend_runs(
        {"good": first},
        {"good": 1.0, "absent": 0.0},
        validated_artifact_id="authored",
        evaluation_reference="unverified",
    )
    assert len(omitted.projections) == len(first.projections)


def signed_profile_frame():
    return pd.DataFrame(
        [
            {
                "player_id": player,
                "position": position,
                "started": True,
                "bps": -2 * player,
                "available_at": "2026-10-01T00:00:00Z",
                **asdict(MatchStats(minutes=90, yellow_cards=1)),
            }
            for player, position in enumerate([1, 2, 3, 4], 1)
        ]
    )


def test_signed_bps_is_separate_from_nonnegative_component_counts_and_future_rows():
    frame = signed_profile_frame()
    fitted = fit_scoring_profiles(frame, "2026-10-02T00:00:00Z")
    assert fitted["version"] == "complete-bayesian-player-scoring-v2"
    assert not fitted["calibrated"]
    for profile in fitted["profiles"].values():
        assert "bps" not in profile["components"]
        assert profile["bps"]["values_by_category"]["3"][0] < 0
        assert profile["bps"]["source_by_category"]["3"] == "player_category"
    changed = frame.copy()
    changed["available_at"] = "2026-10-03T00:00:00Z"
    changed["bps"] = -999
    later = pd.concat([frame, changed], ignore_index=True)
    assert fit_scoring_profiles(later, "2026-10-02T00:00:00Z") == fitted
    frame.loc[0, "yellow_cards"] = -1
    with pytest.raises(ValueError, match="scoring counts"):
        fit_scoring_profiles(frame, "2026-10-02T00:00:00Z")


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -2.5])
def test_signed_bps_rejects_missing_nonfinite_and_fractional_scores(invalid):
    frame = signed_profile_frame()
    frame["bps"] = frame.bps.astype(float)
    frame.loc[0, "bps"] = invalid
    with pytest.raises(ValueError, match="signed integer BPS"):
        fit_scoring_profiles(frame, "2026-10-02T00:00:00Z")


def test_empirical_bps_sampling_preserves_sign_and_whole_fixture_semantics():
    import numpy as np

    from fpl_app.models.bayesian_scoring import BPS_MODEL_KIND, sample_signed_bps

    profile = {
        "kind": BPS_MODEL_KIND,
        "values_by_category": {"0": [-1], "1": [-9], "2": [3], "3": [-25, 15]},
    }
    minutes = np.array([0, 20, 45, 90, 90])
    starts = np.array([False, False, True, True, True])
    first = sample_signed_bps(profile, minutes, starts, np.random.default_rng(42))
    again = sample_signed_bps(profile, minutes, starts, np.random.default_rng(42))
    np.testing.assert_array_equal(first, again)
    np.testing.assert_array_equal(first[:3], [-1, -9, 3])
    assert set(first[3:]) <= {-25, 15}
    with pytest.raises(ValueError, match="refit legacy"):
        sample_signed_bps({"kind": "gamma-poisson"}, minutes, starts, np.random.default_rng(42))
    profile["values_by_category"]["1"] = []
    with pytest.raises(ValueError, match="Missing active"):
        sample_signed_bps(profile, minutes, starts, np.random.default_rng(42))


def test_legacy_bps_count_profiles_fail_explicitly_without_rewriting():
    from copy import deepcopy

    from fpl_app.models.bayesian_scoring import complete_scenarios

    legacy = {"version": "complete-bayesian-player-scoring-v1", "profiles": {}}
    before = deepcopy(legacy)
    with pytest.raises(ValueError, match="refit signed BPS profiles as v2"):
        complete_scenarios(None, None, 1, 2, pd.DataFrame(), legacy)
    assert legacy == before
