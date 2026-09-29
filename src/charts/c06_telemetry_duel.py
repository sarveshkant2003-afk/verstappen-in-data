"""C06 · Telemetry duel — 2025 Japanese GP qualifying, Max vs Norris.

Question: where on the lap was pole won and lost?
Chart type: speed traces aligned by distance + a cumulative time-delta panel below.
Encodings: x = distance into the lap (m) — both laps interpolated onto the same
  grid (never aligned by time: the same second is a different place on track);
  top: speed, Max accent, rival blue, direct-labelled; bottom: running gap in
  seconds, drawn so UP = MAX AHEAD, zero line; corner numbers along the top; the
  corner-to-corner section where Max gained most and lost most is annotated.
Interactivity: hover (unified by distance) → both speeds, the gap.
Caveats: telemetry is sampled, then interpolated; the running gap is computed
  from interpolated elapsed time and can drift by a few hundredths — the final
  gap is taken from the official lap times and quoted in the subtitle.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import stats, theme
from src.telemetry import TEL_DIR


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    a = pd.read_parquet(TEL_DIR / "duel_max.parquet")
    b = pd.read_parquet(TEL_DIR / "duel_rival.parquet")
    corners = pd.read_parquet(TEL_DIR / "duel_corners.parquet")
    meta = json.loads((TEL_DIR / "duel_meta.json").read_text())
    rival = meta["rival_name"]
    gap = b.time - a.time  # >0 = Max ahead at this point of the lap

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.05)
    for df, name, col, w in [(b, rival, t["rival"], 1.8), (a, "Max", t["max"], 2.2)]:
        fig.add_trace(go.Scatter(x=df.distance, y=df.speed, mode="lines", name=name, line=dict(color=col, width=w),
                                 hovertemplate=f"{name}: %{{y:.0f}} km/h<extra></extra>"), row=1, col=1)
        fig.add_annotation(x=df.distance.iloc[-1], y=df.speed.iloc[-1], text=name, xanchor="left", xshift=6,
                           showarrow=False, font=dict(size=11, color=col), row=1, col=1)
    fig.add_trace(go.Scatter(x=a.distance, y=gap, mode="lines", line=dict(color=t["text"], width=1.8),
                             fill="tozeroy", fillcolor=t["band"],
                             hovertemplate="gap %{y:+.3f} s (+ = Max ahead)<extra></extra>"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=t["axis"], width=1), row=2, col=1)

    for c in corners.itertuples():
        fig.add_annotation(x=c.Distance, y=1.0, xref="x", yref="paper", yanchor="bottom", showarrow=False,
                           text=f"{int(c.Number)}{c.Letter or ''}", font=dict(size=9, color=t["muted"]))

    # sections between consecutive corners: where the gap changed most
    edges = np.concatenate([[0], corners.Distance.to_numpy(), [a.distance.iloc[-1]]])
    g_at = np.interp(edges, a.distance, gap)
    change = np.diff(g_at)
    for idx, label in [(int(np.argmax(change)), "gained"), (int(np.argmin(change)), "lost")]:
        x0, x1 = edges[idx], edges[idx + 1]
        fig.add_shape(type="rect", xref="x2", yref="y2 domain", x0=x0, x1=x1, y0=0, y1=1,
                      fillcolor=t["band"], line_width=0, layer="below")
        fig.add_annotation(x=(x0 + x1) / 2, y=1, xref="x2", yref="y2 domain", yanchor="bottom", showarrow=False,
                           text=f"{label} {abs(change[idx]):.3f} s", font=dict(size=10, color=t["text"]))

    final = meta["rival_lap_s"] - meta["max_lap_s"]
    fig.update_yaxes(title=dict(text="km/h"), row=1, col=1)
    fig.update_yaxes(title=dict(text="gap, s"), zeroline=False, row=2, col=1)
    fig.update_xaxes(title=dict(text="distance into the lap, m"), row=2, col=1)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(hovermode="x unified")
    who = "Max" if final > 0 else rival
    return theme.finish(
        fig, mode, f"{meta['season']} {meta['event'].replace(' Grand Prix', ' GP')} qualifying: "
                   f"{abs(final):.3f} s, and where {who} found it",
        f"Max {stats.format_laptime(meta['max_lap_s'])} vs {rival} {stats.format_laptime(meta['rival_lap_s'])} · "
        f"top: speed by distance · bottom: running gap (up = Max ahead) · numbers = corners",
        height=620, note="Both laps interpolated onto one distance grid. Running gap from interpolated time; final gap from official lap times.")
