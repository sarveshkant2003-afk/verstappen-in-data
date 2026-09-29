"""Copy chart images and the poster into the website repo.

    python scripts/export_to_site.py <path to website repo>

The site's project pages are static write-ups on a light background, so they use
the light-theme PNGs, resized to 1400 px wide (2x the 680 px text column).
Files go to <site>/assets/verstappen-in-data/. Nothing else in the site is touched.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.charts import REGISTRY  # noqa: E402

WIDTH = 1400


def _resize(src: Path, dst: Path) -> None:
    """Copy src to dst at WIDTH px wide (macOS `sips`; plain copy elsewhere)."""
    shutil.copy2(src, dst)
    if shutil.which("sips"):
        subprocess.run(["sips", "--resampleWidth", str(WIDTH), str(dst)], check=True, capture_output=True)


def export(site: Path) -> list[Path]:
    if not (site / "index.html").exists():
        raise SystemExit(f"{site} does not look like the website repo (no index.html)")
    dest = site / "assets" / "verstappen-in-data"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for cid in REGISTRY:
        src = config.STATIC_OUT / f"{cid}_light.png"
        if src.exists():
            _resize(src, dest / f"{cid}.png")
            copied.append(dest / f"{cid}.png")
    for name in ("poster_career_stripes.png", "social_card.png"):
        if (config.STATIC_OUT / name).exists():
            _resize(config.STATIC_OUT / name, dest / name) if name.startswith("poster") else \
                shutil.copy2(config.STATIC_OUT / name, dest / name)
            copied.append(dest / name)
    return copied


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/export_to_site.py <site_path>")
    files = export(Path(sys.argv[1]).expanduser().resolve())
    print(f"copied {len(files)} files")
