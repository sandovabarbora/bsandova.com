"""Invented project lists in the word-box format of `pdftotext -tsv`, with the header geometry of the real lists (the
heading words and their positions, read at the data step) and made-up rows, for the tests and the --synthetic run. No
real row, value or name is used here."""
from __future__ import annotations

import datetime as dt
from dataclasses import replace
from pathlib import Path

import config as C

CHAR = 2.47             # pt per character of the 6.5 pt font
PITCH = 7.7             # pt between printed rows
WRAP = 6.5              # pt between the lines of a wrapped cell (one font height; a row adds padding)
FIRST_ROW = 27.0        # pt from the "Evidenční" line to the first row

# (x0, x1, dy from the "Evidenční" line, word) for the heading words
HEADER = [
    (52.7, 75.9, 0, "Evidenční"), (77.2, 88.4, 0, "číslo"), (136.7, 151.1, 0, "Název"), (152.4, 171.8, 0, "projektu"),
    (274.8, 292.1, 0, "Žadatel"), (376.4, 384.7, 0, "DIČ"),
    (416.2, 432.3, -6.5, "Žádost"), (433.7, 436.7, -6.5, "o"), (415.4, 437.6, 0, "registraci"),
    (408.1, 422.9, 6.5, "datum"), (424.1, 444.9, 6.5, "doručení"),
    (461.8, 486.8, -6.5, "Osvědčení"), (461.1, 464.1, 0, "o"), (465.4, 487.6, 0, "registraci"),
    (458.4, 473.2, 6.5, "datum"), (474.5, 490.1, 6.5, "vydání"),
    (516.5, 541.5, -6.5, "Osvědčení"), (517.0, 520.0, 0, "o"), (521.3, 541.0, 0, "evidenci"),
    (513.2, 528.0, 6.5, "datum"), (529.2, 544.8, 6.5, "vydání"),
    (573.5, 592.1, -3.3, "Alokace"),
    (615.9, 629.3, -3.3, "Lhůta"), (630.6, 643.7, -3.3, "podle"), (617.1, 619.8, 3.2, "§"), (621.2, 626.7, 3.2, "48"),
    (628.0, 642.5, 3.2, "odst.1"),
    (656.2, 683.3, -13.0, "Rozhodnutí"), (686.0, 689.0, -13.0, "o"), (664.0, 681.3, -6.5, "zrušení"),
    (658.0, 683.0, 0, "Osvědčení"), (684.3, 687.3, 0, "o"), (662.8, 682.5, 6.5, "evidenci"),
    (656.8, 671.6, 12.9, "datum"), (672.9, 688.5, 12.9, "vydání"),
    (699.8, 726.9, -6.5, "Rozhodnutí"), (728.2, 731.2, -6.5, "o"), (732.5, 747.8, -6.5, "změně"),
    (698.7, 723.7, 0, "Osvědčení"), (726.3, 729.3, 0, "o"), (730.6, 750.3, 0, "evidenci"),
    (708.1, 722.9, 6.5, "datum"), (724.1, 739.7, 6.5, "vydání"),
    (771.2, 783.3, 0, "Nová"), (784.6, 802.7, 0, "alokace"),
    (824.4, 851.5, -13.0, "Rozhodnutí"), (827.2, 830.2, -6.5, "o"), (831.5, 848.6, -6.5, "filmové"),
    (828.5, 847.3, 0, "pobídce"), (826.8, 830.9, 6.5, "1."), (832.1, 849.1, 6.5, "splátka"),
    (822.1, 836.9, 12.9, "datum"), (838.1, 853.7, 12.9, "vydání"),
    (863.3, 890.4, -13.0, "Rozhodnutí"), (866.1, 869.1, -6.5, "o"), (870.6, 887.7, -6.5, "filmové"),
    (867.6, 886.4, 0, "pobídce"), (861.0, 865.1, 6.5, "2."), (866.2, 878.0, 6.5, "nebo"), (879.0, 893.1, 6.5, "jediná"),
    (861.2, 876.0, 12.9, "datum"), (877.2, 892.8, 12.9, "vydání"),
    (901.9, 920.3, -3.3, "Filmová"), (921.7, 940.5, -3.3, "pobídka"), (910.1, 914.2, 3.2, "1."), (915.5, 932.5, 3.2, "splátka"),
    (950.5, 968.9, -3.3, "Filmová"), (970.3, 989.1, -3.3, "pobídka"), (953.5, 957.6, 3.2, "2."), (958.9, 970.7, 3.2, "nebo"),
    (972.0, 986.1, 3.2, "jediná"),
    (999.7, 1018.1, -6.5, "Filmová"), (1019.5, 1038.3, -6.5, "pobídka"), (1003.8, 1034.1, 0, "VYPLACENO"),
    (998.3, 1020.0, 6.5, "(aktuálně"), (1021.3, 1039.6, 6.5, "celkem)"),
]
# where a cell of each column is printed: text and dates start at x, amounts end at x (Excel right-aligns them)
LEFT = {"evidence": 52.7, "title": 99.7, "applicant": 211.0, "tax_id": 366.5, "request_date": 422.8,
        "registration_date": 473.8, "evidence_date": 532.2, "deadline": 626.2, "cancellation_date": 660.0,
        "change_date": 712.0, "decision_1_date": 826.0, "decision_2_date": 871.0}
RIGHT_EDGE = {"allocation": 606.0, "new_allocation": 818.0, "incentive_1": 945.0, "incentive_2": 995.0, "paid": 1045.0}


def _words(text: str, x: float, right: bool = False) -> list[tuple[float, float, str]]:
    parts = text.split(" ")
    width = sum(len(p) * CHAR for p in parts) + 1.5 * (len(parts) - 1)
    pos = x - width if right else x
    out = []
    for p in parts:
        out.append((pos, pos + len(p) * CHAR, p))
        pos += len(p) * CHAR + 1.5
    return out


def tsv(rows: list[dict], rows_per_page: int = 40, header_every_page: bool = True, above_header: str | None = None,
        header: list | None = None) -> str:
    """Rows are {column: printed text}; a "title" may be a list of lines (a wrapped title, centred on the row as Excel
    prints it). Output has the columns of `pdftotext -tsv`, words at level 5."""
    header = HEADER if header is None else header
    lines = ["level\tpage_num\tpar_num\tblock_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]

    def put(page, x0, x1, y, text):
        lines.append(f"5\t{page}\t0\t0\t0\t0\t{x0:.6f}\t{y:.6f}\t{x1 - x0:.6f}\t5.485800\t100\t{text}")

    for start in range(0, max(len(rows), 1), rows_per_page):
        page = start // rows_per_page + 1
        top = 77.3
        if header_every_page or page == 1:
            for x0, x1, dy, w in header:
                put(page, x0, x1, top + dy, w)
            if above_header is not None:
                put(page, 52.7, 80.0, top - 30, above_header)
        y = top + FIRST_ROW
        for row in rows[start:start + rows_per_page]:
            title = row.get("title", "")
            tl = title if isinstance(title, list) else [title]
            half = (PITCH + WRAP * (len(tl) - 1)) / 2
            y += half - PITCH / 2
            for k, text in row.items():
                if k == "title" or k.startswith("_") or not text:
                    continue
                for x0, x1, w in _words(text, RIGHT_EDGE.get(k, LEFT.get(k)), right=k in RIGHT_EDGE):
                    put(page, x0, x1, y + (row.get("_dy", {}).get(k, 0)), w)
            for j, t in enumerate(tl):
                if t:
                    for x0, x1, w in _words(t, LEFT["title"]):
                        put(page, x0, x1, y + WRAP * (j - (len(tl) - 1) / 2), w)
            y += half + PITCH / 2
    return "\n".join(lines) + "\n"


def d(day: dt.date) -> str:
    return day.strftime("%d.%m.%Y")


def czk(n: int) -> str:
    s = f"{n:,}".replace(",", " ")
    return f"{s} Kč"


def project(i: int, year: int, outcome: str = "decided") -> dict:
    """One invented row; `outcome` picks which outcome cells are printed (decided, cancelled, open, none)."""
    req = dt.date(year, 1 + i % 12, 1 + i % 27)
    reg = req + dt.timedelta(days=21)
    row = {"evidence": f"{i}P/{year}", "title": f"Invented Film {i}", "applicant": f"Studio {i} s.r.o.",
           "tax_id": f"CZ{10_000_000 + i}", "request_date": d(req), "registration_date": d(reg),
           "deadline": d(reg.replace(year=reg.year + 4))}
    if outcome == "none":
        return row
    row |= {"evidence_date": d(reg + dt.timedelta(days=90)), "allocation": czk(1_000_000 + 1_000 * i)}
    if outcome == "decided":
        row |= {"decision_2_date": d(reg + dt.timedelta(days=700)), "incentive_2": czk(900_000 + 1_000 * i),
                "paid": czk(900_000 + 1_000 * i)}
    elif outcome == "cancelled":
        row |= {"cancellation_date": d(reg + dt.timedelta(days=400))}
    return row


def list_rows(years: tuple[int, int], n_per_year: int = 3) -> list[dict]:
    rows = []
    for year in range(years[0], years[1] + 1):
        for k in range(1, n_per_year + 1):
            rows.append(project(k, year, ("decided", "cancelled", "open", "none")[k % 4]))
    return rows


def make_lists(root: Path, a: list[dict] | None = None, b: list[dict] | None = None) -> tuple[C.ListSpec, ...]:
    root.mkdir(parents=True, exist_ok=True)
    specs = []
    for spec, rows in zip(C.LISTS, (a, b), strict=True):
        rows = list_rows(spec.years) if rows is None else rows
        path = root / f"list-{spec.name}.tsv"
        path.write_text(tsv(rows), encoding="utf-8")
        specs.append(replace(spec, path=path, expected_rows=len(rows)))
    return tuple(specs)
