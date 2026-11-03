"""The parsers on invented files with the layout of the real ones (synth.py). No real file is read."""
from __future__ import annotations

from decimal import Decimal as D
from fractions import Fraction as F

import config as C
import parse as P
import pytest
import synth as SY
import xlsx as X


@pytest.fixture(scope="module")
def snap(tmp_path_factory):
    d = tmp_path_factory.mktemp("snap")
    return SY.make_snapshot(d)


def test_xlsx_reader_keeps_numbers_exact_and_can_withhold_them(snap):
    wb = X.read_workbook(snap.cnb_indicators)
    row = wb["Česká verze"][5]
    assert row[1].startswith("Spotřebitelské ceny") and row[14] == D("10.7000000000000004")
    layout = X.read_workbook(snap.cnb_indicators, values=False)
    cells = [c for r in layout["Česká verze"] for c in r if c is not None]
    assert X.NUMBER in cells and not any(isinstance(c, D) for c in cells)


def test_silc_deciles(snap):
    s = P.parse_silc_deciles(next(iter(X.read_workbook(snap.silc_3a).values())))
    assert s.households == SY.HH and s.members == SY.MEMBERS and s.children == SY.CHILDREN and s.cu == SY.CU
    assert s.net == SY.NET_CU and s.tax == SY.TAX_CU and s.gross == SY.GROSS_CU
    assert s.emp == SY.EMP_CU and s.self_emp == SY.SELF_CU
    assert (s.income_year, s.survey_year) == (2024, 2025)


def test_silc_header_missing_is_a_parse_error():
    with pytest.raises(P.ParseError, match="header columns"):
        P.parse_silc_deciles([["Tab. 3"], ["no deciles here"]])


def test_senior_columns_and_a_dash_for_no_children(snap):
    rows = next(iter(X.read_workbook(snap.silc_10a).values()))
    cut = P.parse_silc_seniors(rows)
    assert [c.label for c in cut] == ["one person, 65 or more", "two adults, at least one 65 or more"]
    assert cut[0].households == D(640_000) and cut[0].members == D(1) and cut[1].net_per_person == D(200_000)
    rows[14][4] = "-"                                                   # the real file prints a dash for none
    assert P.parse_silc_seniors(rows)[0].children == 0


def test_consumption_tables(snap):
    hh, members = P.parse_hbs_characteristics(next(iter(X.read_workbook(snap.hbs_characteristics).values())))
    assert hh == SY.Q_HH and members == SY.Q_MEMBERS
    spend = P.parse_hbs_expenditure(next(iter(X.read_workbook(snap.hbs_expenditure).values())))
    ref = SY.spend_codes()
    assert set(spend) == set(ref) and spend["01.1.2"] == ref["01.1.2"]
    first = sorted(ref, key=SY._key)[0]
    assert spend[first] == ref[first]                                   # label on one row, numbers on the next
    assert spend["01"] == ref["01"] and spend["01"][0] != D(20)         # the structure block after "Struktura" is not read


def test_expenditure_title_must_say_per_person(snap):
    rows = next(iter(X.read_workbook(snap.hbs_expenditure).values()))
    rows[1][0] = "b/ Skupiny"
    with pytest.raises(P.ParseError, match="per person"):
        P.parse_hbs_expenditure(rows)


def test_map_partition_residuals_follow_the_children():
    spend = {"01": [D(10)], "01.1": [D(6)], "01.1.1": [D(2)], "01.1.2": [D(3)], "01.2.1": [D(1)]}
    entries = [{"coicop": c, "kind": k} for c, k in (("01.1.1", "row"), ("01.1.2", "row"), ("01.2.1", "row"),
                                                     ("01.1~rest", "residual"), ("01~rest", "residual"))]
    v = P.map_partition(spend, entries)
    assert v["01.1~rest"] == [F(1)]                    # 6 - (2 + 3)
    assert v["01~rest"] == [F(3)]                      # 10 - (2 + 3 + 1 + the residual 1)
    assert sum(x[0] for x in v.values()) == 10         # a partition of the division
    with pytest.raises(P.ParseError, match="missing"):
        P.map_partition({"01": [D(1)]}, entries)


def test_the_committed_maps_form_a_partition_on_the_invented_table():
    for path in (C.VAT_MAP, C.EXCISE_MAP):
        entries = P.read_map(path)
        spend = {k: [F(x) for x in v] for k, v in SY.spend_codes().items()}
        vals = P.map_partition(spend, entries)
        for division in {e["coicop"][:2] for e in entries}:
            tot = sum(v[0] for c, v in vals.items() if c.startswith(division + ".") or c == division or c.startswith(division + "~"))
            assert tot == spend[division][0]


def test_budget_items_pick_the_2025_actual_not_the_neighbouring_columns(snap):
    items = P.parse_budget_items(P.read_text(snap.budget_g))
    assert items[1211] == D(300_000_000) and items[1121] == D(130_000_000)
    assert items[1131] == D(2_000_000)                                   # wrapped label: numbers on the next line
    assert 5139 not in items                                             # Tab. 2b is not read
    assert items[1321] == D(3_000_000)                                   # digits inside the label are not numbers


def test_budget_blank_cell_is_zero_and_listed():
    txt = SY.budget_g()
    lines = txt.split("\f")[0].splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(" 1111"))
    lines[i] = lines[i][:160]                                            # cut the line before the 2025 actual
    out = "\f".join(["\n".join(lines)] + txt.split("\f")[1:])
    assert P.parse_budget_items(out)[1111] == 0 and P.blank_items(out) == [1111]


def test_budget_negative_actual_and_unit_guard():
    txt = SY.budget_g()
    neg = txt.replace(SY.fmt_cz(300_000_000), SY.fmt_cz(-300_000_000), 1)
    assert P.parse_budget_items(neg)[1211] == D(-300_000_000)
    with pytest.raises(P.ParseError, match="Tab. 2a not found"):
        P.parse_budget_items("nothing")
    with pytest.raises(P.ParseError, match="unit"):
        P.parse_budget_items(txt.replace("(tis. Kč)", "(mil. Kč)"))


def test_pool_lines():
    items = P.parse_budget_items(SY.budget_g())
    pool = P.pool_lines(items)
    assert pool["vat"] == 300_000_000 * 1000 and pool["pit"] == (120 + 20 + 10) * 10**6 * 1000
    assert pool["cit"] == 130_000_000 * 1000
    assert pool["excise"] == (30 + 40 + 10 + 3 + 1 + 5 + 4) * 10**6 * 1000      # 1221-1225, 1231, 1233
    assert pool["other"] == (2_000_000 + 500_000 + 3_000_000) * 1000             # 1131, 1234, 132x
    assert pool["social"] == (350_000_000 + 40_000_000) * 1000                   # 161x, 162x
    with pytest.raises(P.ParseError):
        P.pool_lines({1211: D(1)})


def test_cnb_quarters_drop_float_noise_and_fill_missing_quarters(snap):
    q = P.parse_cnb_quarterly(X.read_workbook(snap.cnb_indicators))
    assert q[2026] == [D("2.1"), D("2.4"), D("2.6"), D("2.4")] and q[2028][3] is None
    a = P.cnb_annual(q)
    assert a[2026] == D("2.375") and a[2028] == D("2.025")                  # (2.1 + 2.0 + 2.0 + 2.0) / 4


def test_cpi_budget_and_reports(snap):
    assert P.parse_csu_cpi(P.read_text(snap.csu_cpi)) == D("2.5")
    with pytest.raises(P.ParseError):
        P.parse_csu_cpi("Průměrná roční míra inflace")
    assert P.parse_ct_budget(P.read_text(snap.ct_budget)) == F(6_700_000_000)
    n, real = P.parse_ct_report(P.read_text(snap.ct_report), P.read_text(snap.ct_report, layout=False))
    assert n == 3_700_000 and real == 6_400_000_000
    assert P.parse_cro_chart(snap.cro_chart.read_text(encoding="utf-8")) == F(2_400_000_000)
    stock, rev = P.parse_cro_report(P.read_text(snap.cro_report), P.read_text(snap.cro_report, layout=False))
    assert stock == 3_050_000 and rev == 2_300_000_000


def test_cro_report_arithmetic_and_date_column_guards(snap):
    txt = snap.cro_report.read_text(encoding="utf-8")
    with pytest.raises(P.ParseError, match="does not equal"):
        P.parse_cro_report(txt, txt.replace("v částce 2 300 000", "v částce 2 400 000"))
    with pytest.raises(P.ParseError, match="31. 12"):
        P.parse_cro_report(txt.replace("k 31. 12. 2025", "k 30. 6. 2025"), txt)


def test_ct_budget_needs_the_2026_column():
    with pytest.raises(P.ParseError, match="no column for 2026"):
        P.parse_ct_budget(SY.ct_budget().replace("2026", "2027"))


def test_bill_amounts_must_match_the_constants():
    assert P.verify_bill(SY.bill()) == C.BILL_2027
    with pytest.raises(P.ParseError):
        P.verify_bill(SY.bill().replace("5 741 826 000", "5 741 826 001"))


def test_band_labels_bounds_and_schedule_multiples():
    assert P.band_bounds("25 - 49 zaměstnanců") == (25, 49) and P.band_bounds("10 000 a více zaměstnanců") == (10000, None)
    assert P.band_bounds("Bez zaměstnanců") == (0, 0)
    assert P.schedule_multiples(25, 49) == (5, 5) and P.schedule_multiples(500, 999) == (100, 100)
    assert P.schedule_multiples(250, 499) == (70, 70) and P.schedule_multiples(0, 0) == (0, 0)
    assert P.schedule_multiples(20, 30) == (0, 5)       # straddles the 24/25 gap: minimum 0
    assert P.schedule_multiples(45, 60) == (0, 10)
    assert P.schedule_multiples(400, 600) == (0, 100)
    with pytest.raises(P.ParseError):
        P.band_bounds("something else")


def test_employer_counts_skip_terminated_entities_and_reject_unknown_codes(snap, tmp_path):
    labels = P.read_band_codes(snap.band_codes)
    assert len(labels) == 20
    counts = P.count_employers(snap.res_csv, labels)
    assert counts["230"] == SY.BAND_COUNTS["230"]                       # 7 terminated entities are not counted
    bad = tmp_path / "bad.csv"
    bad.write_text("ICO,DDATZAN,KATPO\n1,,999\n", encoding="utf-8")
    with pytest.raises(P.ParseError, match="outside code list"):
        P.count_employers(bad, labels)


def test_gross_line_labels(snap):
    got = P.gross_line_labels(P.read_text(snap.budget_c))
    assert got == {"vat": True, "cit": True, "pit": False, "excise_mineral_oils": True}
