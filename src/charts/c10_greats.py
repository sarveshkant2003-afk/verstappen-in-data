"""C10 · Among the greats.

Question: how does his winning record compare with the all-time greats at the
  same stage of a career?
Chart type: cumulative step lines, wins vs Grand Prix starts.
Encodings: x = start number (career stage, not calendar year, so eras line up);
  y = cumulative GP wins; Max in the accent, others gray, direct end-labels with
  totals; a vertical rule at his current start count; his best 50-start window
  shaded.
Interactivity: hover → driver, start n, season, wins so far.
Caveats: raw wins ignore car quality, calendar length and reliability of each era.
  Start counts are derived from Jolpica and may differ by ±1 from some record books
  (DNS/withdrawal definitions).
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import config, theme

WINDOW = 50


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    cg = tables["career_greats"]
    me_n = int(cg[cg.driver_id == config.DRIVER_ID].start_n.max())

    fig = go.Figure()
    best = {}
    for d, g in cg.groupby("driver_id"):
        roll = g.is_win.astype(int).rolling(WINDOW).sum()
        best[d] = (int(roll.max()), int(g.loc[roll.idxmax(), "start_n"]))

    # shade Max's best window first so it sits under the lines
    wins_best, end = best[config.DRIVER_ID]
    fig.add_vrect(x0=end - WINDOW + 0.5, x1=end + 0.5, fillcolor=t["band"], line_width=0, layer="below")
    fig.add_annotation(x=end - WINDOW / 2, y=1, yref="paper", yanchor="bottom", showarrow=False,
                       text=f"his best {WINDOW} starts: {wins_best} wins", font=dict(size=10, color=t["muted"]))
    fig.add_vline(x=me_n, line=dict(color=t["axis"], width=1))

    order = sorted(cg.driver_id.unique(), key=lambda d: d == config.DRIVER_ID)  # Max drawn last (on top)
    ends = []
    for d in order:
        g = cg[cg.driver_id == d]
        is_me = d == config.DRIVER_ID
        fig.add_trace(go.Scatter(
            x=g.start_n, y=g.wins_cum, mode="lines", line=dict(shape="hv", width=3 if is_me else 1.5,
                                                               color=t["max"] if is_me else t["field"]),
            customdata=g[["driver_name", "season"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>start %{x} (%{customdata[1]}) · %{y} wins<extra></extra>"))
        ends.append((d, g.start_n.iloc[-1], g.wins_cum.iloc[-1], g.driver_name.iloc[0].split(" ")[-1]))

    for d, x, y, name in ends:
        is_me = d == config.DRIVER_ID
        fig.add_annotation(x=x, y=y, text=f"<b>{name}</b> {y}" if is_me else f"{name} {y}", xanchor="left", xshift=5,
                           showarrow=False, bgcolor=t["bg"], borderpad=2,
                           font=dict(size=11, color=t["max"] if is_me else t["muted"]))

    at_me = {d: int(g[g.start_n <= me_n].wins_cum.max()) for d, g in cg.groupby("driver_id")}
    ahead = [d for d in at_me if d != config.DRIVER_ID and at_me[d] > at_me[config.DRIVER_ID]]
    best_run_leader = max(best, key=lambda d: best[d][0]) == config.DRIVER_ID
    names = cg.drop_duplicates("driver_id").set_index("driver_id").driver_name.str.split(" ").str[-1]
    if ahead and best_run_leader:
        title = (f"Fewer wins after {me_n} starts than {' or '.join(names[a] for a in ahead)}, "
                 f"but the best {WINDOW}-race run of any of them")
    else:
        title = "Wins by career start: among the all-time greats"
    fig.update_xaxes(title=dict(text="Grand Prix starts"), range=[0, cg.start_n.max() * 1.1], showgrid=False)
    fig.update_yaxes(title=dict(text="wins"), rangemode="tozero")
    return theme.finish(
        fig, mode, title,
        f"Cumulative Grand Prix wins by career start · vertical rule = his {me_n} starts so far · "
        f"shaded = his best {WINDOW}-start run",
        height=560, note="Start counts from Jolpica-F1; some record books differ by ±1.")
