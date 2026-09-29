"""Visual design system, derived from sarveshkantonline.com (css/style.css).

The site is Gruvbox dark by default with a light toggle (`data-theme`), set in
JetBrains Mono. Every chart is built once per mode; the page swaps between the
two JSON files when the reader toggles the theme.

Colour roles (validated with the dataviz skill's palette validator, both modes):
  max    – Max Verstappen, everywhere. Gruvbox orange (also: Dutch orange).
  rival  – one highlighted comparison (teammate / title rival). Site blue, re-stepped
           for chroma so it doesn't read as gray.
  field  – everyone else: recessive gray.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

FONT = "JetBrains Mono, JetBrainsMono Nerd Font Mono, Fira Code, Courier New, monospace"
SOURCE = "Data: FastF1 · Jolpica-F1 · Analysis: Sarvesh Kant"
MODES = ("dark", "light")

TOKENS: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#282828",        # --bg-body (dark1)
        "panel": "#3c3836",     # --bg-panel (dark2)
        "text": "#ebdbb2",      # --text-on-dark
        "muted": "#a89984",
        "grid": "#3c3836",
        "axis": "#504945",
        "field": "#7c6f64",
        "field_faint": "#504945",
        "max": "#e06a14",
        "rival": "#3a8fc4",
        "band": "rgba(235,219,178,0.05)",
    },
    "light": {
        "bg": "#fbf1c7",        # --light
        "panel": "#ebdbb2",
        "text": "#282828",      # --text-on-light
        "muted": "#7c6f64",
        "grid": "#ebdbb2",
        "axis": "#d5c4a1",
        "field": "#a89984",
        "field_faint": "#d5c4a1",
        "max": "#c8570c",
        "rival": "#1c6f9a",
        "band": "rgba(40,40,40,0.05)",
    },
}

# Tyre compounds: the standard convention mapped onto Gruvbox hues. Hard is drawn
# with an outline so it stays visible on the light surface.
COMPOUNDS = {
    "SOFT": "#cc241d", "MEDIUM": "#d79921", "HARD": "#ebdbb2",
    "INTERMEDIATE": "#79a33a", "WET": "#458588", "UNKNOWN": "#928374",
}


def tok(mode: str) -> dict[str, str]:
    return TOKENS[mode]


def _template(mode: str) -> go.layout.Template:
    t = TOKENS[mode]
    axis = dict(
        showgrid=True, gridcolor=t["grid"], gridwidth=1, zeroline=False,
        showline=True, linecolor=t["axis"], linewidth=1, ticks="outside", tickcolor=t["axis"], ticklen=4,
        tickfont=dict(color=t["muted"], size=11), title=dict(font=dict(color=t["muted"], size=12)),
    )
    return go.layout.Template(layout=go.Layout(
        font=dict(family=FONT, color=t["text"], size=12),
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg"],
        colorway=[t["max"], t["rival"], t["field"]],
        title=dict(x=0, xanchor="left", xref="container", y=0.97, yanchor="top", pad=dict(l=16),
                   font=dict(size=18, color=t["text"], weight=700),
                   subtitle=dict(font=dict(size=12, color=t["muted"]))),
        xaxis=axis, yaxis=axis,
        margin=dict(l=56, r=24, t=96, b=72),
        showlegend=False,
        hoverlabel=dict(bgcolor=t["panel"], bordercolor=t["axis"], font=dict(family=FONT, color=t["text"], size=12)),
        hovermode="closest",
    ))


for _m in MODES:
    pio.templates[f"sarvesh_{_m}"] = _template(_m)
pio.templates.default = "sarvesh_dark"


def finish(fig: go.Figure, mode: str, title: str, subtitle: str, *, height: int = 520,
           source: str = SOURCE, note: str | None = None) -> go.Figure:
    """Apply template, declarative title + subtitle and the bottom-left source line."""
    t = TOKENS[mode]
    fig.update_layout(template=f"sarvesh_{mode}", height=height,
                      title=dict(text=title, subtitle=dict(text=subtitle)))
    foot = source if note is None else f"{note}<br>{source}"
    fig.add_annotation(text=foot, xref="paper", yref="paper", x=0, y=0, xanchor="left", yanchor="top",
                       yshift=-44, showarrow=False, align="left", font=dict(size=10, color=t["muted"]))
    return fig


def mpl_style(mode: str = "light") -> dict:
    """matplotlib rcParams from the same tokens (poster edition)."""
    t = TOKENS[mode]
    return {
        "font.family": "monospace",
        "font.monospace": ["JetBrains Mono", "JetBrainsMono Nerd Font Mono", "DejaVu Sans Mono"],
        "figure.facecolor": t["bg"], "axes.facecolor": t["bg"], "savefig.facecolor": t["bg"],
        "text.color": t["text"], "axes.labelcolor": t["muted"],
        "xtick.color": t["muted"], "ytick.color": t["muted"], "axes.edgecolor": t["axis"],
        "axes.spines.top": False, "axes.spines.right": False,
    }
