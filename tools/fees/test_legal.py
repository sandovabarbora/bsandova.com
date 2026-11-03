"""Worked examples of the statute arithmetic on invented inflation series (design §2.2, §2.3, §2.7). Each expected
value is derived by hand in the comment beside it."""
from __future__ import annotations

from decimal import Decimal as D
from fractions import Fraction as F

import alloc
import config as C
import legal as L
import pytest


def series(**kw):
    base = {2025: D("2.0"), 2026: D("2.0"), 2027: D("2.0"), 2028: D("2.0"), 2029: D("2.0"), 2030: D("2.0")}
    base.update({int(k[1:]): D(v) for k, v in kw.items()})
    return base


def test_step_up_is_a_ceiling_in_integers():
    assert L.step_up(150, 106, 100) == 159          # 159.0 exactly
    assert L.step_up(55, 106, 100) == 59            # 58.3 -> 59
    assert L.step_up(159, 106, 100) == 169          # 168.54 -> 169
    assert L.step_up(5, 11, 10) == 6                # 5.5 -> 6
    assert L.step_up(10, 11, 10) == 11              # exact, no rounding up


def test_current_law_trigger_year_and_restart():
    # 2.5 + 2.5 = 5.0, + 2.0 = 7.0 > 6 in 2027 -> step on 1 July 2028; window restarts with 2028: 2.0 + 2.0 = 4.0 < 6
    infl = series(y2025="2.5", y2026="2.5")
    assert L.current_law_steps(infl, 2025) == [2027]
    m = L.monthly_amounts("CT", infl, 2025, notice={})
    assert m[2027] == [150] * 12
    assert m[2028] == [150] * 6 + [159] * 6        # half-year July step
    assert m[2029] == [159] * 12
    assert L.year_sums(m)[2028] == 6 * 150 + 6 * 159 == 1854
    assert L.monthly_amounts("CRO", infl, 2025, notice={})[2028] == [55] * 6 + [59] * 6


def test_threshold_is_strict():
    # 2.0 x 3 = 6.0 is not above 6 (2027); the sum reaches 8.0 in 2028 -> step in July 2029
    assert L.current_law_steps(series(), 2025) == [2028]


def test_window_starting_2026_is_the_check():
    # 2026: 2.5, 2027: 2.0, 2028: 2.0 = 6.5 > 6 in 2028; the 2025 window crosses in 2027
    infl = series(y2025="2.5", y2026="2.5")
    assert L.current_law_steps(infl, 2026) == [2028]
    assert L.current_law_steps(infl, 2025) == [2027]


def test_second_trigger_inside_the_window_is_computed():
    # 7.0 in 2025 crosses at once: July 2026 (159), window restarts at 2026: 7.0 again -> July 2027 (169), then 2027 -> July 2028 (180)
    infl = series(y2025="7.0", y2026="7.0", y2027="7.0")
    assert L.current_law_steps(infl, 2025)[:3] == [2025, 2026, 2027]
    m = L.monthly_amounts("CT", infl, 2025, notice={})
    assert m[2026] == [150] * 6 + [159] * 6 and m[2027] == [159] * 6 + [169] * 6 and m[2028] == [169] * 6 + [180] * 6


def test_2025_months_follow_the_statutory_change_of_may():
    m = L.monthly_amounts("CT", series(), 2025, notice={})
    assert L.year_sums(m)[2025] == 4 * 135 + 8 * 150
    assert L.year_sums(L.monthly_amounts("CRO", series(), 2025, notice={}))[2025] == 4 * 45 + 8 * 55


def test_notice_override_replaces_the_model_path_from_its_month():
    notice = {"CT": {(2027, 1): 160, (2028, 1): 170}}
    m = L.monthly_amounts("CT", series(y2025="2.5", y2026="2.5"), 2025, notice=notice)
    assert m[2026] == [150] * 12 and m[2027] == [160] * 12 and m[2028] == [170] * 12   # no model step on top
    assert L.monthly_amounts("CRO", series(), 2025, notice=notice)[2027] == [55] * 12


def test_bill_trigger_and_restart_at_the_crossing_year():
    # R1: 2026 4.0 + 2027 4.0 = 8 (t=2028, no); + 2028 3.0 = 11 > 10 at Y=2028 -> raised from 2029
    infl = series(y2026="4.0", y2027="4.0", y2028="3.0")
    amounts, trig = L.bill_path(5_741_826_000, infl, "R1")
    assert amounts[2027] == amounts[2028] == 5_741_826_000
    assert amounts[2029] == 6_316_008_600          # 5 741 826 000 x 11 / 10, exact
    assert trig == [{"crossed_in": 2028, "raised_from": 2029, "window": [2026, 2028]}]
    # the next window starts at 2028 (counted again): 3.0 + 2.0 = 5.0 -> no second step in 2030
    assert amounts[2030] == amounts[2029]


def test_bill_window_counts_the_crossing_year_again_and_can_trigger_twice():
    # 6.0 each year: [2026,2027] = 12 > 10 at t=2028 (Y=2027), restart at 2027: [2027,2028] = 12 > 10 at t=2029, again for 2030
    infl = series(y2026="6.0", y2027="6.0", y2028="6.0", y2029="6.0")
    amounts, trig = L.bill_path(1000, infl, "R1")
    assert [t["raised_from"] for t in trig] == [2028, 2029, 2030]
    assert [t["window"] for t in trig] == [[2026, 2027], [2027, 2028], [2028, 2029]]
    assert (amounts[2028], amounts[2029], amounts[2030]) == (1100, 1210, 1331)


def test_r1_and_r2_differ():
    # 3.3 three times: sum 9.9 is not above 10, but 1.033^3 - 1 = 0.10230... is above 0.10
    infl = series(y2026="3.3", y2027="3.3", y2028="3.3", y2029="0.0")
    assert L.bill_path(1000, infl, "R1")[1] == []
    r2_amounts, r2_trig = L.bill_path(1000, infl, "R2")
    assert r2_trig[0]["raised_from"] == 2029 and r2_amounts[2029] == 1100


def test_r2_threshold_is_strict_in_exact_decimals():
    # (1.1)(1.0) is exactly 1.10: not above 0.10 -> no trigger; one tenth more triggers
    assert not L.bill_exceeds([D("10.0")], "R2")
    assert L.bill_exceeds([D("10.1")], "R2")
    assert not L.bill_exceeds([D(5), D(5)], "R1") and L.bill_exceeds([D(5), D("5.1")], "R1")


def test_price_levels_and_shock():
    infl = L.inflation_series(D("2.5"), {2026: D("2.0"), 2027: D("3.0")}, shock=1)
    assert infl[2025] == D("2.5") and infl[2026] == D("3.0") and infl[2027] == D("4.0") and infl[2029] == D("3.0")
    pl = L.price_levels(L.inflation_series(D("2.5"), {2027: D(10)}, 0))
    assert pl[2026] == 1 and pl[2027] == F(11, 10) and pl[2028] == F(11, 10) * F(102, 100)


def inputs(**kw):
    d = {"csu_2025": D("2.5"), "cnb_annual": {2026: D("2.5"), 2027: D("2.0"), 2028: D("2.0")},
         "fee_line_2026": {"CT": F(3_100_000_000), "CRO": F(1_300_000_000)},
         "realised_2025": {"CT": F(2_900_000_000), "CRO": F(900_000_000)}} | kw
    return L.QaInputs(**d)


def test_paths_real_values_and_x_without_any_trigger():
    # flat 2.0 %: current law steps in July 2029 (sum 8 at 2028); the bill never triggers before 2030 data (4 x 2 = 8 < 10)
    inp = inputs(csu_2025=D("0.0"), cnb_annual={y: D(0) for y in range(2026, 2031)})
    r = L.qa_member(inp, 0, "R1", "A")
    assert r["current_law_steps"] == [] and r["paths_2_and_3_coincide"]
    # zero inflation: price level 1, path 1 = baseline each year, path 2 = bill
    assert r["real"]["p1"] == 4 * 4_400_000_000
    assert r["real"]["p2"] == 4 * 7_807_592_000 == r["real"]["p3"]
    assert r["x"] == F(17_600_000_000 - 31_230_368_000, 10**9)


def test_half_year_step_enters_path_1_pro_rata():
    inp = inputs(csu_2025=D("3.5"), cnb_annual={2026: D("3.5"), 2027: D(0), 2028: D(0)})
    # 3.5 + 3.5 = 7.0 > 6 in 2026 -> July 2027: CT 159, CRO 59; S(2027) = 6x150+6x159 = 1854, S(2026) = 1800
    r = L.qa_member(inp, 0, "R1", "A")
    assert r["current_law_steps"][0] == 2026
    nominal = r["nominal"]["p1"]["CT"]
    assert nominal[2027] == F(3_100_000_000) * 1854 / 1800
    assert nominal[2028] == F(3_100_000_000) * 1908 / 1800
    assert r["nominal"]["p1"]["CRO"][2027] == F(1_300_000_000) * (6 * 55 + 6 * 59) / (12 * 55)


def test_baseline_b_indexes_the_realised_2025_revenue():
    inp = inputs(csu_2025=D(0), cnb_annual={})
    r = L.qa_member(inp, 0, "R1", "B")
    # CT: 5.4 bn x 1800 / (4x135 + 8x150 = 1740)
    assert r["baseline_2026"]["CT"] == F(2_900_000_000) * 1800 / 1740
    assert r["baseline_2026"]["CRO"] == F(900_000_000) * 660 / (4 * 45 + 8 * 55)


def test_baseline_a_falls_back_to_b_for_a_broadcaster_without_a_fee_line():
    inp = inputs(fee_line_2026={"CT": F(3_100_000_000), "CRO": None})
    r = L.qa_member(inp, 0, "R1", "A")
    assert r["baseline_2026"]["CT"] == 3_100_000_000
    assert r["baseline_2026"]["CRO"] == F(900_000_000) * 660 / 620       # S(2026) = 12 x 55; S(2025) = 4 x 45 + 8 x 55


def test_twelve_members_and_the_primary():
    ms = L.qa_members(inputs())
    assert len(ms) == 12
    assert len({(m["shock"], m["reading"], m["baseline"]) for m in ms}) == 12
    assert (0, "R1", "A") in {(m["shock"], m["reading"], m["baseline"]) for m in ms}


@pytest.mark.parametrize("xs,label", [
    ([F(1, 10), F(5)], "bill lower"), ([F(-1, 10), F(-3)], "bill higher"),
    ([F(9, 100), F(-9, 100)], "about equal"), ([F(1), F(-1)], "depends on the assumption"),
    ([F(1), F(5, 100)], "depends on the assumption"), ([F(99, 1000), F(1, 10)], "depends on the assumption")])
def test_labels_and_the_tie_threshold(xs, label):
    assert L.qa_label(xs) == label


def test_shock_moves_triggers_and_deflator_together():
    inp = inputs(csu_2025=D("2.0"), cnb_annual={2026: D("1.0"), 2027: D("1.0"), 2028: D("1.0")})
    lo, hi = L.qa_member(inp, -1, "R1", "A"), L.qa_member(inp, 1, "R1", "A")
    assert lo["inflation"][2028] == 0 and hi["inflation"][2028] == 2 and lo["inflation"][2025] == 2   # 2025 is published
    assert lo["price_level"][2030] < hi["price_level"][2030]


def test_largest_remainder_sums_exactly_and_is_deterministic():
    assert alloc.largest_remainder(10, [1, 1, 1]) == [4, 3, 3]          # 3.33 each: the first index takes the extra crown
    assert alloc.largest_remainder(100, [F(1, 3), F(1, 3), F(1, 3)]) == [34, 33, 33]
    assert alloc.largest_remainder(7, [0, 5, 5]) == [0, 4, 3]
    assert alloc.largest_remainder(0, [1, 2]) == [0, 0]
    out = alloc.largest_remainder(7_807_592_000, [F(13, 7), F(2, 11), F(5), F(1, 3)])
    assert sum(out) == 7_807_592_000
    with pytest.raises(ValueError):
        alloc.largest_remainder(5, [0, 0])
    with pytest.raises(ValueError):
        alloc.largest_remainder(5, [1, -1])


def test_the_bills_total_is_the_sum_of_its_two_amounts():
    assert C.BILL_TOTAL == 7_807_592_000
