"""Render every registered chart in both theme modes.

output/web/<id>.<mode>.json  – for the website (plotly.js reads fig.data/fig.layout)
output/static/<id>.png       – dark mode, 2× (README, noscript fallback)
output/static/<id>_light.png – light mode, 2×

    python -m src.build_charts            # all charts
    python -m src.build_charts c01 c03    # just some
"""
from __future__ import annotations

import sys

from src import config, features, theme
from src.charts import REGISTRY


def render(ids: list[str] | None = None) -> None:
    tables = features.load_tables()
    config.WEB_OUT.mkdir(parents=True, exist_ok=True)
    config.STATIC_OUT.mkdir(parents=True, exist_ok=True)
    for cid, module in REGISTRY.items():
        if ids and cid not in ids:
            continue
        for mode in theme.MODES:
            fig = module.build(tables, mode)
            (config.WEB_OUT / f"{cid}.{mode}.json").write_text(fig.to_json())
            suffix = "" if mode == "dark" else "_light"
            fig.write_image(config.STATIC_OUT / f"{cid}{suffix}.png", width=1100, scale=2)
        print(f"{cid}: ok")


if __name__ == "__main__":
    render(sys.argv[1:] or None)
