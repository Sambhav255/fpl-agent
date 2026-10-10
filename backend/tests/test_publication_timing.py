import pandas as pd
import pytest

from fpl_app.models.publication import publication_timing


def test_information_cutoff_includes_validation_outcomes_not_just_feature_deadline():
    train = pd.DataFrame(
        {
            "decision_cutoff": ["2024-01-01T00:00:00Z"],
            "target_available_at": ["2024-01-02T00:00:00Z"],
        }
    )
    validation = pd.DataFrame(
        {
            "decision_cutoff": ["2024-02-01T00:00:00Z"],
            "target_available_at": ["2024-02-04T00:00:00Z"],
        }
    )
    timing = publication_timing(train, validation)
    assert pd.Timestamp(timing["training_cutoff"]) == pd.Timestamp("2024-02-04T00:00:00Z")
    assert pd.Timestamp(timing["available_at"]) >= pd.Timestamp(timing["training_cutoff"])


def test_missing_or_future_information_cannot_be_published():
    with pytest.raises(ValueError):
        publication_timing(pd.DataFrame({"decision_cutoff": ["2024-01-01"]}))
    with pytest.raises(ValueError):
        publication_timing(
            pd.DataFrame(
                {
                    "decision_cutoff": ["2099-01-01T00:00:00Z"],
                    "target_available_at": ["2099-01-02T00:00:00Z"],
                }
            )
        )
