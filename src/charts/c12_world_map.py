"""C12 · Where he wins.

Question: which circuits suit him?
Chart type: dot map (circuit lat/long from Jolpica), natural-earth projection.
Encodings: dot area = Grands Prix he started there; colour = win rate at that
  circuit, one sequential hue (field gray → accent); circuits with fewer than
  MIN_RACES_PER_CIRCUIT starts are drawn hollow and excluded from the win-rate
  colour scale (too few races to judge). Top circuits by wins direct-labelled.
Interactivity: hover → circuit, locality, starts, wins, win rate, average finish.
Caveats: circuits are identified by Jolpica circuitId; a layout change at the
  same venue counts as the same circuit.
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import config, theme

N_LABELS = 3


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    r = tables["results"]
    gp = r[(r.session == "gp") & (r.status_cat != "DNS")]
    c = gp.groupby("circuit_id").agg(name=("circuit_name", "first"), locality=("locality", "first"),
                                     country=("country", "first"), lat=("lat", "first"), lon=("lon", "first"),
                                     starts=("season", "size"), wins=("position_text", lambda s: (s == "1").sum()),
                                     avg=("position", lambda s: s[gp.loc[s.index, "classified"]].mean())).reset_index()
    c["win_rate"] = 100 * c.wins / c.starts
    ok = c.starts >= config.MIN_RACES_PER_CIRCUIT
    size = lambda s: 6 + 3.2 * s ** 0.5 * 1.6  # noqa: E731  (area-ish scaling)

    def cd(df):
        return df[["name", "locality", "country", "starts", "wins", "win_rate", "avg"]].to_numpy()

    tpl = ("<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>%{customdata[3]} starts · "
           "%{customdata[4]} wins (%{customdata[5]:.0f}%)<br>avg finish %{customdata[6]:.1f}<extra></extra>")
    fig = go.Figure()
    few = c[~ok]
    fig.add_trace(go.Scattergeo(lat=few.lat, lon=few.lon, mode="markers", customdata=cd(few), hovertemplate=tpl,
                                marker=dict(size=size(few.starts), color="rgba(0,0,0,0)", line=dict(color=t["muted"], width=1.5))))
    many = c[ok].sort_values("starts", ascending=False)
    fig.add_trace(go.Scattergeo(lat=many.lat, lon=many.lon, mode="markers", customdata=cd(many), hovertemplate=tpl,
                                marker=dict(size=size(many.starts), color=many.win_rate, cmin=0,
                                            cmax=float(many.win_rate.max()),
                                            colorscale=[[0, t["field"]], [1, t["max"]]], opacity=0.9,
                                            line=dict(color=t["bg"], width=1.5),
                                            colorbar=dict(title=dict(text="win %", font=dict(size=10, color=t["muted"])),
                                                          thickness=8, len=0.45, x=0.99, tickfont=dict(size=9, color=t["muted"]),
                                                          outlinewidth=0))))
    top = c[ok].sort_values(["wins", "win_rate"], ascending=False).head(N_LABELS)
    fig.add_trace(go.Scattergeo(lat=top.lat, lon=top.lon, mode="text", text=top.locality + " · " + top.wins.astype(str) + " wins",
                                textposition="top center", textfont=dict(size=10, color=t["text"]), hoverinfo="skip"))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor=t["panel"], showocean=False,
                    showcountries=False, showcoastlines=False, showframe=False, bgcolor=t["bg"], lataxis_range=[-50, 70])
    fig.update_layout(margin=dict(l=8, r=8, t=100, b=60))
    best = top.iloc[0]
    tied = top[top.wins == best.wins]
    head = (f"{len(tied)} circuits share his record: {', '.join(tied.locality)}, {int(best.wins)} wins each"
            if len(tied) > 1 else f"{best.locality} is his circuit: {int(best.wins)} wins")
    return theme.finish(fig, mode, head,
                        f"Every circuit he has raced · size = starts there · colour = his win rate · "
                        f"hollow = under {config.MIN_RACES_PER_CIRCUIT} starts",
                        height=560)
