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
    """Tidy per-lap table for every driver: position, compound, stint, pit flags, track status, clean flag."""
    laps = session.laps
    clean_idx = stats.clean_laps(laps).index
    cols = ["Driver", "LapNumber", "Position", "Compound", "Stint", "TyreLife", "TrackStatus"]
    df = laps[cols].copy()
    df["LapTime_s"] = laps["LapTime"].dt.total_seconds()
    df["pit_in"] = laps["PitInTime"].notna()
    df["pit_out"] = laps["PitOutTime"].notna()
    df["clean"] = df.index.isin(clean_idx)
    return df.reset_index(drop=True)


LAPS_DIR = config.CACHE / "laps"


def build_laps_table(rounds: list[tuple[int, int]]) -> pd.DataFrame:
    """Download (resumably) every race's laps and combine into laps_2018plus.parquet.

    Each race is saved to data/cache/laps/<season>_<round>.parquet as soon as it
    loads, so an interrupted run (e.g. an API rate limit) resumes where it stopped.
    Failures are listed in data/cache/laps/failures.csv for the audit.
    """
    LAPS_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for i, (season, rnd) in enumerate(rounds, 1):
        out = LAPS_DIR / f"{season}_{rnd:02d}.parquet"
        if out.exists():
            continue
        try:
            df = race_laps(load_session(season, rnd, "R"))
            df.insert(0, "season", season)
            df.insert(1, "round", rnd)
            df.to_parquet(out, index=False)
            print(f"[{i}/{len(rounds)}] {season} R{rnd}: {len(df)} laps", flush=True)
        except Exception as e:
            failures.append({"season": season, "round": rnd, "error": repr(e)[:300]})
            print(f"[{i}/{len(rounds)}] {season} R{rnd}: FAILED {e!r}", flush=True)
    pd.DataFrame(failures, columns=["season", "round", "error"]).to_csv(LAPS_DIR / "failures.csv", index=False)
    parts = [pd.read_parquet(p) for p in sorted(LAPS_DIR.glob("*.parquet"))]
    table = pd.concat(parts, ignore_index=True)
    wet = table.groupby(["season", "round"])["Compound"].agg(
        lambda c: c.isin(["INTERMEDIATE", "WET"]).mean() > 0.1).rename("wet_race")
    table = table.join(wet, on=["season", "round"])
    table.to_parquet(config.PROCESSED / "laps_2018plus.parquet", index=False)
    return table


if __name__ == "__main__":
    res = pd.read_parquet(config.PROCESSED / "results.parquet")
    gp = res[(res["session"] == "gp") & (res["season"] >= 2018)]
    rounds = list(gp[["season", "round"]].drop_duplicates().itertuples(index=False, name=None))
    t = build_laps_table(rounds)
    print(t.shape, "races:", t.groupby(["season", "round"]).ngroups)
