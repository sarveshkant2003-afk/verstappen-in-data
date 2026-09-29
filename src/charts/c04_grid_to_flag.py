"""C04 · Grid to flag.

Question: where did he make up the most ground in a race?
Chart type: dumbbell. One row per race, the TOP_N biggest gains.
Encodings: x = position, P20 on the left, P1 on the right (movement reads left→right
  towards the win); hollow dot = grid slot, filled accent dot = finish; row label
  = race; wins marked in the label. Pit-lane starts are placed at the back of the
  grid (field size) and labelled.
Interactivity: hover → race, grid → finish, places gained, status.
Caveats: classified finishes only; gains from grid penalties (starting far back
  in a fast car) are the usual reason for the biggest climbs — the subtitle says so.
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import config, theme
from src.charts.common import gp_sequence

TOP_N = 12


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    gp = gp_sequence(tables["results"])
    cls = gp[gp["classified"]]
    top = cls.nlargest(TOP_N, "positions_gained").sort_values(["positions_gained", "date"]).reset_index(drop=True)
    top["row"] = top["label"] + top["position_text"].eq("1").map({True: "  ★ win", False: ""})
    top["grid_txt"] = [("pit lane" if g == 0 else f"P{g}") for g in top["grid"]]

    fig = go.Figure()
    for r in top.itertuples():
        fig.add_shape(type="line", x0=r.grid_eff, x1=r.position, y0=r.row, y1=r.row,
                      line=dict(color=t["field"], width=2))
    cd = top[["label", "grid_txt", "position", "positions_gained", "status"]].to_numpy()
    tpl = ("<b>%{customdata[0]}</b><br>grid %{customdata[1]} → P%{customdata[2]}"
           "<br>+%{customdata[3]:.0f} places · %{customdata[4]}<extra></extra>")
    fig.add_trace(go.Scatter(x=top["grid_eff"], y=top["row"], mode="markers", customdata=cd, hovertemplate=tpl,
                             marker=dict(size=10, color=t["bg"], line=dict(color=t["muted"], width=2))))
    fig.add_trace(go.Scatter(x=top["position"], y=top["row"], mode="markers+text", customdata=cd, hovertemplate=tpl,
                             text=[f"+{g:.0f}" for g in top["positions_gained"]], textposition="middle right",
                             textfont=dict(size=10, color=t["muted"]),
                             marker=dict(size=11, color=t["max"], line=dict(color=t["bg"], width=2))))

    n10 = int((cls["positions_gained"] >= 10).sum())
    fq = tables["field_qualifying"]
    q_me = fq[fq["driver_id"] == config.DRIVER_ID][["season", "round", "quali_pos"]]
    pen = top.merge(q_me, on=["season", "round"], how="left")
    n_pen = int((pen["grid_eff"] > pen["quali_pos"]).sum())
    fb = gp[gp["position_text"] == "1"].nlargest(1, "grid").iloc[0]
    fig.update_xaxes(range=[21, -0.8], tickvals=[20, 15, 10, 5, 3, 1], ticktext=["P20", "P15", "P10", "P5", "P3", "P1"],
                     title=None)
    fig.update_yaxes(showgrid=False, title=None, tickfont=dict(size=11, color=t["text"]))
    fig.update_layout(margin=dict(l=210))
    return theme.finish(
        fig, mode, f"From P{fb.grid} on the grid to the win: his greatest comebacks",
        f"His {TOP_N} biggest climbs, grid ○ → finish <span style='color:{t['max']}'>●</span> · "
        f"he gained 10+ places in {n10} Grands Prix",
        height=90 + 38 * TOP_N + 120,
        note=f"Classified finishes only. In {n_pen} of these {TOP_N} races he started behind his qualifying position (grid penalty).")
