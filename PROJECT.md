# PROJECT.md — learning "33 → 1 → 3" well enough to defend it

> This is the teaching file for the project. It explains *what* was built, *why* each decision was taken, and
> *how* to answer the questions an interviewer is likely to ask. It is written as the project is built.
> Sections marked **(coming in Phase N)** are filled in when that phase happens.
>
> Status: **Phase 1 complete (data + stats + audit)** · data cut-off: 2026 Azerbaijan Grand Prix.

---

## 1 · Overview — the story in plain words

Max Verstappen's car number tells the arc of his career:

| Number | Seasons | What it stands for |
|---|---|---|
| **#33** | 2015–2021 | The rise: debut with Toro Rosso, promotion to Red Bull, first win, first title. |
| **#1**  | 2022–2025 | The reign: the reigning champion may carry #1, and he did for four seasons. |
| **#3**  | 2026 | The reset: new regulations, and he gives up #1 after finishing 2nd in 2025. |

All three eras were **verified from the data**, not typed in from memory. `src/results.verify_config()` compares
the car numbers in `config.NUMBER_ERAS` with the numbers in Jolpica's results and stops the pipeline if they disagree.

The project is an **editorial data story**: prose and charts read top to bottom, like a long-form article. It is
deliberately *not* a dashboard. A dashboard lets the reader ask questions. A story answers specific questions,
and every chart title states a finding.

**How this differs from my F1 Race Predictor.** The predictor is machine learning and looks *forward*: given
qualifying and form, who will win on Sunday? This project is descriptive and looks *back*: what did one career
actually look like, and how do we show it honestly? They share domain knowledge (FastF1, F1 rules), but no code,
no models and no repo.

---

## 2 · Data — two sources, two very different things

### 2.1 Jolpica-F1 (the results record)

Jolpica is the community-run successor to the old **Ergast** API, and it uses the same URL scheme and JSON format.
It is a *results database*: who started where, who finished where, points, status, qualifying times, standings.
It covers every season back to 1950, which is why it can give us his 2015 debut and all of Senna's and Prost's careers.

A real example: his first win, `GET https://api.jolpi.ca/ergast/f1/2016/results/` → round 5:

```json
{
  "number": "33", "position": "1", "positionText": "1", "points": "25",
  "Driver": {"driverId": "max_verstappen", "code": "VER", ...},
  "Constructor": {"constructorId": "red_bull", "name": "Red Bull"},
  "grid": "4", "laps": "66", "status": "Finished",
  "Time": {"millis": "6100017", "time": "1:41:40.017"}
}
```

Things to notice (interviewers like these):
* **Everything is a string**, including numbers. The parser converts types explicitly.
* `position` and `positionText` are different fields. `position` is always a number, even for a retirement: every
  car gets an ordered position. `positionText` is `"R"`, `"D"`, `"W"`… when the driver was **not classified**.
  "Classified" therefore comes from `positionText`, never from `position`.
* `Time.millis` is the total race time, and only for finishers on the lead lap. We use it for win margins.

### 2.2 FastF1 live timing (the telemetry record)

FastF1 is a Python library that reads Formula 1's own **live-timing feed**, the data that drives the official timing
screens. That gives much richer data: every lap for every driver, tyre compound and stint, track status (safety car,
red flag), and car telemetry (speed, throttle, brake, gear, DRS, x/y position on track).

A real example: four of his laps from the 2021 Abu Dhabi GP (`laps.load_session(2021, 22)`):

| Lap | LapTime | Stint | Compound | TyreLife | PitIn | TrackStatus | Position | IsAccurate |
|---|---|---|---|---|---|---|---|---|
| 2  | 1:29.103 | 1 | SOFT | 5  | —          | `1`   | 2 | True  |
| 36 | 1:43.598 | 2 | HARD | 23 | 1:56:06.9 | `16`  | 2 | False |
| 53 | 1:42.072 | 3 | HARD | 17 | 2:21:37.6 | `124` | 2 | False |
| 58 | 1:26.618 | 4 | SOFT | 8  | —          | `1`   | 1 | True  |

`TrackStatus` is a **string of codes** for every status seen during the lap: `1` green, `2` yellow, `4` safety car,
`5` red flag, `6` VSC deployed, `7` VSC ending. So `"124"` means "green, then yellow, then safety car" during
lap 53, and lap 36's `"16"` includes a VSC. Both are also in-laps (a PitInTime is set). The clean-lap filter drops
them for both reasons.

### 2.3 Why telemetry starts in 2018

FastF1 can only read what the live-timing archive still serves, and the archive with laps, stints and telemetry is
reliable only **from the 2018 season onwards**. So:
* **2015–2017:** results, grid, status, qualifying and standings (Jolpica), but no stints and no telemetry.
* **2018 →:** everything.

The case study says this plainly in its methodology section, and every telemetry chart (C05, C06, C08) is limited to 2018+.

### 2.4 The light-scope decision

The original plan downloaded laps for *every driver in every race since 2018* to compute race-pace deltas. I chose
**not** to: the project is about clear, strong visuals, and every chart can be built from cheaper data:

| Chart | Original data | What we use instead | Trade-off to admit |
|---|---|---|---|
| C07 dominance | clean-lap pace vs best rival, 2018+ | **winning margin**: gap to P2 as % of race time, 2015+ | Margin is shaped by strategy and safety cars and says nothing about races he didn't win. It covers more years, though, and anyone can understand it. |
| C09 reset | race-pace delta to fastest car | **qualifying gap to the fastest qualifier, %** | One-lap pace is not race pace, but it is clean: same track, same session, same conditions. |

What I learned while measuring: one race loads in about **8 seconds** without telemetry. The full-field download is
cheap (~25 minutes), so it is a possible upgrade, not a hard limit.

### 2.5 Caching and rate limits (engineering)

Jolpica allows a few requests a second and a few hundred an hour. `src/download.py`:
1. Caches **every page** of every response as a JSON file (`data/cache/jolpica/`). A second run makes **zero**
   network calls.
2. Waits at least 0.3 s between calls, and **backs off exponentially on HTTP 429** ("too many requests"), using
   the server's `Retry-After` header if present. The first full run hit 429s on the last endpoints and recovered
   on its own.
3. Writes `data/cache/MANIFEST.json` (when data was fetched, what, and which seasons).
4. `--refresh` re-fetches **only the live season**. Closed seasons never change, so `make refresh` stays cheap.

A design choice to defend: round-by-round standings are **rebuilt** from race + sprint points (one request per season
instead of one per round, about 250 fewer requests), then **verified** against the official final standings. See §4.3.

---

## 3 · Every stat rule, and why

These live in `src/stats.py` as small pure functions: no I/O, and each one is tested with hand-made data in `tests/test_stats.py`.

### 3.1 Race = Grand Prix only
Sprints (since 2021) are short Saturday races worth fewer points. Counting a sprint win as a "win" would inflate
the record and disagree with every official source. Sprints are stored in the same table with `session = "sprint"`,
and `gp_counts()` filters to `session == "gp"` before counting. **Test:** a frame with a sprint win and a GP win
returns `wins == 1`.

### 3.2 Starts
A start is any GP entry that isn't a DNS (did not start). His 2015–2026 count reproduces the official figure (§4.1).

### 3.3 Win and podium
Finishing position 1, or ≤ 3, **by `positionText`**, so an unclassified car can never count as a podium.

### 3.4 Pole vs fastest qualifier — the trap
"Pole position" sounds simple and isn't:
* **Fastest qualifier** = P1 in the qualifying session. Unambiguous, and in the data.
* **Grid P1** = who actually starts first. It differs whenever a **grid penalty** (e.g. an engine change) moves the fastest
  qualifier back, or a lap time is **deleted** after the session.
* **2021 sprint weekends** gave pole to the *sprint winner*.
* Record-keepers disagree on whether a penalised fastest qualifier keeps the pole in the record books.

Our data has **51** fastest-qualifier results; the official record (Wikipedia infobox) says **48** poles. The audit
lists the seven races responsible: five where he was fastest but didn't start first, and two 2021 sprint weekends
where he started first without being fastest. Which of them the official count credits isn't in our data, so
**the case study uses "fastest qualifier" and defines it**, instead of printing a pole number we can't source.
*Interview answer:* "I found that the obvious definition of pole disagrees with the official count by three,
traced the difference to seven specific races, and picked a metric I could define exactly."

### 3.5 Finish status → categories
Jolpica records 63 distinct `status` strings for 2015–2026 ("Engine", "Collision damage", "+2 Laps", …).
`data/reference/status_map.csv` maps each to one of:
`Finished · Lapped · DNF-mechanical · DNF-incident · DNF-other · DNF-unknown · DSQ · DNS`.
* `map_status()` **raises** on any string not in the map, so a new status string after a future race can't slip through silently.
* **Finding:** from 2024, Jolpica reports every retirement as a generic **"Retired"** with no cause. Those become
  `DNF-unknown`. The DNF chart (C13) must show "cause not recorded" for 2024+, not guess.
* A few strings are genuinely ambiguous (Puncture, Tyre, Front wing, Undertray, Out of fuel) and are marked
  `REVIEW` in the file. The mapping is a judgment call, documented, not hidden.
* Status and classification are **independent**. A driver can retire and still be classified (e.g. `Transmission`
  with `positionText = "17"`, because he completed enough laps). We keep both columns.

### 3.6 Positions gained
`grid − finish`, **for classified finishes only**. A DNF is not "lost 15 places", it's a missing value.
A **pit-lane start is recorded as grid 0**. Taken literally, that would be "0 − 6 = −6 places" for a driver who
climbed from the back to P6. `effective_grid()` maps grid 0 to the back of the field (field size), so the same drive
correctly scores +14 in a 20-car field. **Tests:** both cases.

### 3.7 Points across seasons (rescoring)
F1's points systems changed during his career: fastest-lap bonus points in some seasons, sprint points (2021+), and a
half-points race. Comparing raw points across seasons would mix these systems. So:
* **Within a season** (the title fights, C02): official points, because that's what decided the championship.
* **Across seasons**: every GP re-scored with one fixed system, 25-18-15-12-10-8-6-4-2-1, no bonuses (`rescore()`).
**Test:** P1 → 25, P10 → 1, P11 → 0, unclassified P1 → 0.

### 3.8 Qualifying gap to teammate
Qualifying has three knockout sessions (Q1 → Q2 → Q3), and track conditions change between them. Comparing my
Q3 time with a teammate's Q1 time would compare different track conditions. `last_common_session()` picks the **latest session in which
both drivers set a time**; `quali_gap_pct()` expresses the gap **as a percentage of the faster time**, so a 0.2 s gap
at an 80-second lap and at a 100-second lap become comparable. Races where either had no time are skipped, and n is shown.

### 3.9 Win margin (C07)
Gap to P2 in seconds as a % of his race time. `gap_seconds()` returns NaN when the two cars are on different laps,
because then there is no time gap. For all 71 of his wins, P2 was on the lead lap, so all 71 are measurable.

### 3.10 Clean laps (FastF1 charts only)
`clean_laps()` keeps only representative green-flag laps and drops: lap 1 (standing start), in-laps and out-laps
(pit stops), any lap whose track status includes SC/red/VSC (`4`,`5`,`6`,`7`; yellow `2` is kept, because it's usually local),
laps FastF1 flags inaccurate, and deleted laps. **Test:** a six-lap frame keeps exactly laps 2 and 6.

### 3.11 Distance alignment (telemetry)
Two laps take different times, so "speed at t = 30 s" is at different places on track for each driver. You compare
laps **by distance**: `interpolate_to_distance()` resamples each channel onto the same grid (e.g. every 5 m) with
linear interpolation, after dropping duplicate distance samples (which break interpolation). **Test:** a known
input returns the exact expected grid and values.

---

## 4 · Statistics and validation

### 4.1 The audit (CHECKPOINT 1) — reproducing the official record
`notebooks/01_data_audit.ipynb` compares our totals with an independent source (`data/reference/official_totals.csv`,
Wikipedia infobox "as of 2026 Azerbaijan GP", retrieved 2026-09-29):

| Metric | Ours | Official | |
|---|---|---|---|
| Starts | 248 | 248 | ✓ |
| Wins | 71 | 71 | ✓ |
| Podiums | 134 | 134 | ✓ |
| Career points | 3607.5 | 3607.5 | ✓ |
| Championships | 4 | 4 | ✓ |
| Poles | 51 (fastest qualifier) | 48 | explained in §3.4 |

Matching career points *to the half point* shows the sprint points, fastest-lap bonuses and half-points races
are all handled correctly, because the official total includes every one of those.

### 4.2 Sanity checks on known results
* First win: 2016 Spanish GP, grid 4 → P1, Red Bull, car #33 ✓
* Debut: 2015 Australian GP, Toro Rosso, car #33 ✓

### 4.3 Standings reconstruction
Rebuilt cumulative points match the official final standings for **all 267 driver-seasons, to 0.01 points**.
41 rank positions differ. Every one is a **tie on points**, which F1 breaks by count-back (most wins, then most
2nds…), or a driver officially unranked. None are in the top 3. C02 plots *points*, so this doesn't affect it.
*Lesson:* validate every derived table against something independent, and understand every mismatch before moving on.

### 4.4 Medians, % normalisation, bootstrap CIs
*(expanded in Phase 3 with the charts that use them)*
* `bootstrap_median_ci()`: percentile bootstrap. Resample the values with replacement 2,000 times, take the median of
  each resample, and read off the 2.5th/97.5th percentiles. Medians over means because lap times and margins are skewed
  by outliers (a slow lap behind traffic, a late safety car).

### 4.5 Why teammate comparison (and its limits)
*(coming in Phase 2/3)*

---

## 5 · Every function in `src/`

### `src/config.py`
Constants only. Paths, the Jolpica base URL, `DRIVER_ID = "max_verstappen"`, the expected number eras, the greats for
C10, and the rescoring table. The key idea is that anything about his career in here is an *expectation* that
the data checks (`verify_config`), not a fact the code trusts.

### `src/download.py`
```python
def _cache_path(path, offset) -> Path
```
One cache file per (endpoint, page offset), e.g. `2021_results__100.json`. Long keys are shortened with a hash.

```python
def _get(url, params, retries=6) -> dict
```
1. Waits until at least `JOLPICA_MIN_INTERVAL_S` has passed since the last call (a simple client-side rate limiter).
2. `200` → return JSON.
3. `429` or `5xx` → sleep `Retry-After` seconds if the server said so, else `2, 4, 8, 16…` (exponential backoff), then retry.
4. Any other error → raise immediately (a 404 won't fix itself).

```python
def fetch(path, refresh=False) -> list[dict]
```
Pagination loop. Jolpica returns at most 100 rows per page plus `total`, so we keep requesting `offset += limit`
until `offset >= total`. Each page is read from the cache if present. It returns the list of raw pages; merging is the
parser's job (see `_races`).

```python
def fetch_all(refresh_current=False) -> dict
```
The list of endpoints the project needs: per season `races`, `results`, `qualifying`, `sprint` (2021+) and final
`driverStandings`, plus the greats' careers. It writes the manifest.

### `src/results.py`
```python
def _races(path) -> list[dict]
```
**Subtle bug avoided here:** pagination is by *result row*, not by race, so one race's 20 results can be split across
two pages. This merges races by `(season, round)` and concatenates their result lists.

`_race_meta`, `_result_rows` flatten the nested JSON into one row per driver per race, converting every string to its
real type.

* `field_results()`: every driver, every GP and sprint, plus `classified` and `status_cat` columns.
* `field_qualifying()`: Q1/Q2/Q3 in seconds (NaN = no time).
* `official_final_standings()`: the independent check for the reconstruction.
* `greats_results()`: running start count and running win count per driver (C10's axes).
* `standings_by_round()`: sum points per (season, round, driver) so a sprint counts in its weekend's round,
  pivot to a season × round × driver grid, `cumsum` within each season, then rank.
* `max_results()`: his rows, plus the **teammate derived from data** (same season, round, session and constructor,
  different driver: never a hard-coded name), field size, rescored points, effective grid and positions gained.
* `teammate_quali()`: per race, last common session and % gap.
* `pole_gap()`: his time in his last session vs the fastest time **in that same session** (C09).
* `win_margins()`: joins each of his wins to the P2 finisher and computes the % margin.
* `verify_config()`: the guard described in §1.

### `src/stats.py`
Every function is explained with its rule in §3.

### `src/laps.py`
* `load_session()`: enables the FastF1 cache once, refuses pre-2018 years with a clear message, and loads **only the parts
  requested** (laps without telemetry by default, which is what makes a race load in seconds).
* `availability()`: probes a session and reports whether it has laps, clean laps, stints and compounds. It never crashes.
* `race_laps()`: the tidy per-lap table that C08 will use.

---

## 6 · Every chart
*(coming in Phase 3: question → why this form → encodings → alternatives rejected → what it shows → caveats → how to read)*

## 7 · Design system decisions
*(coming in Phase 2: derived from sarveshkantonline.com's CSS)*

## 8 · Website integration
*(coming in Phase 4)*

## 9 · Interview prep
*(built up throughout; completed in Phase 5)*

Questions already answerable from this phase:
1. **"How do you know your numbers are right?"** I reproduced the official starts, wins, podiums, titles and career
   points exactly (3607.5, to the half point), and rebuilt standings match all 267 official driver-seasons. The one
   difference, poles, I traced to seven specific races and explained.
2. **"Why not just count pole positions?"** "Pole" has conflicting definitions (grid penalties, 2021 sprint rules).
   I used a metric I can define exactly and documented the gap.
3. **"How did you handle the API?"** Page-level cache, rate limiter, exponential backoff on 429, and refresh only for the live season.
4. **"What would break when a new race is added?"** A new status string: the mapper raises on purpose.
   Car-number changes: `verify_config` raises.
5. **"Why is 2015–2017 missing from some charts?"** Live-timing data (laps, stints, telemetry) is only available from 2018.

## 10 · Glossary
*(started; completed in Phase 5)*
* **Grand Prix (GP):** the main Sunday race of a weekend.
* **Sprint:** a short Saturday race (2021+) with fewer points; not counted as a GP win.
* **Qualifying (Q1/Q2/Q3):** knockout sessions that set the starting order; slowest cars drop out after Q1 and Q2.
* **Pole position:** starting first. See §3.4 for why this is ambiguous.
* **Grid penalty:** places a driver is moved back on the grid, e.g. for exceeding the engine-part allocation.
* **Classified:** completed enough of the race distance to receive a finishing position, even if the car stopped.
* **DNF / DNS / DSQ:** did not finish / did not start / disqualified.
* **Safety car (SC) / Virtual safety car (VSC):** neutralised racing after an incident; laps under them are much slower.
* **Stint / compound:** the run between pit stops / the tyre type (soft, medium, hard; intermediate and wet for rain).
* **Teammate:** the other driver in the same team, i.e. the same car, so the fairest comparison of drivers.
