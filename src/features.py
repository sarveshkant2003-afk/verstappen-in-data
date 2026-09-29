"""Derived metrics and output/facts.json — the only source of numbers used in prose.

Rule (CLAUDE.md §0): no number appears in the README, captions or the case study
unless it is computed here. Run `python -m src.features` after `src.results`.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src import config, stats
from src.laps import LAPS_DIR, combine


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(config.PROCESSED / f"{name}.parquet")


def load_tables() -> dict[str, pd.DataFrame]:
    names = ["results", "field_results", "qualifying", "field_qualifying", "pole_gap", "standings",
             "official_standings", "win_margins", "career_greats"]
    t = {n: load(n) for n in names}
    # The per-race cache is the source of truth when present (it may be ahead of the
    # combined file while a download is running); a fresh clone uses the committed table.
    laps = config.PROCESSED / "laps_2018plus.parquet"
    if any(LAPS_DIR.glob("*.parquet")):
        t["laps"] = combine()
    elif laps.exists():
        t["laps"] = pd.read_parquet(laps)
    return t


def race_label(row) -> str:
    return f"{row['season']} {row['race_name'].replace(' Grand Prix', ' GP')}"


def title_margins(standings: pd.DataFrame) -> pd.DataFrame:
    """Per season: Max's final points, the best rival's, and the gap (positive = Max ahead)."""
    rows = []
    for s, x in standings.groupby("season"):
        last = x[x["round"] == x["round"].max()]
        me = last[last.driver_id == config.DRIVER_ID].points_cum.iloc[0]
        rival = last[last.driver_id != config.DRIVER_ID].nlargest(1, "points_cum").iloc[0]
        lead = (x[x.driver_id == config.DRIVER_ID].set_index("round").points_cum
                - x[x.driver_id != config.DRIVER_ID].groupby("round").points_cum.max())
        rows.append({"season": s, "rounds": int(x["round"].max()), "points": me, "best_rival": rival.driver_id,
                     "rival_points": rival.points_cum, "final_gap": me - rival.points_cum,
                     "rounds_leading": int((lead > 0).sum())})
    return pd.DataFrame(rows)


def teammate_summary(q: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    q = q.dropna(subset=["gap_pct"])
    out = q.groupby("teammate_id").agg(first=("date", "min"), n_quali=("gap_pct", "size"),
                                       median_gap_pct=("gap_pct", "median"),
                                       quali_ahead_share=("gap_pct", lambda g: (g < 0).mean()))
    gp = results[(results.session == "gp") & results.classified & results.teammate_classified.fillna(False).astype(bool)]
    race = gp.groupby("teammate_id").apply(lambda g: pd.Series({
        "n_race": len(g), "race_ahead_share": (g.position < g.teammate_position).mean()}), include_groups=False)
    return out.join(race).sort_values("first")


def dominance(laps: pd.DataFrame, min_overlap: float = 0.5, n_boot: int = 1000) -> pd.DataFrame:
    """Per race: Max's lap-matched pace vs the closest other driver, % (negative = Max faster).

    For every other driver, take the clean laps both ran on the *same lap numbers*
    (same fuel load and track state) and compute the median of per-lap % differences.
    Only drivers sharing >= min_overlap of Max's clean laps count. The reference is
    the driver Max gained least on (the largest delta) — "vs the fastest other driver".
    CI: bootstrap over the paired laps against that driver.
    """
    clean = laps[laps["clean"] & laps["LapTime_s"].notna()]
    rows = []
    for (s, r), g in clean.groupby(["season", "round"]):
        me = g[g.Driver == config.DRIVER_CODE].set_index("LapNumber")["LapTime_s"]
        if len(me) < 10:
            continue
        cands = []
        for drv, o in g[g.Driver != config.DRIVER_CODE].groupby("Driver"):
            o = o.set_index("LapNumber")["LapTime_s"]
            common = me.index.intersection(o.index)
            if len(common) < min_overlap * len(me):
                continue
            diff = ((me[common] - o[common]) / o[common] * 100).to_numpy()
            cands.append((float(np.median(diff)), drv, diff))
        if not cands:
            continue
        delta, best, diff = max(cands, key=lambda c: c[0])
        rng = np.random.default_rng(int(s) * 100 + int(r))
        boots = np.median(rng.choice(diff, size=(n_boot, len(diff)), replace=True), axis=1)
        rows.append({"season": s, "round": r, "delta_pct": delta, "ci_low": float(np.quantile(boots, 0.025)),
                     "ci_high": float(np.quantile(boots, 0.975)), "best_other": best, "n_laps": len(diff),
                     "wet": bool(g["wet_race"].iloc[0])})
    return pd.DataFrame(rows)


def build_facts(t: dict[str, pd.DataFrame]) -> dict:
    r, fq = t["results"], t["field_qualifying"]
    gp = r[r.session == "gp"].sort_values("date")
    last = gp.iloc[-1]
    counts = stats.gp_counts(r)
    fastest_q = int(((fq.driver_id == config.DRIVER_ID) & (fq.quali_pos == 1)).sum())
    tm = title_margins(t["standings"])
    done = tm[tm.season < last.season]

    by_season = gp.groupby("season").agg(
        starts=("status_cat", lambda s: int((s != "DNS").sum())),
        wins=("position_text", lambda s: int((s == "1").sum())),
        podiums=("position_text", lambda s: int(s.isin(["1", "2", "3"]).sum())),
        not_classified=("classified", lambda s: int((~s).sum())))
    fq_me = fq[(fq.driver_id == config.DRIVER_ID) & (fq.quali_pos == 1)]
    by_season["fastest_qualifier"] = fq_me.groupby("season").size().reindex(by_season.index, fill_value=0)
    by_season["win_pct"] = (100 * by_season.wins / by_season.starts).round(1)

    first_win = gp[gp.position_text == "1"].iloc[0]
    debut = gp.iloc[0]
    wm = t["win_margins"]
    big = wm.nlargest(1, "margin_s").iloc[0]
    close = wm.nsmallest(1, "margin_s").iloc[0]
    cb = gp.nlargest(1, "positions_gained").iloc[0]
    win_from_back = gp[gp.position_text == "1"].nlargest(1, "grid").iloc[0]
    pg = t["pole_gap"].groupby("season").gap_to_fastest_pct.median().round(3)

    cg = t["career_greats"]
    n = counts["starts"]
    greats = {d: {"name": g.driver_name.iloc[0], "starts": int(g.start_n.max()), "wins": int(g.wins_cum.max()),
                  "wins_after_same_starts": int(g[g.start_n <= n].wins_cum.max()),
                  **{f"best_{w}_start_window_wins": int(g.is_win.astype(int).rolling(w).sum().max()) for w in (50, 100)}}
              for d, g in cg.groupby("driver_id")}

    s26 = gp[gp.season == last.season]
    tms = teammate_summary(t["qualifying"], r)

    facts = {
        "data_cutoff": {"season": int(last.season), "round": int(last["round"]), "race": last.race_name,
                        "date": str(last.date.date())},
        "career": {**counts, "fastest_qualifier": fastest_q, "points": float(r.points.sum()),
                   "sprints": int((r.session == "sprint").sum()),
                   "sprint_wins": int(((r.session == "sprint") & (r.position_text == "1")).sum()),
                   "titles": int((done.final_gap > 0).sum()),
                   "title_seasons": done[done.final_gap > 0].season.astype(int).tolist(),
                   "win_pct": round(100 * counts["wins"] / counts["starts"], 1)},
        "eras": {str(k): list(v) for k, v in config.NUMBER_ERAS.items()},
        "debut": {"race": race_label(debut), "team": debut.constructor, "number": int(debut.number)},
        "first_win": {"race": race_label(first_win), "grid": int(first_win.grid), "team": first_win.constructor},
        "by_season": {int(k): v for k, v in by_season.to_dict("index").items()},
        "title_fights": {int(row.season): {"final_gap": float(row.final_gap), "best_rival": row.best_rival,
                                           "rounds_leading": row.rounds_leading, "rounds": row.rounds}
                         for row in tm.itertuples()},
        "win_margin": {"n_wins": int(len(wm)), "median_s": round(float(wm.margin_s.median()), 3),
                       "largest": {"race": race_label(big), "seconds": round(float(big.margin_s), 3)},
                       "smallest": {"race": race_label(close), "seconds": round(float(close.margin_s), 3)}},
        "biggest_comeback": {"race": race_label(cb), "grid": int(cb.grid_eff), "finish": int(cb.position),
                             "gained": int(cb.positions_gained)},
        "win_from_furthest_back": {"race": race_label(win_from_back), "grid": int(win_from_back.grid)},
        "gap_to_fastest_qualifier_median_pct": {int(k): float(v) for k, v in pg.items()},
        "teammates": {k: {"first": str(v["first"].date()), "n_quali": int(v.n_quali),
                          "median_gap_pct": round(float(v.median_gap_pct), 3),
                          "quali_ahead_share": round(float(v.quali_ahead_share), 3),
                          "n_race": int(v.n_race) if pd.notna(v.n_race) else 0,
                          "race_ahead_share": round(float(v.race_ahead_share), 3) if pd.notna(v.race_ahead_share) else None}
                      for k, v in tms.iterrows()},
        "greats": greats,
        "current_season": {"races": len(s26), "wins": int((s26.position_text == "1").sum()),
                           "podiums": int(s26.position_text.isin(["1", "2", "3"]).sum()),
                           "not_classified": int((~s26.classified).sum()),
                           "championship_position": int(t["official_standings"].query(
                               "season == @last.season and driver_id == @config.DRIVER_ID").position.iloc[0]),
                           "last_results": s26.tail(4).position_text.tolist()},
    }
    if "laps" in t:
        dom = dominance(t["laps"])
        dom.to_parquet(config.PROCESSED / "dominance.parquet", index=False)
        dry = dom[~dom.wet]
        expected = set(range(2018, int(last.season) + 1))
        have = set(t["laps"]["season"].unique())
        facts["dominance"] = {
            "coverage_complete": expected <= have,
            "seasons_missing": sorted(int(x) for x in expected - have),
            "races": int(len(dom)), "wet_races": int(dom.wet.sum()),
            "median_delta_pct_by_season": {int(k): round(float(v), 3)
                                           for k, v in dry.groupby("season").delta_pct.median().items()},
            "share_fastest_by_season": {int(k): round(float(v), 3)
                                        for k, v in dry.groupby("season").delta_pct.apply(lambda d: (d < 0).mean()).items()},
        }
    return facts


def main() -> dict:
    facts = build_facts(load_tables())
    config.OUTPUT.mkdir(exist_ok=True)
    config.FACTS.write_text(json.dumps(facts, indent=2, ensure_ascii=False, default=str))
    return facts


if __name__ == "__main__":
    f = main()
    print(json.dumps({k: f[k] for k in ("data_cutoff", "career", "current_season")}, indent=2, ensure_ascii=False))
