"""Cached, rate-limited access to the Jolpica-F1 API (Ergast-compatible).

Every HTTP response is stored as JSON under data/cache/jolpica/, so re-running
the pipeline makes zero network calls unless `refresh_season` asks for fresh
data for the live season. Run as a script to fetch everything the project uses:

    python -m src.download            # use cache where possible
    python -m src.download --refresh  # re-fetch the current season
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src import config

_last_call = 0.0


def _cache_path(path: str, offset: int) -> Path:
    key = f"{path.strip('/')}__{offset}"
    safe = key.replace("/", "_")
    if len(safe) > 120:  # keep filenames short but unique
        safe = safe[:80] + hashlib.sha1(key.encode()).hexdigest()[:12]
    return config.JOLPICA_CACHE / f"{safe}.json"


def _get(url: str, params: dict[str, Any], retries: int = 6) -> dict:
    """GET with a minimum interval between calls and exponential backoff on 429/5xx."""
    global _last_call
    for attempt in range(retries):
        wait = config.JOLPICA_MIN_INTERVAL_S - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429 or resp.status_code >= 500:
            backoff = int(resp.headers.get("Retry-After", 0)) or 2 ** (attempt + 1)
            print(f"  HTTP {resp.status_code} on {url} — backing off {backoff}s")
            time.sleep(backoff)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"Gave up on {url} after {retries} attempts")


def fetch(path: str, refresh: bool = False) -> list[dict]:
    """Return every page of `MRData` for an endpoint like '2021/results'.

    Pages are cached individually. `refresh=True` ignores the cache (used for the
    live season). Tables that span pages (e.g. one race's results split across
    two pages) are merged by the parsers in src/results.py, not here.
    """
    config.JOLPICA_CACHE.mkdir(parents=True, exist_ok=True)
    url = f"{config.JOLPICA_BASE}/{path.strip('/')}/"
    pages: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        cp = _cache_path(path, offset)
        if cp.exists() and not refresh:
            mr = json.loads(cp.read_text())
        else:
            mr = _get(url, {"limit": config.JOLPICA_PAGE_LIMIT, "offset": offset})["MRData"]
            cp.write_text(json.dumps(mr))
        pages.append(mr)
        total = int(mr["total"])
        offset += int(mr["limit"])
    return pages


def current_season() -> int:
    return datetime.now(timezone.utc).year


def seasons() -> list[int]:
    return list(range(config.FIRST_SEASON, current_season() + 1))


def fetch_all(refresh_current: bool = False) -> dict[str, Any]:
    """Fetch every endpoint the project needs; return a manifest dict."""
    fetched: list[str] = []
    now = current_season()

    def get(path: str, season: int | None = None) -> list[dict]:
        fetched.append(path)
        return fetch(path, refresh=refresh_current and season == now)

    get(f"drivers/{config.DRIVER_ID}")
    for s in seasons():
        print(f"season {s}")
        get(f"{s}/races", s)
        get(f"{s}/results", s)
        get(f"{s}/qualifying", s)
        if s >= 2021:
            get(f"{s}/sprint", s)
        # Round-by-round standings are rebuilt from race + sprint points in
        # src/results.py; the official end-of-season (or latest) table is fetched
        # once per season to verify that reconstruction.
        get(f"{s}/driverStandings", s)
    for d in config.GREATS:
        print(f"greats: {d}")
        # Greats' careers are closed except Max/Hamilton; refresh those with the live season.
        fetched.append(f"drivers/{d}/results")
        fetch(f"drivers/{d}/results", refresh=refresh_current and d in ("max_verstappen", "hamilton"))

    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": config.JOLPICA_BASE,
        "endpoints": len(fetched),
        "seasons": seasons(),
    }
    config.MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-fetch the current season")
    args = ap.parse_args()
    print(json.dumps(fetch_all(refresh_current=args.refresh), indent=2))
