"""Project-wide constants: IDs, paths, seasons, points system.

Anything describing Max's career (numbers, eras) is an *expectation* that
`results.verify_config()` checks against the data; the pipeline fails loudly
if the data disagrees.
"""
from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
JOLPICA_CACHE = CACHE / "jolpica"
FASTF1_CACHE = CACHE / "fastf1"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"
OUTPUT = ROOT / "output"
WEB_OUT = OUTPUT / "web"
STATIC_OUT = OUTPUT / "static"
FACTS = OUTPUT / "facts.json"
MANIFEST = CACHE / "MANIFEST.json"

# --- Jolpica API -------------------------------------------------------------
JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
JOLPICA_PAGE_LIMIT = 100          # API maximum per page
JOLPICA_MIN_INTERVAL_S = 0.3      # stay under the 4 req/s burst limit

# --- Who ---------------------------------------------------------------------
DRIVER_ID = "max_verstappen"      # Jolpica driverId
DRIVER_CODE = "VER"               # FastF1 abbreviation
FIRST_SEASON = 2015

# Expected car-number eras (inclusive seasons). Verified against data.
NUMBER_ERAS: dict[int, tuple[int, int]] = {
    33: (2015, 2021),
    1: (2022, 2025),
    3: (2026, 2026),
}

# All-time greats for C10 (Jolpica driverIds).
GREATS = [
    "max_verstappen",
    "hamilton",
    "michael_schumacher",
    "vettel",
    "senna",
    "prost",
]

# --- Stat rules --------------------------------------------------------------
# Fixed system used to re-score every GP for cross-season comparisons.
RESCORE_POINTS: dict[int, int] = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

MIN_RACES_PER_CIRCUIT = 3
