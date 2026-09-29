"""Render the theme swatch sheet (colour tokens + a sample chart) for both modes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src import config, theme


def sheet(mode: str) -> go.Figure:
    t = theme.tok(mode)
    roles = [("max", "Max"), ("rival", "one rival"), ("field", "the field"),
             ("text", "text"), ("muted", "secondary text"), ("grid", "gridlines")]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.32, 0.68], vertical_spacing=0.16)
    for i, (k, label) in enumerate(roles):
        fig.add_shape(type="rect", x0=i, x1=i + 0.8, y0=0, y1=1, fillcolor=t[k],
                      line=dict(color=t["axis"], width=1), row=1, col=1)
        fig.add_annotation(x=i + 0.4, y=-0.25, text=f"<b>{k}</b><br>{t[k]}<br>{label}", showarrow=False,
                           font=dict(size=10, color=t["muted"]), yanchor="top", row=1, col=1)
    for i, (c, col) in enumerate(theme.COMPOUNDS.items()):
        if c == "UNKNOWN":
            continue
        fig.add_shape(type="circle", x0=6.2 + i * 0.36, x1=6.5 + i * 0.36, y0=0.35, y1=0.65, fillcolor=col,
                      line=dict(color=t["text"], width=1), row=1, col=1)
    fig.add_annotation(x=7.1, y=-0.25, text="tyres S · M · H · I · W", showarrow=False,
                       font=dict(size=10, color=t["muted"]), yanchor="top", row=1, col=1)
    fig.update_xaxes(visible=False, range=[-0.1, 8.1], row=1, col=1)
    fig.update_yaxes(visible=False, range=[-1.2, 1.1], row=1, col=1)

    # sample: season-median qualifying gap to the fastest qualifier
    pg = pd.read_parquet(config.PROCESSED / "pole_gap.parquet")
    s = pg.groupby("season").gap_to_fastest_pct.median().reset_index()
    fig.add_trace(go.Scatter(x=pg.season + (pg["round"] / 30 - 0.4), y=pg.gap_to_fastest_pct.clip(upper=3),
                             mode="markers", marker=dict(size=5, color=t["field"]),
                             hovertemplate="%{y:.2f} %<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=s.season, y=s.gap_to_fastest_pct, mode="lines+markers",
                             line=dict(color=t["max"], width=2), marker=dict(size=8, line=dict(color=t["bg"], width=2)),
                             hovertemplate="%{x}: median %{y:.2f} %<extra></extra>"), row=2, col=1)
    fig.update_yaxes(title_text="gap to fastest qualifier, %", rangemode="tozero", row=2, col=1)
    fig.update_xaxes(dtick=1, showgrid=False, row=2, col=1)
    return theme.finish(fig, mode, f"Theme swatches · {mode} mode",
                        "Tokens from sarveshkantonline.com (Gruvbox + JetBrains Mono); sample chart: qualifying pace by season",
                        height=640)


if __name__ == "__main__":
    for m in theme.MODES:
        out = config.STATIC_OUT / f"theme_swatches_{m}.png"
        sheet(m).write_image(out, width=1000, scale=2)
        print(out)
