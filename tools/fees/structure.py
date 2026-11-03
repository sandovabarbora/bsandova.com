"""Layout check of the snapshot files that shows labels, positions and counts only. Spreadsheets are read with
`values=False` (a numeric cell is a sentinel), text sources go through the `locate_*` steps, whose raw tokens are never
printed. Nothing here converts or shows a number from a source."""
from __future__ import annotations

import csv
from collections.abc import Iterator

import config as C
import inputs as I
import parse as P
import xlsx as X


def sheet_layout(path, name: str):
    wb = X.read_workbook(path, values=False)
    if name not in wb:
        raise P.ParseError(f"sheet {name!r} not found in {path.name}")
    return wb[name]


def numeric(rows, i: int, cols, dash_ok: bool = False) -> bool:
    def ok(c) -> bool:
        return c == X.NUMBER or (dash_ok and isinstance(c, str) and c.strip() in P.DASHES)
    return all(j < len(rows[i]) and ok(rows[i][j]) for j in cols)


def count_numeric(rows, i: int, cols) -> int:
    return sum(1 for j in cols if j < len(rows[i]) and rows[i][j] == X.NUMBER)


def describe(src: I.Sources) -> Iterator[str]:
    rows3 = sheet_layout(src.silc_3a, "příjmy")
    loc = P.locate_silc_deciles(rows3)
    bad = [k for k, i in loc["rows"].items() if not numeric(rows3, i, loc["cols"], k == "children")]
    yield f"SILC Tab. 3a: located rows with a non-numeric cell in a decile column: {bad or 'none'}"
    yield f"SILC Tab. 3a: decile columns {loc['cols']}; rows {loc['rows']}; income year {loc['income_year']}, survey year {loc['survey_year']}"
    rows10 = sheet_layout(src.silc_10a, "příjmy")
    loc = P.locate_silc_seniors(rows10)
    bad = [k for k, i in loc["rows"].items() if not numeric(rows10, i, loc["cols"].values(), k == "children")]
    yield f"SILC Tab. 10a: located rows with a non-numeric senior cell: {bad or 'none'}"
    yield f"SILC Tab. 10a: senior columns {loc['cols']}; rows {loc['rows']}"
    rowsc = sheet_layout(src.hbs_characteristics, "Charakteristiky")
    loc = P.locate_hbs_characteristics(rowsc)
    yield f"consumption chars: numeric cells in the located rows: {numeric(rowsc, loc['households'], loc['cols']) and numeric(rowsc, loc['members'], loc['cols'])}"
    yield f"consumption chars: quintile columns {loc['cols']}; households row {loc['households']}; members row {loc['members']}"
    rowse = sheet_layout(src.hbs_expenditure, "Vydaje")
    loc = P.locate_hbs_expenditure(rowse)
    codes = {c for _, c in loc["coded"]}
    lacking = []
    for i, c in loc["coded"]:
        n = count_numeric(rowse, i, loc["cols"])
        continued = (n == 0 and i + 1 < loc["end"] and count_numeric(rowse, i + 1, loc["cols"]) == len(loc["cols"])
                     and not (rowse[i + 1] and isinstance(rowse[i + 1][0], str) and P._CODE.match(rowse[i + 1][0].strip())))
        if n != len(loc["cols"]) and not continued:
            lacking.append(c)
    yield f"consumption spend: coded rows with no numbers in the five quintile cells (own or next row): {lacking or 'none'}"
    yield f"consumption spend: quintile columns {loc['cols']}; {len(loc['coded'])} coded rows before the structure block"
    for name, path in (("vat_map", src.vat_map), ("excise_map", src.excise_map)):
        entries = P.read_map(path)
        rows = [e["coicop"] for e in entries if e["kind"] == "row"]
        parents = [e["coicop"][:-5] for e in entries if e["coicop"].endswith("~rest")]
        miss = sorted(c for c in rows + parents if c not in codes)
        yield f"{name}: {len(entries)} entries; codes missing from the table: {miss or 'none'}"
    hits = P.locate_budget_items(P.read_text(src.budget_g))
    got = {h["code"] for h in hits}
    pool = [*C.ITEM_VAT, *C.ITEM_EXCISE, *C.ITEM_PIT, *C.ITEM_CIT]
    yield (f"budget Tab. 2a: {len(hits)} item lines; pool items missing: {sorted(set(pool) - got) or 'none'}; "
           f"token counts per line {sorted({h['tokens'] for h in hits})}; "
           f"items with an empty cell under Skutečnost 2025: {sorted(h['code'] for h in hits if h['raw'] is None)}")
    yield f"budget Tab. 2a pool items absent: {P.pool_absent(dict.fromkeys(got, 0))}; expected {sorted(C.POOL_ABSENT)}"
    gl = P.gross_line_labels(P.read_text(src.budget_c))
    yield f"budget Part C gross-line labels present: {gl}"
    wb = X.read_workbook(src.cnb_indicators, values=False)
    loc = P.locate_cnb_inflation(wb)
    row = wb["Česká verze"][loc["row"]]
    cells = [row[j + k] == X.NUMBER if j + k < len(row) else False
             for _, j in sorted(loc["groups"].items(), key=lambda kv: kv[1]) for k in range(4)]
    first_empty = cells.index(False) if False in cells else len(cells)
    yield (f"ČNB indicators: consumer-price row {loc['row']}; quarter groups {sorted(loc['groups'])}; "
           f"{cells.count(False)} empty quarters, all trailing: {not any(cells[first_empty:])}")
    P.locate_csu_cpi(P.read_text(src.csu_cpi, layout=False))
    yield "ČSÚ CPI statement for 2025: found"
    loc = P.locate_ct_budget(P.read_text(src.ct_budget))
    yield f"ČT budget line: found, unit factor {loc['unit']}, {loc['columns']} columns"
    loc = P.locate_ct_report(P.read_text(src.ct_report), P.read_text(src.ct_report, layout=False))
    yield f"ČT report: household sentence found; revenue row found, unit factor {loc['unit']}, {loc['columns']} columns"
    P.locate_cro_chart(src.cro_chart.read_text(encoding="utf-8"))
    yield "ČRo chart: item 'Výnosy z rozhlasových poplatků' found once"
    P.locate_cro_report(P.read_text(src.cro_report), P.read_text(src.cro_report, layout=False))
    yield "ČRo report: stock row 'FYZICKÉ OSOBY' (31 Dec 2025 column) and realised-revenue sentence found"
    P.verify_bill(P.read_text(src.bill, layout=False))
    yield "bill: both 2027 amounts match config.BILL_2027"
    labels = P.read_band_codes(src.band_codes)
    bounds = {c: P.band_bounds(t) for c, t in labels.items()}
    yield f"RES band codes: {len(labels)} labels, all parse; bounds and schedule multiples: " \
          f"{ {c: (b, P.schedule_multiples(*b)) for c, b in bounds.items()} }"
    with open(src.res_csv, encoding="utf-8-sig", newline="") as f:
        head = next(csv.reader(f))
    yield f"res_data.csv: KATPO column {head.index('KATPO')}, DDATZAN column {head.index('DDATZAN')}"
