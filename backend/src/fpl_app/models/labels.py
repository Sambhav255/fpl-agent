"""Availability labels. Unknown minutes are excluded; a real zero stays a non-appearance."""

from __future__ import annotations

import numpy as np
import pandas as pd


def minute_appearance_labels(
    minutes: pd.Series, threshold: float = 0, *, at_least: bool = False
) -> pd.Series:
    parsed = pd.to_numeric(minutes, errors="coerce")
    known = pd.Series(np.isfinite(parsed.to_numpy(dtype="float64")), index=parsed.index)
    labels = pd.Series(np.nan, index=parsed.index, dtype="float64")
    chosen = parsed.loc[known]
    labels.loc[known] = (chosen >= threshold if at_least else chosen > threshold).astype(float)
    return labels
