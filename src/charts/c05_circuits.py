"""C05 · Circuits in colour (2018+).

Question: what do his fastest laps look like at the tracks where he wins most?
Chart type: small-multiple track maps from car position data.
Encodings: each panel = his fastest lap in the latest qualifying he topped at one
  of his six most-won circuits (chosen from data: src.telemetry.map_candidates);
  line drawn as dense markers coloured by speed on one perceptually ordered ramp
  (dark = slow, bright = fast; neighbouring Gruvbox hues only, no rainbow);
  every map rotated to the circuit's conventional orientation (FastF1 circuit
  info), equal aspect, identical styling. Panel title = place, year, wins there.
Interactivity: hover → speed, gear, distance into the lap.
Caveats: position data is sampled (~4 Hz), interpolated to a 1,000-point grid.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import theme
from src.telemetry import TEL_DIR

COLS = 3
RAMP = {"dark": ["#3c3836", "#9d0006", "#d65d0e", "#fabd2f", "#fbf1c7"],
        "light": ["#d5c4a1", "#d79921", "#d65d0e", "#9d0006", "#3c1a14"]}


def _rotate(x: np.ndarray, y: np.ndarray, deg: float) -> tuple[np.ndarray, np.ndarray]:
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    meta = json.loads((TEL_DIR / "maps_meta.json").read_text())
    rows = math.ceil(len(meta) / COLS)
    fig = make_subplots(rows=rows, cols=COLS, horizontal_spacing=0.02, vertical_spacing=0.08,
                        subplot_titles=[f"<b>{m['locality']}</b> · {m['season']} · {m['wins']} wins" for m in meta])
    traces = [pd.read_parquet(TEL_DIR / f"map_{m['circuit_id']}.parquet") for m in meta]
    vmin = min(tr.speed.min() for tr in traces)
    vmax = max(tr.speed.max() for tr in traces)
    stops = RAMP[mode]
    scale = [[i / (len(stops) - 1), c] for i, c in enumerate(stops)]
    for k, (m, tr) in enumerate(zip(meta, traces)):
        x, y = _rotate(tr.x.to_numpy(), tr.y.to_numpy(), m["rotation"])
        fig.add_trace(go.Scattergl(
            x=x, y=y, mode="markers",
            marker=dict(size=4, color=tr.speed, colorscale=scale, cmin=vmin, cmax=vmax,
                        showscale=k == 0,
                        colorbar=dict(title=dict(text="km/h", font=dict(size=10, color=t["muted"])), thickness=8,
                                      len=0.5, tickfont=dict(size=9, color=t["muted"]), outlinewidth=0)),
            customdata=np.stack([tr.speed, tr.ngear.round(), tr.distance], axis=-1),
            hovertemplate="%{customdata[0]:.0f} km/h · gear %{customdata[1]:.0f}<br>%{customdata[2]:.0f} m into the lap"
                          "<extra></extra>"), row=k // COLS + 1, col=k % COLS + 1)
        axis = k + 1
        fig.update_xaxes(visible=False, row=k // COLS + 1, col=k % COLS + 1)
        fig.update_yaxes(visible=False, scaleanchor=f"x{axis if axis > 1 else ''}", scaleratio=1,
                         row=k // COLS + 1, col=k % COLS + 1)
    fig.update_annotations(selector=dict(xref="paper"), font=dict(size=11, color=t["text"]))
    return theme.finish(
        fig, mode, "Where he wins most, drawn by his own fastest laps",
        "His fastest qualifying lap at each of his six most-won circuits since 2018 · colour = speed "
        "(dark = slow corners, bright = straights)",
        height=330 * rows + 150, note="Car position data from F1 live timing, rotated to each circuit's usual orientation.")
