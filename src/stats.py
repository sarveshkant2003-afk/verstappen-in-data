"""F1 stat rules (CLAUDE.md §4.4) as small, pure, tested functions.

Nothing in here touches the network or the disk; tests/test_stats.py covers
every rule with tiny hand-made inputs.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.config import RESCORE_POINTS

STATUS_CATEGORIES = [
    "Finished", "Lapped", "DNF-mechanical", "DNF-incident", "DNF-other", "DNF-unknown", "DSQ", "DNS",
]


# --- Results -----------------------------------------------------------------
def is_classified(position_text: str) -> bool:
    """Jolpica positionText is numeric for classified drivers; R/D/E/W/F/N otherwise."""
    return str(position_text).isdigit()


def map_status(status: pd.Series, status_map: pd.DataFrame) -> pd.Series:
    """Map raw Jolpica status strings to categories; unknown strings raise."""
    lookup = dict(zip(status_map["status"], status_map["category"]))
    unknown = sorted(set(status) - set(lookup))
    if unknown:
        raise ValueError(f"Unmapped status strings — add them to status_map.csv: {unknown}")
    return status.map(lookup)


def gp_counts(results: pd.DataFrame) -> dict[str, int]:
    """Starts, wins and podiums, counting Grands Prix only (sprints excluded).

    A 'start' is any GP entry except DNS.
    """
    gp = results[results["session"] == "gp"]
    started = gp[gp["status_cat"] != "DNS"]
    pos = started["position_text"]
    return {
        "starts": len(started),
        "wins": int((pos == "1").sum()),
        "podiums": int(pos.isin(["1", "2", "3"]).sum()),
    }


def rescore(position: int, classified: bool) -> int:
    """Points under one fixed system (25-18-15-…-1, no bonuses) for cross-season charts."""
    return RESCORE_POINTS.get(int(position), 0) if classified else 0


def effective_grid(grid: int, field_size: int) -> int:
    """Grid slot with pit-lane starts (grid 0) moved to the back of the field."""
    return field_size if grid == 0 else grid


def positions_gained(grid: int, finish: int, classified: bool, field_size: int) -> float:
    """grid − finish for classified finishes; NaN otherwise. Pit-lane start = back of grid."""
    if not classified:
        return math.nan
    return effective_grid(grid, field_size) - finish


def gap_seconds(winner_ms: float, other_ms: float, winner_laps: int, other_laps: int) -> float:
    """Race gap in seconds between two finishers on the same lap; NaN if lapped or no time."""
    if winner_laps != other_laps or pd.isna(winner_ms) or pd.isna(other_ms):
        return math.nan
    return (other_ms - winner_ms) / 1000


# --- Qualifying --------------------------------------------------------------
def laptime_to_seconds(text: str | None) -> float:
    """'1:23.456' → 83.456; empty/None/'' → NaN."""
    if not text:
        return math.nan
    parts = str(text).split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError:
        return math.nan


def last_common_session(mine: dict[str, float], theirs: dict[str, float]) -> tuple[str | None, float, float]:
    """Latest session (q3 → q2 → q1) in which *both* drivers set a time.

    Returns (session, my_time, their_time), or (None, nan, nan) if none.
    """
    for q in ("q3", "q2", "q1"):
        a, b = mine.get(q, math.nan), theirs.get(q, math.nan)
        if pd.notna(a) and pd.notna(b):
            return q, float(a), float(b)
    return None, math.nan, math.nan


def quali_gap_pct(mine: float, other: float) -> float:
    """Signed gap as % of the faster of the two times. Positive = I was slower."""
    if pd.isna(mine) or pd.isna(other):
        return math.nan
    return 100 * (mine - other) / min(mine, other)


# --- Laps & telemetry (FastF1) ----------------------------------------------
def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Keep only representative green-flag laps from a FastF1 Laps frame.

    Drops: lap 1, in-laps and out-laps, any lap whose TrackStatus contains a
    non-green code (SC '4', red '5', VSC '6'/'7'; yellow '2' kept), laps FastF1
    marks inaccurate, and deleted laps.
    """
    ok = laps["LapNumber"] > 1
    ok &= laps["PitInTime"].isna() & laps["PitOutTime"].isna()
    status = laps["TrackStatus"].fillna("").astype(str)
    ok &= ~status.str.contains("[4567]", regex=True)
    if "IsAccurate" in laps:
        ok &= laps["IsAccurate"].astype("boolean").fillna(False).astype(bool)
    if "Deleted" in laps:
        ok &= ~laps["Deleted"].astype("boolean").fillna(False).astype(bool)
    ok &= laps["LapTime"].notna()
    return laps[ok]


def interpolate_to_distance(distance: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Resample a telemetry channel onto a common distance grid (metres).

    `distance` must be increasing; duplicates are dropped before interpolating.
    """
    d = np.asarray(distance, dtype=float)
    v = np.asarray(values, dtype=float)
    d, idx = np.unique(d, return_index=True)
    return np.interp(grid, d, v[idx])


def distance_grid(length_m: float, step_m: float = 5.0) -> np.ndarray:
    return np.arange(0.0, length_m, step_m)


# --- Uncertainty -------------------------------------------------------------
def bootstrap_median_ci(values: np.ndarray, n_boot: int = 2000, ci: float = 0.95,
                        seed: int = 0) -> tuple[float, float, float]:
    """Median with a percentile bootstrap CI. Returns (median, low, high)."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(v, size=(n_boot, len(v)), replace=True), axis=1)
    a = (1 - ci) / 2
    return float(np.median(v)), float(np.quantile(meds, a)), float(np.quantile(meds, 1 - a))


def format_laptime(seconds: float) -> str:
    """83.456 → '1:23.456'."""
    if pd.isna(seconds):
        return "—"
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:06.3f}"
