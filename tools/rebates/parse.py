"""The two project lists (design §2.2) into rows. The PDFs are Excel prints with one header block per page; poppler's
`pdftotext -tsv` gives every word with its box, and the columns are found from that header block on each page, so a
cell is assigned by position, never by its order in the row. The only I/O is `read_words`. Messages of a ParseError
carry evidence numbers, column names and digit-masked shapes, never a value."""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import config as C


class ParseError(Exception):
    """A layout or cell the parser does not recognise (design §3 check 1)."""


# the columns in the order the lists print them; the real header differs from the names of design §2.2 (one allocation
# and one new allocation, then two incentive amounts by instalment), see README "Open items"
TEXT = ("evidence", "title", "applicant", "tax_id")
DATES = ("request_date", "registration_date", "evidence_date", "deadline", "cancellation_date", "change_date",
         "decision_1_date", "decision_2_date")
AMOUNTS = ("allocation", "new_allocation", "incentive_1", "incentive_2", "paid")
COLUMNS = ("evidence", "title", "applicant", "tax_id", "request_date", "registration_date", "evidence_date",
           "allocation", "deadline", "cancellation_date", "change_date", "new_allocation", "decision_1_date",
           "decision_2_date", "incentive_1", "incentive_2", "paid")
# blinding: the data step never shows, sums or summarises these (design §0: no allocation, payout or decision read)
OUTCOME = ("allocation", "cancellation_date", "change_date", "new_allocation", "decision_1_date", "decision_2_date",
           "incentive_1", "incentive_2", "paid")
MULTI_DATES = ("evidence_date", "change_date")      # the only columns that print several dates in one cell
RIGHT = COLUMNS[4:]                                 # the date and amount block, assigned by position

HEADER_REACH = 16.0     # pt above and below the "Evidenční" word that hold the header block (real: 10 to 13)
WORD_GAP = 2.5         # header words of one heading are this close; headings are 7 pt or more apart
LINE_TOL = 0.5          # words whose tops differ by at most this are one printed line
LEFT_TOL = 3.0          # an evidence number starts at the left edge of its header word
CELL_GAP = 3.0          # words closer than this on a line are one cell ("1 234 567 Kč"; columns are 10 pt or more apart)
ROW_REACH = 12.0        # a line without an evidence number belongs to the nearest row within this distance
AMBIGUOUS = 0.6         # a cell nearer than this ratio to its second-nearest column than to its own is refused

EVIDENCE = re.compile(r"\d{1,3}(?:P/|P|/P/|/)\d{4}")   # #P/####, ###/P/####, ##/#### and, in list A, ##P####
_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_DATES = re.compile(r"\d{1,2}\.\d{1,2}\.\d{4}(?:[/,]\d{1,2}\.\d{1,2}\.\d{4})*")
_AMOUNT = re.compile(r"(-?)(\d{1,3}(?: \d{3})*|\d+)(?:,(\d{1,2}))?(?: ?Kč)?")
_SPACES = re.compile(r"[\s   ]+")


def mask(text: str) -> str:
    return re.sub(r"\d", "#", text)


def year_of(evidence: str) -> int:
    return int(evidence[-4:])


def parse_date(text: str) -> dt.date:
    m = _DATE.fullmatch(_SPACES.sub("", text))
    if not m:
        raise ValueError("not a date")
    return dt.date(int(m[3]), int(m[2]), int(m[1]))


def parse_dates(text: str) -> tuple[dt.date, ...]:
    """A cell that may print several dates, separated by "/" or "," (re-issued evidence certificates, repeated changes)."""
    return tuple(parse_date(t) for t in re.split(r"[/,]", _SPACES.sub("", text)))


def parse_amount(text: str) -> int | Fraction:
    """Exact CZK: an int, or a Fraction when the cell prints haléře (some new allocations do)."""
    t = _SPACES.sub(" ", text.replace("−", "-")).strip()
    m = _AMOUNT.fullmatch(t)
    if not m:
        raise ValueError("not an amount")
    whole = int(m[2].replace(" ", ""))
    value: int | Fraction = whole if m[3] is None else whole + Fraction(int(m[3]), 10 ** len(m[3]))
    return -value if m[1] else value


# ---------------------------------------------------------------- words

@dataclass(frozen=True)
class Word:
    page: int
    x0: float
    x1: float
    y: float
    text: str

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2


def words_from_tsv(tsv: str) -> list[Word]:
    out = []
    for line in tsv.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or f[0] != "5":
            continue
        x0, y, w = float(f[6]), float(f[7]), float(f[8])
        out.append(Word(int(f[1]), x0, x0 + w, y, f[11]))
    return out


def read_words(path: Path) -> list[Word]:
    """A PDF through `pdftotext -tsv`; any other file is read as that TSV already, which is the seam the tests use."""
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return words_from_tsv(path.read_text(encoding="utf-8"))
    tsv = subprocess.run(["pdftotext", "-tsv", str(path), "-"], capture_output=True, text=True, check=True).stdout
    return words_from_tsv(tsv)


def pdftotext_version() -> str:
    try:
        r = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=False)
        return (r.stderr or r.stdout).splitlines()[0]
    except (OSError, IndexError):
        return "unavailable"


# ---------------------------------------------------------------- the header block

@dataclass(frozen=True)
class Band:
    x0: float
    x1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2


def classify(label: str) -> str | None:
    t = label.lower()
    # order matters: the cancellation and change headings also say "Osvědčení o evidenci", the request one "registraci"
    rules = (("evidenční" in t and "číslo" in t, "evidence"), ("název" in t, "title"), ("žadatel" in t, "applicant"),
             (t == "dič", "tax_id"), ("žádost" in t, "request_date"), ("zrušení" in t, "cancellation_date"),
             ("změně" in t, "change_date"), ("rozhodnutí" in t and "pobídce" in t and "1." in t, "decision_1_date"),
             ("rozhodnutí" in t and "pobídce" in t and "2." in t, "decision_2_date"), ("vyplaceno" in t, "paid"),
             ("filmová pobídka" in t and "1." in t, "incentive_1"), ("filmová pobídka" in t and "2." in t, "incentive_2"),
             ("lhůta" in t, "deadline"), (t == "nová alokace", "new_allocation"), (t == "alokace", "allocation"),
             ("osvědčení" in t and "registraci" in t, "registration_date"),
             ("osvědčení" in t and "evidenci" in t, "evidence_date"))
    return next((name for hit, name in rules if hit), None)


def header_bands(header: Sequence[Word]) -> dict[str, Band]:
    """Header words grouped by horizontal overlap; each group is one column, named by its label."""
    groups: list[list[Word]] = []
    for w in sorted(header, key=lambda w: w.x0):
        if groups and w.x0 <= max(g.x1 for g in groups[-1]) + WORD_GAP:
            groups[-1].append(w)
        else:
            groups.append([w])
    bands, labels = {}, []
    for g in groups:
        label = " ".join(w.text for w in sorted(g, key=lambda w: (round(w.y, 1), w.x0)))
        name = classify(label)
        labels.append(name or "?")
        if name is None or name in bands:
            raise ParseError(f"header group not recognised or repeated: {mask(label)!r}")
        bands[name] = Band(min(w.x0 for w in g), max(w.x1 for w in g))
    if tuple(labels) != COLUMNS:
        raise ParseError(f"header columns {labels} differ from the expected {list(COLUMNS)}")
    return bands


# ---------------------------------------------------------------- rows

@dataclass(repr=False)
class Row:
    list_name: str
    page: int
    evidence: str
    title: str = ""
    applicant: str = ""
    tax_id: str = ""
    request_date: dt.date | None = None
    registration_date: dt.date | None = None
    evidence_date: tuple[dt.date, ...] = ()
    allocation: int | Fraction = 0
    deadline: dt.date | None = None
    cancellation_date: dt.date | None = None
    change_date: tuple[dt.date, ...] = ()
    new_allocation: int | Fraction = 0
    decision_1_date: dt.date | None = None
    decision_2_date: dt.date | None = None
    incentive_1: int | Fraction = 0
    incentive_2: int | Fraction = 0
    paid: int | Fraction = 0
    listed: frozenset[str] = field(default_factory=frozenset)   # columns with a printed cell (§2.3 "if listed")
    unreadable: frozenset[str] = frozenset()                     # printed cells pinned in config.UNREADABLE_CELLS

    @property
    def year(self) -> int:
        return year_of(self.evidence)

    def __repr__(self) -> str:
        # blinding: a row printed by mistake shows no outcome cell
        return f"Row({self.list_name} {self.evidence})"


def _lines(words: Iterable[Word]) -> list[list[Word]]:
    out: list[list[Word]] = []
    for w in sorted(words, key=lambda w: w.y):
        if out and w.y - out[-1][0].y <= LINE_TOL:
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(line, key=lambda w: w.x0) for line in out]


def _text_left(rows: Sequence[list[Word]], lo: float, hi: float, what: str, page: int) -> float:
    # Excel left-aligns a text cell, so its first word starts at the same x on every row: the leftmost x that at least
    # half the rows share
    votes = Counter()
    for ws in rows:
        votes.update({round(w.x0 * 2) / 2 for w in ws if lo < w.x0 <= hi})
    if not votes:
        return hi - 1                                   # no row on the page prints this column; check 1 names the row
    common = sorted(x for x, n in votes.items() if 2 * n >= len(rows))
    if not common:
        raise ParseError(f"page {page}: the {what} column has no left edge shared by half the rows")
    x = common[0]
    return x - 0.25


def raw_rows(words: Sequence[Word], list_name: str) -> list[tuple[int, dict[str, str]]]:
    """(page, {column: printed text}) per row, header blocks dropped, wrapped lines merged into their row."""
    out = []
    bands: dict[str, Band] | None = None
    for page in sorted({w.page for w in words}):
        pw = [w for w in words if w.page == page]
        anchors = [w for w in pw if w.text == "Evidenční"]
        if len(anchors) > 1:
            raise ParseError(f"list {list_name} page {page}: {len(anchors)} header blocks")
        if anchors:
            top = anchors[0].y
            if any(w.y < top - HEADER_REACH for w in pw):
                raise ParseError(f"list {list_name} page {page}: text above the header block")
            bands = header_bands([w for w in pw if abs(w.y - top) <= HEADER_REACH])
            data = [w for w in pw if w.y > top + HEADER_REACH]
        elif bands is None:
            raise ParseError(f"list {list_name}: the first page has no header block")
        else:
            data = pw                                                     # a page without a repeated header
        out.extend((page, r) for r in _page_rows(data, bands, list_name, page))
    return out


def _page_rows(data: Sequence[Word], bands: dict[str, Band], list_name: str, page: int) -> list[dict[str, str]]:
    lines = _lines(data)
    if not lines:
        return []
    is_row = [line[0].x0 <= bands["evidence"].x0 + LEFT_TOL for line in lines]
    starts = [i for i, r in enumerate(is_row) if r]
    if not starts:
        raise ParseError(f"list {list_name} page {page}: lines but no evidence number")
    members: dict[int, list[Word]] = {i: list(lines[i]) for i in starts}
    for i, line in enumerate(lines):
        if is_row[i]:
            continue
        y = line[0].y
        own = min(starts, key=lambda s: (abs(lines[s][0].y - y), -s))   # a tie goes to the lower row
        if abs(lines[own][0].y - y) > ROW_REACH:
            raise ParseError(f"list {list_name} page {page}: a line {abs(lines[own][0].y - y):.1f} pt from any row")
        members[own].extend(line)
    first = {i: lines[i][0] for i in starts}
    for i in starts:
        if not EVIDENCE.fullmatch(first[i].text):
            raise ParseError(f"list {list_name} page {page}: an evidence number of an unknown shape {mask(first[i].text)!r}")
    rows = [members[i] for i in starts]
    t_left = _text_left(rows, bands["evidence"].x1, bands["title"].x0 + 1, "title", page)
    a_left = _text_left(rows, bands["title"].x1, bands["applicant"].x0 + 1, "applicant", page)
    d_left = _text_left(rows, bands["applicant"].x1, bands["tax_id"].x0 + 1, "tax ID", page)
    r_left = bands["request_date"].x0 - 2
    out = []
    for i in starts:
        ev = first[i]
        cells: dict[str, list[str]] = {}
        rest = [w for w in members[i] if w is not ev]
        for name, lo, hi in (("title", t_left, a_left), ("applicant", a_left, d_left), ("tax_id", d_left, r_left)):
            ws = sorted((w for w in rest if lo <= w.x0 < hi), key=lambda w: (round(w.y), w.x0))
            if ws:
                cells[name] = [" ".join(w.text for w in ws)]
        if any(w.x0 < t_left for w in rest):
            raise ParseError(f"list {list_name} {ev.text}: text left of the title column")
        right = [w for w in rest if w.x0 >= r_left]
        if any(w.y != ev.y and abs(w.y - ev.y) > LINE_TOL for w in right):
            raise ParseError(f"list {list_name} {ev.text}: a date or amount on a wrapped line")
        for cell in _cells(right):
            name = _nearest(cell, bands, list_name, ev.text)
            cells.setdefault(name, []).append(" ".join(w.text for w in cell))
        for name, got in cells.items():
            if len(got) > 1:
                raise ParseError(f"list {list_name} {ev.text}: {len(got)} cells in column {name}")
        out.append({"evidence": ev.text, **{k: v[0] for k, v in cells.items()}})
    return out


def _cells(words: Sequence[Word]) -> list[list[Word]]:
    out: list[list[Word]] = []
    for w in sorted(words, key=lambda w: w.x0):
        # a cell already holding whole dates is closed: a wide multi-date cell can come within CELL_GAP of the
        # date beside it (list A, 65P/2019)
        closed = out and _DATES.fullmatch(_SPACES.sub("", " ".join(x.text for x in out[-1])))
        if out and not closed and w.x0 - out[-1][-1].x1 <= CELL_GAP:
            out[-1].append(w)
        else:
            out.append([w])
    return out


def _kind(text: str) -> tuple[str, ...]:
    # a cell's masked shape picks the kind of column it may go to; amounts are right-aligned and dates are not, so a
    # short amount can sit nearer a date heading than its own
    t = _SPACES.sub("", text)
    if _DATES.fullmatch(t):
        return DATES
    if t.endswith("Kč") or re.fullmatch(r"-?[\d,]+", t):
        return AMOUNTS
    return RIGHT


def _distances(cell: Sequence[Word], bands: dict[str, Band]) -> list[tuple[float, str]]:
    kind = _kind(" ".join(w.text for w in cell))
    if kind is AMOUNTS:                                   # right-aligned: right edge against the heading's right edge
        return sorted((abs(bands[c].x1 - cell[-1].x1), c) for c in kind)
    cx = (cell[0].x0 + cell[-1].x1) / 2
    return sorted((abs(bands[c].cx - cx), c) for c in kind)


def _nearest(cell: Sequence[Word], bands: dict[str, Band], list_name: str, ev: str) -> str:
    d = _distances(cell, bands)
    if d[0][0] > AMBIGUOUS * d[1][0]:
        raise ParseError(f"list {list_name} {ev}: a cell between columns {d[0][1]} and {d[1][1]}")
    return d[0][1]


def margins(words: Sequence[Word]) -> float:
    """The largest ratio, over all date and amount cells, of the distance to the own column over the distance to the
    next column of the same kind (a layout figure; 0 is a perfect fit, AMBIGUOUS refuses)."""
    worst = 0.0
    for page in sorted({w.page for w in words}):
        pw = [w for w in words if w.page == page]
        top = next(w.y for w in pw if w.text == "Evidenční")
        bands = header_bands([w for w in pw if abs(w.y - top) <= HEADER_REACH])
        for line in _lines(w for w in pw if w.y > top + HEADER_REACH and w.x0 >= bands["request_date"].x0 - 2):
            for cell in _cells(line):
                d = _distances(cell, bands)
                worst = max(worst, d[0][0] / d[1][0])
    return worst


def convert(page: int, raw: dict[str, str], list_name: str) -> Row:
    ev = raw["evidence"]
    row = Row(list_name, page, ev, listed=frozenset(k for k in raw if k in RIGHT))
    for k in ("title", "applicant", "tax_id"):
        setattr(row, k, raw.get(k, ""))
    pinned = frozenset(k for k in RIGHT if (list_name, ev, k) in C.UNREADABLE_CELLS)
    for k in RIGHT:
        if k not in raw:
            if k in pinned:
                raise ParseError(f"list {list_name} {ev}: column {k} is pinned as unreadable but empty")
            continue
        if k in pinned:
            continue
        try:
            if k in MULTI_DATES:
                setattr(row, k, parse_dates(raw[k]))
            else:
                setattr(row, k, parse_date(raw[k]) if k in DATES else parse_amount(raw[k]))
        except ValueError:
            kind = "date" if k in DATES else "amount"
            raise ParseError(f"list {list_name} {ev}: column {k} is not a {kind}: {mask(raw[k])!r}") from None
    row.unreadable = pinned
    # §3 check 1: every row has an evidence number, a title and a registration request date
    if not row.title:
        raise ParseError(f"list {list_name} {ev}: no title")
    if row.request_date is None:
        raise ParseError(f"list {list_name} {ev}: no registration request date")
    return row


def parse_words(words: Sequence[Word], list_name: str) -> list[Row]:
    return [convert(page, raw, list_name) for page, raw in raw_rows(words, list_name)]


def parse_list(path: Path, list_name: str) -> list[Row]:
    return parse_words(read_words(path), list_name)
