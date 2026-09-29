"""C01 · Every race (hero).

Question: what does the whole career look like, race by race?
Chart type: timeline strip / dot plot. One dot per Grand Prix.
Encodings: x = race number in chronological order (even spacing, so busy and
  short seasons don't distort the arc); y = finishing position, P1 at top;
  colour = win (Max accent) vs any other finish (field gray); not-classified
  finishes sit in a separate band below P20 as crosses (shape, not just colour);
  a thin line = rolling 10-race median finish, to make the three acts legible.
  Background: the #1 era tinted, eras labelled; team spells labelled in the band.
Interactivity: hover → race, team, grid → finish, status, points.
Caveats: sprints excluded. Finishing position doesn't account for car pace:
  a P5 in a slow 2015 Toro Rosso may be a better drive than a P2 in 2023.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src import theme
from src.charts.common import add_era_bands, gp_sequence, season_ticks

DNF_Y = 23.5


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    gp = gp_sequence(tables["results"])
    n = len(gp)
    win = gp["position_text"] == "1"
    cls = gp["classified"]

    def hover(df):
        grid = df["grid"].map(lambda g: "pit lane" if g == 0 else f"P{g}")
        fin = df["position_text"].where(df["classified"], "not classified").map(
            lambda p: f"P{p}" if p.isdigit() else p)
        return np.stack([df["label"], df["constructor"], grid, fin, df["status"], df["points"]], axis=-1)

    tpl = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>grid %{customdata[2]} → %{customdata[3]}"
           "<br>%{customdata[4]} · %{customdata[5]} pts<extra></extra>")

    fig = go.Figure()
    add_era_bands(fig, gp, mode)

    # rolling median of classified finishes; DNFs are shown by their own crosses, not folded into the line
    y_roll = gp["position"].where(cls).rolling(10, min_periods=5, center=True).median()
    fig.add_trace(go.Scatter(x=gp["i"], y=y_roll, mode="lines", line=dict(color=t["muted"], width=1.5),
                             hoverinfo="skip", name="10-race median"))

    other = gp[cls & ~win]
    fig.add_trace(go.Scatter(x=other["i"], y=other["position"], mode="markers", name="finish",
                             marker=dict(size=7, color=t["field"], line=dict(color=t["bg"], width=1)),
                             customdata=hover(other), hovertemplate=tpl))
    wins = gp[win]
    fig.add_trace(go.Scatter(x=wins["i"], y=wins["position"], mode="markers", name="win",
                             marker=dict(size=9, color=t["max"], line=dict(color=t["bg"], width=1.5)),
                             customdata=hover(wins), hovertemplate=tpl))
    dnf = gp[~cls]
    fig.add_trace(go.Scatter(x=dnf["i"], y=[DNF_Y] * len(dnf), mode="markers", name="not classified",
                             marker=dict(size=7, symbol="x-thin", color=t["muted"], line=dict(color=t["muted"], width=1.5)),
                             customdata=hover(dnf), hovertemplate=tpl))

    # team spells: a small label at the bottom of each spell
    for team, g in gp.groupby("constructor", sort=False):
        fig.add_annotation(x=g["i"].min() - 0.5, y=25.3, text=team, xanchor="left", showarrow=False,
                           font=dict(size=10, color=t["muted"]))
        fig.add_shape(type="line", x0=g["i"].min() - 0.5, x1=g["i"].max() + 0.5, y0=24.7, y1=24.7,
                      line=dict(color=t["axis"], width=2))

    # a few purposeful annotations
    first_win = gp[win].iloc[0]
    fig.add_annotation(x=first_win["i"], y=1, ax=28, ay=-34, text="first win,<br>" + first_win["label"],
                       showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=t["muted"], xanchor="left",
                       font=dict(size=10, color=t["text"]), align="left")

    ticks, labels = season_ticks(gp)
    fig.update_xaxes(tickvals=ticks, ticktext=labels, range=[-1.5, n + 0.5], showgrid=False, title=None)
    fig.update_yaxes(range=[26, 0], tickvals=[1, 3, 5, 10, 15, 20, DNF_Y],
                     ticktext=["P1", "P3", "P5", "P10", "P15", "P20", "DNF"], title=None, zeroline=False)
    fig.update_layout(hovermode="closest", margin=dict(t=110))
    wins_n, starts = int(win.sum()), n
    return theme.finish(fig, mode, f"{starts} races in three acts: the rise, the reign, the reset",
                        f"Finishing position in each of his {starts} Grands Prix · <span style='color:{t['max']}'>●</span> "
                        f"win ({wins_n}) · ● other finish · × not classified · line: 10-race median of classified finishes",
                        height=560)
