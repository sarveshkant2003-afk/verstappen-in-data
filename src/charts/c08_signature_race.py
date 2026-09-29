"""C08 · Anatomy of a signature race — 2024 São Paulo GP.

Question: how did the race unfold, lap by lap?
Chart type: position-by-lap ("bump") chart + tyre-stint strip, shared lap axis.
Encodings: x = lap (lap 0 = grid slot, from Jolpica); y = running position, P1 at
  top; every other driver a thin gray line, Max the accent line; neutralised laps
  shaded and labelled (safety car / VSC in amber, red flag in red — flag colours,
  always with a text label); pit stops = triangles on his line; bottom strip = his
  stints coloured by compound (standard tyre colours, outlined).
Interactivity: hover → driver, lap, position, compound.
Caveats: position is recorded at the end of each lap (timing-line order), so a
  pass mid-lap appears on the next lap. Track status per lap is the union of codes
  seen by any car on that lap.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import config, theme
from src.laps import LAPS_DIR

SEASON, ROUND = 2024, 21
FLAGS = {"red": ("5",), "SC": ("4",), "VSC": ("6", "7")}


def _periods(laps: pd.Series) -> list[tuple[int, int]]:
    """Contiguous lap ranges from a sorted list of lap numbers."""
    out, start, prev = [], None, None
    for lap in laps:
        if start is None:
            start = prev = lap
        elif lap == prev + 1:
            prev = lap
        else:
            out.append((start, prev))
            start = prev = lap
    if start is not None:
        out.append((start, prev))
    return out


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    laps = pd.read_parquet(LAPS_DIR / f"{SEASON}_{ROUND:02d}.parquet").dropna(subset=["Position"])
    fr = tables["field_results"]
    race = fr[(fr.season == SEASON) & (fr["round"] == ROUND) & (fr.session == "gp")]
    grid0 = race.assign(LapNumber=0, Position=race.grid.where(race.grid > 0, len(race)))[
        ["driver_code", "LapNumber", "Position"]].rename(columns={"driver_code": "Driver"})
    pos = pd.concat([grid0, laps[["Driver", "LapNumber", "Position", "Compound"]]], ignore_index=True)
    names = race.set_index("driver_code")["family_name"]
    me_code = config.DRIVER_CODE
    last_lap = int(laps.LapNumber.max())

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.86, 0.14], vertical_spacing=0.04)

    # neutralised periods (union of codes seen on each lap)
    status = laps.groupby("LapNumber")["TrackStatus"].apply(lambda s: "".join(s.dropna().astype(str)))
    flag_fill = {"red": "rgba(204,36,29,0.16)", "SC": "rgba(215,153,33,0.16)", "VSC": "rgba(215,153,33,0.09)"}
    taken: set[int] = set()
    for kind in ("red", "SC", "VSC"):
        hit = sorted(int(l) for l, s in status.items() if any(c in s for c in FLAGS[kind]) and int(l) not in taken)
        taken |= set(hit)
        for a, b in _periods(hit):
            # add_shape, not add_vrect(row=…): add_vrect skips subplots that have no traces yet
            fig.add_shape(type="rect", xref="x", yref="y domain", x0=a - 0.5, x1=b + 0.5, y0=0, y1=1,
                          fillcolor=flag_fill[kind], line_width=0, layer="below")
            fig.add_annotation(x=(a + b) / 2, y=1.0, xref="x", yref="paper", yanchor="bottom", showarrow=False,
                               text=kind, font=dict(size=10, color=t["muted"]))

    for drv, g in pos.groupby("Driver"):
        g = g.sort_values("LapNumber")
        is_me = drv == me_code
        fig.add_trace(go.Scatter(
            x=g.LapNumber, y=g.Position, mode="lines",
            line=dict(color=t["max"] if is_me else t["field"],
                      width=3 if is_me else 1),
            opacity=1 if is_me else 0.55,
            customdata=[[names.get(drv, drv)]] * len(g),
            hovertemplate="<b>%{customdata[0]}</b> · lap %{x}: P%{y}<extra></extra>"), row=1, col=1)
    # redraw Max on top
    fig.data = tuple(sorted(fig.data, key=lambda tr: tr.line.width))

    me = laps[laps.Driver == me_code].sort_values("LapNumber")
    pits = me[me.pit_in]
    fig.add_trace(go.Scatter(x=pits.LapNumber, y=pits.Position, mode="markers",
                             marker=dict(symbol="triangle-down", size=11, color=t["max"], line=dict(color=t["bg"], width=1.5)),
                             hovertemplate="pit stop, lap %{x}<extra></extra>"), row=1, col=1)

    # stints strip
    for stint, s in me.groupby("Stint"):
        comp = s.Compound.iloc[0]
        fig.add_trace(go.Bar(x=[s.LapNumber.max() - s.LapNumber.min() + 1], base=[s.LapNumber.min() - 0.5], y=["tyres"],
                             orientation="h", width=0.6,
                             marker=dict(color=theme.COMPOUNDS.get(comp, theme.COMPOUNDS["UNKNOWN"]),
                                         line=dict(color=t["text"], width=1)),
                             hovertemplate=f"stint {int(stint)}: {comp.lower()}, laps {int(s.LapNumber.min())}–"
                                           f"{int(s.LapNumber.max())}<extra></extra>"), row=2, col=1)
        fig.add_annotation(x=(s.LapNumber.min() + s.LapNumber.max()) / 2, y="tyres", text=comp.lower(),
                           showarrow=False, font=dict(size=10, color="#282828"), row=2, col=1)

    # key moments, from data
    grid = int(race[race.driver_code == me_code].grid.iloc[0])
    lead = me[me.Position == 1].LapNumber.min()
    fig.add_annotation(x=0, y=grid, text=f"P{grid} on the grid", xanchor="left", xshift=8, showarrow=False,
                       font=dict(size=11, color=t["max"]), row=1, col=1)
    if pd.notna(lead):
        fig.add_annotation(x=lead, y=1, ax=0, ay=40, text=f"leads from lap {int(lead)}", showarrow=True, arrowhead=0,
                           arrowcolor=t["muted"], font=dict(size=11, color=t["text"]), row=1, col=1)
    podium = race[race.position <= 3].sort_values("position")
    for r in podium.itertuples():
        if r.driver_code != me_code:
            fig.add_annotation(x=last_lap, y=r.position, text=f"{r.family_name} P{r.position}", xanchor="left",
                               xshift=6, showarrow=False, font=dict(size=10, color=t["muted"]), row=1, col=1)

    finish = int(race[race.driver_code == me_code].position.iloc[0])
    wet = me.Compound.isin(["INTERMEDIATE", "WET"]).all()
    name = race.race_name.iloc[0].replace(" Grand Prix", " GP")
    title = f"P{grid} to P{finish}{' in the rain' if wet else ''}: the {SEASON} {name}, lap by lap"
    fig.update_yaxes(autorange="reversed", tickvals=[1, 5, 10, 15, 20], ticktext=["P1", "P5", "P10", "P15", "P20"],
                     row=1, col=1)
    fig.update_yaxes(showgrid=False, showline=False, ticks="", row=2, col=1)
    fig.update_xaxes(range=[-0.5, last_lap + 7], showgrid=False, row=1, col=1)
    fig.update_xaxes(title=dict(text="lap"), row=2, col=1)
    fig.update_layout(barmode="overlay", bargap=0)
    return theme.finish(
        fig, mode, title,
        f"Running position every lap · <span style='color:{t['max']}'>━</span> Max · ━ everyone else · "
        f"▼ pit stop · shaded: neutralised laps · strip: his tyres",
        height=620, note="Position at the timing line at the end of each lap; lap 0 = starting grid.")
