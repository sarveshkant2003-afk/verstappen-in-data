"""C03 · The teammate gap.

Question: how much faster than his teammate was he, and did that change?
Chart type: dot plot over his career with a rolling median line.
Encodings: x = race number (same axis as C01); y = qualifying advantage over the
  teammate, % of the faster lap (up = Max faster), from the last session both set
  a time in; gray dots = races, accent line = 10-race rolling median; each teammate
  spell is bracketed and labelled with name, n and median. Dots beyond ±CLIP % are
  pinned to the edge as triangles (value in hover).
Interactivity: hover → race, teammate, session, both lap times, gap.
Caveats: qualifying only (one lap, no strategy). Teammate comparison controls for
  the car, not for car set-up preferences or a team favouring one driver.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src import stats, theme
from src.charts.common import add_era_bands, gp_sequence, season_ticks

CLIP = 2.0
MIN_LABEL_N = 5


def spells(df) -> list[dict]:
    """Contiguous runs of the same teammate, in race order."""
    out, run = [], None
    for row in df.itertuples():
        if run is None or row.teammate_id != run["id"]:
            run = {"id": row.teammate_id, "name": row.teammate_name, "rows": []}
            out.append(run)
        run["rows"].append(row)
    return out


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    gp = gp_sequence(tables["results"])
    names = tables["field_results"].drop_duplicates("driver_id").set_index("driver_id")["family_name"]
    q = tables["qualifying"].dropna(subset=["gap_pct"]).merge(gp[["season", "round", "i", "label"]], on=["season", "round"])
    q = q.sort_values("i").reset_index(drop=True)
    q["adv"] = -q["gap_pct"]
    q["teammate_name"] = q["teammate_id"].map(names)
    q["y"] = q["adv"].clip(-CLIP, CLIP)
    clipped = q["adv"].abs() > CLIP

    fig = go.Figure()
    add_era_bands(fig, gp, mode)
    fig.add_hline(y=0, line=dict(color=t["axis"], width=1))

    cd = np.stack([q["label"], q["teammate_name"], q["session"].str.upper(),
                   q["time"].map(stats.format_laptime), q["teammate_time"].map(stats.format_laptime),
                   q["adv"].map(lambda v: f"{v:+.2f} %")], axis=-1)
    tpl = ("<b>%{customdata[0]}</b> · vs %{customdata[1]}<br>%{customdata[2]}: %{customdata[3]} vs %{customdata[4]}"
           "<br>Max %{customdata[5]} (+ = faster)<extra></extra>")
    for mask, symbol in [(~clipped, "circle"), (clipped, "triangle-up")]:
        sub = q[mask]
        sym = [("triangle-down" if v < 0 else "triangle-up") if symbol != "circle" else "circle" for v in sub["adv"]]
        fig.add_trace(go.Scatter(x=sub["i"], y=sub["y"], mode="markers", customdata=cd[mask.to_numpy()],
                                 marker=dict(size=6, symbol=sym, color=t["field"], line=dict(color=t["bg"], width=1)),
                                 hovertemplate=tpl))

    roll = q.set_index("i")["adv"].rolling(10, min_periods=5, center=True).median()
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=t["max"], width=2.5),
                             hoverinfo="skip"))

    # spell brackets; each teammate labelled once (at their longest spell) with career totals vs Max
    per_tm = q.groupby("teammate_id")["adv"].agg(["size", "median"])
    all_spells = spells(q)
    longest = {}
    for k, sp in enumerate(all_spells):
        if len(sp["rows"]) > len(all_spells[longest.get(sp["id"], k)]["rows"]) or sp["id"] not in longest:
            longest[sp["id"]] = k
    last_i = q["i"].max()
    labelled = 0
    for k, sp in enumerate(all_spells):
        rows = sp["rows"]
        x0, x1 = rows[0].i - 0.4, rows[-1].i + 0.4
        y_br = -CLIP - 0.25 - 0.32 * (labelled % 2)
        fig.add_shape(type="line", x0=x0, x1=x1, y0=y_br, y1=y_br, line=dict(color=t["muted"], width=1))
        n, med = per_tm.loc[sp["id"], "size"], per_tm.loc[sp["id"], "median"]
        if longest[sp["id"]] == k and len(rows) >= MIN_LABEL_N:
            near_end = x1 > last_i - 12
            fig.add_annotation(x=x1 if near_end else (x0 + x1) / 2, y=y_br, yshift=-2, yanchor="top",
                               xanchor="right" if near_end else "center", showarrow=False,
                               text=f"<b>{sp['name']}</b> n={n} · {med:+.2f}%", font=dict(size=9.5, color=t["text"]))
            labelled += 1

    ticks, labels = season_ticks(gp)
    n_tm = q["teammate_id"].nunique()
    fig.update_xaxes(tickvals=ticks, ticktext=labels, range=[-1.5, len(gp) + 0.5], showgrid=False)
    fig.update_yaxes(range=[-CLIP - 1.0, CLIP + 0.3], tickvals=[-2, -1, 0, 1, 2],
                     ticktext=["−2 %", "−1 %", "0", "+1 %", "+2 %"], title=dict(text="Max faster →", standoff=4))
    # The title is a finding; re-check it on every rebuild so `make refresh` can't leave it stale.
    live = int(q["season"].max())
    early = q[q["season"] <= 2018]["adv"].median()
    middle = q[(q["season"] >= 2019) & (q["season"] < live)]["adv"].median()
    latest = q[q["season"] == live]["adv"].median()
    if early < middle / 3 and latest < middle / 3:
        title = f"Early teammates kept up. Then nobody did, until {live}"
    else:
        title = "The teammate gap, race by race"
    return theme.finish(
        fig, mode, title,
        f"Qualifying advantage over his teammate, % of lap time (up = Max faster) · {len(q)} races, {n_tm} teammates · "
        f"<span style='color:{t['max']}'>━</span> 10-race rolling median",
        height=560, note=f"Last session both drivers set a time in (Q3, else Q2, else Q1). Beyond ±{CLIP:g} % pinned to the edge (▲▼). n and median over all races with that teammate.")
