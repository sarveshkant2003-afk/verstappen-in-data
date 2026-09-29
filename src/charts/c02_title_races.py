"""C02 · Every title race.

Question: how did each of his championship seasons unfold, round by round?
Chart type: small multiples of cumulative-points lines, one panel per season.
Encodings: x = round; y = official cumulative points (shared across panels, so a
  575-point season looks bigger than a 49-point one); Max in the accent, the two
  best-placed other drivers in gray, direct-labelled at the line end. Seasons
  decided by fewer than KNIFE_EDGE points between Max and the nearest driver get
  a tinted panel and the margin in the panel title.
Interactivity: hover → driver, round, points.
Caveats: official points, which include sprint and fastest-lap bonuses of their
  era (right for a within-season chart). The live season is marked as unfinished.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import config, theme

KNIFE_EDGE = 10
COLS = 4


def _spread(values: list[float], min_gap: float) -> list[float]:
    """Nudge label y-positions apart so no two are closer than min_gap (keeps order)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < min_gap:
            out[b] = out[a] + min_gap
    return out


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    st = tables["standings"]
    names = tables["field_results"].drop_duplicates("driver_id").set_index("driver_id")["family_name"]
    live = int(tables["results"]["season"].max())
    seasons = sorted(st.season.unique())
    rows = math.ceil(len(seasons) / COLS)

    panel = {}
    for s in seasons:
        x = st[st.season == s]
        last = x[x["round"] == x["round"].max()]
        me = last[last.driver_id == config.DRIVER_ID].iloc[0]
        others = last[last.driver_id != config.DRIVER_ID].nlargest(2, "points_cum")
        gap = me.points_cum - others.points_cum.iloc[0]
        pos = int(me["rank"])
        if s == live:
            head = f"{s} · P{pos} so far"
        elif pos == 1:
            head = f"{s} · <b>champion</b>, +{gap:g}"
        else:
            head = f"{s} · P{pos}"
        if s != live and abs(gap) < KNIFE_EDGE and pos <= 2:
            head = f"<b>{s} · {'champion' if gap > 0 else 'P2'}, {gap:+g}</b>".replace("-", "−")
        panel[s] = dict(x=x, rivals=others.driver_id.tolist(), gap=gap, head=head,
                        knife=s != live and abs(gap) < KNIFE_EDGE and pos <= 2)

    fig = make_subplots(rows=rows, cols=COLS, shared_yaxes=True, horizontal_spacing=0.025, vertical_spacing=0.09,
                        subplot_titles=[panel[s]["head"] for s in seasons])
    ymax_guess = st.points_cum.max()
    ymax = st[st.driver_id.isin([config.DRIVER_ID] + sum((p["rivals"] for p in panel.values()), []))].points_cum.max()

    for k, s in enumerate(seasons):
        r, c = k // COLS + 1, k % COLS + 1
        p = panel[s]
        if p["knife"]:
            fig.add_shape(type="rect", xref=f"x{k + 1 if k else ''} domain", yref=f"y{k + 1 if k else ''} domain",
                          x0=0, x1=1, y0=0, y1=1, fillcolor=t["band"], line_width=0, layer="below")
        ends = {d: p["x"][p["x"].driver_id == d].sort_values("round").points_cum.iloc[-1]
                for d in p["rivals"] + [config.DRIVER_ID]}
        # Max's end is included so rival labels also step clear of the orange line end
        label_y = dict(zip(ends, _spread(list(ends.values()), ymax_guess * 0.075)))
        for d in p["rivals"] + [config.DRIVER_ID]:
            y = p["x"][p["x"].driver_id == d].sort_values("round")
            is_me = d == config.DRIVER_ID
            fig.add_trace(go.Scatter(
                x=y["round"], y=y.points_cum, mode="lines",
                line=dict(color=t["max"] if is_me else t["field"], width=2.5 if is_me else 1.5),
                customdata=[[names.get(d, d), s]] * len(y),
                hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]} round %{x}<br>%{y:g} pts<extra></extra>"),
                row=r, col=c)
            if not is_me:
                fig.add_annotation(x=y["round"].iloc[-1], y=label_y[d], text=names.get(d, d),
                                   xanchor="left", xshift=3, showarrow=False, font=dict(size=9, color=t["muted"]),
                                   row=r, col=c)
        fig.update_xaxes(range=[0, p["x"]["round"].max() + 7], row=r, col=c)

    fig.update_xaxes(showgrid=False, tickfont=dict(size=9), dtick=10, ticks="")
    fig.update_yaxes(range=[0, ymax * 1.08], tickfont=dict(size=9), dtick=200)
    fig.update_annotations(selector=dict(xref="paper"), font=dict(size=11, color=t["text"]), xanchor="left", x=None)
    # subplot titles: left-align over each panel
    for k, a in enumerate([a for a in fig.layout.annotations if a.yref == "paper"][:len(seasons)]):
        c = k % COLS
        a.x = fig.layout[f"xaxis{k + 1 if k else ''}"].domain[0]
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
    titles = sum(1 for s in seasons if s != live and panel[s]["gap"] > 0)
    knives = [s for s in seasons if panel[s]["knife"]]
    title = (f"{words.get(titles, titles)} titles, {words.get(len(knives), len(knives)).lower()} knife-edges: "
             + ", ".join(f"{panel[s]['gap']:+g} in {s}".replace("-", "−") for s in knives))
    return theme.finish(
        fig, mode, title,
        f"Cumulative championship points by round · <span style='color:{t['max']}'>━</span> Max · "
        f"━ the two best-placed rivals · tinted = decided by under {KNIFE_EDGE} points",
        height=190 * rows + 170, note=f"{live} is still in progress (data cut-off).")
