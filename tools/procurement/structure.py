"""Structure and coverage of Registr smluv dumps, without looking at the analysis range (design §0, E5).

    nice -n 20 python3 tools/procurement/structure.py tools/data/procurement/dump_2024_05.xml ...

BLIND = (450 000, 14 000 000] Kč holds every threshold, control and window of the design, with margin. A record
whose price without VAT (or VAT-inclusive price / 1.21) lies in BLIND enters only counts that do not condition on
value (field presence, subject stems over all records, publication lag, year concluded); every count that
conditions on value uses records outside BLIND only. No contract value is printed. Output:
docs/research/procurement-bunching-structure.json.
"""
from __future__ import annotations

import collections
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules  # noqa: E402

NS = "{http://portal.gov.cz/rejstriky/ISRS/1.2/}"
BLIND = (450_000, 14_000_000)
FAR = [(60_000, 120_000), (120_000, 240_000), (240_000, 450_000),
       (15_000_000, 22_000_000), (30_000_000, 45_000_000)]
FIELDS = ["hodnotaBezDph", "hodnotaVcetneDph", "cenaNeuvedena", "ciziMena", "navazanyZaznam", "schvalil",
          "cisloSmlouvy", "evidencniCisloZakazky"]
OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "procurement-bunching-structure.json"


def as_value(text: str | None) -> float | None:
    try:
        return float(text) if text not in (None, "") else None
    except ValueError:
        return None


def in_blind(v: float | None) -> bool:
    return v is not None and BLIND[0] < v <= BLIND[1]


def band_of(v: float | None) -> str | None:
    if v is None:
        return None
    for lo, hi in FAR:
        if lo < v <= hi:
            return f"({lo}, {hi}]"
    return None


def period_of(concluded: str) -> str:
    try:
        d = date.fromisoformat(concluded[:10])
    except ValueError:
        return "unparsed"
    if date(2020, 1, 1) <= d <= date(2024, 12, 31):
        return "pre"
    if date(2025, 7, 1) <= d <= date(2026, 6, 30):
        return "post"
    if date(2025, 4, 3) <= d <= date(2025, 6, 30):
        return "transition"
    return "other"


def month_lag(concluded: str, published: str) -> str:
    try:
        days = (date.fromisoformat(published[:10]) - date.fromisoformat(concluded[:10])).days
    except ValueError:
        return "unparsed"
    for limit, name in [(-1, "published before concluded"), (30, "0-30 days"), (91, "31-91 days"),
                        (365, "92-365 days")]:
        if days <= limit:
            return name
    return "over 365 days"


def scan(path: Path) -> dict:
    paths, present, lag, year, far, cur = (collections.Counter() for _ in range(6))
    presence_by_period = collections.defaultdict(collections.Counter)
    far_presence = collections.defaultdict(collections.Counter)
    stems_all, stems_outside, flags_outside = collections.Counter(), collections.Counter(), collections.Counter()
    keys = collections.Counter()
    linked = collections.Counter()
    payer = collections.Counter()
    n = valid = unparsable = equal_outside = outside = 0
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
        is_valid = el.findtext(f"{NS}platnyZaznam") == "1"
        valid += is_valid
        s = el.find(f"{NS}smlouva")
        for f in FIELDS:
            present[f] += s.find(f"{NS}{f}") is not None
        cur[s.findtext(f"{NS}ciziMena/{NS}mena") or "CZK (no ciziMena)"] += 1
        concluded = s.findtext(f"{NS}datumUzavreni") or ""
        year[concluded[:4] or "missing"] += 1
        lag[month_lag(concluded, el.findtext(f"{NS}casZverejneni") or "")] += 1
        subjects.add(s.findtext(f"{NS}subjekt/{NS}ico"))
        raw = s.findtext(f"{NS}hodnotaBezDph")
        v, vat = as_value(raw), as_value(s.findtext(f"{NS}hodnotaVcetneDph"))
        unparsable += raw is not None and v is None
        per = period_of(concluded)
        presence_by_period[per]["records"] += 1
        presence_by_period[per]["hodnotaBezDph"] += v is not None
        presence_by_period[per]["hodnotaVcetneDph only"] += v is None and vat is not None
        subj = s.findtext(f"{NS}predmet") or ""
        hits = rules.stem_hits(subj)
        stems_all.update(hits)
        has_link = el.find(f"{NS}navazanyZaznam") is not None or s.find(f"{NS}navazanyZaznam") is not None
        linked["navazanyZaznam"] += has_link
        linked["navazanyZaznam and stem dodatk"] += has_link and "dodatk" in hits
        pl = s.findtext(f"{NS}subjekt/{NS}platce")
        payer[f"subjekt/platce={pl}"] += 1
        pr = {p.findtext(f"{NS}prijemce") for p in s.findall(f"{NS}smluvniStrana")} - {None}
        payer["some party prijemce=1"] += "1" in pr
        payer["some party prijemce=0"] += "0" in pr
        # value-conditioned counts: records outside BLIND on every value they carry
        if not in_blind(v) and not in_blind(None if vat is None else vat / 1.21):
            b = band_of(v)
            if b:
                far[b] += 1
            vb = band_of(None if vat is None else vat / 1.21)
            if vb:
                far_presence[vb]["with VAT"] += 1
                far_presence[vb]["also without VAT"] += v is not None
            if v is not None:
                outside += 1
                stems_outside.update(hits)
                flags_outside.update(k for k, on in rules.flags(subj).items() if on)
                equal_outside += vat is not None and abs(v - vat) < 0.005
                if is_valid:
                    parties = sorted({p.findtext(f"{NS}ico") or "" for p in s.findall(f"{NS}smluvniStrana")}
                                     | {s.findtext(f"{NS}subjekt/{NS}ico") or ""})
                    keys[(tuple(parties), concluded[:10], s.findtext(f"{NS}cisloSmlouvy") or "", raw)] += 1
        el.clear()
    return {"records": n, "valid_records": valid, "distinct_subject_ico": len(subjects),
            "field_present": dict(present), "hodnotaBezDph_unparsable": unparsable,
            "currency": dict(cur.most_common(8)), "year_concluded": dict(sorted(year.items())),
            "publication_lag": dict(lag), "presence_by_period_all_values": {k: dict(c) for k, c in
                                                                           presence_by_period.items()},
            "far_band_counts_hodnotaBezDph": dict(far),
            "far_band_presence_by_vat_value": {k: dict(c) for k, c in far_presence.items()},
            "outside_blind_with_value": outside, "outside_blind_value_equals_vat_value": equal_outside,
            "outside_blind_content_key_duplicates_removed": sum(c - 1 for c in keys.values() if c > 1),
            "stem_hits_all_records": dict(stems_all.most_common()),
            "stem_hits_outside_blind": dict(stems_outside.most_common()),
            "flags_outside_blind": dict(flags_outside), "linked_records": dict(linked), "payer_flags": dict(payer),
            "element_paths": dict(sorted(paths.items()))}


def main() -> None:
    res = {Path(p).name: scan(Path(p)) for p in sys.argv[1:]}
    OUT.write_text(json.dumps({"blind_range_kc": BLIND, "far_bands_kc": FAR, "files": res}, indent=1,
                              ensure_ascii=False))
    print("ok")


if __name__ == "__main__":
    main()
