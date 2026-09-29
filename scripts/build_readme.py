"""Render README.md from output/facts.json so every number in it is computed.

    python scripts/build_readme.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

CASE_STUDY = "https://sarveshkantonline.com/projects/verstappen-in-data.html"
GALLERY = [("c01", "Every race"), ("c02", "Every title race"), ("c03", "The teammate gap"),
           ("c07", "The dominance index"), ("c08", "Anatomy of a signature race"), ("c10", "Among the greats")]


def pct(x: float) -> str:
    return f"{x:.2f} %"


def render(f: dict) -> str:
    c, cut = f["career"], f["data_cutoff"]
    tf = f["title_fights"]
    knife = {int(s): v for s, v in tf.items() if abs(v["final_gap"]) < 10 and int(s) < cut["season"]}
    tm = f["teammates"]
    early = [k for k in tm if tm[k]["first"] < "2019"]
    later = [k for k in tm if "2019" <= tm[k]["first"] < str(cut["season"])]
    latest = max(tm, key=lambda k: tm[k]["first"])
    g = f["greats"]
    me = g[config.DRIVER_ID]
    ahead = sorted([d for d in g if d != config.DRIVER_ID and g[d]["wins_after_same_starts"] > me["wins_after_same_starts"]],
                   key=lambda d: -g[d]["wins_after_same_starts"])
    cs = f["current_season"]

    gallery_rows = []
    for i in range(0, len(GALLERY), 2):
        cells = GALLERY[i:i + 2]
        gallery_rows.append("| " + " | ".join(f"**{t}**<br><img src=\"output/static/{cid}.png\" width=\"420\">"
                                              for cid, t in cells) + " |")

    knife_txt = " and ".join(
        f"**{s}** ({'won' if v['final_gap'] > 0 else 'lost'} by {abs(v['final_gap']):g} points)" for s, v in sorted(knife.items()))
    # stored gap is negative when Max is faster; "advantage" flips the sign
    early_txt = ", ".join(f"{k.replace('_', ' ').title()} ({-tm[k]['median_gap_pct']:+.2f} %)" for k in early)
    later_rng = [abs(tm[k]["median_gap_pct"]) for k in later if tm[k]["n_quali"] >= 10]
    dom = f.get("dominance", {})
    dom_line = ""
    if dom and dom.get("coverage_complete"):
        share = dom["share_fastest_by_season"]
        best = max(share, key=share.get)
        dom_line = (f"- **Race pace:** lap-matched against the closest rival each race, his best season was **{best}**, "
                    f"when he was the fastest driver in {share[best]:.0%} of dry races.\n")

    return f"""# 33 → 1 → 3 — Max Verstappen's Formula 1 Career in Data

<img src="output/static/poster_career_stripes.png" alt="Career stripes: one stripe per Grand Prix, coloured by finishing position" width="100%">

A visualization-first data story about one Formula 1 career, told through his three car numbers:
**#33** (the rise), **#1** (the reign) and **#3** (the {cut['season']} reset). Every chart title states a finding the data
supports; where the data contradicts a popular narrative, the chart says so.

**→ Read the interactive case study:** {CASE_STUDY} *(publishing soon)*

This is a descriptive, editorial project: prose and charts read top to bottom, not a dashboard and not a model.
(For forward-looking machine learning on F1, see my separate **F1 Race Predictor**.)

## Key findings

- **{c['starts']} Grands Prix, {c['wins']} wins, {c['titles']} titles** ({', '.join(map(str, c['title_seasons']))}).
- **Two titles were decided by under 10 points:** {knife_txt}.
- **Early teammates kept up; later ones didn't.** Median qualifying advantage over {early_txt}; over every teammate from 2019 to {cut['season'] - 1}: {min(later_rng):.2f}–{max(later_rng):.2f} %. In {cut['season']}, over {latest.title()}: {-tm[latest]['median_gap_pct']:+.2f} % (n={tm[latest]['n_quali']}).
- **Among the greats:** after {c['starts']} starts he has {me['wins_after_same_starts']} wins; {', '.join(f"{g[d]['name']} had {g[d]['wins_after_same_starts']}" for d in ahead)} at the same point. But his best 50-start run had **{me['best_50_start_window_wins']} wins**, more than any of them.
{dom_line}- **{cut['season']} so far:** {cs['wins']} wins, {cs['podiums']} podiums in {cs['races']} races, P{cs['championship_position']} in the championship.

## Gallery

| | |
|---|---|
{chr(10).join(gallery_rows)}

All charts are interactive on the case-study page (hover for every value) and come in the site's dark and light themes.

## Methodology (summary)

- **Data:** [Jolpica-F1](https://github.com/jolpica/jolpica-f1) (the Ergast-compatible API) for results, qualifying and
  standings, {f['by_season'] and min(map(int, f['by_season']))} → today; [FastF1](https://github.com/theOehrly/Fast-F1) for
  lap-by-lap timing and telemetry, which **exists only from 2018**.
- **Validated:** starts, wins, podiums, titles and career points reproduce the official record exactly; rebuilt
  standings match every official driver-season (`notebooks/01_data_audit.ipynb`).
- **Races = Grands Prix only;** sprints are stored separately and never counted as wins.
- **"Fastest qualifier"** is used instead of "pole", because pole counts differ between record-keepers (grid
  penalties, 2021 sprint rules) — see the audit for the reconciliation.
- **Qualifying gaps** use the last session both drivers set a time in, as % of the faster lap.
- **Race pace** compares laps both drivers ran cleanly on the same lap numbers (lap 1, pit laps and safety-car laps
  excluded), with bootstrap confidence intervals; wet races are shown separately.
- Full definitions and every edge case: [`PROJECT.md`](PROJECT.md).

**Data cut-off:** {cut['season']} {cut['race']} (round {cut['round']}, {cut['date']}). The season is live; `make refresh`
re-pulls data after each race and rebuilds every chart and this README.

## Reproduce

```bash
make setup     # Python 3.12 venv + pinned dependencies
make data      # fetch (cached) Jolpica data → data/processed/*.parquet
python -m src.laps   # FastF1 laps 2018+ (first run takes hours: FastF1 limits itself to 500 calls/hour)
make test      # stat-rule unit tests
make charts    # every chart → output/web (JSON) + output/static (PNG)
make refresh   # after a new race
```

## Structure

```
src/        download · results · laps · stats · features · theme · charts/cXX_*.py · poster · build_charts
scripts/    export_to_site.py · build_readme.py · swatches.py
notebooks/  01_data_audit · 02_eda
data/       reference/ (hand-curated, sourced) · processed/ (parquet) · cache/ (gitignored)
output/     facts.json (every number in the prose) · web/ · static/
```

## Attribution and disclaimer

Data from Jolpica-F1 and FastF1 (F1 live-timing). This is an unofficial project, not associated in any way with the
Formula 1 companies. F1, FORMULA ONE and related marks are trademarks of Formula One Licensing B.V. No logos or
photos are used.

## Author

Sarvesh Kant · [sarveshkantonline.com](https://sarveshkantonline.com) · [GitHub](https://github.com/sarveshkant2003-afk)

Code: MIT License.
"""


if __name__ == "__main__":
    facts = json.loads(config.FACTS.read_text())
    (ROOT / "README.md").write_text(render(facts))
    print("README.md written")
