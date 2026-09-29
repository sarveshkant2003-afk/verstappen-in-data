"""C09 · The reset (closing chapter): 2026 against the reign.

Question: how far has he fallen back in 2026, and is it getting better?
Chart type: three small-multiple strip plots (season on x) + one wide panel with
  the within-season trend.
Encodings: top row, one panel per measure, seasons REIGN_FROM → live season on x:
  (a) finishing position, (b) qualifying gap to the fastest qualifier (%),
  (c) race-pace gap to the fastest other driver (%); gray dots = races, accent
  bar = season median. For (b) and (c) lower = better, drawn with the best at top.
  Bottom: the live season race by race — both gaps as lines on one % axis
  (same unit), finishing position printed above each round.
Interactivity: hover → race and value.
Caveats: dated by the data cut-off; the live season is a partial sample. Qualifying
  gap uses the fastest time in the same session he last ran in.
"""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import theme
from src.charts.c07_dominance import data as dominance_data

REIGN_FROM = 2022
CLIP = 3.0  # % — gaps beyond this are pinned to the panel edge as triangles


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    gp, dom = dominance_data(tables)
    live = int(gp.season.max())
    seasons = list(range(REIGN_FROM, live + 1))
    fin = gp[gp.season.isin(seasons)]
    pg = tables["pole_gap"].merge(gp[["season", "round", "label"]], on=["season", "round"])
    pg = pg[pg.season.isin(seasons)]
    rp = dom[dom.season.isin(seasons) & ~dom.wet]

    fig = make_subplots(rows=2, cols=3, row_heights=[0.55, 0.45], vertical_spacing=0.2, horizontal_spacing=0.07,
                        specs=[[{}, {}, {}], [{"colspan": 3}, None, None]],
                        subplot_titles=["finishing position", "qualifying: gap to fastest, %",
                                        "race pace: gap to fastest other driver, %", f"{live}, race by race"])
    panels = [
        (1, fin.assign(v=fin.position.where(fin.classified)), "P%{y:.0f}", True),
        (2, pg.assign(v=pg.gap_to_fastest_pct), "%{y:.2f} %", True),
        (3, rp.assign(v=rp.delta_pct), "%{y:+.2f} %", True),
    ]
    for col, df, fmt, reverse in panels:
        jitter = (df.groupby("season").cumcount() % 7 - 3) * 0.05
        pinned = (df.v > CLIP) if col > 1 else df.v.isna() & False
        # hover shows the true value; the marker is drawn at the clip line
        fig.add_trace(go.Scatter(x=df.season + jitter, y=df.v.where(~pinned, CLIP), mode="markers",
                                 customdata=df.label + " (true value " + df.v.round(2).astype(str) + ")",
                                 marker=dict(size=5, color=t["field"], opacity=0.8,
                                             symbol=["triangle-down" if p else "circle" for p in pinned]),
                                 hovertemplate="%{customdata}: " + fmt + "<extra></extra>"), row=1, col=col)
        med = df.groupby("season").v.median()
        if col == 3:
            for sn in seasons:
                if sn not in med.index:
                    fig.add_annotation(x=sn, y=0.5, yref="y3 domain", text="no lap<br>data", showarrow=False,
                                       font=dict(size=9.5, color=t["muted"]), row=1, col=col)
        fig.add_trace(go.Scatter(x=med.index, y=med.values, mode="markers",
                                 marker=dict(symbol="line-ew", size=26, line=dict(color=t["max"], width=3)),
                                 hovertemplate="%{x} median: " + fmt + "<extra></extra>"), row=1, col=col)
        fig.update_xaxes(tickvals=seasons, ticktext=[f"{s}*" if s == live else str(s) for s in seasons],
                         showgrid=False, range=[REIGN_FROM - 0.6, live + 0.6], row=1, col=col)
        if col > 1:
            fig.update_yaxes(range=[CLIP + 0.15, min(-0.3, float(df.v.min()) - 0.1)], ticksuffix=" %", row=1, col=col)
        elif reverse:
            fig.update_yaxes(autorange="reversed", row=1, col=col)
    fig.update_yaxes(tickvals=[1, 5, 10, 15, 20], ticktext=["P1", "P5", "P10", "P15", "P20"], row=1, col=1)

    # within-season trend
    lq = pg[pg.season == live].sort_values("round")
    lr = rp[rp.season == live].sort_values("round")
    lf = fin[fin.season == live].sort_values("round")
    fig.add_trace(go.Scatter(x=lq["round"], y=lq.gap_to_fastest_pct, mode="lines+markers", customdata=lq.label,
                             line=dict(color=t["rival"], width=2), marker=dict(size=6),
                             hovertemplate="%{customdata}<br>qualifying gap %{y:.2f} %<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=lr["round"], y=lr.delta_pct, mode="lines+markers", customdata=lr.label,
                             line=dict(color=t["max"], width=2.5), marker=dict(size=7),
                             hovertemplate="%{customdata}<br>race-pace gap %{y:+.2f} %<extra></extra>"), row=2, col=1)
    ymax = max(lq.gap_to_fastest_pct.max(), lr.delta_pct.max() if len(lr) else 0)
    for r in lf.itertuples():
        txt = f"P{r.position}" if r.classified else "DNF"
        fig.add_annotation(x=r.round, y=ymax * 1.18, text=txt, showarrow=False, font=dict(size=9.5, color=t["muted"]),
                           row=2, col=1)
    for y, txt, col in [(lq.gap_to_fastest_pct.iloc[-1], "qualifying", t["rival"]),
                        (lr.delta_pct.iloc[-1] if len(lr) else None, "race pace", t["max"])]:
        if y is not None:
            fig.add_annotation(x=lf["round"].max(), y=y, text=txt, xanchor="left", xshift=8, showarrow=False,
                               font=dict(size=10, color=col), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=t["axis"], width=1), row=2, col=1)
    fig.update_xaxes(title=dict(text="round"), dtick=1, showgrid=False, range=[0.5, lf["round"].max() + 2.5], row=2, col=1)
    fig.update_yaxes(autorange="reversed", ticksuffix=" %", row=2, col=1)
    fig.update_annotations(selector=dict(xref="paper"), font=dict(size=11, color=t["text"]))

    # title from data: compare the live season's medians with the reign's, and the trend within the season
    reign_q = pg[pg.season < live].gap_to_fastest_pct.median()
    live_q = lq.gap_to_fastest_pct.median()
    half = len(lf) // 2
    early_fin = lf.head(half).position.where(lf.head(half).classified, 20).median()
    late_fin = lf.tail(len(lf) - half).position.where(lf.tail(len(lf) - half).classified, 20).median()
    wins = int((lf.position_text == "1").sum())
    if wins == 0 and live_q > reign_q and late_fin < early_fin:
        title = f"{live}: no wins yet and slower than the reign, but finishing higher as the season goes on"
    else:
        title = f"{live} against the reign"
    return theme.finish(
        fig, mode, title,
        f"Top: each dot a Grand Prix, <span style='color:{t['max']}'>━</span> = season median; lower is better, drawn "
        f"at the top · bottom: {live} round by round (dry races for race pace)",
        height=760, note=f"* {live} is in progress; data to the cut-off. Race pace excludes wet races. "
                         f"▼ = beyond {CLIP:g} %, pinned to the edge. Retirements have no finishing position.")
