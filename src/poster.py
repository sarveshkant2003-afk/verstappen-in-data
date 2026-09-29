"""Poster edition: "career stripes" — one vertical stripe per Grand Prix.

Colour = finishing position on a sequential yellow→orange→deep-red ramp (P1
brightest), not classified = neutral gray. Era labels underneath. Inspired by
Ed Hawkins' warming stripes: no axes, the shape of the career carries it.
Output: output/static/poster_career_stripes.png (300 dpi) + a 1200×630 social card.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.patches import Rectangle

from src import config, features
from src.charts.common import ERA_LABELS, gp_sequence

BG, TEXT, MUTED, DNF = "#1d2021", "#ebdbb2", "#a89984", "#504945"
RAMP = LinearSegmentedColormap.from_list("stripes", ["#fabd2f", "#fe8019", "#d65d0e", "#9d0006", "#3c1a14"])


def _font() -> str:
    """Prefer JetBrains Mono (the site's font) if installed; fall back to DejaVu Sans Mono."""
    for p in [*Path.home().glob("Library/Fonts/JetBrainsMono*NerdFontMono-*.ttf"),
              *Path("/Library/Fonts").glob("JetBrainsMono*.ttf")]:
        font_manager.fontManager.addfont(str(p))
    names = {f.name for f in font_manager.fontManager.ttflist}
    for n in ("JetBrains Mono", "JetBrainsMono Nerd Font Mono", "JetBrainsMonoNL Nerd Font Mono"):
        if n in names:
            return n
    return "DejaVu Sans Mono"


def colour(position: int, classified: bool) -> tuple:
    if not classified:
        return to_rgba(DNF)
    return RAMP(min(position - 1, 19) / 19)


def draw(width_in: float, height_in: float, *, social: bool = False) -> plt.Figure:
    t = features.load_tables()
    gp = gp_sequence(t["results"])
    n = len(gp)
    plt.rcParams["font.family"] = _font()

    fig = plt.figure(figsize=(width_in, height_in), facecolor=BG)
    top, strip_h = (0.66, 0.38) if not social else (0.70, 0.40)
    ax = fig.add_axes([0.05, top - strip_h, 0.90, strip_h])
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for r in gp.itertuples():
        ax.add_patch(Rectangle((r.i, 0), 1.0, 1, color=colour(r.position, r.classified), lw=0))

    # era brackets + labels underneath
    last = gp.number.iloc[-1]
    for number, g in gp.groupby("number", sort=False):
        x0, x1 = g.i.min() + 0.3, g.i.max() + 0.7
        ax.plot([x0, x1], [-0.06, -0.06], color=MUTED, lw=1, clip_on=False)
        # the short final era is right-aligned so its label doesn't run off the edge
        xl, ha = (x1, "right") if number == last else ((x0 + x1) / 2, "center")
        ax.text(xl, -0.12, ERA_LABELS[number], color=TEXT, ha=ha, va="top",
                fontsize=11 if not social else 13, fontweight="bold")
        ax.text(xl, -0.24, f"{g.season.min()}–{g.season.max()}" if g.season.min() != g.season.max()
                else str(g.season.min()), color=MUTED, ha=ha, va="top", fontsize=9 if not social else 11)

    wins = int((gp.position_text == "1").sum())
    cut = gp.iloc[-1]
    fig.text(0.05, 0.93, "33 → 1 → 3", color=TEXT, fontsize=34 if not social else 40, fontweight="bold", va="top")
    fig.text(0.05, 0.81 if not social else 0.83,
             f"Max Verstappen · every Grand Prix, {gp.season.min()}–{cut.season} · {n} starts · {wins} wins",
             color=MUTED, fontsize=12 if not social else 15, va="top")

    # legend: ramp + DNF chip
    lg = fig.add_axes([0.05, 0.08, 0.30, 0.025])
    for p in range(1, 21):
        lg.add_patch(Rectangle((p - 1, 0), 1, 1, color=colour(p, True), lw=0))
    lg.add_patch(Rectangle((21, 0), 1, 1, color=DNF, lw=0))
    lg.set_xlim(0, 22)
    lg.set_ylim(0, 1)
    lg.axis("off")
    for x, s in [(0.5, "P1"), (9.5, "P10"), (19.5, "P20"), (21.5, "DNF")]:
        lg.text(x, -0.4, s, color=MUTED, ha="center", va="top", fontsize=8 if not social else 10)
    fig.text(0.95, 0.06, f"Data: Jolpica-F1 · to {cut.season} {cut.race_name} · Sarvesh Kant",
             color=MUTED, ha="right", fontsize=8 if not social else 10)
    return fig


def main() -> None:
    config.STATIC_OUT.mkdir(parents=True, exist_ok=True)
    draw(16, 7).savefig(config.STATIC_OUT / "poster_career_stripes.png", dpi=300, facecolor=BG)
    draw(12, 6.3, social=True).savefig(config.STATIC_OUT / "social_card.png", dpi=100, facecolor=BG)
    print("poster: ok")


if __name__ == "__main__":
    main()
