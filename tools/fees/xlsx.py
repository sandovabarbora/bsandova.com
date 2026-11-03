"""Minimal stdlib reader for .xlsx worksheets (no openpyxl, so CI needs nothing extra). Numbers come back as Decimal
from the text stored in the file, never through binary floating point; every other cell is a str."""
from __future__ import annotations

import re
import zipfile
from decimal import Decimal
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
Cell = str | Decimal | None


def col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _shared(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]


def sheet_paths(z: zipfile.ZipFile) -> dict[str, str]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).iter(_REL)}
    out = {}
    for s in wb.find("m:sheets", NS):
        target = rels[s.get(f"{{{NS['r']}}}id")].lstrip("/")
        out[s.get("name")] = target if target.startswith("xl/") else "xl/" + target
    return out


def _cell(c: ET.Element, shared: list[str]) -> Cell:
    t = c.get("t")
    if t == "inlineStr":
        return "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
    v = c.find("m:v", NS)
    if v is None or v.text is None:
        return None
    if t == "s":
        return shared[int(v.text)]
    if t in ("str", "e", "b"):
        return v.text
    return Decimal(v.text)


def read_sheet(z: zipfile.ZipFile, path: str, shared: list[str]) -> list[list[Cell]]:
    rows: list[list[Cell]] = []
    root = ET.fromstring(z.read(path))
    for row in root.iter(f"{{{NS['m']}}}row"):
        r = int(row.get("r")) - 1
        while len(rows) <= r:
            rows.append([])
        cells = rows[r]
        for c in row.findall("m:c", NS):
            i = col_index(c.get("r"))
            while len(cells) <= i:
                cells.append(None)
            cells[i] = _cell(c, shared)
    return rows


def read_workbook(path) -> dict[str, list[list[Cell]]]:
    with zipfile.ZipFile(path) as z:
        shared = _shared(z)
        return {name: read_sheet(z, p, shared) for name, p in sheet_paths(z).items()}
