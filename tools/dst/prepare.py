"""Build the region × date × clock-hour cells of design §2 from the police's yearly archives.

Two layouts (seen as headers and the dictionary only, change note of 2 Oct 2026):
  - 2016–2022: one headerless CSV per region (file name = region code), cp1250, ';', 64 fields in the documented
    order (p1, p36, p37, p2a, weekday, p2b, p6, …, p19 at index 21, …);
  - 2023–2025: `Inehody.xls`, an HTML table with a header row (p1, p2a, p2b, p4a, …, p6, …, p19, …).
Region codes are the same in both (00–07, 14–19). Pedestrians' table and vehicle tables are not used.

Writes tools/data/dst/cells.parquet (one row per region × date × hour, days −28 … +21 around each change, day 0
dropped) and tools/data/dst/prepare_log.json (records read, records with an invalid time, by year). Prints only
those diagnostics.

    uv run --with pandas --with pyarrow --with shapely python tools/dst/prepare.py
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sun import dark_share  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = Path(os.environ.get("DST_DATA", ROOT / "tools" / "data" / "dst"))
YEARS = range(2016, 2026)
DAYS = [d for d in range(-28, 22) if d != 0]
HOURS = list(range(24))
GROUP = {6: "morning", 7: "morning", 10: "control", 11: "control", 12: "control", 13: "control",
         16: "evening", 17: "evening", 18: "evening"}
REGION = {"00": "CZ-PR", "01": "CZ-ST", "02": "CZ-JC", "03": "CZ-PL", "04": "CZ-US", "05": "CZ-KR", "06": "CZ-JM",
          "07": "CZ-MO", "14": "CZ-OL", "15": "CZ-ZL", "16": "CZ-VY", "17": "CZ-PA", "18": "CZ-LI", "19": "CZ-KA"}
CSV_IDX = {"p2a": 3, "p2b": 5, "p6": 6, "p19": 21}


def change_day(year: int) -> date:
    d = date(year, 10, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def parse_date(s: str):
    s = s.strip().strip('"')
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    return None


def parse_hour(s: str):
    """p2b is HHMM (as text or number, also 'HH:MM'); hour 25 or minute 60 mean unknown."""
    s = s.strip().strip('"').replace(":", "")
    if not s.isdigit():
        return None
    v = int(s)
    h, m = divmod(v, 100)
    return h if 0 <= h <= 23 and 0 <= m <= 59 else None


def records(year: int):
    """Yield (region code, p2a, p2b, p6, p19) as strings."""
    arc = D / f"{year}.rar"
    names = subprocess.run(["bsdtar", "-tf", str(arc)], capture_output=True, text=True, check=True).stdout.split()
    if "Inehody.xls" in names:
        raw = subprocess.run(["bsdtar", "-xOf", str(arc), "Inehody.xls"], capture_output=True, check=True).stdout
        text = raw.decode("cp1250", errors="replace")
        rows = re.split(r"(?i)<tr", text)[1:]
        head = [h.strip() for h in re.findall(r"(?i)<t[hd][^>]*>([^<]*)", rows[0])]
        ix = {k: head.index(k) for k in ("p2a", "p2b", "p4a", "p6", "p19")}
        for r in rows[1:]:
            c = re.findall(r"(?i)<td[^>]*>([^<]*)", r)
            if len(c) > max(ix.values()):
                yield c[ix["p4a"]].strip(), c[ix["p2a"]], c[ix["p2b"]], c[ix["p6"]].strip(), c[ix["p19"]].strip()
    else:
        for n in names:
            m = re.fullmatch(r"(\d\d)\.csv", n)
            if not m:
                continue
            raw = subprocess.run(["bsdtar", "-xOf", str(arc), n], capture_output=True, check=True).stdout
            for row in csv.reader(io.StringIO(raw.decode("cp1250", errors="replace")), delimiter=";"):
                if len(row) >= 64:
                    yield (m.group(1), row[CSV_IDX["p2a"]], row[CSV_IDX["p2b"]], row[CSV_IDX["p6"]].strip('" '),
                           row[CSV_IDX["p19"]].strip('" '))


def centroids() -> dict:
    gj = json.loads((D / "geo" / "ne_10m_admin_1.geojson").read_text())
    out = {}
    for f in gj["features"]:
        iso = f["properties"].get("iso_3166_2")
        if iso in REGION.values():
            c = shape(f["geometry"]).centroid
            out[iso] = (c.y, c.x)
    return out


def main() -> None:
    cen = centroids()
    counts, log = {}, {}
    for year in YEARS:
        c0 = change_day(year)
        lo, hi = c0 + timedelta(days=min(DAYS)), c0 + timedelta(days=max(DAYS))
        n = bad_time = bad_region = 0
        for reg, p2a, p2b, p6, p19 in records(year):
            n += 1
            d = parse_date(p2a)
            if d is None or not (lo <= d <= hi) or d == c0:
                continue
            h = parse_hour(p2b)
            if h is None:
                bad_time += 1
                continue
            if reg not in REGION:
                bad_region += 1
                continue
            key = (REGION[reg], d, h)
            k = counts.setdefault(key, [0, 0, 0])
            k[0] += p6 == "4"
            k[1] += p6 != "4"
            k[2] += p19 in {"4", "5", "6", "7"}
        log[year] = {"records": n, "window_invalid_time": bad_time, "window_unknown_region": bad_region}
        print(year, log[year])
    rows = []
    for year in YEARS:
        c0 = change_day(year)
        for iso, (lat, lon) in cen.items():
            for t in DAYS:
                d = c0 + timedelta(days=t)
                off = 2 if t < 0 else 1
                for h in HOURS:
                    ped, other, dark_rec = counts.get((iso, d, h), [0, 0, 0])
                    rows.append({"region": iso, "year": year, "date": d.isoformat(), "t": t, "hour": h,
                                 "dow": d.weekday(), "group": GROUP.get(h, "other"), "ped": ped, "other": other,
                                 "police_dark": dark_rec, "dark": dark_share(d, h, off, lat, lon)})
    pd.DataFrame(rows).to_parquet(D / "cells.parquet", index=False)
    (D / "prepare_log.json").write_text(json.dumps({"years": log, "centroids": cen}, indent=1, default=str))
    print("cells", len(rows))


if __name__ == "__main__":
    main()
