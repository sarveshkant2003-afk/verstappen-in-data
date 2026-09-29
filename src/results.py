"""Jolpica JSON (from the cache) → tidy pandas tables.

Builds the full-field tables first (every driver, every GP/sprint/qualifying
session), then derives Max-centric tables from them. Run as a script to write
data/processed/*.parquet.
"""
from __future__ import annotations

import pandas as pd

from src import config, stats
from src.download import fetch, seasons


# --- Parsing helpers ---------------------------------------------------------
def _races(path: str) -> list[dict]:
    """All races for an endpoint, merging races that were split across pages."""
    merged: dict[tuple[str, str], dict] = {}
    list_key = None
    for page in fetch(path):
        for race in page["RaceTable"]["Races"]:
            key = (race["season"], race["round"])
            if key not in merged:
                merged[key] = {k: v for k, v in race.items()}
                list_key = next((k for k in ("Results", "SprintResults", "QualifyingResults") if k in race), list_key)
                if list_key:
                    merged[key][list_key] = list(race.get(list_key, []))
            else:
                merged[key][list_key].extend(race.get(list_key, []))
    return list(merged.values())


def _race_meta(race: dict) -> dict:
    c = race["Circuit"]
    return {
        "season": int(race["season"]),
        "round": int(race["round"]),
        "race_name": race["raceName"],
        "date": pd.Timestamp(race["date"]),
        "circuit_id": c["circuitId"],
        "circuit_name": c["circuitName"],
        "locality": c["Location"]["locality"],
        "country": c["Location"]["country"],
        "lat": float(c["Location"]["lat"]),
        "lon": float(c["Location"]["long"]),
    }


def _result_rows(races: list[dict], list_key: str, session: str) -> list[dict]:
    rows = []
    for race in races:
        meta = _race_meta(race)
        for r in race.get(list_key, []):
            rows.append({
                **meta,
                "session": session,
                "driver_id": r["Driver"]["driverId"],
                "driver_code": r["Driver"].get("code"),
                "driver_name": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
                "number": int(r["number"]),
                "constructor_id": r["Constructor"]["constructorId"],
                "constructor": r["Constructor"]["name"],
                "grid": int(r["grid"]),
                "position": int(r["position"]),
                "position_text": r["positionText"],
                "points": float(r["points"]),
                "laps": int(r["laps"]),
                "status": r["status"],
                "time_ms": float(r["Time"]["millis"]) if "Time" in r else None,
            })
    return rows


# --- Full-field tables -------------------------------------------------------
def field_results() -> pd.DataFrame:
    """Every driver's GP and sprint results for every season Max raced."""
    rows: list[dict] = []
    for s in seasons():
        rows += _result_rows(_races(f"{s}/results"), "Results", "gp")
        if s >= 2021:
            rows += _result_rows(_races(f"{s}/sprint"), "SprintResults", "sprint")
    df = pd.DataFrame(rows)
    status_map = pd.read_csv(config.REFERENCE / "status_map.csv", comment="#")
    df["classified"] = df["position_text"].map(stats.is_classified)
    df["status_cat"] = stats.map_status(df["status"], status_map)
    return df.sort_values(["season", "round", "session", "position"]).reset_index(drop=True)


def field_qualifying() -> pd.DataFrame:
    """Every driver's Q1/Q2/Q3 times (seconds; NaN where no time was set)."""
    rows = []
    for s in seasons():
        for race in _races(f"{s}/qualifying"):
            meta = _race_meta(race)
            for q in race.get("QualifyingResults", []):
                rows.append({
                    **meta,
                    "driver_id": q["Driver"]["driverId"],
                    "constructor_id": q["Constructor"]["constructorId"],
                    "quali_pos": int(q["position"]),
                    **{k.lower(): stats.laptime_to_seconds(q.get(k)) for k in ("Q1", "Q2", "Q3")},
                })
    return pd.DataFrame(rows).sort_values(["season", "round", "quali_pos"]).reset_index(drop=True)


def official_final_standings() -> pd.DataFrame:
    """Official driver standings at the end of each season (latest round for the live one)."""
    rows = []
    for s in seasons():
        lists = fetch(f"{s}/driverStandings")[0]["StandingsTable"]["StandingsLists"]
        for sl in lists:
            for d in sl["DriverStandings"]:
                rows.append({
                    "season": int(sl["season"]),
                    "after_round": int(sl["round"]),
                    "driver_id": d["Driver"]["driverId"],
                    "position": int(d.get("position", 0) or 0),
                    "points": float(d["points"]),
                    "wins": int(d["wins"]),
                })
    return pd.DataFrame(rows)


def greats_results() -> pd.DataFrame:
    """Race-by-race GP results for the all-time greats (C10)."""
    rows = []
    for d in config.GREATS:
        for race in _races(f"drivers/{d}/results"):
            r = race["Results"][0]
            rows.append({
                "driver_id": d,
                "driver_name": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
                "season": int(race["season"]),
                "round": int(race["round"]),
                "date": pd.Timestamp(race["date"]),
                "position_text": r["positionText"],
                "position": int(r["position"]),
                "status": r["status"],
            })
    df = pd.DataFrame(rows).sort_values(["driver_id", "date"]).reset_index(drop=True)
    # A start excludes did-not-start entries and (pre-2000s) failures to qualify/pre-qualify.
    status_map = pd.read_csv(config.REFERENCE / "status_map.csv", comment="#")
    lookup = dict(zip(status_map["status"], status_map["category"]))
    dns = df["status"].map(lookup).eq("DNS") | df["position_text"].isin(["F", "W"]) \
        | df["status"].str.contains("qualify", case=False)
    df = df[~dns].reset_index(drop=True)
    df["start_n"] = df.groupby("driver_id").cumcount() + 1
    df["is_win"] = df["position_text"] == "1"
    df["wins_cum"] = df.groupby("driver_id")["is_win"].cumsum()
    return df


# --- Derived tables ----------------------------------------------------------
def standings_by_round(field: pd.DataFrame) -> pd.DataFrame:
    """Cumulative official points after every GP round, all drivers.

    Sprint points count toward the round they belong to. Positions tie-break on
    points only (a simplification; official count-back is not reproduced).
    """
    pts = field.groupby(["season", "round", "driver_id"], as_index=False)["points"].sum()
    grid = (pts.pivot_table(index=["season", "round"], columns="driver_id", values="points", fill_value=0)
               .groupby(level="season").cumsum())
    long = grid.stack().rename("points_cum").reset_index()
    # Drop drivers before their first appearance in a season (all-zero prefix is fine
    # but drivers who never raced that season must not appear).
    raced = pts[["season", "driver_id"]].drop_duplicates()
    long = long.merge(raced, on=["season", "driver_id"])
    long["rank"] = long.groupby(["season", "round"])["points_cum"].rank(method="min", ascending=False).astype(int)
    return long.sort_values(["season", "round", "rank"]).reset_index(drop=True)


def max_results(field: pd.DataFrame) -> pd.DataFrame:
    """Max's GP + sprint results with teammate, rescored points and gains."""
    me = field[field["driver_id"] == config.DRIVER_ID].copy()
    others = field[field["driver_id"] != config.DRIVER_ID]
    tm = (others.merge(me[["season", "round", "session", "constructor_id"]],
                       on=["season", "round", "session", "constructor_id"])
                [["season", "round", "session", "driver_id", "driver_name", "position", "position_text", "classified"]]
                .rename(columns={"driver_id": "teammate_id", "driver_name": "teammate_name",
                                 "position": "teammate_position", "position_text": "teammate_position_text",
                                 "classified": "teammate_classified"}))
    me = me.merge(tm, on=["season", "round", "session"], how="left")
    field_size = field.groupby(["season", "round", "session"])["driver_id"].count().rename("field_size")
    me = me.join(field_size, on=["season", "round", "session"])
    me["points_rescored"] = [stats.rescore(p, c) if s == "gp" else 0
                             for p, c, s in zip(me["position"], me["classified"], me["session"])]
    me["grid_eff"] = [stats.effective_grid(g, n) for g, n in zip(me["grid"], me["field_size"])]
    me["positions_gained"] = [stats.positions_gained(g, p, c, n)
                              for g, p, c, n in zip(me["grid"], me["position"], me["classified"], me["field_size"])]
    return me.sort_values(["date", "session"]).reset_index(drop=True)


def teammate_quali(quali: pd.DataFrame) -> pd.DataFrame:
    """Max vs teammate qualifying % gap per GP (last common session)."""
    me = quali[quali["driver_id"] == config.DRIVER_ID]
    tm = quali[quali["driver_id"] != config.DRIVER_ID].merge(
        me[["season", "round", "constructor_id"]], on=["season", "round", "constructor_id"])
    m = me.merge(tm, on=["season", "round"], suffixes=("", "_tm"))
    out = []
    for _, r in m.iterrows():
        session, mine, theirs = stats.last_common_session(
            {"q1": r["q1"], "q2": r["q2"], "q3": r["q3"]},
            {"q1": r["q1_tm"], "q2": r["q2_tm"], "q3": r["q3_tm"]})
        out.append({
            "season": r["season"], "round": r["round"], "date": r["date"], "race_name": r["race_name"],
            "constructor_id": r["constructor_id"], "teammate_id": r["driver_id_tm"],
            "quali_pos": r["quali_pos"], "teammate_quali_pos": r["quali_pos_tm"],
            "session": session, "time": mine, "teammate_time": theirs,
            "gap_pct": stats.quali_gap_pct(mine, theirs) if session else None,
        })
    return pd.DataFrame(out)


def pole_gap(quali: pd.DataFrame) -> pd.DataFrame:
    """Max's best qualifying time vs the fastest qualifier, % (C09 pace proxy).

    Compares times from the same session only: Max's time in the last session he
    ran vs the fastest time *in that session*. This avoids comparing Q1 to Q3
    track conditions.
    """
    rows = []
    for (s, rnd), g in quali.groupby(["season", "round"]):
        me = g[g["driver_id"] == config.DRIVER_ID]
        if me.empty:
            continue
        me = me.iloc[0]
        sess = next((q for q in ("q3", "q2", "q1") if pd.notna(me[q])), None)
        if sess is None:
            continue
        best = g[sess].min()
        rows.append({"season": s, "round": rnd, "date": me["date"], "race_name": me["race_name"],
                     "session": sess, "gap_to_fastest_pct": stats.quali_gap_pct(me[sess], best)})
    return pd.DataFrame(rows)


def win_margins(field: pd.DataFrame) -> pd.DataFrame:
    """For each GP Max won: gap to P2 as % of his race time (C07)."""
    gp = field[field["session"] == "gp"]
    wins = gp[(gp["driver_id"] == config.DRIVER_ID) & (gp["position_text"] == "1")]
    p2 = gp[gp["position"] == 2][["season", "round", "driver_id", "time_ms", "laps"]]
    m = wins.merge(p2, on=["season", "round"], suffixes=("", "_p2"))
    m["margin_s"] = [stats.gap_seconds(a, b, la, lb) for a, b, la, lb
                     in zip(m["time_ms"], m["time_ms_p2"], m["laps"], m["laps_p2"])]
    m["margin_pct"] = 100 * m["margin_s"] / (m["time_ms"] / 1000)
    return m[["season", "round", "date", "race_name", "driver_id_p2", "margin_s", "margin_pct"]]


def verify_config(me: pd.DataFrame) -> dict[int, list[int]]:
    """Check car-number eras in config against the data; raise on mismatch."""
    seen = me.groupby("number")["season"].agg(lambda s: sorted(set(s))).to_dict()
    for number, (a, b) in config.NUMBER_ERAS.items():
        expected = [s for s in range(a, b + 1) if s in set(me["season"])]
        if seen.get(number) != expected:
            raise ValueError(f"Car #{number}: config says {expected}, data says {seen.get(number)}")
    return seen


def build() -> dict[str, pd.DataFrame]:
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    field = field_results()
    quali = field_qualifying()
    tables = {
        "field_results": field,
        "results": max_results(field),
        "qualifying": teammate_quali(quali),
        "field_qualifying": quali,
        "pole_gap": pole_gap(quali),
        "standings": standings_by_round(field),
        "official_standings": official_final_standings(),
        "win_margins": win_margins(field),
        "career_greats": greats_results(),
    }
    verify_config(tables["results"])
    for name, df in tables.items():
        df.to_parquet(config.PROCESSED / f"{name}.parquet", index=False)
    return tables


if __name__ == "__main__":
    for name, df in build().items():
        print(f"{name:20s} {df.shape}")
