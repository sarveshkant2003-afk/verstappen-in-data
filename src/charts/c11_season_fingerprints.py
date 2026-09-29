"""C11 · Season fingerprints.

Question: what did each season look like across several measures at once?
Chart type: heatmap table, season (rows) × metric (columns), values printed.
Encodings: cell colour = how good that season was *for that metric*, scaled per
  column from worst to best on one sequential hue (the accent), so every column
  uses the full range; average finish and not-classified % are inverted (lower is
  better). The printed value carries the number; colour only ranks.
Interactivity: hover → season, metric, value, rank within the column.
Caveats: per-column scaling means colours are comparable down a column, not across.
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import config, theme

METRICS = [  # (label, column, higher_is_better, format)
    ("win %", "win_pct", True, "{:.0f}%"),
    ("podium %", "podium_pct", True, "{:.0f}%"),
    ("avg finish", "avg_finish", False, "{:.1f}"),
    ("not classified %", "nc_pct", False, "{:.0f}%"),
    ("fastest qualifier %", "fq_pct", True, "{:.0f}%"),
]


def season_table(tables: dict):
    r, fq = tables["results"], tables["field_qualifying"]
    gp = r[(r.session == "gp") & (r.status_cat != "DNS")]
    s = gp.groupby("season").agg(starts=("position", "size"),
                                 wins=("position_text", lambda x: (x == "1").sum()),
                                 podiums=("position_text", lambda x: x.isin(["1", "2", "3"]).sum()),
                                 avg_finish=("position", lambda x: x[gp.loc[x.index, "classified"]].mean()),
                                 nc=("classified", lambda x: (~x).sum()))
    s["fq"] = fq[(fq.driver_id == config.DRIVER_ID) & (fq.quali_pos == 1)].groupby("season").size().reindex(s.index, fill_value=0)
    s["win_pct"] = 100 * s.wins / s.starts
    s["podium_pct"] = 100 * s.podiums / s.starts
    s["nc_pct"] = 100 * s.nc / s.starts
    s["fq_pct"] = 100 * s.fq / s.starts
    return s


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    s = season_table(tables)
    live = int(s.index.max())
    z, text, hover = [], [], []
    for season, row in s.iterrows():
        zr, tr, hr = [], [], []
        for label, col, hib, fmt in METRICS:
            v = row[col]
            lo, hi = s[col].min(), s[col].max()
            score = (v - lo) / (hi - lo) if hi > lo else 0.5
            zr.append(score if hib else 1 - score)
            tr.append(fmt.format(v))
            rank = int(s[col].rank(ascending=not hib, method="min")[season])
            hr.append(f"<b>{season}{' (so far)' if season == live else ''}</b> · {label}: {fmt.format(v)}<br>"
                      f"#{rank} of {len(s)} seasons")
        z.append(zr)
        text.append(tr)
        hover.append(hr)

    scale = [[0, t["panel"]], [1, t["max"]]]
    ylabels = [f"{i}{' *' if i == live else ''}" for i in s.index]
    fig = go.Figure(go.Heatmap(z=z, x=[m[0] for m in METRICS], y=ylabels, colorscale=scale, showscale=False,
                               zmin=0, zmax=1, xgap=2, ygap=2, text=text, texttemplate="%{text}",
                               textfont=dict(size=11), customdata=hover, hovertemplate="%{customdata}<extra></extra>"))
    # dark cells get light text, light cells dark text
    fig.update_traces(textfont_color=t["text"])
    fig.update_yaxes(type="category", autorange="reversed", showgrid=False, showline=False, ticks="", tickfont=dict(color=t["text"]))
    fig.update_xaxes(side="top", showgrid=False, showline=False, ticks="", tickfont=dict(color=t["text"]))
    best = s["win_pct"].idxmax()
    return theme.finish(
        fig, mode, f"{best}: the season every column agrees on",
        "One row per season · colour ranks each season within its column (darker orange = better) · value printed",
        height=620, note=f"* {live} is in progress. Win/podium/not-classified % of GP starts; avg finish over classified finishes.") \
        if all(s[c].idxmax() == best for c in ("win_pct", "podium_pct", "fq_pct")) and s["avg_finish"].idxmin() == best \
        else theme.finish(fig, mode, "Season fingerprints", "One row per season · colour ranks within each column",
                          height=620)
