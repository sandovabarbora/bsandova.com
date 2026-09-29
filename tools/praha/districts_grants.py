"""Part 3 extended, the grant lists in part III of the city's closing accounts, 2014-2025
(docs/research/prague-districts-design.md, §4.2-4.3).

Sections (headings as printed):
  2014, 2016-2023  5.2 budget measures, state transfers; 5.3 budget measures, the city's own grants;
                   5.4 operational programmes; 5.5 / 5.6 drawdown of the city's grants (this year / earlier years)
  2015             one section 5.4 with all budget measures, separated here by ÚZ
  2024             5.2 drawdown of the city's grants in the year (a: non-investment, b: investment), 5.3 earlier years
  2025             5.2.1 drawdown by district block (investment, then non-investment), 5.3.x earlier years

Each item row carries the budget measure (RO), the resolution, the purpose code (ÚZ), the district and the amount.
Budget-measure lists and the 2024 list are in thousand CZK; the 2025 list is in CZK.

The two column pairs of a budget-measure list are two directions of money, not copies (correction of 30 Sep 2026):
5347 / 6363 is the city's expenditure, i.e. the city paying the district; 4137 / 4251 is the city's income, i.e.
money the district pays the city (loan repayments "splátka NFV", returned grants "vratka", transfers from districts).
Each amount is assigned to the column whose header code it sits under. The city's own grant is the amount in 5347 /
6363; an amount in 4137 / 4251 is recorded separately as a district-to-city flow. Investment is the 6363 / 4251 pair
where the list has one (2020-2023), otherwise the list's "b)" subsection. In a drawdown list the amount is the first
column, the budget adjustment ("úprava rozpočtu"), i.e. the amount granted.

A row is a **city's own grant** (the primary outcome, §4.3) if its ÚZ is a number from 1 to 999 (leading zeros and a
/ZJ suffix ignored) and it is not in the year-end settlement series (RO 8000-8999). State ÚZ (98xxx, 1xxxx, 3xxxx and
longer codes) and rows with no ÚZ, "-" or "xx" (settlements, local-fee top-ups, returns carrying no ÚZ, the additional
financial relationship) are excluded (rule recorded 29 Sep 2026, before any amount was summed). The rule keeps ÚZ 99
(income-tax refunds passed to districts), 98 (gambling-levy shares) and 8 (repayable loans); a robustness check
drops them.

Resolutions: "8/27" is ZHMP session 8, item 27. It is dated by the exact resolution number in Part 1's roll-call
files; if the number is not there, by its session, but only when that session sat on a single day in the list's year
(sessions continue over several days: the 2022-term session 1 sat on 3 Nov, 24 Nov, 15 Dec 2022 and 16 Feb 2023).
Other rows (RHMP resolutions, sessions with several days, unrecognised numbers) take the date of the nearest dated RO
in the same list (correction of 30 Sep 2026: the first version kept one date per session number).

Modes:
    --structure   counts and coverage only; reads no amount (the registered pre-join step)
    --bridge      Lin's concordance of the budget-measure and drawdown lists, 2019-2023; prints only the statistic
    --build       writes tools/data/praha3x/grants.csv, the item rows with amounts (after registration)

Usage:
    uv run --with pandas python tools/praha/districts_grants.py --structure
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

import csv
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get("PRAHA3X", ROOT / "tools" / "data" / "praha3x"))
CITY, TXT = RAW / "city", RAW / "city_txt"
OUT = ROOT / "docs" / "research" / "prague-districts-grants-structure.json"
SMALL = ["Suchdol", "Čakovice", "Petrovice", "Zbraslav", "Satalice", "Velká Chuchle", "Lysolaje", "Nebušice",
         "Ďáblice", "Dolní Chabry", "Dolní Měcholupy", "Štěrboholy", "Běchovice", "Benice", "Březiněves",
         "Dolní Počernice", "Dubeč", "Klánovice", "Koloděje", "Kolovraty", "Královice", "Křeslice", "Nedvězí",
         "Vinoř", "Lipence", "Lochkov", "Přední Kopanina", "Řeporyje", "Slivenec", "Zličín", "Troja", "Kunratice",
         "Libuš", "Šeberov", "Újezd"]
SHORT = {"Měcholupy": "Dolní Měcholupy", "Dol. Měcholupy": "Dolní Měcholupy", "Dol.Měcholupy": "Dolní Měcholupy",
         "Počernice": "Dolní Počernice", "Dol. Počernice": "Dolní Počernice", "Dol.Počernice": "Dolní Počernice",
         "Kopanina": "Přední Kopanina", "Chuchle": "Velká Chuchle", "Chabry": "Dolní Chabry",
         "Kuntratice": "Kunratice", "D. Měcholupy": "Dolní Měcholupy", "D. Počernice": "Dolní Počernice", "D. Chabry": "Dolní Chabry", "Průhonic": "Újezd", "Újezd u Průhonic": "Újezd", "Śtěrboholy": "Štěrboholy"}
NAMES = sorted(SMALL + list(SHORT), key=len, reverse=True)
DISTRICT = r"(?:MČ\s)?(Praha\s?\d{1,2}\b|(?:Praha\s?[-–]\s*)?(?:" + "|".join(map(re.escape, NAMES)) + r"))"
HEAD = re.compile(r"^\s*(5\.\d(?:\.\d)?)\.?\s+(Přehled rozpočtových opatření|Čerpání)", re.I)
RESOLUTION = r"(R\s*\d{1,5}(?:\s+bod\s+\d{1,3})?|Z\s?\d{1,2}/\d{1,3}|\d{1,2}M?/\d{1,3}|\d{1,2}\.V|\d{1,5})"  # R 927 RHMP; 8/27 ZHMP
UZ = r"(\d{1,9}(?:/\d{1,3})?|[xX]{2}(?:/\d{1,3})?|-)"
LAYOUT_A = re.compile(rf"^\s*(\d{{1,5}}(?:\s\(\d{{4}}\))?)?\s+{RESOLUTION}\s+(?:{UZ}\s+)?{DISTRICT}\s")  # [RO] usn [ÚZ] MČ
# settlement rows of 2015 that print only the district (RO and resolution on the first row of the block)
LAYOUT_S = re.compile(rf"^\s*(?:(\d{{1,5}})\s+)?(?:(Z\s?\d{{1,2}}/\d{{1,3}})\s+)?{DISTRICT}\s+finanční vypořádání", re.I)
LAYOUT_B = re.compile(rf"^\s*(\d{{1,5}}(?:\s\(\d{{4}}\))?)?\s+{RESOLUTION}\s+{DISTRICT}\s+\S+\s+{UZ}\s")  # [RO] usn MČ ORJ ÚZ
# 2025: RO, then anything (a day, a resolution, the purpose, ORG), then ÚZ, then the amounts
LAYOUT_D = re.compile(r"^\s*(\d{4})\s+(.*?)\s(\d{1,5})\s+-?\d{1,3}(?: \d{3})*,\d{2}")
BLOCK = re.compile(r"^\s*MČ\s+(Praha\s?\d{1,2}|Praha\s?-\s?[^\d]+?)\s*(?:-\s*)?$")
AMOUNTS = re.compile(r"-?\d{1,3}(?: \d{3})*,\d{1,2}")
AMOUNT = re.compile(r"-?\d{1,3}(?: \d{3})*,\d{1,2}\s*$")
TOTAL = re.compile(r"(?i)celkem|mezisoučet|součet|úhrn")
CODES = re.compile(r"\b(4137|4251|5347|6363)\b")
SUB_A = re.compile(r"^\s*a\)|^\s*Neinvestiční dotace\s*$")
SUB_B = re.compile(r"^\s*b\)|^\s*Investiční dotace\s*$|^\s*Investiční\s*$")


def sessions() -> dict[int, dict]:
    """ZHMP dates by term: {"res": resolution number -> date, "sess": session -> set of dates}, from Part 1's
    roll-call files (tools/data/zhmp)."""
    out = {}
    for term in (2010, 2014, 2018, 2022):
        path = ROOT / "tools" / "data" / "zhmp" / f"votes{term}.csv"
        if not path.exists():
            path = RAW.parent / "zhmp" / f"votes{term}.csv"
        text = path.read_text(encoding="utf-8-sig")
        head = text.splitlines()[0]
        rows = csv.DictReader(text.splitlines(), delimiter=";" if head.count(";") > head.count(",") else ",")
        t = out.setdefault(term, {"res": {}, "sess": {}})
        for r in rows:
            res = r["cislousneseni"].strip().replace(" ", "")
            day = r["datumjednani"].split()[0] if r["datumjednani"] else ""
            if "/" in res and day:
                d, m, y = day.split(".")
                t["res"].setdefault(res, f"{y}-{m}-{d}")
                t["sess"].setdefault(res.split("/")[0], set()).add(f"{y}-{m}-{d}")
    return out


def zhmp_date(resolution: str, year: int, lookup: dict) -> str | None:
    """The date of a ZHMP 'session/item' resolution approved in the list's year or the year before: the exact
    resolution number first, then a session that sat on one day only in that year; otherwise None."""
    m = re.fullmatch(r"Z?(\d{1,2}M?)/(\d{1,3})", (resolution or "").replace(" ", ""))
    if not m:
        return None
    key = f"{m.group(1)}/{m.group(2)}"
    for want in (str(year), str(year - 1)):
        exact = sorted(t["res"][key] for t in lookup.values() if key in t["res"] and t["res"][key][:4] == want)
        if exact:
            return exact[0]
    for want in (str(year), str(year - 1)):
        days = sorted({d for t in lookup.values() for d in t["sess"].get(m.group(1), set()) if d[:4] == want})
        if len(days) == 1:
            return days[0]
        if len(days) > 1:
            return None  # several sitting days: dated by RO order instead
    return None


def text(path: Path) -> str:
    out = TXT / f"{path.parent.name}__{path.stem}.txt"
    if not out.exists():
        TXT.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".pdf":
            subprocess.run(["pdftotext", "-layout", str(path), str(out)], check=True)
        elif path.suffix == ".docx":
            xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
            out.write_text(re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml)))
        else:
            out.write_text("")
    return out.read_text(errors="replace")


def lists_in(year: int) -> list[Path]:
    """The file of a closing account that carries the chapter 5 district lists (the part III report; in 2024 the
    same lists are also reprinted in the resolution, which is skipped)."""
    files = [p for p in sorted((CITY / f"closing_{year}").iterdir()) if p.suffix in (".pdf", ".docx")]
    found = [p for p in files if sum(bool(HEAD.match(line)) for line in text(p).splitlines()) >= 2]
    return [p for p in found if "usneseni" not in p.stem.lower()] or found


def sections(lines: list[str]) -> list[tuple[str, int, int, str]]:
    """(number, start, end, title) of each chapter 5 section body; the table of contents repeats the headings, so
    the last occurrence of each number is the body."""
    last = {}
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if m:
            last[m.group(1)] = (i, line.strip())
    order = sorted(last.items(), key=lambda x: x[1][0])
    return [(s, i, order[k + 1][1][0] if k + 1 < len(order) else len(lines), t) for k, (s, (i, t)) in enumerate(order)]


def role(year: int, sec: str, title: str) -> str | None:
    """Which list a section is: 'measures' (the city's budget measures), 'drawdown' (this year's grants), or None."""
    t = title.lower()
    if year <= 2023 and sec == "5.3":
        return "measures"
    if year == 2015 and sec == "5.4":
        return "measures"
    if 2019 <= year <= 2023 and sec == "5.5":
        return "drawdown"
    if year == 2024 and sec == "5.2":
        return "drawdown"
    if year == 2025 and sec == "5.2.1":
        return "drawdown"
    return None if "čerpání" not in t else None


def district_name(raw: str) -> str:
    raw = re.sub(r"\s+", " ", raw.strip()).rstrip(" -")
    raw = re.sub(r"^Praha\s?[-–]\s*", "", raw)
    if re.fullmatch(r"Praha ?\d{1,2}", raw):
        n = int(raw.split("Praha")[1])
        # the city numbers its districts 1-57 (allocation tables "MČ P 1-57"); 23-57 are the named districts,
        # alphabetically; a few 2017 rows use that number instead of the name
        return f"Praha {n}" if n <= 22 else "Praha-" + INDEX[n - 23]
    return "Praha-" + SHORT.get(raw, raw)


INDEX = ["Běchovice", "Benice", "Březiněves", "Čakovice", "Ďáblice", "Dolní Chabry", "Dolní Měcholupy",
         "Dolní Počernice", "Dubeč", "Klánovice", "Koloděje", "Kolovraty", "Královice", "Křeslice", "Kunratice",
         "Libuš", "Lipence", "Lochkov", "Lysolaje", "Nebušice", "Nedvězí", "Petrovice", "Přední Kopanina",
         "Řeporyje", "Satalice", "Slivenec", "Suchdol", "Šeberov", "Štěrboholy", "Troja", "Újezd", "Velká Chuchle",
         "Vinoř", "Zbraslav", "Zličín"]


def city_own(uz: str | None, ro: str | None) -> bool:
    if not uz or uz in ("-",) or uz.lower().startswith("xx"):
        return False
    code = int(uz.split("/")[0])
    return 1 <= code <= 999 and not (ro and ro.isdigit() and 8000 <= int(ro) <= 8999)


def items(year: int, lookup: dict) -> tuple[list[dict], dict]:
    """Item rows (amount kept as text) and per-section coverage counts."""
    out, cover = [], {}
    for path in lists_in(year):
        lines = text(path).splitlines()
        for sec, start, end, title in sections(lines):
            kind = role(year, sec, title)
            if not kind:
                continue
            c = {"candidate_lines": 0, "parsed": 0, "zhmp": 0, "zhmp_dated": 0, "undated": 0, "direction_out": 0,
                 "direction_in": 0, "direction_both": 0, "direction_zero": 0, "no_header": 0, "assigned_by_position": 0,
                 "column_vs_sub_conflict": 0,
                 "sub_a": 0, "sub_b": 0, "column_cap": 0, "column_cur": 0, "unmarked": 0, "city_own": 0}
            sub, header, unit, block, ro_prev = None, None, "thousand" if year < 2025 else "CZK", None, None
            learned = {}  # column -> end position of its amounts, from the last line that printed every column
            recent = []
            for line in lines[start:end]:
                has_amount = bool(AMOUNT.search(line))
                if not has_amount:
                    if SUB_A.search(line):
                        sub = "a"
                    elif SUB_B.search(line):
                        sub = "b"
                    if CODES.search(line):
                        header = {m.group(1): m.end() for m in CODES.finditer(line)}
                        learned = {}
                    if re.search(r"\bv Kč\b", line):
                        unit = "CZK"
                    elif re.search(r"tis\. Kč", line):
                        unit = "thousand"
                    b = BLOCK.match(line)
                    if b:
                        block = b.group(1)
                    p = re.search(r"\b(\d{1,2}/\d{1,3})\b", line) if year == 2025 else None
                    if p:
                        recent = [p.group(1)]
                    continue
                if TOTAL.search(line):
                    continue
                d = LAYOUT_D.match(line) if year == 2025 else None
                a = None if d else (LAYOUT_A.match(line) or LAYOUT_B.match(line) or LAYOUT_S.match(line))
                is_candidate = bool(re.search(DISTRICT, line)) or bool(re.match(r"^\s*\d{4}\s", line))
                if not (a or d):
                    c["candidate_lines"] += is_candidate
                    continue
                c["candidate_lines"] += 1
                c["parsed"] += 1
                amounts = [(m.group(0), m.end()) for m in AMOUNTS.finditer(line)]
                row = {"year": year, "section": sec, "kind": kind, "file": path.name, "unit": unit, "sub": sub}
                if d:
                    inline = re.search(r"\b(\d{1,2}/\d{1,3})\b", d.group(2))
                    res = inline.group(1) if inline else (recent[-1] if recent else None)
                    row |= {"ro": d.group(1), "district": district_name(block or ""), "org": None,
                            "uz": d.group(3), "resolution": res, "date": zhmp_date(res, year, lookup)}
                    c["zhmp"] += res is not None
                    c["zhmp_dated"] += row["date"] is not None
                    recent = []
                    column = None
                else:
                    groups = a.groups()
                    ro, res = groups[0], (groups[1] or "").replace(" ", "")
                    if a.re is LAYOUT_S:
                        ro, res, uz, dist = groups[0], (groups[1] or "settlement").replace(" ", ""), None, groups[2]
                    elif a.re is LAYOUT_A:
                        uz, dist = groups[2], groups[3]
                    else:
                        dist, uz = groups[2], groups[3]
                    ro = ro or ro_prev
                    ro_prev = ro
                    row |= {"ro": ro, "resolution": res, "uz": uz, "district": district_name(dist), "org": None,
                            "date": zhmp_date(res, year, lookup) if "/" in res else None}
                    c["zhmp"] += "/" in res
                    c["zhmp_dated"] += row["date"] is not None and "/" in res
                    column = None
                if kind == "drawdown":
                    row["out_text"] = amounts[0][0] if amounts else None
                    row["in_text"] = None
                    row["direction"] = "out"
                else:
                    # each amount goes to the column whose header code it sits under: 5347 / 6363 = the city pays
                    # the district; 4137 / 4251 = the district pays the city (correction of 30 Sep 2026)
                    # amounts are right-aligned and offset from their header codes, so position alone misleads: a
                    # line that prints every column (zeros included) is assigned by order and teaches the columns'
                    # positions; a shorter line is assigned by those learned positions
                    order = sorted(header, key=header.get) if header else []
                    if order and len(amounts) == len(order):
                        assigned = list(zip(order, amounts))
                        learned = {k: pos for k, (_, pos) in assigned}
                    elif order and path.suffix == ".pdf":  # a .docx rendition (2015) has no column layout
                        ref = learned or header
                        assigned = [(min(ref, key=lambda k: abs(ref[k] - pos)), (t, pos)) for t, pos in amounts]
                        c["assigned_by_position"] += 1
                    else:
                        assigned = [("5347", a_) for a_ in amounts]
                    outs, ins, cols = [], [], []
                    for col, (t, pos) in assigned:
                        if float(t.replace(" ", "").replace(",", ".")) == 0.0:
                            continue
                        cols.append(col)
                        (outs if col in ("5347", "6363") else ins).append(t)
                    row["out_text"] = ";".join(outs) or None
                    row["in_text"] = ";".join(ins) or None
                    row["direction"] = "both" if outs and ins else "out" if outs else "in" if ins else "zero"
                    column = cols[-1] if cols else None
                    c["direction_" + row["direction"]] += 1
                    c["no_header"] += not header
                row["column"] = column
                # investment: the 6363 / 4251 pair where the list has one (2020-2023); otherwise the list's "b)"
                # subsection (investment transfers) against "a)" (non-investment)
                split_header = bool(header) and any(k in header for k in ("4251", "6363"))
                if kind == "measures" and split_header and column:
                    row["investment"] = column in ("4251", "6363")
                    c["column_vs_sub_conflict"] += sub is not None and (sub == "b") != row["investment"] \
                        and city_own(row["uz"], row["ro"])
                else:
                    row["investment"] = None if sub is None else sub == "b"
                c["column_cap" if column in ("4251", "6363") else "column_cur" if column else "unmarked"] += 1
                c["sub_a"] += sub == "a"
                c["sub_b"] += sub == "b"
                row["city_own"] = city_own(row["uz"], row["ro"])
                c["city_own"] += row["city_own"]
                c["undated"] += row["date"] is None
                out.append(row)
            c["coverage"] = round(c["parsed"] / c["candidate_lines"], 4) if c["candidate_lines"] else None
            cover[f"{path.stem}:{sec}:{kind}"] = c
    return out, cover


def date_by_ro(rows: list[dict]) -> None:
    """Rows without a date take the date of the nearest dated RO in the same list (RO numbers run in time order)."""
    by_list = {}
    for r in rows:
        by_list.setdefault((r["year"], r["file"], r["section"]), []).append(r)
    for group in by_list.values():
        dated = [(int(r["ro"]), r["date"]) for r in group if r["date"] and (r["ro"] or "").isdigit()]
        for r in group:
            if r["date"] is None and dated and (r["ro"] or "").isdigit():
                r["date"] = min(dated, key=lambda x: abs(x[0] - int(r["ro"])))[1]
                r["date_source"] = "ro"
            elif r["date"]:
                r.setdefault("date_source", "resolution")


def value(text: str | None, unit: str) -> float:
    """Sum of the ';'-joined amounts of one row, in CZK."""
    if not text:
        return 0.0
    v = sum(float(t.replace(" ", "").replace(",", ".")) for t in text.split(";"))
    return v * 1000 if unit == "thousand" else v


def structure(lookup: dict) -> dict:
    report = {}
    for y in range(2014, 2026):
        rows, cover = items(y, lookup)
        date_by_ro(rows)
        own = [r for r in rows if r["city_own"]]
        report[str(y)] = {"files": sorted({r["file"] for r in rows}), "sections": cover,
                          "city_own_rows": len(own),
                          "city_own_rows_dated": sum(r["date"] is not None for r in own),
                          "city_own_rows_dated_by_ro": sum(r.get("date_source") == "ro" for r in own),
                          "city_own_rows_with_investment_marker": sum(r["investment"] is not None for r in own),
                          "city_own_rows_investment": sum(bool(r["investment"]) for r in own),
                          "districts_named": len({r["district"] for r in rows})}
    return report


def lin(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    vx = sum((a - mx) ** 2 for a in x) / n
    vy = sum((b - my) ** 2 for b in y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / n
    return 2 * cov / (vx + vy + (mx - my) ** 2)


def main() -> None:
    lookup = sessions()
    if "--structure" in sys.argv:
        report = structure(lookup)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
        for y, r in report.items():
            cov = [s["coverage"] for s in r["sections"].values() if s["coverage"] is not None]
            print(y, "coverage by list", cov, "own rows", r["city_own_rows"], "dated", r["city_own_rows_dated"],
                  "inv marker", r["city_own_rows_with_investment_marker"], "districts", r["districts_named"])
    elif "--bridge" in sys.argv:
        # district x list-year sums of the city's own grants in the two kinds of list; only Lin's CCC is printed
        cells = {}
        for y in range(2019, 2024):
            rows, _ = items(y, lookup)
            for r in rows:
                if r["city_own"] and r["out_text"]:
                    key = (r["district"], y)
                    cells.setdefault(key, {"measures": 0.0, "drawdown": 0.0})[r["kind"]] += value(r["out_text"], r["unit"])
        x = [v["measures"] for v in cells.values()]
        y = [v["drawdown"] for v in cells.values()]
        stat = {"lin_ccc": round(lin(x, y), 4), "cells": len(cells), "years": [2019, 2023],
                "rule": "CCC >= 0.9: 2024-2025 drawdown lists used as registered; else the 2023 event's post window is 2023 only"}
        (ROOT / "docs" / "research" / "prague-districts-bridge.json").write_text(json.dumps(stat, indent=1) + "\n")
        print(json.dumps(stat))
    elif "--build" in sys.argv:
        rows = []
        for y in range(2014, 2026):
            r, _ = items(y, lookup)
            date_by_ro(r)
            rows += r
        for r in rows:
            r["amount_czk"] = value(r["out_text"], r["unit"])   # city -> district
            r["from_district_czk"] = value(r["in_text"], r["unit"])  # district -> city
        keys = sorted({k for r in rows for k in r})
        with open(RAW / "grants.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(len(rows), "rows")
    else:
        sys.exit("choose --structure, --bridge or --build")


if __name__ == "__main__":
    main()
