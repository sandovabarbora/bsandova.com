"""Downloads of the bypass accidents study (design §2): the Police of the Czech Republic record-level accident files
for every year published in that form, their field descriptions, RÚIAN municipality and cadastral-unit polygons
(ČÚZK), the current and historical RÚIAN exchange files (which cadastral unit belonged to which municipality when;
§2 "Municipalities", §3.3), and the OpenStreetMap geometry of the ways listed in the bypass list (Q3), from Overpass
or, when every Overpass server fails, from the main OSM API.

The archive page (archiv.policie.gov.cz/clanek/statistika-nehodovosti.aspx) has one tab per year; tabs for 2015 and
earlier hold only yearbooks and PDF summaries, no record files, so the record files start in 2016. The tabs are read
again on every run and the year list is written with the hashes, so that statement is checked, not assumed.

Writes the files under tools/data/bypass/raw/ and docs/research/bypass-files.sha256 (sha256, file, URL, date).
Nothing in an accident file is opened here.

    nice -n 20 uv run --no-project python -I tools/bypass/fetch.py
"""
from __future__ import annotations

import base64
import csv
import datetime as dt
import hashlib
import json
import re
import urllib.parse
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools/data/bypass/raw"
MANIFEST = ROOT / "docs/research/bypass-files.sha256"
UA = "bsandova.com research"
POLICE = "https://archiv.policie.gov.cz/"
TAB = POLICE + "clanek/statistika-nehodovosti.aspx?q={q}"
TABS = range(1, 21)
YEARS = range(2014, 2026)
RUIAN_SHP = "https://services.cuzk.gov.cz/shp/stat/epsg-5514/1.zip"
RUIAN_HIST = "https://vdp.cuzk.gov.cz/vymenny_format/historicka/{d}_ST_UZHZ.xml.zip"
RUIAN_NOW = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{d}_ST_UZSZ.xml.zip"
RUIAN_DATE = "20260930"
# a full-year record file is the tab's RAR/ZIP whose name has the year but no month
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter")
OSM_API = "https://api.openstreetmap.org/api/0.6/"
LIST = ROOT / "tools/bypass/bypasses.csv"
YEAR_FILE = re.compile(r"soubor/((?:data|datagis|data-gis|data-web|data-na-web)[-a-z]*?(?:rok-)?(20\d\d)-(?:rar|zip)\.aspx)")
DEC_FILE = re.compile(r"soubor/(data-web-12-(20\d\d)-(?:rar|zip)\.aspx)")
FIELDS_FILE = re.compile(r"soubor/(polozky-formulare[-a-z0-9]*-xlsx\.aspx)")


def get(url: str, retries: int = 4) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(20 * (attempt + 1))
    raise AssertionError


def tab_url(n: int) -> str:
    q = base64.b64encode(f"chnum={n}".encode()).decode().replace("=", "%3d")
    return TAB.format(q=q)


def record_files(page: str) -> dict[int, str]:
    """{year: soubor path} of the full-year record file on one tab; the 2025 tab names it by December only."""
    out = {int(y): "soubor/" + p for p, y in YEAR_FILE.findall(page)}
    for p, y in DEC_FILE.findall(page):
        if int(y) not in out and re.search(rf'soubor/{re.escape(p)}"[^>]*>\s*Data za rok {y}', page):
            out[int(y)] = "soubor/" + p
    return out


def scan() -> tuple[dict[int, str], set[str], dict[int, list[str]]]:
    """Record files and field descriptions on every tab, and the files of tabs that have no record file."""
    files, fields, without = {}, set(), {}
    for n in TABS:
        page = get(tab_url(n)).decode("utf-8", "replace")
        found = record_files(page)
        files |= found
        fields |= {"soubor/" + f for f in FIELDS_FILE.findall(page)}
        listed = sorted(set(re.findall(r'soubor/[^"]+', page)))
        if not found and listed:
            without[n] = listed
        time.sleep(1)
    return files, fields, without


def way_ids() -> list[int]:
    with LIST.open(encoding="utf-8") as f:
        return sorted({int(w) for r in csv.DictReader(f) for w in re.findall(r"\d+", r["osm_ways"] or "")})


def overpass(ids: list[int]) -> dict | None:
    query = f"[out:json][timeout:120];way(id:{','.join(map(str, ids))});out geom;"
    for url in OVERPASS:
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": query}).encode(),
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                els = json.loads(r.read())["elements"]
            return {"source": url, "ways": {str(e["id"]): {"tags": e.get("tags", {}),
                                                           "lonlat": [[g["lon"], g["lat"]] for g in e["geometry"]]}
                                            for e in els if e["type"] == "way"}}
        except (OSError, ValueError, KeyError):
            continue
    return None


def osm_api(ids: list[int], batch: int = 100) -> dict:
    """The main OSM API, when every Overpass server fails: ways by id in batches, then their nodes."""
    ways, nodes = {}, {}
    for i in range(0, len(ids), batch):
        part = json.loads(get(f"{OSM_API}ways.json?ways={','.join(map(str, ids[i:i + batch]))}"))
        ways |= {e["id"]: e for e in part["elements"]}
        time.sleep(1)
    refs = sorted({n for w in ways.values() for n in w["nodes"]})
    for i in range(0, len(refs), batch * 2):
        part = json.loads(get(f"{OSM_API}nodes.json?nodes={','.join(map(str, refs[i:i + batch * 2]))}"))
        nodes |= {e["id"]: (e["lon"], e["lat"]) for e in part["elements"] if "lon" in e}
        time.sleep(1)
    return {"source": OSM_API, "ways": {str(k): {"tags": w.get("tags", {}),
                                                 "lonlat": [list(nodes[n]) for n in w["nodes"] if n in nodes]}
                                        for k, w in ways.items()}}


def save_osm(name: str) -> tuple[str, str, str, str]:
    path = RAW / name
    if not path.exists():
        ids = way_ids()
        got = overpass(ids) or osm_api(ids)
        got["requested"] = len(ids)
        path.write_text(json.dumps(got, ensure_ascii=False))
    return sha256(path), name, json.loads(path.read_text())["source"], dt.date.today().isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save(url: str, name: str) -> tuple[str, str, str, str]:
    path = RAW / name
    if not path.exists():
        path.write_bytes(get(url))
        time.sleep(2)
    return sha256(path), name, url, dt.date.today().isoformat()


def name_for(soubor: str) -> str:
    stem = soubor.removeprefix("soubor/").removesuffix(".aspx")
    return re.sub(r"-(rar|zip|xlsx)$", r".\1", stem)


def main() -> None:
    for d in ("police", "ruian", "osm"):
        (RAW / d).mkdir(parents=True, exist_ok=True)
    files, fields, without = scan()
    years = sorted(y for y in files if y in YEARS)
    rows = [save(POLICE + files[y], f"police/{y}_{name_for(files[y])}") for y in years]
    rows += [save(POLICE + f, f"police/{name_for(f)}") for f in sorted(fields)]
    rows.append(save(RUIAN_SHP, "ruian/stat_epsg5514.zip"))
    rows.append(save(RUIAN_NOW.format(d=RUIAN_DATE), f"ruian/{RUIAN_DATE}_ST_UZSZ.xml.zip"))
    rows.append(save(RUIAN_HIST.format(d=RUIAN_DATE), f"ruian/{RUIAN_DATE}_ST_UZHZ.xml.zip"))
    rows.append(save_osm("osm/ways.json"))
    head = ["# Bypass accidents study: raw files (sha256, file under tools/data/bypass/raw/, URL, download date)",
            f"# Police record-level files found for years {years}; first year in that form: {years[0]}",
            "# Archive tabs with files but no record file: "
            + "; ".join(f"tab {n}: {len(v)} ({sum('-pdf' in x for x in v)} PDF)" for n, v in without.items())]
    MANIFEST.write_text("\n".join(head + ["  ".join(r) for r in rows]) + "\n")
    print("record files", years, "first", years[0])


if __name__ == "__main__":
    main()
