"""Bind a feature panel to its audit before any trainer can use the rows."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fpl_app.features.pipeline import utc


def bind_panel_audit(frame: pd.DataFrame, audit: dict[str, Any], checksum: str) -> None:
    if audit.get("panel_sha256") != checksum:
        raise ValueError("Training unavailable: audit panel checksum is not bound to this parquet")
    if "rows" in audit and int(audit["rows"]) != len(frame):
        raise ValueError("Training unavailable: audit row count does not match the panel")
    for column in ("replay_timing", "timing_verified", "source_refs", "season"):
        if column not in frame.columns:
            raise ValueError(f"Training unavailable: {column} provenance column missing")
    timings = frame["replay_timing"]
    expected = {str(audit.get("replay_timing"))}
    if timings.isna().any() or set(timings.astype(str).unique()) != expected:
        raise ValueError("Training unavailable: row replay_timing does not match the audit")
    refs = frame["source_refs"]
    if refs.isna().any() or refs.astype(str).str.strip().eq("").any():
        raise ValueError("Training unavailable: row source provenance is missing")
    flags = frame["timing_verified"]
    if flags.isna().any():
        raise ValueError("Training unavailable: timing_verified is missing")
    timing = audit.get("replay_timing")
    if timing == "verified" and not bool(flags.eq(True).all()):
        raise ValueError("Training unavailable: strict audit contains unverified rows")
    if timing == "conservative_assumed" and not bool(flags.eq(False).all()):
        raise ValueError("Training unavailable: approximate audit contains verified or mixed rows")
    for value in frame["decision_cutoff"]:
        utc(value)
    observed = pd.to_numeric(frame["target_points"], errors="coerce").notna()
    published = frame.loc[observed, "target_available_at"]
    if bool(observed.any()) and published.isna().any():
        raise ValueError(
            "Training unavailable: observed targets are missing publication timestamps"
        )
    for value in published:
        utc(value)


def filter_targets(frame: pd.DataFrame, drop_missing_targets: bool) -> pd.DataFrame:
    points = pd.to_numeric(frame["target_points"], errors="coerce")
    present = points.notna()
    if bool(present.any()) and not np.isfinite(points.loc[present].to_numpy(dtype=float)).all():
        raise ValueError("nonfinite targets")
    if not drop_missing_targets:
        return frame
    kept = frame.loc[present].reset_index(drop=True)
    if kept.empty:
        raise ValueError("Training unavailable: no observed targets")
    return kept
