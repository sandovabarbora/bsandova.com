"""Pop, measured: parse the raw pages into one part's published tables (series design §2; part 1 design §3).

Writes, under docs/research/, for the artist <slug> in tools/pop/artists.json:
  <slug>-ones.csv       songs with the focal song's global peak: track, label, artist's own, days, first listed
                        date, still charting, kept (first listed on or after 8 January 2017)
  <slug>-countries.csv  per country chart: the focal song's days and peak, still charting, number ones' days
  <slug>-songs.csv      every song on the artist's kworb.net songs page, with its streams (Q4)
  <slug>-tour.csv       Boxscore entries of the artist's tours: tour, dates, city, venue, nights, sold, available,
                        revenue

    uv run --with beautifulsoup4 python tools/pop/parse.py harry-styles
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "data" / "pop" / "raw"
OUT = ROOT / "docs" / "research"
ARTISTS = json.loads((Path(__file__).with_name("artists.json")).read_text(encoding="utf-8"))


def totals(cc: str) -> list[dict]:
    """Rows of a daily-totals page: track id, artist ids, label text, days, peak, total streams. Each table row is
    read on its own: title cell, Days, T10, Pk, (x?), PkStreams, Total."""
    text = (RAW / "totals" / f"{cc}.html").read_text(encoding="utf-8")
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", text, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        track = re.search(r"track/([A-Za-z0-9]+)\.html", tds[0]) if tds else None
        if not track or len(tds) < 7:
            continue
        rows.append({"track": track.group(1), "artists": re.findall(r"artist/([A-Za-z0-9]+)\.html", tds[0]),
                     "label": html.unescape(re.sub(r"<[^>]+>", "", tds[0])).strip(),
                     "days": int(tds[1]), "peak": int(tds[3]), "total": int(tds[-1].replace(",", ""))})
    return rows


def charting(cc: str) -> set[str]:
    text = (RAW / "daily" / f"{cc}.html").read_text(encoding="utf-8")
    return set(re.findall(r"track/([A-Za-z0-9]+)\.html", text))


def first_date(track: str) -> str | None:
    path = RAW / "tracks" / f"{track}.html"
    if not path.exists():
        return None
    dates = re.findall(r"<td>(\d{4})/(\d\d)/(\d\d)</td>", path.read_text(encoding="utf-8"))
    return min("-".join(d) for d in dates) if dates else None


def focal(artist: dict) -> dict:
    """The registered focal song, or by the series rule the artist's song with the largest global Total."""
    mine = [r for r in totals("global") if artist["spotify"] in r["artists"]]
    by_rule = max(mine, key=lambda r: r["total"])
    chosen = next((r for r in mine if r["track"] == artist.get("focal")), by_rule)
    return chosen | {"rule_pick": by_rule["track"]}


def ones(artist: dict, song: dict) -> list[dict]:
    now = charting("global")
    out, missing = [], []
    for r in totals("global"):
        if r["peak"] != song["peak"]:
            continue
        first = first_date(r["track"])
        if first is None:
            missing.append(r["track"])
        out.append({"track": r["track"], "label": r["label"], "peak": r["peak"], "own": artist["spotify"] in r["artists"],
                    "focal": r["track"] == song["track"], "days": r["days"], "first_listed": first or "",
                    "still_charting": r["track"] in now, "kept": bool(first) and first >= "2017-01-08"})
    if missing:
        sys.exit(f"{len(missing)} track pages missing; collect them first: {missing[:5]}")
    return out


def countries(song: dict) -> list[dict]:
    meta = json.loads((RAW / "collected.json").read_text())
    out = []
    for cc in meta["countries"]:
        if cc == "global":
            continue
        rows = totals(cc)
        mine = next((r for r in rows if r["track"] == song["track"]), None)
        if mine is None:
            continue
        out.append({"country": cc, "focal_days": mine["days"], "focal_peak": mine["peak"],
                    "still_charting": song["track"] in charting(cc),
                    "ones_days": " ".join(str(r["days"]) for r in rows if r["peak"] == 1)})
    return out


def num(s: str) -> int | None:
    m = re.search(r"[\d,]{3,}", s)
    return int(m.group().replace(",", "")) if m else None


def grid(table) -> tuple[list[str], list[list[tuple[int, str]]]]:
    """A rendered HTML table as a full grid: header names, and per body row a list of (cell id, text), with row and
    column spans carried, so every row sees the cell that covers it and its id."""
    head = [re.sub(r"\s*\(.*|\[.*|/.*", "", th.get_text(" ", strip=True)) for th in table.find("tr").find_all(["th", "td"])]
    carry: dict[int, list] = {}
    out, uid = [], 0
    for tr in table.find_all("tr")[1:]:
        cells = list(tr.find_all(["th", "td"], recursive=False))
        row, col = [], 0
        while cells or any(c >= col and v[0] > 0 for c, v in carry.items()):
            if col in carry and carry[col][0] > 0:
                row.append((carry[col][1], carry[col][2]))
                carry[col][0] -= 1
                col += 1
                continue
            if not cells:
                break
            c = cells.pop(0)
            uid += 1
            text = re.sub(r"\[[^\]]*\]", "", c.get_text(" ", strip=True))
            for _ in range(int(c.get("colspan", 1) or 1)):
                if int(c.get("rowspan", 1) or 1) > 1:
                    carry[col] = [int(c.get("rowspan")) - 1, uid, text]
                row.append((uid, text))
                col += 1
        out.append(row)
    return head, out


def tour(artist: dict) -> list[dict]:
    """Boxscore entries of every tour listed for the artist, each tagged with its tour name."""
    out = []
    for name in artist["tours"]:
        path = RAW / "wiki" / f"{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}.json"
        page = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if "parse" not in page:
            print("no page:", name)
            continue
        # a table without a year in its caption or header takes the tour's start year from the infobox
        start = re.search(r"\|\s*start_date\s*=[^\n]*?(20\d\d)", page["parse"]["wikitext"]["*"])
        out.extend(dict(e, tour=name, year=e["year"] or (start.group(1) if start else "")) for e in tour_tables(page))
    return out


def year_of(date: str, table_year) -> str:
    """The show's year: written in its date, else the table's caption or header, else empty."""
    m = re.search(r"\b(20\d\d)\b", date) or table_year
    return m.group(1) if m else ""


def tour_tables(page: dict) -> list[dict]:
    """Boxscore entries: one per attendance cell ("sold / available"); its nights are the show rows it covers."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page["parse"]["text"]["*"], "html.parser")
    out = []
    for table in soup.select("table.wikitable"):
        head, body = grid(table)
        if "Attendance" not in head or "Date" not in head[0]:
            continue
        ix = {h: i for i, h in enumerate(head)}
        cap = table.find("caption")
        year = re.search(r"\b(20\d\d)\b", (cap.get_text(" ") if cap else "") + " " + table.find("tr").get_text(" "))
        entries: dict[int, dict] = {}
        venues: dict[int, set] = {}
        for row in body:
            if len(row) <= ix["Attendance"] or row[0][1].lower().startswith("total"):
                continue
            aid, att = row[ix["Attendance"]]
            m = re.search(r"([\d,]+)\s*/\s*([\d,]+)", att)
            if not m:
                continue
            get = lambda h: row[ix[h]][1] if h in ix and ix[h] < len(row) else ""
            e = entries.setdefault(aid, {"year": year_of(row[0][1], year), "first_date": row[0][1], "city": get("City"), "country": get("Country"),
                                         "venue": get("Venue"), "nights": 0,
                                         "sold": int(m.group(1).replace(",", "")),
                                         "available": int(m.group(2).replace(",", "")),
                                         "revenue_usd": num(get("Revenue")) or ""})
            e["nights"] += 1
            if "Venue" in ix and ix["Venue"] < len(row):
                venues.setdefault(aid, set()).add(row[ix["Venue"]][0])
        for aid, e in entries.items():
            # an attendance cell spanning several venues is a leg's total, not a run in one venue (Q3)
            e["multi_venue"] = len(venues.get(aid, ())) > 1
            # a hybrid entry counts online viewers with the hall, so neither its sell-through nor its price is a hall's
            e["hybrid"] = bool(re.search(r"weverse|online|youtube|livestream|virtual|streaming", e["venue"], re.I)) \
                or e["sold"] > e["available"]
        out.extend(entries.values())
    return out


ALIAS = {"England": "GBR", "Scotland": "GBR", "Wales": "GBR", "Northern Ireland": "GBR", "United Kingdom": "GBR",
         "United States": "USA", "South Korea": "KOR", "Czech Republic": "CZE", "Czechia": "CZE", "Turkey": "TUR",
         "Russia": "RUS", "Hong Kong": "HKG", "Macau": "MAC", "Puerto Rico": "PRI", "Taiwan": None}


def with_income(entries: list[dict]) -> list[dict]:
    """Adds each entry's ISO3 code and the World Bank GDP per capita (current US$) for its year, or the latest
    earlier year (series design §4)."""
    wb = json.loads((RAW / "worldbank-gdppc.json").read_text())[1]
    names = {r["country"]["value"]: r["countryiso3code"] for r in wb if r["countryiso3code"]}
    gdp: dict[str, dict[int, float]] = {}
    for r in wb:
        if r["value"] is not None and r["countryiso3code"]:
            gdp.setdefault(r["countryiso3code"], {})[int(r["date"])] = r["value"]
    for e in entries:
        iso = ALIAS[e["country"]] if e["country"] in ALIAS else names.get(e["country"])
        years = sorted(y for y in gdp.get(iso, {}) if not e["year"] or y <= int(e["year"]))
        e["iso3"] = iso or ""
        e["gdppc_usd"] = round(gdp[iso][years[-1]], 2) if iso and years else ""
    return entries


def songs(slug: str) -> list[dict]:
    """Every song on the kworb.net artist songs page (series design §4, Q4); a trailing * marks a feature."""
    table = (RAW / "songs" / f"{slug}.html").read_text(encoding="utf-8").split("<table")[2]
    out = []
    for track, title, streams in re.findall(r'open\.spotify\.com/track/([A-Za-z0-9]+)"[^>]*>(.*?)</a>.*?<td>([\d,]+)</td>', table, re.S):
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        out.append({"track": track, "title": title.rstrip("* "), "feature": title.endswith("*"),
                    "streams": int(streams.replace(",", ""))})
    return sorted(out, key=lambda r: -r["streams"])


def write(name: str, rows: list[dict]) -> None:
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(name, len(rows))


if __name__ == "__main__":
    slug = sys.argv[1]
    artist = ARTISTS[slug]
    song = focal(artist)
    print("focal:", song["label"], "| rule pick:", song["rule_pick"], "| global peak:", song["peak"])
    write(f"{slug}-ones.csv", ones(artist, song))
    write(f"{slug}-countries.csv", countries(song))
    write(f"{slug}-songs.csv", songs(slug))
    entries = with_income(tour(artist))
    unmatched = sorted({e["country"] for e in entries if not e["iso3"]})
    if unmatched:
        print("countries without World Bank income:", unmatched)
    if entries:
        write(f"{slug}-tour.csv", entries)
