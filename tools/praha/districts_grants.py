"""Part 3 extended, the grant lists in part III of the city's closing accounts, 2014-2025
(docs/research/prague-districts-design.md, §4).

Before registration this script runs in --structure mode only: it finds the chapter 5 lists in each year's files,
and counts rows, sections, layouts and the coverage of the fields the design needs (budget measure, resolution,
purpose code ÚZ, the non-investment / investment column). It reads no amount: amount columns are recognised by
position and pattern and never converted to numbers.

Sections (headings as printed):
  2014-2023  5.2 budget measures, state transfers (ÚZ 98xxx and other state ÚZ)
             5.3 budget measures, the city's own grants
             5.4 budget measures, operational programmes
             5.5 / 5.6 drawdown of the city's grants (current and earlier years)
  2024-2025  5.2 / 5.3 drawdown lists only

Resolutions are printed as numbers: "8/27" is ZHMP session 8, item 27; a plain number is an RHMP resolution. Their
dates come from a separate lookup (§4 of the design), not from these files.

Usage:
    uv run python tools/praha/districts_grants.py --structure
    PRAHA3X=/abs/path/to/tools/data/praha3x uv run ...   (when run from a worktree)
"""

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
DISTRICT = r"(Praha\s?\d{1,2}\b|(?:Praha\s?-\s?)?(?:" + "|".join(map(re.escape, SMALL)) + r"))"
HEAD = re.compile(r"^\s*(5\.\d(?:\.\d)?)\.?\s+(Přehled rozpočtových opatření|Čerpání)", re.I)
RESOLUTION = r"(R\s?\d{1,5}|\d{1,2}/\d{1,3}|\d{1,5})"  # R 927 = RHMP; 8/27 = ZHMP session/item
LAYOUT_A = re.compile(rf"^\s*(\d{{1,5}})?\s+{RESOLUTION}\s+(\d{{1,5}})\s+{DISTRICT}\s")  # [RO] usn ÚZ MČ
LAYOUT_B = re.compile(rf"^\s*(\d{{1,5}})?\s+{RESOLUTION}\s+{DISTRICT}\s+\S+\s+(\d{{1,5}})\s")  # [RO] usn MČ ORJ ÚZ
# 2024-2025 drawdown lists: per-district blocks; RO, resolution day (the number sits on the line above), purpose,
# ORG, ÚZ
LAYOUT_D = re.compile(r"^\s*(\d{3,5})\s+(\d{1,2}\.\s?\d{1,2}\.)\s+(.*?)\s+(\d{5,7}|-)\s+(\d{1,5})\s+-?\d")
AMOUNT = re.compile(r"-?\d{1,3}(?: \d{3})*,\d{1,2}\s*$")
INVEST_HEADER = re.compile(r"\b(4251|6363|6349|6341)\b")
CURRENT_HEADER = re.compile(r"\b(4137|5347)\b")
STATE_UZ = re.compile(r"^98\d{3}$|^1\d{4}$|^3\d{4}$|^1\d{5}$")


def sessions() -> dict[int, dict[int, str]]:
    """ZHMP session dates by term and session number, from Part 1's roll-call files (tools/data/zhmp)."""
    out = {}
    for term in (2010, 2014, 2018, 2022):
        path = ROOT / "tools" / "data" / "zhmp" / f"votes{term}.csv"
        if not path.exists():
            path = RAW.parent / "zhmp" / f"votes{term}.csv"
        head = path.read_text(encoding="utf-8-sig").splitlines()[0]
        sep = ";" if head.count(";") > head.count(",") else ","
        import csv
        rows = csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines(), delimiter=sep)
        for r in rows:
            s = r["cislousneseni"].split("/")[0].strip()
            day = r["datumjednani"].split()[0] if r["datumjednani"] else ""
            if s.isdigit() and day:
                d, m, y = day.split(".")
                out.setdefault(term, {}).setdefault(int(s), f"{y}-{m}-{d}")
    return out


def dated(resolution: str, year: int, lookup: dict) -> bool:
    """A ZHMP 'session/item' resolution resolves to a session held in the list's year or the year before."""
    s = int(resolution.split("/")[0])
    return any(str(year - 1) <= t.get(s, "0")[:4] <= str(year) for t in lookup.values())


def text(path: Path) -> str:
    out = TXT / f"{path.parent.name}__{path.stem}.txt"
    if not out.exists():
        TXT.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".pdf":
            subprocess.run(["pdftotext", "-layout", str(path), str(out)], check=True)
        elif path.suffix == ".docx":
            xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
            rows = re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.S)
            body = re.sub(r"</w:p>", "\n", xml)
            cells = ["   ".join(re.sub(r"<[^>]+>", "", c) for c in re.findall(r"<w:tc[ >].*?</w:tc>", r, re.S))
                     for r in rows]
            out.write_text(re.sub(r"<[^>]+>", "", body) + "\n" + "\n".join(cells))
        else:
            out.write_text("")
    return out.read_text(errors="replace")


def lists_in(year: int) -> list[Path]:
    """The files of a closing account that carry the chapter 5 district lists."""
    files = [p for p in sorted((CITY / f"closing_{year}").iterdir()) if p.suffix in (".pdf", ".docx")]
    return [p for p in files if sum(bool(HEAD.match(line)) for line in text(p).splitlines()) >= 2]


def structure(year: int, lookup: dict) -> dict:
    out = {"files": [], "sections": {}}
    for path in lists_in(year):
        lines = text(path).splitlines()
        out["files"].append(path.name)
        heads = [(i, HEAD.match(line).group(1), line.strip()[:90]) for i, line in enumerate(lines) if HEAD.match(line)]
        # the table of contents repeats the headings: keep the last run, i.e. the body
        seen, body = set(), []
        for i, sec, title in reversed(heads):
            if sec not in seen:
                seen.add(sec)
                body.append((i, sec, re.sub(r"\d", "#", title)))
        body.sort()
        for k, (start, sec, title) in enumerate(body):
            end = body[k + 1][0] if k + 1 < len(body) else len(lines)
            rows = {"title": title, "rows_layout_A": 0, "rows_layout_B": 0, "rows_layout_D": 0, "with_ro": 0,
                    "with_resolution_day": 0, "district_lines_unparsed": 0,
                    "with_zhmp_resolution": 0, "zhmp_dated": 0, "with_rhmp_resolution": 0, "with_uz": 0, "state_uz": 0,
                    "with_amount": 0, "under_investment_header": 0, "under_current_header": 0,
                    "headers_both_columns": 0}
            column = None
            for line in lines[start:end]:
                if not AMOUNT.search(line) and (INVEST_HEADER.search(line) or CURRENT_HEADER.search(line)):
                    inv, cur = bool(INVEST_HEADER.search(line)), bool(CURRENT_HEADER.search(line))
                    column = "both" if inv and cur else "inv" if inv else "cur"
                    rows["headers_both_columns"] += column == "both"
                    continue
                d = LAYOUT_D.match(line)
                if d:
                    rows["rows_layout_D"] += 1
                    rows["with_ro"] += 1
                    rows["with_resolution_day"] += 1
                    rows["with_uz"] += 1
                    rows["with_amount"] += bool(AMOUNT.search(line))
                    continue
                a, b = LAYOUT_A.match(line), LAYOUT_B.match(line)
                m = a or b
                if not m:
                    if re.search(DISTRICT, line) and AMOUNT.search(line):
                        rows["district_lines_unparsed"] += 1
                    continue
                rows["rows_layout_A" if a else "rows_layout_B"] += 1
                res = m.group(2)
                rows["with_ro"] += bool(m.group(1))
                rows["with_zhmp_resolution" if "/" in res else "with_rhmp_resolution"] += 1
                rows["zhmp_dated"] += "/" in res and dated(res, year, lookup)
                uz = m.group(3) if a else m.group(4)
                rows["with_uz"] += bool(uz)
                rows["state_uz"] += bool(STATE_UZ.match(uz or ""))
                rows["with_amount"] += bool(AMOUNT.search(line))
                rows["under_investment_header"] += column == "inv"
                rows["under_current_header"] += column == "cur"
            out["sections"][f"{path.stem}:{sec}"] = rows
    return out


def main() -> None:
    if "--structure" not in sys.argv:
        sys.exit("before registration only --structure is allowed")
    lookup = sessions()
    report = {str(y): structure(y, lookup) for y in range(2014, 2026)}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    for y, r in report.items():
        tot = {k: sum(s[k] for s in r["sections"].values()) for k in ["rows_layout_A", "rows_layout_B",
                                                                     "rows_layout_D", "district_lines_unparsed"]}
        print(y, len(r["files"]), "files", len(r["sections"]), "sections", tot)


if __name__ == "__main__":
    main()
