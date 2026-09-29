# CLAUDE.md — "33 → 1 → 3": Max Verstappen's Formula 1 Career in Data

> Spec + rules for Claude Code. Read this whole file before doing anything.

---

## 0. Context and working mode

**Who I am:** Sarvesh Kant, MSc Statistics & Computing student (BHU), preparing for ML/DS roles.
Website: https://sarveshkantonline.com · GitHub: https://github.com/sarveshkant2003-afk
Machine: Mac, Homebrew, VS Code with Python/Jupyter extensions.

**Why this project exists:** an interviewer asked whether I have data-visualization projects. I don't yet.
This project fixes that: a **visualization-first data story** (beautiful, editorial charts — NOT a dashboard)
about Max Verstappen's F1 career, published as an interactive case study on my website, with all code on GitHub.

**How it differs from my F1 Race Predictor:** the predictor is ML and forward-looking (predict results).
This project is descriptive and visual (tell the story of one career). Reuse my FastF1 knowledge, but share no code
with the predictor repo, and make the difference obvious in README and website copy.

**Working mode (same as my F1 predictor and traffic RL projects):**
1. You (Claude Code) build the full project. I review at every **CHECKPOINT** (section 12). At a checkpoint, stop,
   render what you built to PNG, tell me the file paths to open, summarise decisions, and wait for my go-ahead.
2. Start in **plan mode**: read this file, inspect the environment, propose a concrete plan, confirm with me.
3. Write a detailed teaching file **PROJECT.md** (section 11). Treat it as a first-class deliverable, written with
   high effort — never rushed or left to the end as a summary.
4. Act as a mentor too: proactively tell me what would take the project from good to great, and flag weak charts.
5. **Never invent numbers, races, dates or quotes.** Every number in prose, README, captions or website copy is
   computed by the pipeline and stored in `output/facts.json`.
6. Commit after each milestone with meaningful messages (section 10). No single giant commit at the end.
7. When a choice is subjective (colors, chart form, wording), recommend one option with a reason, then ask.

---

## 0.1 Decisions log (overrides the sections below where they conflict)

- **2026-09-29 · Light data scope.** No full-field FastF1 bulk download. Priority is clean, strong visuals, not
  pipeline depth. Consequences:
  - `laps_2018plus.parquet` is **not built**. FastF1 is loaded only for the handful of sessions C05, C06, C08 need.
  - **C07 dominance index** → winning margin (gap to P2 as % of race time, from Jolpica race times), 2015–now.
  - **C09 reset** → pace proxy = qualifying gap to pole (%) from Jolpica qualifying, not race-pace delta.
  - C14 lap-one gains uses FastF1 only if cheap; otherwise dropped from the Tier 2 shortlist.
- **2026-09-29 · Environment.** Python 3.12 venv; Jolpica accessed via a small cached `requests` client in
  `src/download.py` (transparent pagination + 429 backoff) instead of `fastf1.ergast`.
- **2026-09-29 · Scope revised (supersedes "light data scope" for laps).** Full-field race laps 2018+ ARE built
  (`laps_2018plus.parquet`, resumable, newest season first). FastF1 self-limits to 500 calls/h (~9 calls/race),
  so the first build takes ~3–4 h. C07 = original lap-pace dominance index; winning margin rejected in EDA.
  C09 uses both quali gap to fastest qualifier and race-pace delta.
- **2026-09-29 · Checkpoint answers.** Status-map REVIEW rows agreed. Poles → "fastest qualifier" everywhere.
  C08 signature race = 2024 São Paulo GP. Max's colour = orange (#e06a14 dark / #c8570c light).
  Website integration deferred until the charts are complete.
  C06 duel = 2025 Japanese GP qualifying, Max vs Norris. C05 circuits chosen from data (six most-won since 2018).
  C14 built and cut (lap-1 gains mostly reflect grid slot).
- **2026-09-29 · Git.** Commit locally per milestone; create the GitHub remote and push at CHECKPOINT 1.

---

## 1. Deliverables

1. Public GitHub repo **`verstappen-in-data`** under `sarveshkant2003-afk`.
2. Interactive case-study page on my site: **`/projects/verstappen-in-data.html`**.
3. A new **projects hub** on my site (`/projects.html`) + a projects section on the homepage, listing this project and
   my other projects (F1 Race Predictor, Adaptive Traffic Signal RL, Neural Network from Scratch).
4. A strong **README.md** with a static chart gallery.
5. **PROJECT.md** teaching file with interview prep.
6. A high-resolution **poster edition**: "career stripes" (section 6, C01) for README banner and LinkedIn.
7. A `make refresh` command that re-pulls data after each 2026 race and rebuilds the charts (the season is live).

## 2. Non-goals

- Not a dashboard: no filter panels, no KPI tiles, no Streamlit for this project. It is an editorial data story —
  prose and charts read top to bottom, like a long-form article.
- No ML models.
- No scraping of formula1.com or other sites. Data comes from FastF1 and the Jolpica-F1 API only, plus small
  hand-curated reference files in `data/reference/`, each with a source URL and "as of" date.
- No F1 logos, team logos or driver photos (trademark/copyright). Charts only.

---

## 3. Tech stack

- Python 3.11+ in a project venv `.venv` (recent FastF1 needs ≥ 3.10).
- `fastf1` (latest 3.x) — session results, laps, stints, track status, weather, telemetry, position data.
  Its `fastf1.ergast` interface talks to **Jolpica-F1** (the Ergast-compatible successor) for historical results.
- `pandas`, `numpy`, `pyarrow` — data. `scipy` — bootstrap helpers.
- `plotly` — all interactive charts. `kaleido` — static PNG export (if kaleido asks for Chrome, run `plotly_get_chrome`).
- `matplotlib` — poster edition only.
- `requests`, `jupyter`, `pytest`.
- Frontend: the existing static site (plain HTML/CSS/JS). plotly.js from CDN, **pinned to the exact version**
  bundled with the Python plotly package (`plotly.offline.get_plotlyjs_version()`).

Pin versions in `requirements.txt`.

---

## 4. Data

### 4.1 Sources and what each covers
| Source | Coverage | Used for |
|---|---|---|
| Jolpica-F1 (via `fastf1.ergast`) | All seasons incl. his 2015 debut | Race & sprint results, grid, status, qualifying, driver/constructor standings per round, lap-by-lap positions & times, pit stops, circuits (with lat/long) |
| FastF1 live-timing data | **2018 onwards only** | Clean-lap analysis, compounds & stints, track status (SC/VSC), weather, telemetry (speed/throttle/brake/gear/DRS), car position (track maps) |

Consequence: 2015–2017 charts can use results and lap times, but not telemetry or stints. The audit and the case study
must say this plainly.

### 4.2 Caching and rate limits
- Enable the FastF1 cache at `data/cache/fastf1/` (gitignored) before any call.
- Respect Jolpica rate limits: cache every response, never loop without the cache, back off on HTTP 429.
- Bulk loading every 2018–2026 race is slow. Load with only what each chart needs
  (e.g. `session.load(telemetry=False, weather=False, messages=False)` for lap analysis) and **tell me the expected
  download time before starting a bulk load.**
- `src/download.py` is idempotent and writes `data/cache/MANIFEST.json` (what was fetched, when, data cut-off race).

### 4.3 Identifying Max
- Jolpica driver ID (confirm: `max_verstappen`), FastF1 abbreviation `VER`, driver numbers **33 (2015–2021), 1 (2022–2025),
  3 (2026)** — verify all of these from the data and store in `src/config.py`. Never filter by driver number alone.
- Teammates: derive from results per race (same constructor, same race). Don't hardcode names.

### 4.4 F1 stat rules (must be exactly right — interviewers will probe these)
| Concept | Rule |
|---|---|
| Race | Grand Prix only. Sprints stored separately and flagged; never mixed into GP win/podium counts. |
| Win / podium | GP finishing position 1 / ≤ 3. |
| Pole | "Fastest qualifier" = qualifying P1 from Jolpica. Official pole counts differ on some 2021 sprint weekends — reconcile in the audit and document. Grid P1 ≠ pole (grid penalties). |
| Finish status | Map Jolpica `status` strings → {Finished, Lapped, DNF-mechanical, DNF-incident, DNF-other, DSQ, DNS} in `data/reference/status_map.csv`. Review the mapping with me. |
| Classified | Use Jolpica `positionText` (numeric = classified; R/D/W/N etc. = not). |
| Positions gained | grid − finish for classified finishes only. Pit-lane start (grid 0) → treat as back of grid, documented. |
| Points across seasons | Points systems changed (fastest-lap bonus years, sprint formats). For **cross-season** charts, re-score every GP with one fixed system (25-18-15-12-10-8-6-4-2-1, no bonuses) and say so. For **within-season** charts, use official points. |
| Clean laps | Exclude lap 1, in/out laps, laps under SC/VSC/red flag (track status), laps FastF1 marks inaccurate, and deleted laps. Flag wet races (intermediate/wet compounds) and analyse them separately. |
| Race pace | Median of clean laps; compare as % delta to a reference so circuits of different length are comparable. |
| Qualifying gap to teammate | Use the last session both drivers set a time in (Q3 if both reached it, else Q2, else Q1); express as % of the faster time. Skip sessions where either had no time; show n. |
| Telemetry comparison | Align by **distance**, not time: interpolate both laps onto a common distance grid. |
| Small samples | Per-circuit stats need ≥ 3 races; per-teammate stats show n. |

Write these as small, pure, tested functions in `src/stats.py`.

### 4.5 Coverage audit — CHECKPOINT 1
`notebooks/01_data_audit.ipynb`:
- Starts, wins, podiums, poles, points per season and career from our data vs official figures in
  `data/reference/official_totals.csv` (source URL + "as of" date; I can supply them if you can't fetch them).
- Which races have FastF1 lap/telemetry data and which don't; list failures.
- The latest race in the data = the **data cut-off**, shown on the case-study page.

### 4.6 Processed tables (`data/processed/`, parquet; commit if < 25 MB total)
- `results.parquet` — every GP and sprint he entered: season, round, date, circuit, team, grid, finish, status category,
  official points, rescored points, teammate id, teammate finish.
- `qualifying.parquet` — his and his teammate's times per session; derived % gap.
- `standings.parquet` — driver standings after every round of every season he raced (all drivers — needed for rivals).
- `laps_2018plus.parquet` — clean-lap table for him and the field (needed for pace deltas), with compound, stint, track status.
- `career_greats.parquet` — race-by-race wins for a small set of all-time greats (for C10), from Jolpica.
- `output/facts.json` — every headline number used in any text.

Telemetry/position data for C05–C06 is extracted per chosen lap only, downsampled, and saved to `data/processed/telemetry/`.

### 4.7 Reference files (`data/reference/`, hand-curated, each with source + date)
- `status_map.csv`, `official_totals.csv`, `signature_races.csv` (I choose from candidates),
  `eras.csv` (car-number eras and team spells — verified against data).

---

## 5. The story

**Title:** *33 → 1 → 3 — Max Verstappen's Formula 1 Career in Data.*
His car number tells the arc: #33 (the rise), #1 (the reign as champion), #3 (the 2026 reset under new regulations,
where Red Bull has struggled). Verify all era boundaries from data.

**Chapters:**
1. The whole career at a glance
2. #33 — The rise: teenage debut, early teammates, comeback drives
3. The title fights: every season's championship race, round by round
4. #1 — The reign: how dominant was dominant?
5. Anatomy of a signature race
6. Among the greats
7. #3 — The reset: 2026 so far (living chapter, updated by `make refresh`)

**Titles are findings, written only after the data confirms them.** If the data contradicts a popular narrative,
say so. Draft chart titles at CHECKPOINT 2.

---

## 6. Chart catalogue

Each chart module lives in `src/charts/cXX_<name>.py`, exposes `build(tables) -> go.Figure`, and has a docstring
stating: the question, chart type, encodings, interactivity, caveats.

### Tier 1 — must ship (9)

**C01 · Every race (hero).** Interactive timeline of every GP: x = race (chronological), y = finishing position
(P1 at top), DNFs as a separate marker band at the bottom; wins in the accent color, everything else muted;
background bands for the 33 / 1 / 3 eras and team spells. Hover: race, grid → finish, status, points.
**Poster edition ("career stripes")**: one thin vertical stripe per GP, color = finishing position (sequential scale,
DNF distinct), era labels underneath — matplotlib, 300 dpi.

**C02 · Every title race.** Small multiples, one panel per season: cumulative official points by round for him
(accent) and the top rivals (gray, direct-labelled). Highlight the seasons where the title was decided late.

**C03 · The teammate gap.** Qualifying % gap to teammate for every race, 2015–now, points colored/labelled by teammate
spell, rolling median line, zero reference. Show n per teammate.

**C04 · Grid to flag.** Positions gained (grid → finish) for every classified GP: a grid × finish 2D heatmap or a
dumbbell/strip of gains; label his biggest comeback drives (determined from data).

**C05 · Circuits in color (2018+).** Track maps from car position data for his fastest race or qualifying lap at 4–6
circuits, line colored by speed (or gear), small multiples with identical styling. Rotate each map to the circuit's
conventional orientation (FastF1 circuit info has rotation).

**C06 · Telemetry duel (2018+).** One key qualifying lap vs a rival's: speed trace aligned by distance + a delta-time
panel below, corner numbers marked, the sections where the lap was won/lost annotated. I pick the session from candidates.

**C07 · The dominance index (2018+).** Per race: his median clean-lap pace as % delta to the best other driver
(negative = faster than everyone); points + rolling line across 2018–2026 with bootstrap CIs (resample laps **within**
race, report per-race CI); wet races marked. This is the core "how dominant was the reign" chart.

**C08 · Anatomy of a signature race.** Position-by-lap chart (all drivers gray, him in accent) + his stint bar
underneath (compound colors) + SC/VSC periods shaded + pit stops marked. Candidates (confirm data availability, I pick):
the 2021 Abu Dhabi finale, the 2024 São Paulo wet win, the 2016 Spanish GP (first win; results/laps only, no stints).

**C09 · The reset (closing chapter).** 2026 vs 2022–2025: finishing positions, qualifying gap to teammate, and pace delta
to the fastest car, side by side (small multiples or dot plot). Include the within-2026 trend. Honest conclusion,
clearly dated with the data cut-off.

### Tier 2 — should ship (pick at least 4 after EDA)

- **C10 · Among the greats.** Cumulative GP wins vs GP starts for him and a few all-time greats (e.g. Hamilton,
  Schumacher, Vettel, Senna, Prost), direct end-labels. Pure Jolpica data.
- **C11 · Season fingerprints.** Season × metric heatmap (win %, podium %, average finish, DNF %, fastest-qualifier %).
- **C12 · Where he wins.** World dot map at circuit lat/long (from Jolpica): size = races, color = wins or average finish.
- **C13 · How the races ended.** DNF anatomy by season (mechanical vs incident vs other) — stacked bars or waffle.
- **C14 · Lap-one gains.** Positions gained or lost on lap 1 by season (from lap-position data).

### Tier 3 — stretch (only after everything above is live)
- S1 Animated race replay (Plotly frames) of the signature race's running order.
- S2 Wet vs dry performance comparison.
- S3 Red Bull pit-stop durations over time (Jolpica pit stops).
- S4 Scrollytelling for chapter 1 (sticky chart + steps, e.g. Scrollama).

---

## 7. Visual design system

- **Match my website.** First read the site's CSS: fonts, colors, background, accent, light/dark handling.
  Build `src/theme.py` with a registered Plotly template `sarvesh` and a matplotlib style derived from the same tokens.
  Show me a swatch sheet at CHECKPOINT 2. The default Plotly look must not be recognisable anywhere.
- **Highlight + gray:** Max in one accent color everywhere; rivals and the field in grays, direct-labelled.
  Don't use FastF1's default team colors except where team identity is the point.
- **Tyre compounds** use the standard convention (soft red, medium yellow, hard white/light gray, inter green, wet blue),
  with an outline so "hard" is visible on a light background.
- Era bands (33 / 1 / 3) use the same subtle tints in every chart that shows time.
- Every chart: declarative **title** (the finding), **subtitle** (what's shown / how to read), **source line**
  bottom-left: "Data: FastF1 · Jolpica-F1 · Analysis: Sarvesh Kant".
- Direct labels over legends; few, purposeful annotations.
- Avoid: pie/donut, 3D, dual y-axes, rainbow scales (speed maps use a perceptually uniform scale), raw column names in hovers.
- Lap times formatted `m:ss.sss`; gaps as `+0.123 s` or `0.21 %`.
- Custom `hovertemplate` on every trace.
- **Mobile:** readable at 380 px width; small multiples reflow to fewer columns; fewer annotations on small screens.
- **Accessibility:** each chart has an `aria-label` and a one-sentence takeaway in its caption; meaning never carried
  by color alone.

---

## 8. Repo structure

```
verstappen-in-data/
├── CLAUDE.md
├── PROJECT.md
├── README.md
├── LICENSE                     # MIT for code
├── requirements.txt
├── Makefile                    # make data / make charts / make site SITE=<path> / make test / make refresh / make all
├── data/
│   ├── cache/                  # FastF1 + Jolpica cache — gitignored
│   ├── processed/              # parquet + telemetry/
│   └── reference/              # hand-curated CSVs with sources
├── src/
│   ├── config.py               # IDs, eras, thresholds, paths, points system for rescoring
│   ├── download.py
│   ├── results.py              # Jolpica → results/qualifying/standings tables
│   ├── laps.py                 # FastF1 → clean-lap table (2018+)
│   ├── telemetry.py            # per-lap extraction, distance alignment, downsampling
│   ├── stats.py                # stat rules (section 4.4)
│   ├── features.py             # derived metrics + facts.json
│   ├── theme.py                # plotly template + mpl style
│   ├── charts/
│   │   ├── __init__.py         # registry: id → module
│   │   └── c01_every_race.py … c14_lap_one.py
│   ├── poster.py               # matplotlib career-stripes poster
│   └── build_charts.py         # renders all charts → output/
├── scripts/
│   └── export_to_site.py       # copies JSON/PNG into the website repo
├── notebooks/
│   ├── 01_data_audit.ipynb
│   ├── 02_eda.ipynb
│   └── 03_chart_gallery.ipynb
├── tests/
│   └── test_stats.py
└── output/
    ├── facts.json
    ├── web/                    # cXX.json (fig.to_json)
    └── static/                 # cXX.png @2x, poster_career_stripes.png
```

Exports: web JSON contains aggregated or downsampled data only and stays small (telemetry ≤ ~1,000 points per trace);
static PNGs at scale 2.

---

## 9. Website integration

### 9.1 Access and safety
- The website is a separate local repo. Ask me for its path; I'll add it with `/add-dir <path>`.
- Before editing, read: `index.html`, one blog post (`blog/neural-network-from-scratch.html` is the best template for a
  long-form page), all CSS, and deploy config (Netlify / Vercel / GitHub Pages — find out which).
- Work on a new branch `projects-section`. Never break existing pages. Confirm with me before deploying.

**Current site (Sept 2026):** nav = home, about, blog, photos, cv. Homepage sections: "01 // PORTFOLIO",
"02 // writing", "03 // moments". Terminal-style branding ("> sarvesh kant"). No projects section yet.

### 9.2 `projects.html` — the hub
- Add **projects** to the nav on every page (between about and blog).
- Card grid; each card: thumbnail, title, one-line pitch, tech tags, one headline result, links
  `[Case study] [GitHub] [Live demo]` (only those that exist).
- Projects:
  - **33 → 1 → 3** (this project) → case-study page. Tags: data visualization, storytelling.
  - **F1 Race Predictor** (FastF1 + ML, Streamlit app). Tags: machine learning, prediction.
  - **Adaptive Traffic Signal** (tabular Q-learning in SUMO).
  - **Neural Network from Scratch** → link the existing blog post.
- The two F1 cards must read as clearly different projects (story vs prediction).
- Ask me for repo URLs, Streamlit URL, screenshots/GIFs and headline results for the other projects.
  Do not make up any metric.

### 9.3 Homepage
Add a projects section with 3 featured cards. I lean toward placing it right after the intro (renumbering
"// writing" and "// moments"). Show me before committing.

### 9.4 Case-study page `projects/verstappen-in-data.html`
- Same layout, typography and tone as the blog posts.
- Structure: hero (title, subtitle, C01) → TL;DR with 3 findings → chapters (prose + charts) → methodology
  (sources, coverage, 2018+ telemetry limit, stat definitions, rescoring, caveats) → **data cut-off line** →
  links (GitHub, poster PNG) → credits + "unofficial, not associated with Formula 1" disclaimer.
- Prose: first person, concise. Mark every paragraph you draft with `<!-- DRAFT -->` — I will rewrite in my own voice.
  All numbers from `facts.json`.
- Charts: load plotly.js once (pinned version, `defer`). Each chart:
  ```html
  <figure>
    <div class="chart" data-src="/projects/verstappen-in-data/charts/c01.json" aria-label="..."></div>
    <figcaption>One-sentence takeaway.</figcaption>
    <noscript><img src="/projects/verstappen-in-data/charts/c01.png" alt="..."></noscript>
  </figure>
  ```
  A small script lazy-loads each JSON with `IntersectionObserver` and calls
  `Plotly.newPlot(el, fig.data, fig.layout, {responsive: true, displayModeBar: false})`.
  If the site has a theme toggle, re-style charts on theme change.
- `scripts/export_to_site.py <site_path>` copies JSON + PNG into the site; `make refresh` re-runs it.
- `<title>`, meta description, Open Graph + Twitter card tags using the poster PNG (good LinkedIn previews).

### 9.5 Streamlit policy (other projects)
Streamlit Community Cloud apps go to sleep after about 12 hours without visitors and show a wake-up screen.
So a Streamlit link is **never** the only way to see a project:
- **F1 Predictor:** project page shows screenshots/GIF and results; Streamlit button labelled
  "Live app (may take ~30 s to wake up)".
- **Traffic RL:** no Streamlit. Show a GIF/MP4 of SUMO fixed-timing vs RL-controlled, the training reward curve, and a
  waiting-time comparison chart built with the same Plotly theme.
- **Neural Net (stretch):** run "Draw a Digit" live in the browser — export the 784→128→10 weights to JSON and
  implement the forward pass in JavaScript. No server needed.

### 9.6 QA before deploy
Local server (`python3 -m http.server` in site root): every page and nav link works; no console errors; charts
lazy-load; readable at 380 px; Lighthouse performance ≥ 85 on the case study; OG preview checked.

---

## 10. GitHub

- `git init` at start; `.gitignore`: `.venv/`, `data/cache/`, `.ipynb_checkpoints/`, `.DS_Store`, `__pycache__/`.
- Create the remote with `gh repo create sarveshkant2003-afk/verstappen-in-data --public` if `gh` is installed and
  authenticated; otherwise give me exact steps.
- Commit per milestone with prefixes (`data:`, `feat:`, `chart:`, `fix:`, `docs:`, `site:`).
- README: poster image, one-paragraph pitch, **link to the live case study**, gallery (2-column table of 6 charts),
  key findings, methodology summary, data cut-off, reproduce steps (`make all`), structure, data attribution,
  unofficial-data disclaimer, license, author links.
- Repo description + topics: `data-visualization`, `plotly`, `formula1`, `fastf1`, `sports-analytics`, `python`,
  `data-storytelling`.
- Keep notebooks light (clear huge outputs).

---

## 11. PROJECT.md — teaching file (high effort)

Same pattern as my F1 predictor. This is how I learn the project well enough to defend it in interviews. Required sections:

1. Overview and the story in plain words.
2. Data: what Jolpica gives vs what FastF1 live timing gives, with one real example of each; why telemetry starts in 2018.
3. Every stat rule from 4.4 with the *why* and the edge cases (sprints, pit-lane starts, status mapping, points rescoring).
4. Statistics: clean-lap filtering, medians vs means, % normalisation across circuits, bootstrap CIs, distance
   alignment and interpolation, minimum-sample thresholds, and why teammate comparison is the standard way to
   separate driver from car (and its limits).
5. **Every function in `src/`**: embedded code with line-by-line explanation.
6. **Every chart**: question → why this chart type → encodings → alternatives rejected → what it shows →
   caveats → "how to read this".
7. Design system decisions (color, type, annotation, decluttering) with before/after examples.
8. Website integration: JSON export, lazy loading, `make refresh`, why a static page instead of Streamlit.
9. Interview prep: a 60-second pitch; 25+ likely questions with model answers (stats, design, engineering,
   "how is this different from your predictor", "what next"); limitations I should admit upfront.
10. Glossary of F1 terms for interviewers who don't follow F1.

Keep PROJECT.md updated as you build; do a final careful pass at the end.

---

## 12. Phases and checkpoints

| Phase | Work | Stop at |
|---|---|---|
| 0 · Setup | Plan mode: read this file, check Python/venv/gh, propose plan | Plan approved |
| 1 · Data | cache → results/qualifying/standings (Jolpica) → clean laps (FastF1, 2018+) → stats → tests | **CHECKPOINT 1:** coverage audit |
| 2 · EDA | `02_eda.ipynb`: quick, ugly charts for every story question; list which narratives hold | **CHECKPOINT 2:** story, draft titles, theme swatches |
| 3 · Tier 1 charts | C01 + poster first (sets the visual language) → iterate → C02–C09 | **CHECKPOINT 3:** C01 · **CHECKPOINT 4:** all Tier 1 |
| 4 · Website | hub, homepage section, case study with Tier 1 | **CHECKPOINT 5:** local review → deploy |
| 5 · Polish | Tier 2 charts, README, PROJECT.md complete, `make refresh` tested | **CHECKPOINT 6** |
| 6 · Stretch | Tier 3 (optional) | — |
| 7 · Final | QA, interview-prep review, optional blog-post outline (I write the post) | Done |

After Phase 4 the project is shippable — I'll send the link to the interviewer then, and keep polishing.

**Required tests (`tests/test_stats.py`), using tiny hand-made data:**
sprint results excluded from GP counts · status strings map to the right category · positions gained skip
non-classified finishes · pit-lane start handled · rescoring gives 25 for P1 and 0 for P11 · qualifying gap uses the last
common session · clean-lap filter drops lap 1, pit laps and SC laps · distance interpolation returns a common grid.
**Sanity check:** reproduce a few known results from the data (e.g. his first win's grid and finish) and investigate any mismatch.

---

## 13. Rules

- Don't fabricate anything. If data is missing, say so.
- Don't scrape websites; use FastF1 + Jolpica with caching.
- Don't ship default Plotly or default FastF1 plotting styles.
- Small, typed, documented functions; clarity over cleverness.
- Use plan mode for each phase; stop at checkpoints.
- Tell me when a chart isn't working and propose a better form rather than polishing a weak idea.

## 14. Definition of done

- [ ] Coverage audit documented; 2018+ telemetry limit and data cut-off stated in README and case study
- [ ] All stat tests pass; sanity checks match
- [ ] Tier 1 (C01–C09) + at least 4 Tier 2 charts, all on the custom theme, readable at 380 px
- [ ] Career-stripes poster exported
- [ ] Case-study page live on sarveshkantonline.com; projects hub + homepage section live; nav updated site-wide
- [ ] The two F1 projects clearly distinguished on the site
- [ ] Other projects presented without depending on a Streamlit app being awake
- [ ] `make refresh` updates data and charts after a new race
- [ ] README with gallery and live link; repo topics set; history of meaningful commits
- [ ] PROJECT.md complete with per-function explanations, per-chart rationale and interview Q&A
- [ ] Every number in any text traceable to `facts.json`
