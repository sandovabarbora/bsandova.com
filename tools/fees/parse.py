"""Parsers for the snapshot files. Pure functions on rows (xlsx) or text (PDF, HTML, JS); the only I/O is `read_text`
and `count_employers`. Each source has a `locate_*` step that finds rows, columns and tokens by label and returns raw
strings, and a `parse_*` step that converts them. The structure stage of the cli runs only the locate steps, so a real
file can be checked for layout without any number being computed or shown."""
from __future__ import annotations

import csv
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import config as C
import xlsx as X

Rows = list[list[X.Cell]]


class ParseError(Exception):
    """A layout the parser does not recognise. Messages carry labels and counts, never values."""


# ---------------------------------------------------------------- numbers and text

_NUM = re.compile(r"(?<![\d,.])[-−–]?(?:\d{1,3}(?:[   ]\d{3})+|\d+)(?:,\d+)?(?![\d])")


def dec(token: str) -> Decimal:
    t = token.replace("−", "-").replace("–", "-")
    t = re.sub(r"[   ]", "", t).replace(",", ".")
    return Decimal(t)


def number_tokens(line: str, start: int = 0) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in _NUM.finditer(line) if m.start() >= start]


def read_text(path: Path, layout: bool = True) -> str:
    """PDF through poppler's pdftotext (-layout keeps table columns); anything else as UTF-8 text. The synthetic
    fixtures are plain text files, which is the seam the tests use."""
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return path.read_text(encoding="utf-8")
    args = ["pdftotext"] + (["-layout"] if layout else []) + [str(path), "-"]
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def pdftotext_version() -> str:
    try:
        r = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=False)
        return (r.stderr or r.stdout).splitlines()[0]
    except (OSError, IndexError):
        return "unavailable"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"-\s*\n\s*", "", text))


def _unit(text: str) -> int:
    if re.search(r"\(v tis\. Kč\)", text):
        return 1000
    if re.search(r"\(v mil\. Kč\)", text):
        return 10**6
    raise ParseError("no unit label (tis. Kč / mil. Kč) near the table")


# ---------------------------------------------------------------- xlsx helpers

def _label(row: Sequence[X.Cell], n: int = 3) -> str:
    return " ".join(str(c) for c in row[:n] if isinstance(c, str))


def _find_row(rows: Rows, pattern: str, start: int = 0, flags: int = 0) -> int:
    rx = re.compile(pattern, flags)
    hits = [i for i in range(start, len(rows)) if rx.search(_label(rows[i]))]
    if not hits:
        raise ParseError(f"row not found: /{pattern}/")
    if len(hits) > 1:
        raise ParseError(f"row label matches {len(hits)} rows: /{pattern}/")
    return hits[0]


def _header_cols(rows: Rows, words: Sequence[str]) -> list[int]:
    for r in rows[:15]:
        cols = [j for j, c in enumerate(r) if isinstance(c, str) and c.strip().startswith(words[0])]
        if not cols:
            continue
        found = []
        for w in words:
            hit = [j for j, c in enumerate(r) if isinstance(c, str) and c.strip().startswith(w)]
            if len(hit) != 1:
                break
            found.append(hit[0])
        if len(found) == len(words):
            return found
    raise ParseError("header columns not found: " + ", ".join(words))


DASHES = ("-", "\u2013", "\u2014")           # a dash in a table cell means none (e.g. no dependent children)


def _cells(rows: Rows, i: int, cols: Sequence[int], dash_ok: bool = False) -> list[Decimal]:
    out = []
    for j in cols:
        c = rows[i][j] if j < len(rows[i]) else None
        if dash_ok and isinstance(c, str) and c.strip() in DASHES:
            c = Decimal(0)
        if not isinstance(c, Decimal):
            raise ParseError(f"row {i} has no number in column {j}")
        out.append(c)
    return out


def _year(rows: Rows, pattern: str) -> int:
    rx = re.compile(pattern)
    for r in rows[:40]:
        for c in r:
            if isinstance(c, str) and (m := rx.search(c)):
                return int(m.group(1))
    raise ParseError(f"year label not found: /{pattern}/")


# ---------------------------------------------------------------- SILC

DECILE_WORDS = ("nejnižších", "druhých", "třetích", "čtvrtých", "pátých", "šestých", "sedmých", "osmých", "devátých",
                "nejvyšších")
QUINTILE_WORDS = ("nejnižších", "druhých", "třetích", "čtvrtých", "nejvyšších")
SILC_ROWS = {"households": r"^\s*Počet domácností\b", "members": r"^\s*Členů\s*$", "children": r"vyživovaných dětí",
             "cu": r"OECD\s+modif\.", "gross": r"^\s*A\.\s*Hrubé peněžní příjmy", "emp": r"^\s*\d\.\s*Příjmy ze závislé činnosti",
             "self": r"^\s*\d\.\s*Příjmy z podnikání", "tax": r"^\s*C\.\s*Daň z příjmů fyzických osob",
             "net": r"^\s*E\.\s*Čisté peněžní příjmy"}


@dataclass(frozen=True)
class SilcDeciles:
    """Tab. 3a: deciles of net money income per modified OECD consumption unit. Income rows are annual CZK per
    consumption unit; `cu` is the mean number of units per household (the equivalent size)."""
    households: list[Decimal]
    members: list[Decimal]
    children: list[Decimal]
    cu: list[Decimal]
    gross: list[Decimal]
    emp: list[Decimal]
    self_emp: list[Decimal]
    tax: list[Decimal]
    net: list[Decimal]
    income_year: int
    survey_year: int


def locate_silc_deciles(rows: Rows) -> dict:
    cols = _header_cols(rows, DECILE_WORDS)
    return {"cols": cols, "rows": {k: _find_row(rows, p) for k, p in SILC_ROWS.items()},
            "income_year": _year(rows, r"PŘEHLED PŘÍJMŮ za rok (\d{4})"), "survey_year": _year(rows, r"Rok\s+(\d{4})")}


def parse_silc_deciles(rows: Rows) -> SilcDeciles:
    loc = locate_silc_deciles(rows)
    v = {k: _cells(rows, i, loc["cols"], dash_ok=k == "children") for k, i in loc["rows"].items()}
    return SilcDeciles(v["households"], v["members"], v["children"], v["cu"], v["gross"], v["emp"], v["self"], v["tax"],
                       v["net"], loc["income_year"], loc["survey_year"])


@dataclass(frozen=True)
class SeniorCut:
    label: str
    households: Decimal
    members: Decimal
    children: Decimal
    net_per_person: Decimal                 # annual net money income per person


SENIOR_COLUMNS = {"one person, 65 or more": r"a více let", "two adults, at least one 65 or more": r"aspoň jeden"}


def locate_silc_seniors(rows: Rows) -> dict:
    cols = {}
    for name, rx in SENIOR_COLUMNS.items():
        hit = [(i, j) for i, r in enumerate(rows[:12]) for j, c in enumerate(r)
               if isinstance(c, str) and re.search(rx, c)]
        if len(hit) != 1:
            raise ParseError(f"senior column not found once: {name}")
        cols[name] = hit[0][1]
    pats = {k: SILC_ROWS[k] for k in ("households", "members", "children", "net")}
    return {"cols": cols, "rows": {k: _find_row(rows, p) for k, p in pats.items()}}


def parse_silc_seniors(rows: Rows) -> list[SeniorCut]:
    loc = locate_silc_seniors(rows)
    out = []
    for name, j in loc["cols"].items():
        v = {k: _cells(rows, i, [j], dash_ok=k == "children")[0] for k, i in loc["rows"].items()}
        out.append(SeniorCut(name, v["households"], v["members"], v["children"], v["net"]))
    return out


# ---------------------------------------------------------------- consumption (household budget statistics)

@dataclass(frozen=True)
class Hbs:
    households: list[Decimal]               # five quintiles of net money income per person
    members: list[Decimal]
    spend_pp: dict[str, list[Decimal]]      # CZ-COICOP code -> annual CZK per person, five quintiles


def locate_hbs_characteristics(rows: Rows) -> dict:
    cols = _header_cols(rows, QUINTILE_WORDS)
    return {"cols": cols, "households": _find_row(rows, r"Počet domácností \(absol\.\)"),
            "members": _find_row(rows, r"^\s*členů\b", flags=re.IGNORECASE)}


def parse_hbs_characteristics(rows: Rows) -> tuple[list[Decimal], list[Decimal]]:
    loc = locate_hbs_characteristics(rows)
    return _cells(rows, loc["households"], loc["cols"]), _cells(rows, loc["members"], loc["cols"])


_CODE = re.compile(r"^\d{2}(\.\d+)*$")


def locate_hbs_expenditure(rows: Rows) -> dict:
    cols = _header_cols(rows, QUINTILE_WORDS)
    if not any(isinstance(c, str) and "na osobu" in c for r in rows[:4] for c in r):
        raise ParseError("title does not say the table is per person")
    end = next((i for i, r in enumerate(rows) if isinstance(r[0] if r else None, str)
                and r[0].strip().startswith("Struktura")), len(rows))
    coded: list[tuple[int, str]] = []
    for i in range(end):
        c = rows[i][0] if rows[i] else None
        if isinstance(c, str) and _CODE.match(c.strip()):
            coded.append((i, c.strip()))
    return {"cols": cols, "end": end, "coded": coded}


def _numeric_count(rows: Rows, i: int, cols: Sequence[int]) -> int:
    return sum(1 for j in cols if j < len(rows[i]) and isinstance(rows[i][j], Decimal))


def _row_numbers(rows: Rows, i: int, cols: Sequence[int], end: int) -> list[Decimal]:
    """The five quintile numbers of a coded row. Only a row with no numeric quintile cell at all takes them from the
    next row (a label that continues there, which carries no code of its own); a partly numeric row is an error."""
    n = _numeric_count(rows, i, cols)
    if n == len(cols):
        return _cells(rows, i, cols)
    if n == 0 and i + 1 < end:
        nxt = rows[i + 1]
        if not (nxt and isinstance(nxt[0], str) and _CODE.match(nxt[0].strip())):
            return _cells(rows, i + 1, cols)
    raise ParseError(f"row {i} has {n} of {len(cols)} numeric quintile cells")


def parse_hbs_expenditure(rows: Rows) -> dict[str, list[Decimal]]:
    loc = locate_hbs_expenditure(rows)
    out: dict[str, list[Decimal]] = {}
    for i, code in loc["coded"]:
        if code in out:
            raise ParseError(f"code listed twice: {code}")
        out[code] = _row_numbers(rows, i, loc["cols"], loc["end"])
    return out


# ---------------------------------------------------------------- the VAT and excise maps

def read_map(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def map_partition(spend: Mapping[str, Sequence[Fraction]], entries: list[dict]) -> dict[str, list[Fraction]]:
    """Value of every map entry. A residual `P~rest` is the parent's value less every other entry strictly under P,
    deepest parents first; the entries then form a partition of the spending (design change log, N5)."""
    vals: dict[str, list[Fraction]] = {}
    codes = [e["coicop"] for e in entries]
    for e in entries:
        if e["kind"] == "row":
            if e["coicop"] not in spend:
                raise ParseError(f"mapped row missing from the table: {e['coicop']}")
            vals[e["coicop"]] = [Fraction(x) for x in spend[e["coicop"]]]
    residuals = sorted((c for c in codes if c.endswith("~rest")), key=lambda c: -c.count("."))
    for code in residuals:
        parent = code[:-len("~rest")]
        if parent not in spend:
            raise ParseError(f"residual parent missing from the table: {parent}")
        under = [c for c in codes if c.startswith(parent + ".") and c != code]
        if any(c not in vals for c in under):
            raise ParseError(f"residual {code} needs a child not yet computed")
        n = len(spend[parent])
        vals[code] = [Fraction(spend[parent][k]) - sum(vals[c][k] for c in under) for k in range(n)]
        # the table is rounded to whole CZK: the children may exceed the parent by up to half a unit per rounded cell
        # (the parent and each child); such a residual is rounding and counts as 0 (design change log, 3 Nov 2026)
        bound = Fraction(len(under) + 1, 2)
        if any(v < -bound for v in vals[code]):
            raise ParseError(f"residual {code} is negative beyond rounding: the listed children exceed the parent")
        vals[code] = [max(v, Fraction(0)) for v in vals[code]]
    return vals


# ---------------------------------------------------------------- state budget (Part G, Tab. 2a)

@dataclass(frozen=True)
class BudgetHeader:
    first_start: int
    skut_end: int


def _budget_header(lines: list[str], year: int) -> BudgetHeader | None:
    for i, line in enumerate(lines[:12]):
        yrs = [m for m in re.finditer(r"\b(20\d\d)\b", line)]
        pos = [m.start() for m in yrs if int(m.group(1)) == year]
        if not pos:
            continue
        sk = [m for k in range(i + 1, min(i + 5, len(lines))) for m in re.finditer("Skutečnost", lines[k])]
        mine = [m for m in sk if m.start() >= pos[0]]
        if sk and mine:
            return BudgetHeader(min(m.start() for m in sk) - 15, mine[0].end())
    return None


def locate_budget_items(text: str, year: int = C.BUDGET_YEAR) -> list[dict]:
    """Item lines (four-digit budget item, label, raw column tokens) of Tab. 2a, with the position of the token that
    sits under the column Skutečnost of `year`."""
    pages = text.split("\f")
    if not any(p.lstrip().startswith("Tabulka č. 2a") for p in pages):
        raise ParseError("Tab. 2a not found")
    if not re.search(r"Tabulka č\. 2a[^\n]*\(tis\. Kč\)", text):
        raise ParseError("Tab. 2a has no tis. Kč unit label")
    hits, header, in_items, active = [], None, False, False
    for page in pages:
        lines = page.splitlines()
        first = next((ln for ln in lines if ln.strip()), "")
        if first.lstrip().startswith("Tabulka č. 2a"):
            active = True
            header = _budget_header(lines, year) or header
        elif first.lstrip().startswith("Tabulka č."):
            active = False
        if not active:
            continue
        if header is None:
            raise ParseError("Tab. 2a header with the column Skutečnost not found")
        for k, line in enumerate(lines):
            if re.match(r"^\s*Položka\s*$", line):
                in_items = True
                continue
            m = re.match(r"^\s*(\d{4})\s*([^\W\d_].*)$", line)
            if not (in_items and m):
                continue
            toks = number_tokens(line, header.first_start)
            if not toks and k + 1 < len(lines) and not re.search(r"[^\W\d_]", lines[k + 1]):
                toks = number_tokens(lines[k + 1], header.first_start)
            best = min(toks, key=lambda t: abs(t[1] - header.skut_end), default=None)
            blank = best is None or abs(best[1] - header.skut_end) > 8     # the cell under Skutečnost is empty here
            hits.append({"code": int(m.group(1)), "label": m.group(2)[:60], "raw": None if blank else best[2],
                         "tokens": len(toks)})
    if not hits:
        raise ParseError("no budget items found")
    return hits


def parse_budget_items(text: str, year: int = C.BUDGET_YEAR) -> dict[int, Decimal]:
    out: dict[int, Decimal] = {}
    for h in locate_budget_items(text, year):
        if h["code"] in out:
            raise ParseError(f"item listed twice: {h['code']}")
        out[h["code"]] = Decimal(0) if h["raw"] is None else dec(h["raw"])
    return out                                    # tis. Kč; an empty Skutečnost cell is read as 0 (see blank_items)


def blank_items(text: str, year: int = C.BUDGET_YEAR) -> list[int]:
    return [h["code"] for h in locate_budget_items(text, year) if h["raw"] is None]


POOL_CODES = (*C.ITEM_VAT, *C.ITEM_EXCISE, *C.ITEM_PIT, *C.ITEM_CIT)


def pool_absent(items: Mapping[int, Decimal]) -> list[int]:
    return sorted(c for c in POOL_CODES if c not in items)


def pool_lines(items: Mapping[int, Decimal], blank: Sequence[int] = ()) -> dict[str, Fraction]:
    """The tax pool and its parts in CZK as Fractions (design §2.4, change log open item 4). A pool item with an empty
    cell, or an absent item other than config.POOL_ABSENT, is an error."""
    if set(pool_absent(items)) != set(C.POOL_ABSENT):
        raise ParseError(f"pool items absent from Tab. 2a: {pool_absent(items)}, expected {sorted(C.POOL_ABSENT)}")
    empty = sorted(c for c in blank if c in POOL_CODES)
    if empty:
        raise ParseError(f"pool items with an empty cell under Skutečnost: {empty}")

    def total(codes) -> Fraction:
        return sum((Fraction(items[c]) * 1000 for c in codes if c in items), Fraction(0))
    other = sum((Fraction(v) * 1000 for c, v in items.items() if str(c).startswith(C.OUT_OF_POOL_PREFIXES)), Fraction(0))
    si = sum((Fraction(v) * 1000 for c, v in items.items() if str(c).startswith(C.ITEM_SOCIAL_PREFIXES)), Fraction(0))
    return {"vat": total(C.ITEM_VAT), "excise": total(C.ITEM_EXCISE), "pit": total(C.ITEM_PIT),
            "cit": total(C.ITEM_CIT), "other": other, "social": si}


GROSS_LABELS = {
    "vat": r"Celostátní inkaso DPH",
    "cit": r"[Cc]elostátní inkaso daní z příjmů právnických osob",
    "pit": r"[Cc]elostátní (?:inkaso|výnos)[^\n]{0,40}daní? z příjmů fyzických osob",
    "excise_mineral_oils": r"z minerálních olejů \(celostátní výnos\)",
}


def gross_line_labels(text_c: str) -> dict[str, bool]:
    """Whether Part C carries a national (gross) line by label (check 7 of §7); no value is read."""
    return {k: bool(re.search(p, text_c)) for k, p in GROSS_LABELS.items()}


# ---------------------------------------------------------------- inflation

def locate_cnb_inflation(sheets: Mapping[str, Rows]) -> dict:
    rows = sheets["Česká verze"]
    i = _find_row(rows, r"^\s*Spotřebitelské ceny\s+\(%, meziročně, průměr\)")
    groups = {}
    for r in rows[:6]:
        for j, c in enumerate(r):
            if isinstance(c, str) and (m := re.search(r"čtvrtletí roku\s+(\d{4})", c)):
                groups[int(m.group(1))] = j
    if not groups:
        raise ParseError("no 'čtvrtletí roku' group headers")
    return {"row": i, "groups": groups}


def parse_cnb_quarterly(sheets: Mapping[str, Rows]) -> dict[int, list[Decimal | None]]:
    loc = locate_cnb_inflation(sheets)
    row = sheets["Česká verze"][loc["row"]]
    quant = Decimal(1).scaleb(-C.CNB_NOISE_DP)
    out = {}
    for y, j in sorted(loc["groups"].items(), key=lambda kv: kv[1]):
        out[y] = [row[j + k].quantize(quant) if j + k < len(row) and isinstance(row[j + k], Decimal) else None
                  for k in range(4)]
    flat_q = [q for y in out for q in out[y]]
    first_none = next((k for k, q in enumerate(flat_q) if q is None), len(flat_q))
    if any(q is not None for q in flat_q[first_none:]):
        raise ParseError("ČNB consumer-price row has an empty quarter before a filled one")
    return out


def cnb_annual(quarterly: Mapping[int, list[Decimal | None]]) -> dict[int, Decimal]:
    """Mean of the four quarterly y/y values; a missing quarter takes 2.0 % (design §2.6)."""
    return {y: sum((q if q is not None else C.CNB_TARGET for q in qs), Decimal(0)) / 4 for y, qs in quarterly.items()}


_CPI = re.compile(r"Průměrná roční míra inflace.{0,200}?za\s+12\s+měsíců\s+roku\s+(\d{4})\s+proti\s+průměru\s+12\s+"
                  r"měsíců\s+roku\s+(\d{4})\s+činila\s+(?:v České republice\s+)?([-−–]?\d+(?:,\d+)?)\s*%", re.DOTALL)


def locate_csu_cpi(text: str, year: int = 2025) -> str:
    m = next((m for m in _CPI.finditer(flat(text)) if int(m.group(1)) == year), None)
    if m is None:
        raise ParseError(f"ČSÚ annual-average inflation statement for {year} not found")
    return m.group(3)


def parse_csu_cpi(text: str, year: int = 2025) -> Decimal:
    return dec(locate_csu_cpi(text, year))


# ---------------------------------------------------------------- broadcasters

def locate_ct_budget(text: str, year: int = 2026) -> dict:
    """The one line 'příjem z televizních poplatků' with four columns under a header of two years (rozpočet, rozpočet,
    rozdíl, %). Two such lines are an error."""
    lines = text.splitlines()
    found = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*příjem z televizních poplatků\s+\S", line)
        if not m:
            continue
        toks = number_tokens(line, m.end() - 1)
        above = lines[max(0, i - 8):i]
        yline = next((ln for ln in reversed(above) if len(re.findall(r"\b20\d\d\b", ln)) >= 2
                      and not re.search(r"[^\W\d_]", ln)), None)
        if len(toks) != 4 or yline is None:
            continue
        years = [int(y) for y in re.findall(r"\b(20\d\d)\b", yline)]
        if year not in years:
            raise ParseError(f"ČT budget table has no column for {year}")
        found.append({"raw": toks[years.index(year)][2], "unit": _unit("\n".join(above)), "columns": len(toks)})
    if not found:
        raise ParseError("ČT budget line 'příjem z televizních poplatků' with four columns not found")
    if len(found) > 1:
        raise ParseError(f"ČT budget line found {len(found)} times")
    return found[0]


def parse_ct_budget(text: str, year: int = 2026) -> Fraction:
    loc = locate_ct_budget(text, year)
    return Fraction(dec(loc["raw"])) * loc["unit"]


_CT_HH = re.compile(r"K\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s+měla\s+Česká\s+televize\s+v\s+evidenci\s+celkem\s+"
                    r"(\d{1,3}(?:[  ]\d{3})*)\s+domácností")


def locate_ct_report(layout: str, prose: str, year: int = 2025) -> dict:
    m = _CT_HH.search(flat(prose))
    if not m or int(m.group(3)) != year or (m.group(1), m.group(2)) != ("31", "12"):
        raise ParseError("ČT household count sentence for 31 December of the year not found")
    lines = layout.splitlines()
    found = []
    for i, line in enumerate(lines):
        if not re.match(r"^\s*příjem z televizních poplatků\s+\S", line):
            continue
        above = lines[max(0, i - 8):i]
        head = next((ln for ln in reversed(above) if "Skutečnost" in ln and "Rozpočet" in ln), None)
        toks = number_tokens(line, 25)
        if head is None or len(toks) != 4:
            continue
        order = re.findall(r"Rozpočet|Skutečnost|Rozdíl|Plnění", head)
        found.append({"households": m.group(4), "revenue": toks[order.index("Skutečnost")][2],
                      "unit": _unit("\n".join(above)), "columns": len(toks)})
    if not found:
        raise ParseError("ČT report table line 'příjem z televizních poplatků' with four columns not found")
    if len(found) > 1:
        raise ParseError(f"ČT report table line found {len(found)} times")
    return found[0]


def parse_ct_report(layout: str, prose: str, year: int = 2025) -> tuple[Fraction, Fraction]:
    loc = locate_ct_report(layout, prose, year)
    return Fraction(dec(loc["households"])), Fraction(dec(loc["revenue"])) * loc["unit"]


_CRO_FEE = re.compile(r"\[\s*'Výnosy z rozhlasových poplatků'\s*,\s*(-?\d+(?:\.\d+)?)\s*\]")


def locate_cro_chart(js: str) -> str:
    hits = _CRO_FEE.findall(js)
    if len(hits) != 1:
        raise ParseError(f"ČRo chart item 'Výnosy z rozhlasových poplatků' found {len(hits)} times")
    return hits[0]


def parse_cro_chart(js: str) -> Fraction:
    return Fraction(Decimal(locate_cro_chart(js))) * 1000          # values are displayed x 1000 (design change log)


_CRO_REV = re.compile(r"Výnosy z rozhlasových poplatků byly oproti původní plánované roční hodnotě\s+"
                      r"(\d{1,3}(?: \d{3})*)\s+tis\. Kč vykázány v objemu o\s+(\d{1,3}(?: \d{3})*)\s+tis\. Kč vyšším,"
                      r"\s+tj\. v částce\s+(\d{1,3}(?: \d{3})*)\s+tis\. Kč")


def locate_cro_report(layout: str, prose: str, year: int = 2025) -> dict:
    lines = layout.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"FYZICKÉ OSOBY\s+(?=\d)", line)
        if not m:
            continue
        toks = number_tokens(line, m.end())
        dates = []
        for ln in reversed(lines[max(0, i - 25):i]):
            dates = [(int(d), int(mo), int(y)) for d, mo, y in re.findall(r"k\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", ln)]
            if len(dates) == 2:
                break
        if len(toks) != 3 or len(dates) != 2:
            continue
        idx = [k for k, d in enumerate(dates) if d == (31, 12, year)]
        if idx != [1]:
            raise ParseError("ČRo stock table: the column 'k 31. 12. <year>' is not the second date")
        stock = toks[2][2]
        break
    else:
        raise ParseError("ČRo stock table row 'FYZICKÉ OSOBY' not found")
    r = _CRO_REV.search(flat(prose))
    if not r:
        raise ParseError("ČRo realised fee revenue sentence not found")
    return {"stock": stock, "planned": r.group(1), "excess": r.group(2), "realised": r.group(3)}


def parse_cro_report(layout: str, prose: str, year: int = 2025) -> tuple[Fraction, Fraction]:
    loc = locate_cro_report(layout, prose, year)
    planned, excess, realised = (dec(loc[k]) for k in ("planned", "excess", "realised"))
    if planned + excess != realised:
        raise ParseError("ČRo revenue sentence: planned + excess does not equal the total")
    return Fraction(dec(loc["stock"])), Fraction(realised) * 1000


# ---------------------------------------------------------------- the bill

def verify_bill(text: str) -> dict[str, int]:
    """The bill's own amounts (a legal text, not outcome data), checked against the constants of config."""
    found = [int(re.sub(r"\D", "", a)) for a in
             re.findall(r"Příspěvek pro rok 2027 činí celkem\s+(\d{1,3}(?:[  ]\d{3})+)\s+Kč", flat(text))]
    if sorted(found) != sorted(C.BILL_2027.values()):
        raise ParseError("the bill's 2027 amounts do not match config.BILL_2027")
    t = flat(text)
    for phrase in ("překročí 10 procentních bodů", "zvýší o 10 %"):
        if t.count(phrase) < 2:                    # the clause is identical in the two acts
            raise ParseError(f"the bill's clause no longer reads '{phrase}'")
    return dict(C.BILL_2027)


# ---------------------------------------------------------------- employers by size band (RES)

def read_band_codes(path: Path) -> dict[str, str]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["chodnota"]: r["text"] for r in csv.DictReader(f)}


def band_bounds(label: str) -> tuple[int, int | None]:
    if label in C.BAND_LABELS_ZERO:
        return (0, 0)
    m = re.match(r"^(\d[\d ]*?)\s*-\s*(\d[\d ]*?)\s+zaměstnan", label)
    if m:
        return int(m.group(1).replace(" ", "")), int(m.group(2).replace(" ", ""))
    m = re.match(r"^(\d[\d ]*?)\s+a více zaměstnanců$", label)
    if m:
        return int(m.group(1).replace(" ", "")), None
    raise ParseError(f"unknown size-band label: {label}")


def schedule_multiples(lo: int, hi: int | None) -> tuple[int, int]:
    """Lowest and highest multiple of the §5 schedule over the classes a band overlaps (design §3, check 1): a band
    inside one class has that multiple; a straddling band has 0 as its minimum."""
    over = [m for (a, b, m) in C.SCHEDULE if (hi is None or a <= hi) and (b is None or b >= lo)]
    return (over[0] if len(over) == 1 else 0), over[-1]


def count_employers(csv_path: Path, codes: Mapping[str, str]) -> dict[str, int]:
    """Entities without a termination date, by KATPO (design change log). Streams the file."""
    counts = {c: 0 for c in codes}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        head = next(rd)
        try:
            k, d = head.index("KATPO"), head.index("DDATZAN")
        except ValueError as e:
            raise ParseError("res_data.csv lacks KATPO or DDATZAN") from e
        unknown = set()
        for row in rd:
            if row[d].strip():
                continue
            code = row[k].strip()
            if code in counts:
                counts[code] += 1
            else:
                unknown.add(code)
        if unknown - {""}:
            raise ParseError("res_data.csv has size codes outside code list 579: " + ", ".join(sorted(unknown)[:5]))
    return counts
