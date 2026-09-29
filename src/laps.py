"""FastF1 access for the few sessions the story needs (2018+ only).

Light-scope decision (CLAUDE.md §0.1): no bulk download. Charts ask for one
session at a time; FastF1's own cache (data/cache/fastf1/) makes repeats free.
"""
from __future__ import annotations

import logging

import fastf1
import pandas as pd

from src import config, stats

_enabled = False


def _enable_cache() -> None:
    global _enabled
    if not _enabled:
        config.FASTF1_CACHE.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(config.FASTF1_CACHE))
        fastf1.set_log_level(logging.WARNING)
        _enabled = True


def load_session(year: int, round_: int, kind: str = "R", *, laps: bool = True,
                 telemetry: bool = False, messages: bool = False) -> fastf1.core.Session:
    """Load one session with only the parts a chart needs. kind: 'R', 'Q', 'S', 'SQ'."""
    if year < 2018:
        raise ValueError("FastF1 live-timing data starts in 2018; use Jolpica for earlier races.")
    _enable_cache()
    s = fastf1.get_session(year, round_, kind)
    s.load(laps=laps, telemetry=telemetry, weather=False, messages=messages)
    return s


def availability(year: int, round_: int, kind: str = "R") -> dict:
    """Probe a session: does it have laps for Max, stints, and track-status data?"""
    try:
        s = load_session(year, round_, kind)
        me = s.laps.pick_drivers(config.DRIVER_CODE)
        return {
            "year": year, "round": round_, "session": kind, "event": s.event["EventName"],
            "laps_total": len(s.laps), "laps_max": len(me),
            "clean_laps_max": len(stats.clean_laps(me)),
            "stints_max": int(me["Stint"].nunique()),
            "compounds_max": sorted(me["Compound"].dropna().unique().tolist()),
            "ok": len(me) > 0,
        }
    except Exception as e:  # report, don't crash the audit
        return {"year": year, "round": round_, "session": kind, "ok": False, "error": repr(e)}


def race_laps(session: fastf1.core.Session) -> pd.DataFrame:
    """Tidy per-lap table for every driver: position, compound, stint, pit flags, track status."""
    cols = ["Driver", "LapNumber", "Position", "LapTime", "Compound", "Stint", "TyreLife",
            "PitInTime", "PitOutTime", "TrackStatus"]
    df = session.laps[cols].copy()
    df["LapTime_s"] = df["LapTime"].dt.total_seconds()
    df["pit_in"] = df["PitInTime"].notna()
    return df.drop(columns=["LapTime", "PitInTime", "PitOutTime"])
