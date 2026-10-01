"""Pop, measured: the sources beyond the kworb chart collection (series design §2 and §4).

  wiki      the Wikipedia article of every tour listed in artists.json (rendered HTML and wikitext, revision id)
  worldbank GDP per capita, current US dollars (NY.GDP.PCAP.CD), every country, 2016–2025
  songs     the kworb.net artist songs page of every artist (Q4)

Raw files go to tools/data/pop/raw/; run `collect.py` first for the chart pages. Requests are slow on purpose.

    python3 tools/pop/collect_extra.py wiki worldbank songs
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "pop" / "raw"
ARTISTS = json.loads(Path(__file__).with_name("artists.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "bsandova.com research (contact via bsandova.com)"}


def get(url: str, pause: float) -> bytes:
    for wait in (0, 60, 180, 300):
        time.sleep(wait)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            time.sleep(pause)
            return data
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
    raise RuntimeError(f"gave up: {url}")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def wiki() -> None:
    for a in ARTISTS.values():
        for name in a["tours"]:
            path = RAW / "wiki" / f"{slug(name)}.json"
            if path.exists():
                continue
            q = urllib.parse.urlencode({"action": "parse", "page": name, "prop": "text|wikitext|revid", "format": "json",
                                        "redirects": 1})
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(get(f"https://en.wikipedia.org/w/api.php?{q}", 10))
            print("wiki", name, "missing" if "error" in json.loads(path.read_text()) else "ok", flush=True)


def worldbank() -> None:
    path = RAW / "worldbank-gdppc.json"
    if not path.exists():
        url = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?date=2016:2025&format=json&per_page=20000"
        path.write_bytes(get(url, 2))
    print("worldbank", len(json.loads(path.read_text())[1]), "rows")


def songs() -> None:
    for key, a in ARTISTS.items():
        path = RAW / "songs" / f"{key}.html"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(f"https://kworb.net/spotify/artist/{a['spotify']}_songs.html", 3))
        print("songs", key, flush=True)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for step in sys.argv[1:]:
        {"wiki": wiki, "worldbank": worldbank, "songs": songs}[step]()
