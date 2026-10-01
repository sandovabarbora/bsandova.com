"""Download the Czech film fund's published decision tables (rozhodovací tabulky).

The State Cinematography Fund (SFK, 2013-2024, oldfondkinematografie.cz) and its successor the
State Audiovisual Fund (SFA, 2025-, sfa.gov.cz) publish one spreadsheet per call: every
application with its points per criterion and the support awarded. This script collects the
links from the pages that list them, downloads every spreadsheet whose name marks it as a
decision table, and writes a manifest with the source URL, access time and SHA-256.

Nothing here joins an outcome (release, admissions); see docs/research/film-fund-design.md.

    uv run --no-project --with requests python tools/film/collect_tables.py
"""

from __future__ import annotations

import csv
import hashlib
import re
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data" / "film" / "raw"
MANIFEST = ROOT / "tools" / "data" / "film" / "manifest.csv"
UA = {"User-Agent": "bsandova.com research (film fund study; contact via bsandova.com)"}
PAUSE_S = 1.5   # between requests: the fund's servers are small

OLD = "https://oldfondkinematografie.cz/"
LIST_PAGES = [
    OLD + "zapisy-z-jednani-rady-statniho-fondu-kinematografie.html",
    OLD + "vyroba-ceskeho-kinematografickeho-dila.html",
    OLD + "vyvoj-ceskeho-kinematografickeho-dila.html",
    "https://sfa.gov.cz/jednani/2025",
    "https://sfa.gov.cz/jednani",
]
# a decision table by its file name; the forms and budgets that sit next to them do not match
TABLE = re.compile(r"(?i)(rozhod|vysledk|výsledk)[^/]*\.xlsx?$")


def links(page: str, html: str) -> list[str]:
    out = []
    for href in re.findall(r'href="([^"]+)"', html):
        url = urllib.parse.urljoin(page, href.replace("&amp;", "&"))
        if TABLE.search(urllib.parse.unquote(urllib.parse.urlparse(url).path)):
            out.append(url)
    return out


def local_name(url: str) -> str:
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    # keep the folder (it carries the meeting date) in the file name, flattened
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.strip("/").split("files/", 1)[-1].split("data/meeting/", 1)[-1])
    return name[-180:]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update(UA)
    urls: list[str] = []
    for page in LIST_PAGES:
        r = s.get(page, timeout=60)
        r.raise_for_status()
        found = links(page, r.text)
        print(f"{page}: {len(found)} tables")
        urls += found
        time.sleep(PAUSE_S)
    urls = list(dict.fromkeys(urls))
    rows = []
    for i, url in enumerate(urls, 1):
        dest = OUT / local_name(url)
        if not dest.exists():
            r = s.get(url, timeout=120)
            if r.status_code in (403, 404) and re.search(r"[^\x00-\x7f]", url):
                # the old server stores file names decomposed (NFD); the page links them composed
                time.sleep(PAUSE_S)
                r = s.get(urllib.parse.quote(unicodedata.normalize("NFD", url), safe=":/"), timeout=120)
            if r.status_code != 200:
                print(f"  {r.status_code} {url}")
                rows.append({"file": "", "url": url, "status": r.status_code, "accessed": "", "sha256": ""})
                continue
            dest.write_bytes(r.content)
            time.sleep(PAUSE_S)
        rows.append({"file": dest.name, "url": url, "status": 200,
                     "accessed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
        if i % 50 == 0:
            print(f"  {i}/{len(urls)}")
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "status", "accessed", "sha256"])
        w.writeheader()
        w.writerows(rows)
    print(f"{sum(r['status'] == 200 for r in rows)} of {len(rows)} downloaded -> {OUT}")


if __name__ == "__main__":
    main()
