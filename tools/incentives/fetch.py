"""Download step of the investment incentives study (design §2 "Outcome", "District boundaries").

Fetches the MPSV monthly district files nezamestnanost-mesicni-MM-YYYY.json for July 2004 – December 2024 and the
code lists that place a municipality in a district: the ČSÚ lists of parts of municipalities and of
cadastral areas, the ČSÚ municipality → district (LAU 1) link valid on
31 December 2024 (districts as of 2024), the municipality → district (NUTS 4) link on both sides of 1 January 2007
(Vyhláška 513/2006) and 1 January 2016 (Brdy), the MPSV region list, the ČSÚ district list (číselník 101) and the ČSÚ
open data set 130149 (population by sex and basic age groups, 31 December 2000–2024, used only as the denominator of
Q3 under the second 26 October 2026 change log entry). Files are saved as they come and are never
opened here beyond a JSON parse check; no value is printed. One thread, a pause between requests. Writes
docs/research/incentives-mpsv-files.sha256 (file, URL, download date, sha256).

    nice -n 20 uv run --no-project python -I tools/incentives/fetch.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import CODES_DIR, CZSO_DIR, MPSV_DIR, ROOT, UA, sha256

MPSV_BASE = "https://data.mpsv.cz/od/soubory/nezamestnanost-mesicni/"
FIRST, LAST = (2004, 7), (2024, 12)
CSU_EXPORT = ("https://apl2.czso.cz/iSMS/do_cis_export?kodcis={cis}&typdat=1&cisvaz={vaz}&datpohl={day}"
              "&cisjaz=203&format=2&separator=%2C")
LAU_LINK = "109_1770"  # ČSÚ: municipality → district by LAU 1 code (the code MPSV lists as kodLau)
PART_LINK = "43_1218"  # ČSÚ: part of a municipality → municipality, for place strings that name a part
CADASTRE_LINK = "43_1176"  # ČSÚ: cadastral area → municipality
NUTS_LINK = "101_333"  # ČSÚ: municipality → district by NUTS 4 code, valid back before 2007
CODE_LISTS = {
    "obce_okres_lau_2024-12-31.csv": CSU_EXPORT.format(cis=43, vaz=LAU_LINK, day="31.12.2024"),
    "obce_okres_nuts_2006-12-31.csv": CSU_EXPORT.format(cis=43, vaz=NUTS_LINK, day="31.12.2006"),
    "obce_okres_nuts_2007-01-01.csv": CSU_EXPORT.format(cis=43, vaz=NUTS_LINK, day="01.01.2007"),
    "obce_okres_nuts_2015-12-31.csv": CSU_EXPORT.format(cis=43, vaz=NUTS_LINK, day="31.12.2015"),
    "obce_okres_nuts_2016-01-01.csv": CSU_EXPORT.format(cis=43, vaz=NUTS_LINK, day="01.01.2016"),
    "obce_okres_nuts_2024-12-31.csv": CSU_EXPORT.format(cis=43, vaz=NUTS_LINK, day="31.12.2024"),
    "casti_obce_2024-12-31.csv": CSU_EXPORT.format(cis=42, vaz=PART_LINK, day="31.12.2024"),
    "katastry_2024-12-31.csv": CSU_EXPORT.format(cis=52, vaz=CADASTRE_LINK, day="31.12.2024"),
    "mpsv_kraje.json": "https://data.mpsv.cz/od/soubory/ciselniky/kraje.json",
    "okresy_101.csv": "https://apl2.czso.cz/iSMS/do_cis_export?kodcis=101&typdat=0&cisjaz=203&format=2&separator=%2C",
}
CZSO_DOCS = "https://csu.gov.cz/docs/107508/"
# ČSÚ product page: https://csu.gov.cz/produkty/obyvatelstvo-k-3112-podle-pohlavi-v-obcich (data set 130149)
POPULATION_FILES = {
    "130149-25data052025.zip": CZSO_DOCS + "caaa6ad1-ddd1-c0df-1683-3c23ccf1f0c7/130149-25data052025.zip?version=1.0",
    "130149-25schema052025.json": CZSO_DOCS + "59a2a4da-5451-6714-8cc1-0c68742e1e12/130149-25schema052025.json?version=1.0",
    "130149-23dds.htm": CZSO_DOCS + "0abd5d4b-e556-e9cd-5bc4-c20888fa7b81/130149-23dds.htm?version=1.0",
}
HASH_FILE = ROOT / "docs/research/incentives-mpsv-files.sha256"
PAUSE_S = 1.5
RETRIES = 4
BACKOFF_S = 20


def months(first: tuple[int, int] = FIRST, last: tuple[int, int] = LAST) -> list[tuple[int, int]]:
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def mpsv_name(y: int, m: int) -> str:
    return f"nezamestnanost-mesicni-{m:02d}-{y}.json"


def get(url: str) -> tuple[bytes, str]:
    for attempt in range(RETRIES):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=120) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(BACKOFF_S * (attempt + 1))
    raise AssertionError("unreachable")


def is_json_file(body: bytes, ctype: str) -> bool:
    """The MPSV server answers a missing file with an HTML page and status 200."""
    if "json" not in ctype:
        return False
    try:
        json.loads(body)
    except ValueError:
        return False
    return True


def fetch_one(url: str, dest: Path, want_json: bool) -> str:
    if dest.exists():
        return "kept"
    body, ctype = get(url)
    if want_json and not is_json_file(body, ctype):
        return "missing"
    if not want_json and not body.strip():
        return "empty"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    time.sleep(PAUSE_S)
    return "saved"


def hash_lines(entries: list[tuple[Path, str]], dates: dict[str, str]) -> list[str]:
    lines = ["# Investment incentives study: MPSV monthly district files, code lists and ČSÚ population (Q3 only), fetched before any outcome value is read",
             "# file\turl\tdownload_date\tsha256"]
    for path, url in entries:
        if path.exists():
            lines.append(f"{path.relative_to(path.parents[1])}\t{url}\t{dates.get(path.name, '')}\t{sha256(path)}")
    return lines


def recorded_dates() -> dict[str, str]:
    if not HASH_FILE.exists():
        return {}
    out = {}
    for line in HASH_FILE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            f, _url, day, _h = line.split("\t")
            out[Path(f).name] = day
    return out


def main() -> None:
    today = dt.date.today().isoformat()
    dates = recorded_dates()
    entries, status = [], {}
    for name, url in CODE_LISTS.items():
        dest = CODES_DIR / name
        s = fetch_one(url, dest, want_json=name.endswith(".json"))
        status[name] = s
        if s == "saved" or name not in dates:
            dates[name] = today
        entries.append((dest, url))
    for name, url in POPULATION_FILES.items():
        dest = CZSO_DIR / name
        s = fetch_one(url, dest, want_json=False)
        status[name] = s
        if s == "saved" or name not in dates:
            dates[name] = today
        entries.append((dest, url))
    for y, m in months():
        name = mpsv_name(y, m)
        dest = MPSV_DIR / name
        s = fetch_one(MPSV_BASE + name, dest, want_json=True)
        status[name] = s
        if s == "saved" or name not in dates:
            dates[name] = today
        entries.append((dest, MPSV_BASE + name))
    HASH_FILE.write_text("\n".join(hash_lines(entries, dates)) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for s in status.values():
        counts[s] = counts.get(s, 0) + 1
    print("status counts:", counts)
    print("not saved:", sorted(k for k, s in status.items() if s in ("missing", "empty")))


if __name__ == "__main__":
    main()
