"""Helpers shared by chart modules: era bands, race ordering, formatting."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src import config, theme

ERA_LABELS = {33: "#33 · the rise", 1: "#1 · the reign", 3: "#3 · the reset"}


def gp_sequence(results: pd.DataFrame) -> pd.DataFrame:
    """His Grands Prix in date order with a 0-based race index `i` (the x-axis of career timelines)."""
    gp = results[results["session"] == "gp"].sort_values("date").reset_index(drop=True)
    gp["i"] = gp.index
    gp["label"] = gp["season"].astype(str) + " " + gp["race_name"].str.replace(" Grand Prix", " GP")
    return gp


def add_era_bands(fig: go.Figure, gp: pd.DataFrame, mode: str, *, x: str = "i", label_y: float = 1.0,
                  row: int | None = None, col: int | None = None, labels: bool = True) -> None:
    """Shade the #1 era, draw hairlines at era changes and label each era at the top.

    Eras are read from the car number in the data, so they can't drift from config.
    Only the middle era is tinted: alternating neutral tint keeps color free for data.
    """
    t = theme.tok(mode)
    last_era = gp["number"].iloc[-1]
    for number, g in gp.groupby("number", sort=False):
        x0, x1 = g[x].min() - 0.5, g[x].max() + 0.5
        if number == 1:
            fig.add_vrect(x0=x0, x1=x1, fillcolor=t["band"], line_width=0, layer="below", row=row, col=col)
        if labels:
            is_last = number == last_era
            fig.add_annotation(x=x1 if is_last else (x0 + x1) / 2, y=label_y, xref="x", yref="paper", yanchor="bottom",
                               xanchor="right" if is_last else "center",
                               text=f"<b>{ERA_LABELS.get(number, f'#{number}')}</b>", showarrow=False,
                               font=dict(size=11, color=t["muted"]))


def season_ticks(gp: pd.DataFrame, x: str = "i") -> tuple[list, list]:
    first = gp.groupby("season")[x].min()
    return first.tolist(), [str(s) if s % 2 == 1 or s == first.index.min() else "" for s in first.index]


def ordinal(n: int) -> str:
    return f"P{int(n)}"
