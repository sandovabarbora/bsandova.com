"""Structure and coverage of Registr smluv dumps, with counts only in value bands far from every threshold (§11).

    nice -n 20 python3 tools/procurement/structure.py tools/data/procurement/dump_2024_05.xml ...

Prints element paths, field presence, publication lags and record counts in the FAR bands. It never prints a
contract value, and no count, share or statistic of any record whose value lies in BLIND (0.45–14 million Kč,
which holds every threshold, control and window of the design, with margin); such records are counted only into
one total that is not printed. Output goes to docs/research/procurement-bunching-structure.json.
"""
from __future__ import annotations

import collections
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

NS = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
BLIND = (450_000, 14_000_000)
FAR = [(60_000, 120_000), (120_000, 240_000), (240_000, 450_000),
       (15_000_000, 22_000_000), (30_000_000, 45_000_000)]
FIELDS = ["hodnotaBezDph", "hodnotaVcetneDph", "cenaNeuvedena", "ciziMena", "navazanyZaznam", "schvalil",
          "cisloSmlouvy"]
OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "procurement-bunching-structure.json"


def as_value(text: str | None) -> float | None:
    try:
        return float(text) if text not in (None, "") else None
    except ValueError:
        return None


def band_of(v: float) -> str | None:
    for lo, hi in FAR:
        if lo < v <= hi:
            return f"({lo}, {hi}]"
    return None


def month_lag(concluded: str, published: str) -> str:
    try:
        c, p = date.fromisoformat(concluded[:10]), date.fromisoformat(published[:10])
    except ValueError:
        return "unparsed"
    days = (p - c).days
    for limit, name in [(-1, "published before concluded"), (30, "0-30 days"), (91, "31-91 days"),
                        (365, "92-365 days")]:
        if days <= limit:
            return name
    return "over 365 days"


def scan(path: Path) -> dict:
    paths, present = collections.Counter(), collections.Counter()
    lag, year, far, cur = (collections.Counter() for _ in range(4))
    n = valid = unparsable = 0
    subjects = set()
    stack: list[str] = []
    for event, el in ET.iterparse(path, events=("start", "end")):
        tag = el.tag.removeprefix(NS)
        if event == "start":
            stack.append(tag)
            paths["/".join(stack[1:])] += 1
            continue
        stack.pop()
        if tag != "zaznam":
            continue
        n += 1
        valid += el.findtext(f"{NS}platnyZaznam") == "1"
        s = el.find(f"{NS}smlouva")
        for f in FIELDS:
            present[f] += s.find(f"{NS}{f}") is not None
        cur[s.findtext(f"{NS}ciziMena/{NS}mena") or "CZK (no ciziMena)"] += 1
        concluded = s.findtext(f"{NS}datumUzavreni") or ""
        year[concluded[:4] or "missing"] += 1
        lag[month_lag(concluded, el.findtext(f"{NS}casZverejneni") or "")] += 1
        subjects.add(s.findtext(f"{NS}subjekt/{NS}ico"))
        raw = s.findtext(f"{NS}hodnotaBezDph")
        v = as_value(raw)
        unparsable += raw is not None and v is None
        if v is not None and not (BLIND[0] < v <= BLIND[1]):
            b = band_of(v)
            if b:
                far[b] += 1
        el.clear()
    return {"records": n, "valid_records": valid, "distinct_subject_ico": len(subjects),
            "field_present": dict(present), "hodnotaBezDph_unparsable": unparsable,
            "currency": dict(cur.most_common(8)), "year_concluded": dict(sorted(year.items())),
            "publication_lag": dict(lag), "far_band_counts_hodnotaBezDph": dict(far),
            "element_paths": dict(sorted(paths.items()))}


def main() -> None:
    res = {Path(p).name: scan(Path(p)) for p in sys.argv[1:]}
    OUT.write_text(json.dumps({"blind_range_kc": BLIND, "far_bands_kc": FAR, "files": res}, indent=1,
                              ensure_ascii=False))
    for name, r in res.items():
        print(name, {k: r[k] for k in ("records", "valid_records", "distinct_subject_ico", "field_present",
                                       "far_band_counts_hodnotaBezDph")})


if __name__ == "__main__":
    main()
