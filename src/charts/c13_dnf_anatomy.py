"""C13 · How the races ended — retirements by cause and season.

Question: how often did his races end early, and why?
Chart type: stacked bars per season (counts), few categories.
Encodings: x = season; y = number of Grands Prix ending in retirement; segments
  = cause: mechanical (blue), incident (gray), cause not recorded (outlined only,
  2024+ where Jolpica reports a generic "Retired"). Direct labels on the first bar
  that has each category; 2px surface gap between segments.
Interactivity: hover → season, cause, count, races.
Caveats: categories come from data/reference/status_map.csv (ambiguous strings
  reviewed); includes retirements that were still classified (>90 % distance).
"""
from __future__ import annotations

import plotly.graph_objects as go

from src import theme

CATS = [("DNF-mechanical", "mechanical"), ("DNF-incident", "incident"), ("DNF-other", "other"),
        ("DNF-unknown", "cause not recorded")]


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    r = tables["results"]
    gp = r[r.session == "gp"]
    seasons = sorted(gp.season.unique())
    d = gp[gp.status_cat.str.startswith("DNF")].copy()
    d["race"] = d.race_name.str.replace(" Grand Prix", " GP")
    style = {"DNF-mechanical": dict(color=t["rival"]), "DNF-incident": dict(color=t["field"]),
             "DNF-other": dict(color=t["muted"]),
             "DNF-unknown": dict(color=t["bg"], line=dict(color=t["muted"], width=1.5))}
    fig = go.Figure()
    for cat, label in CATS:
        x = d[d.status_cat == cat]
        if x.empty:
            continue
        g = x.groupby("season").agg(n=("race", "size"), races=("race", lambda s: "<br>".join(s)))
        g = g.reindex(seasons).fillna({"n": 0, "races": ""})
        mk = style[cat]
        fig.add_trace(go.Bar(x=g.index, y=g.n, name=label, width=0.62,
                             marker=dict(color=mk["color"], line=mk.get("line", dict(color=t["bg"], width=2))),
                             customdata=g.races, hovertemplate=f"<b>%{{x}}</b> · {label}: %{{y}}<br>%{{customdata}}<extra></extra>"))
    starts = gp[gp.status_cat != "DNS"].groupby("season").size()
    tot = d.groupby("season").size().reindex(seasons, fill_value=0)
    live = seasons[-1]
    early = d[d.season <= 2021]
    reign = d[(d.season >= 2022) & (d.season < live)]
    fig.add_trace(go.Scatter(x=tot.index, y=tot.values, mode="text", text=[f"{v}/{starts[s]}" for s, v in tot.items()],
                             textposition="top center", textfont=dict(size=9.5, color=t["muted"]), hoverinfo="skip",
                             showlegend=False))
    fig.update_layout(barmode="stack", bargap=0.3, showlegend=True,
                      legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(size=11, color=t["text"])))
    fig.update_xaxes(dtick=1, showgrid=False)
    fig.update_yaxes(title=dict(text="retirements"), dtick=1, range=[0, tot.max() + 1.5])
    title = (f"{len(early)} retirements in {early.season.nunique()} seasons, {len(reign)} in the four-year reign, "
             f"{int(tot[live])} already in {live}")
    return theme.finish(fig, mode, title,
                        "Grands Prix that ended in retirement, by cause · label = retirements / starts that season",
                        height=520, note="From 2024 the results feed records only 'Retired', so the cause is not known.")
