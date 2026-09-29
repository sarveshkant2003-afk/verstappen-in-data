"""Copy chart JSON/PNG, the poster and facts.json into the website repo.

    python scripts/export_to_site.py <path to website repo>

Writes to <site>/projects/verstappen-in-data/{charts/,img/,facts.json}. Only files
this project produced are touched; nothing else in the site is modified.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.charts import REGISTRY  # noqa: E402


def export(site: Path) -> list[Path]:
    if not (site / "index.html").exists():
        raise SystemExit(f"{site} does not look like the website repo (no index.html)")
    dest = site / "projects" / "verstappen-in-data"
    charts, img = dest / "charts", dest / "img"
    charts.mkdir(parents=True, exist_ok=True)
    img.mkdir(parents=True, exist_ok=True)
    copied = []
    for cid in REGISTRY:
        for src in [*config.WEB_OUT.glob(f"{cid}.*.json"), *config.STATIC_OUT.glob(f"{cid}*.png")]:
            target = (charts if src.suffix == ".json" else img) / src.name
            shutil.copy2(src, target)
            copied.append(target)
    for name in ("poster_career_stripes.png", "social_card.png"):
        if (config.STATIC_OUT / name).exists():
            shutil.copy2(config.STATIC_OUT / name, img / name)
            copied.append(img / name)
    shutil.copy2(config.FACTS, dest / "facts.json")
    copied.append(dest / "facts.json")
    return copied


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/export_to_site.py <site_path>")
    files = export(Path(sys.argv[1]).expanduser().resolve())
    print(f"copied {len(files)} files")
