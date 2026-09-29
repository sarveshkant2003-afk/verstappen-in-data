"""C07 · The dominance index (2018+).

Question: how much faster than everyone else was his race pace, race by race?
Chart type: dot plot with confidence whiskers + rolling median line.
Encodings: x = race number (same axis as C01, from 2018); y = his lap-matched pace
  vs the closest other driver, % — median of per-lap differences on laps both ran
  cleanly (same lap numbers → same fuel load and track state); plotted so UP = MAX
  FASTER; gray dot = dry race with a 95 % bootstrap CI whisker (paired laps
  resampled within the race); hollow = wet race (excluded from
  the line); accent line = rolling median over 10 dry races.
Interactivity: hover → race, delta, CI, who the best other driver was, n laps.
Caveats: the reference is the *fastest other driver that day*, a hard bar; a
  leader managing a gap, different tyre strategies and traffic all move medians.
  Clean laps exclude lap 1, pit laps, SC/VSC/red-flag laps (see stats.clean_laps).
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src import features, theme
from src.charts.common import add_era_bands, gp_sequence, season_ticks


def data(tables: dict):
    gp = gp_sequence(tables["results"])
    dom = features.dominance(tables["laps"]).merge(gp[["season", "round", "i", "label", "number"]], on=["season", "round"])
    dom["adv"] = -dom["delta_pct"]
    dom["adv_lo"], dom["adv_hi"] = -dom["ci_high"], -dom["ci_low"]
    return gp, dom.sort_values("i").reset_index(drop=True)


def build(tables: dict, mode: str = "dark") -> go.Figure:
    t = theme.tok(mode)
    gp, dom = data(tables)
    names = tables["field_results"].drop_duplicates("driver_code").set_index("driver_code")["family_name"]
    gp18 = gp[gp.season >= int(dom.season.min())]

    fig = go.Figure()
    add_era_bands(fig, gp18, mode)
    fig.add_hline(y=0, line=dict(color=t["axis"], width=1))
    fig.add_annotation(x=gp18.i.min(), y=0, yshift=8, xanchor="left", showarrow=False,
                       text="level with the fastest other driver", font=dict(size=10, color=t["muted"]))

    def cd(df):
        return np.stack([df.label, df.adv.map(lambda v: f"{v:+.2f} %"), df.adv_lo.map(lambda v: f"{v:+.2f}"),
                         df.adv_hi.map(lambda v: f"{v:+.2f}"), df.best_other.map(lambda c: names.get(c, c)),
                         df.n_laps], axis=-1)

    tpl = ("<b>%{customdata[0]}</b><br>Max %{customdata[1]} vs %{customdata[4]} (up = faster)"
           "<br>95% CI %{customdata[2]} to %{customdata[3]} · %{customdata[5]} matched laps<extra></extra>")
    dry, wet = dom[~dom.wet], dom[dom.wet]
    fig.add_trace(go.Scatter(x=dry.i, y=dry.adv, mode="markers", customdata=cd(dry), hovertemplate=tpl,
                             error_y=dict(type="data", symmetric=False, array=dry.adv_hi - dry.adv,
                                          arrayminus=dry.adv - dry.adv_lo, color=t["field"], thickness=1, width=0),
                             marker=dict(size=7, color=t["field"], line=dict(color=t["bg"], width=1))))
    fig.add_trace(go.Scatter(x=wet.i, y=wet.adv, mode="markers", customdata=cd(wet), hovertemplate=tpl + "",
                             marker=dict(size=8, color=t["bg"], line=dict(color=t["muted"], width=1.5))))
    roll = dry.set_index("i")["adv"].rolling(10, min_periods=5, center=True).median()
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=t["max"], width=2.5),
                             hoverinfo="skip"))

    share = dry.groupby("season").adv.apply(lambda a: (a > 0).mean())
    n_by = dry.groupby("season").size()
    best = share.idxmax()
    k, n = int(round(share[best] * n_by[best])), int(n_by[best])
    title = f"His best season on race pace was {best}: fastest of all in {k} of {n} dry races"

    ticks, labels = season_ticks(gp18)
    lim = float(np.nanquantile(dom.adv.abs(), 0.97)) + 0.2
    fig.update_xaxes(tickvals=ticks, ticktext=labels, showgrid=False, range=[gp18.i.min() - 1.5, gp18.i.max() + 1])
    fig.update_yaxes(range=[-lim, lim], ticksuffix=" %", title=dict(text="Max faster →", standoff=4))
    missing = sorted(set(gp18.season) - set(dom.season))
    note = "Lap-matched: median % difference on laps both drivers ran cleanly; reference = the driver he beat by least (≥50 % shared laps). Wet races hollow."
    if missing:
        note += f" Lap data still downloading for: {', '.join(map(str, missing))}."
    return theme.finish(
        fig, mode, title,
        f"Race pace per Grand Prix since {int(dom.season.min())}, % of lap time (up = faster than everyone) · "
        f"<span style='color:{t['max']}'>━</span> rolling median of 10 dry races · ○ wet race",
        height=560, note=note)
