"""The list parser on invented word boxes with the header geometry of the real lists (synth.py). No real file is read."""
from __future__ import annotations

import datetime as dt
import re
from fractions import Fraction as F

import config as C
import parse as P
import pytest
import synth as SY


def parse(rows, name="A", **kw):
    return P.parse_words(P.words_from_tsv(SY.tsv(rows, **kw)), name)


def full_row():
    return {"evidence": "12P/2019", "title": "Invented Film", "applicant": "Studio s.r.o.", "tax_id": "CZ12345678",
            "request_date": "01.02.2019", "registration_date": "15.02.2019", "evidence_date": "01.06.2019",
            "allocation": "1 234 567 Kč", "deadline": "15.02.2023", "cancellation_date": "02.02.2020",
            "change_date": "03.03.2020", "new_allocation": "1 111 111,50 Kč", "decision_1_date": "04.04.2021",
            "decision_2_date": "05.05.2022", "incentive_1": "222 222 Kč", "incentive_2": "888 888 Kč",
            "paid": "1 111 110 Kč"}


@pytest.mark.parametrize("text,value", [("1 234 567 Kč", 1_234_567), ("1 234 567 Kč", 1_234_567),
                                        ("12 345", 12_345), ("0 Kč", 0), ("870 873,50 Kč", F(1_741_747, 2)),
                                        ("1 000,05 Kč", F(100_005, 100)), ("1234567Kč", 1_234_567), ("-5 000 Kč", -5000)])
def test_amounts_are_exact(text, value):
    got = P.parse_amount(text)
    assert got == value and type(got) is (int if isinstance(value, int) else F)


@pytest.mark.parametrize("text", ["1 23 Kč", "12,345 Kč", "abc", "1.234 Kč", ""])
def test_amounts_that_do_not_read(text):
    with pytest.raises(ValueError):
        P.parse_amount(text)


@pytest.mark.parametrize("text,value", [("05.03.2019", dt.date(2019, 3, 5)), ("5. 3. 2019", dt.date(2019, 3, 5)),
                                        ("5.3.2019", dt.date(2019, 3, 5)), ("31.12.2020", dt.date(2020, 12, 31))])
def test_dates(text, value):
    assert P.parse_date(text) == value


@pytest.mark.parametrize("text", ["5.3.19", "32.01.2019", "2019-03-05", "05.03.2019/06.03.2019"])
def test_dates_that_do_not_read(text):
    with pytest.raises(ValueError):
        P.parse_date(text)


def test_several_dates_in_one_cell():
    assert P.parse_dates("18.08.2017/04.04.2019") == (dt.date(2017, 8, 18), dt.date(2019, 4, 4))
    assert P.parse_dates("01.01.2020, 02.02.2021") == (dt.date(2020, 1, 1), dt.date(2021, 2, 2))
    with pytest.raises(ValueError):
        P.parse_dates("01.01.2020/0101.2021")


@pytest.mark.parametrize("ev,year", [("1P/2016", 2016), ("12P/2019", 2019), ("123P/2025", 2025),
                                     ("199/P/2025", 2025), ("64/2023", 2023), ("11P2019", 2019)])
def test_evidence_number_shapes_and_their_year(ev, year):
    assert P.EVIDENCE.fullmatch(ev) and P.year_of(ev) == year
    row = full_row() | {"evidence": ev}
    (got,) = parse([row])
    assert got.evidence == ev and got.year == year


def test_every_column_lands_in_its_own_field():
    (r,) = parse([full_row()])
    assert (r.evidence, r.title, r.applicant, r.tax_id) == ("12P/2019", "Invented Film", "Studio s.r.o.", "CZ12345678")
    assert (r.request_date, r.registration_date, r.evidence_date, r.deadline) == (
        dt.date(2019, 2, 1), dt.date(2019, 2, 15), (dt.date(2019, 6, 1),), dt.date(2023, 2, 15))
    assert (r.cancellation_date, r.change_date) == (dt.date(2020, 2, 2), (dt.date(2020, 3, 3),))
    assert (r.decision_1_date, r.decision_2_date) == (dt.date(2021, 4, 4), dt.date(2022, 5, 5))
    assert (r.allocation, r.new_allocation) == (1_234_567, F(2_222_223, 2))
    assert (r.incentive_1, r.incentive_2, r.paid) == (222_222, 888_888, 1_111_110)
    assert r.listed == frozenset(P.RIGHT)


def test_empty_cells_are_zero_or_none_and_not_listed():
    row = {k: v for k, v in full_row().items() if k in P.TEXT + ("request_date", "registration_date", "deadline")}
    (r,) = parse([row])
    assert r.allocation == r.new_allocation == r.incentive_1 == r.incentive_2 == r.paid == 0
    assert r.evidence_date == r.change_date == () and r.cancellation_date is None and r.decision_2_date is None
    assert r.listed == {"request_date", "registration_date", "deadline"}


def test_small_amounts_and_neighbouring_dates_stay_in_their_columns():
    # a right-aligned short amount sits nearer the deadline heading than its own; its shape keeps it an amount
    row = full_row() | {"allocation": "5 Kč", "new_allocation": "7 Kč", "paid": "1 Kč", "incentive_2": "3 Kč"}
    (r,) = parse([row])
    assert (r.allocation, r.new_allocation, r.paid, r.incentive_2) == (5, 7, 1, 3)
    assert r.deadline == dt.date(2023, 2, 15)


def test_a_wide_multi_date_cell_does_not_swallow_the_date_beside_it():
    row = full_row() | {"evidence_date": "15.09.2020/07.06.2022"}
    row["_dy"] = {}
    words = P.words_from_tsv(SY.tsv([row]))
    # a wide cell overflows its column on both sides, as 65P/2019 in the real list A: it starts 2 pt after the date before it
    reg = next(w for w in words if w.text == "15.02.2019" and w.x0 < 500)
    words = [P.Word(w.page, reg.x1 + 2, reg.x1 + 2 + (w.x1 - w.x0), w.y, w.text) if "/" in w.text and "." in w.text
             else w for w in words]
    (r,) = P.parse_words(words, "A")
    assert r.registration_date == dt.date(2019, 2, 15)
    assert r.evidence_date == (dt.date(2020, 9, 15), dt.date(2022, 6, 7))


def test_dates_and_amounts_printed_with_spaces():
    row = full_row() | {"request_date": "1. 2. 2019", "paid": "1 111 110 Kč"}
    (r,) = parse([row])
    assert r.request_date == dt.date(2019, 2, 1) and r.paid == 1_111_110


def test_wrapped_titles_are_merged_into_their_row():
    rows = [full_row() | {"evidence": "1P/2019"},
            full_row() | {"evidence": "2P/2019", "title": ["A Very Long Invented", "Title That Wraps"]},
            full_row() | {"evidence": "3P/2019", "title": ["One", "Two", "Three"]},
            full_row() | {"evidence": "4P/2019"}]
    got = parse(rows)
    assert [r.evidence for r in got] == ["1P/2019", "2P/2019", "3P/2019", "4P/2019"]
    assert [r.title for r in got] == ["Invented Film", "A Very Long Invented Title That Wraps", "One Two Three",
                                      "Invented Film"]


def test_an_applicant_printed_just_above_its_row_belongs_to_it():
    rows = [full_row() | {"evidence": f"{i}P/2023", "applicant": f"Studio {i} s.r.o."} for i in range(1, 4)]
    rows[1]["_dy"] = {"applicant": -0.9}                  # list B prints some applicants about 1 pt higher
    got = parse(rows, "B")
    assert [r.applicant for r in got] == ["Studio 1 s.r.o.", "Studio 2 s.r.o.", "Studio 3 s.r.o."]


def test_repeated_headers_and_page_breaks():
    rows = [full_row() | {"evidence": f"{i}P/2019"} for i in range(1, 12)]
    got = parse(rows, rows_per_page=4)
    assert [r.evidence for r in got] == [f"{i}P/2019" for i in range(1, 12)]
    assert [r.page for r in got] == [1] * 4 + [2] * 4 + [3] * 3
    assert all(r.title == "Invented Film" for r in got)
    again = parse(rows, rows_per_page=4, header_every_page=False)      # a page without a header keeps the columns
    assert [(r.evidence, r.paid) for r in again] == [(r.evidence, r.paid) for r in got]


def test_check_1_a_row_without_title_or_request_date_stops_with_its_number():
    with pytest.raises(P.ParseError, match="12P/2019: no title"):
        parse([full_row() | {"title": ""}])
    with pytest.raises(P.ParseError, match="12P/2019: no registration request date"):
        parse([full_row() | {"request_date": ""}])


def test_a_cell_that_does_not_read_stops_with_its_number_and_a_masked_shape_only():
    with pytest.raises(P.ParseError, match=r"12P/2019: column decision_2_date is not a date: '##\.##\.##'") as e:
        parse([full_row() | {"decision_2_date": "05.05.22"}])
    assert not re.search(r"05\.05", str(e.value))
    with pytest.raises(P.ParseError, match="column change_date is not a date"):
        parse([full_row() | {"change_date": "03.03.2020/0303.2021"}])


def test_a_pinned_unreadable_cell_is_listed_without_a_value(monkeypatch):
    monkeypatch.setattr(C, "UNREADABLE_CELLS", frozenset({("A", "12P/2019", "change_date")}))
    (r,) = parse([full_row() | {"change_date": "03.03.2020/0303.2021"}])
    assert r.change_date == () and "change_date" in r.listed and r.unreadable == {"change_date"}
    with pytest.raises(P.ParseError, match="pinned as unreadable but empty"):
        parse([full_row() | {"change_date": ""}])


def test_unknown_evidence_number_shapes_and_text_above_the_header_stop():
    with pytest.raises(P.ParseError, match="unknown shape '##X##'"):
        parse([full_row() | {"evidence": "12X34"}])
    with pytest.raises(P.ParseError, match="text above the header block"):
        parse([full_row()], above_header="Seznam")


def test_a_header_that_differs_from_the_printed_columns_stops():
    header = [h for h in SY.HEADER if h[3] != "VYPLACENO" and h[0] < 998]   # drop the paid column
    with pytest.raises(P.ParseError, match="header columns"):
        parse([full_row()], header=header)
    with pytest.raises(P.ParseError, match="no header block"):
        P.parse_words(P.words_from_tsv(SY.tsv([full_row()], header=[])), "A")


def test_two_cells_in_one_column_stop():
    words = P.words_from_tsv(SY.tsv([full_row()]))
    extra = next(w for w in words if w.text == "05.05.2022")
    words.append(P.Word(extra.page, extra.x0 + 26, extra.x1 + 26, extra.y, "06.06.2022"))
    with pytest.raises(P.ParseError, match="2 cells in column decision_2_date|between columns"):
        P.parse_words(words, "A")


def test_a_row_prints_no_value():
    (r,) = parse([full_row()])
    assert repr(r) == "Row(A 12P/2019)"


def test_layout_margins_of_the_synthetic_lists_are_clear():
    assert P.margins(P.words_from_tsv(SY.tsv([full_row()] * 3))) < P.AMBIGUOUS
