"""The data-step checks of §3 (2, 3, 6, 7) on invented rows: each stop and each flag, and what the report holds."""
from __future__ import annotations

import datetime as dt
import json

import config as C
import parse as P
import pytest
import structure as S
import synth as SY


def rows(name, specs):
    path = next(s.path for s in specs if s.name == name)
    return P.parse_list(path, name)


@pytest.fixture
def lists(tmp_path):
    specs = SY.make_lists(tmp_path)
    return {s.name: rows(s.name, specs) for s in specs}, specs


def edit(row: P.Row, **kw) -> P.Row:
    for k, v in kw.items():
        setattr(row, k, v)
    return row


def test_clean_lists_neither_stop_nor_flag(lists):
    got, specs = lists
    rep = S.report(got, specs)
    assert rep["stops"] == [] and rep["flags"] == [] and rep["evidence_numbers_in_a_flag_or_stop"] == []
    assert rep["check_6_counts"]["A"] == {"rows": 18, "distinct_numbers": 18, "expected_rows": 18,
                                          "rows_equal_distinct": True, "equals_expected": True}
    assert rep["coverage"]["A"]["numbers_per_suffix_year"] == {y: 3 for y in range(2016, 2022)}


def test_check_2_a_duplicate_number_stops_also_across_lists(lists):
    got, specs = lists
    got["B"][0].evidence = got["A"][0].evidence
    rep = S.report(got, specs)
    assert "check_2" in rep["stops"] and rep["check_2_unique_numbers"]["duplicates"] == [got["A"][0].evidence]


def test_check_2_pairs_with_same_title_tax_id_and_request_date_are_listed_not_stopped(lists):
    got, specs = lists
    a, b = got["A"][2], got["B"][1]
    edit(b, title=a.title.upper(), tax_id=a.tax_id, request_date=a.request_date)
    rep = S.report(got, specs)
    assert rep["check_2_unique_numbers"]["pairs_same_title_tax_id_request"] == [[a.evidence, b.evidence]]
    assert rep["stops"] == [] and rep["flags"] == []


def test_check_3_a_2022_suffix_stops(lists):
    got, specs = lists
    got["B"][0].evidence = "5P/2022"
    rep = S.report(got, specs)
    assert "check_3" in rep["stops"] and rep["check_3_year_coverage"]["suffix_2022"] == ["5P/2022"]
    assert rep["check_3_year_coverage"]["suffix_outside_stated_years"]["B"] == []      # reported once, as the stop


@pytest.mark.parametrize("name,ev", [("A", "7P/2015"), ("A", "7P/2023"), ("B", "7P/2021"), ("B", "7P/2027")])
def test_check_3_a_suffix_outside_the_stated_years_flags(lists, name, ev):
    got, specs = lists
    got[name][0].evidence = ev
    rep = S.report(got, specs)
    assert rep["stops"] == [] and rep["flags"] == ["check_3"]
    assert rep["check_3_year_coverage"]["suffix_outside_stated_years"][name] == [ev]
    assert ev in rep["evidence_numbers_in_a_flag_or_stop"]


def test_check_3_the_odd_formats_take_the_four_digit_suffix(lists):
    got, specs = lists
    got["B"][0].evidence, got["B"][1].evidence, got["A"][0].evidence = "199/P/2025", "64/2023", "11P2019"
    rep = S.report(got, specs)
    assert rep["flags"] == [] and rep["coverage"]["B"]["odd_format_numbers"] == ["199/P/2025", "64/2023"]
    assert rep["coverage"]["A"]["odd_format_numbers"] == ["11P2019"]


def test_check_3_a_2022_request_with_another_suffix_flags(lists):
    got, specs = lists
    r = edit(got["B"][0], request_date=dt.date(2022, 1, 3))
    rep = S.report(got, specs)
    assert rep["flags"] == ["check_3"] and rep["check_3_year_coverage"]["request_2022_other_suffix"] == [r.evidence]


def test_check_6_rows_against_distinct_numbers_and_the_expected_count(lists):
    got, specs = lists
    specs = tuple(s if s.name == "B" else S.C.ListSpec(s.name, s.path, s.list_date, s.years, 507) for s in specs)
    rep = S.report(got, specs)
    assert rep["flags"] == ["check_6"] and rep["stops"] == []
    assert rep["check_6_counts"]["A"]["equals_expected"] is False and rep["check_6_counts"]["B"]["equals_expected"]
    got["A"][1].evidence = got["A"][0].evidence
    rep = S.report(got, specs)
    assert {"check_2", "check_6"} <= set(rep["stops"])
    assert rep["check_6_counts"]["A"]["rows_equal_distinct"] is False


def test_check_7_deadline_four_years_after_registration(lists):
    got, specs = lists
    rep = S.report(got, specs)["check_7_deadline"]["A"]
    assert rep["with_both_dates"] == 18 and rep["deviating_from_4_years_pm_31_days"] == 0
    assert 1460 <= rep["days_min"] <= rep["days_max"] <= 1461 and rep["flag"] is False
    edit(got["A"][0], deadline=got["A"][0].registration_date + dt.timedelta(days=1461 + 32))
    rep = S.report(got, specs)                                  # 1 of 18 is 5.6 % > 5 %: flags
    assert rep["flags"] == ["check_7"] and rep["check_7_deadline"]["A"]["deviating_numbers"] == [got["A"][0].evidence]
    assert got["A"][0].evidence in rep["evidence_numbers_in_a_flag_or_stop"]


def test_check_7_at_most_five_percent_does_not_flag(lists):
    got, specs = lists
    many = got["A"] * 2                                         # 36 rows, 1 off: 2.8 %
    many = [P.Row(r.list_name, r.page, f"{i}P/2016", title="t", request_date=r.request_date,
                  registration_date=r.registration_date, deadline=r.deadline) for i, r in enumerate(many, 1)]
    edit(many[0], deadline=many[0].registration_date + dt.timedelta(days=1461 - 40))
    rep = S.check_7({"A": many})
    assert rep["A"]["deviating_from_4_years_pm_31_days"] == 1 and rep["flag"] is False
    edit(many[1], deadline=None)                                # rows without a deadline are not in the base
    assert S.check_7({"A": many})["A"]["with_both_dates"] == 35


def test_plus_years_on_29_february():
    assert S.plus_years(dt.date(2020, 2, 29), 4) == dt.date(2024, 2, 29)
    assert S.plus_years(dt.date(2020, 2, 29), 1) == dt.date(2021, 2, 28)


def test_the_report_holds_no_outcome_value(lists):
    got, specs = lists
    text = json.dumps(S.report(got, specs), default=str)
    for r in got["A"] + got["B"]:
        for k in P.OUTCOME:
            v = getattr(r, k)
            if v in (None, 0, ()):
                continue
            for x in (v if isinstance(v, tuple) else (v,)):
                assert str(x) not in text and (not isinstance(x, dt.date) or x.isoformat() not in text)


def test_a_failed_parse_is_a_stop_with_the_message():
    rep = S.failed_parse(P.ParseError("list A 1P/2016: no title"))
    assert rep["stops"] == ["check_1"] and not rep["check_1_row_parse"]["passed"]
    assert list(S.describe(rep)) == ["check 1 (row parse): STOP: list A 1P/2016: no title"]


def test_config_lists_and_rates():
    assert [s.expected_rows for s in C.LISTS] == [507, 462] and C.S2026 == 1_611_972_229
    assert C.headline_rate(dt.date(2024, 12, 31)) == C.highest_rate(dt.date(2024, 12, 31)) == S.C.Fraction(1, 5)
    assert (C.headline_rate(dt.date(2025, 1, 1)), C.highest_rate(dt.date(2025, 1, 1))) == (
        S.C.Fraction(1, 4), S.C.Fraction(7, 20))
