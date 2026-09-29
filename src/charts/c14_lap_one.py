"""C14 · Lap-one gains (2018+).

Question: does he make up places at the start, and did that change over time?
Chart type: jittered strip per season + season median marker.
Encodings: x = season; y = places gained on lap 1 (grid slot − position at the end
  of lap 1; up = gained); gray dots = races, accent bar = season median; zero line.
  Pit-lane starts count from the back of the grid.
Interactivity: hover → race, grid → lap-1 position.
Caveats: a start from pole can only lose places, so front-row seasons sit at or
  below zero by construction — the subtitle says so. Lap-1 position is at the
  timing line, not after the first corner. Retirements on lap 1 are excluded.
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import config, theme
from src.charts.common import gp_sequence


def data(tables: dict):
    gp = gp_sequence(tables["results"])
    laps = tables["laps"]
    l1 = laps[(laps.Driver == config.DRIVER_CODE) & (laps.LapNumber == 1)][["season", "round", "Position"]]
    m = gp.merge(l1, on=["season", "round"]).dropna(subset=["Position"])
    m["gain"] = m["grid_eff"] - m["Position"]
    return m


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    m = data(tables)
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color=t["axis"], width=1))
    jitter = (m.groupby("season").cumcount() % 9 - 4) * 0.04
    fig.add_trace(go.Scatter(x=m.season + jitter, y=m.gain, mode="markers",
                             customdata=m[["label", "grid_eff", "Position"]].to_numpy(),
                             marker=dict(size=7, color=t["field"], opacity=0.85, line=dict(color=t["bg"], width=1)),
                             hovertemplate="<b>%{customdata[0]}</b><br>grid P%{customdata[1]} → P%{customdata[2]:.0f} "
                                           "after lap 1 (%{y:+d})<extra></extra>"))
    med = m.groupby("season").agg(gain=("gain", "median"), grid=("grid_eff", "median"), n=("gain", "size"))
    fig.add_trace(go.Scatter(x=med.index, y=med.gain, mode="markers",
                             marker=dict(symbol="line-ew", size=30, line=dict(color=t["max"], width=3)),
                             customdata=med[["grid", "n"]].to_numpy(),
                             hovertemplate="%{x}: median %{y:+.1f} places · median grid P%{customdata[0]:.0f} "
                                           "· n=%{customdata[1]}<extra></extra>"))
    for s, r in med.iterrows():
        fig.add_annotation(x=s, y=m.gain.min() - 1.2, text=f"grid P{r.grid:.0f}", showarrow=False,
                           font=dict(size=9.5, color=t["muted"]))
    gained = (m.gain > 0).mean()
    lost = (m.gain < 0).mean()
    fig.update_xaxes(dtick=1, showgrid=False)
    fig.update_yaxes(title=dict(text="places gained on lap 1"), zeroline=False)
    return theme.finish(
        fig, mode, f"On lap one he gained places in {gained:.0%} of starts and lost them in {lost:.0%}",
        f"Grid slot − position after lap 1, every Grand Prix since {int(m.season.min())} (up = gained) · "
        f"<span style='color:{t['max']}'>━</span> season median · median grid slot under each season",
        height=520, note="Starting from the front limits how much can be gained: from pole, the best is 0.")
