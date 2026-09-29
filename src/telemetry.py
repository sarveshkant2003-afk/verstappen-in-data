"""Per-lap telemetry for C05 (track maps) and C06 (qualifying duel).

Telemetry is heavy, so it is extracted for single chosen laps only, aligned by
distance, downsampled (≤ MAX_POINTS per trace) and saved to
data/processed/telemetry/ so charts never touch the network.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src import config, stats
from src.laps import load_session

TEL_DIR = config.PROCESSED / "telemetry"
MAX_POINTS = 1000

# C06: picked from data-derived candidates (closest poles against a title rival).
DUEL = {"season": 2025, "round": 3, "session": "Q", "rival": "NOR"}


def _fastest(session, driver: str):
    return session.laps.pick_drivers(driver).pick_fastest()


def lap_trace(lap, length_m: float | None = None) -> pd.DataFrame:
    """Speed, throttle, brake, gear, X/Y and elapsed time on a common distance grid."""
    tel = lap.get_telemetry().dropna(subset=["Distance"])  # get_telemetry() already adds Distance
    length = length_m or float(tel["Distance"].max())
    grid = np.linspace(0, length, MAX_POINTS)
    t = tel["Time"].dt.total_seconds().to_numpy()
    out = {"distance": grid, "time": stats.interpolate_to_distance(tel["Distance"], t, grid)}
    for col in ("Speed", "Throttle", "nGear", "X", "Y"):
        out[col.lower()] = stats.interpolate_to_distance(tel["Distance"], tel[col].astype(float), grid)
    out["brake"] = stats.interpolate_to_distance(tel["Distance"], tel["Brake"].astype(float), grid)
    return pd.DataFrame(out)


def extract_duel() -> None:
    s = load_session(DUEL["season"], DUEL["round"], DUEL["session"], telemetry=True)
    me, rival = _fastest(s, config.DRIVER_CODE), _fastest(s, DUEL["rival"])
    a, b = me.get_telemetry(), rival.get_telemetry()
    length = float(min(a["Distance"].max(), b["Distance"].max()))  # common grid within both laps
    TEL_DIR.mkdir(parents=True, exist_ok=True)
    lap_trace(me, length).to_parquet(TEL_DIR / "duel_max.parquet", index=False)
    lap_trace(rival, length).to_parquet(TEL_DIR / "duel_rival.parquet", index=False)
    ci = s.get_circuit_info()
    ci.corners[["Number", "Letter", "Distance"]].to_parquet(TEL_DIR / "duel_corners.parquet", index=False)
    meta = {**DUEL, "event": s.event["EventName"], "max_lap_s": me["LapTime"].total_seconds(),
            "rival_lap_s": rival["LapTime"].total_seconds(), "rival_name": s.get_driver(DUEL["rival"])["LastName"]}
    (TEL_DIR / "duel_meta.json").write_text(json.dumps(meta, indent=2))


def map_candidates(tables: dict, n: int = 6) -> list[dict]:
    """His n most-won circuits since 2018; for each, the latest qualifying he topped there."""
    r, fq = tables["results"], tables["field_qualifying"]
    gp = r[(r.session == "gp") & (r.season >= 2018)]
    wins = gp[gp.position_text == "1"].groupby("circuit_id").size().sort_values(ascending=False)
    top_q = fq[(fq.driver_id == config.DRIVER_ID) & (fq.quali_pos == 1) & (fq.season >= 2018)]
    out = []
    for cid, w in wins.items():
        q = top_q[top_q.circuit_id == cid].sort_values("season")
        if q.empty:
            continue
        last = q.iloc[-1]
        out.append({"circuit_id": cid, "wins": int(w), "season": int(last.season), "round": int(last["round"]),
                    "locality": last.locality})
        if len(out) == n:
            break
    return out


def extract_maps(tables: dict) -> None:
    TEL_DIR.mkdir(parents=True, exist_ok=True)
    meta = []
    for c in map_candidates(tables):
        s = load_session(c["season"], c["round"], "Q", telemetry=True)
        tr = lap_trace(_fastest(s, config.DRIVER_CODE))
        rot = float(s.get_circuit_info().rotation)
        tr.to_parquet(TEL_DIR / f"map_{c['circuit_id']}.parquet", index=False)
        meta.append({**c, "rotation": rot, "event": s.event["EventName"]})
        print(f"map: {c['locality']} {c['season']}")
    (TEL_DIR / "maps_meta.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    from src import features
    extract_duel()
    extract_maps(features.load_tables())
