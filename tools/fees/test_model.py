"""Q-B, firms and labels on invented inputs; each expected value is derived in the comment beside it."""
from __future__ import annotations

from decimal import Decimal as D
from fractions import Fraction as F

import alloc
import analysis as A
import config as C
import inputs as I
import model as M
import parse as P
import pytest
import synth as SY


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    return I.load(SY.make_snapshot(tmp_path_factory.mktemp("snap")))


@pytest.fixture(scope="module")
def inp(loaded):
    return loaded.qb


def replace(inp, **kw):
    return M.QbInputs(**{**inp.__dict__, **kw})


def test_living_minimum_of_the_mean_household():
    assert M.living_minimum(F(1), F(0)) == 4860                             # one person: the single-person amount
    assert M.living_minimum(F(2), F(0)) == 4470 + 4040                      # first adult + one further adult
    # 3 members, 1 child: 4470 + 4040 + one child at the mean of 3490, 3050, 2480 = 9020 / 3
    assert M.living_minimum(F(3), F(1)) == 4470 + 4040 + F(9020, 3)
    assert M.living_minimum(F(14, 10), F(2, 10)) == 4470 + F(2, 10) * 4040 + F(2, 10) * F(9020, 3)


def test_exemption_bound_flags_the_poorest_decile_only_on_invented_data(inp):
    # decile 1: 110 000 x 1.25 / 12 = 11 458.33 against 2.15 x 5 879.3 = 12 640.5 -> exempt; decile 2: 16 875 > 14 156 -> not
    assert M.exempt_flags(inp.silc) == [True] + [False] * 9


def test_if_no_decile_is_exempt_the_first_is(inp):
    rich = P.SilcDeciles(**{**inp.silc.__dict__, "net": [D(10**7)] * 10})
    assert M.exempt_flags(rich) == [True] + [False] * 9


def test_payer_share_cap_and_shortfall():
    hh = [F(100)] * 2 + [F(0)] * 8
    shares, short = M.payer_shares(hh, [True, False] + [True] * 8, F(6, 10))
    assert shares[:2] == [0, 1] and short == F(6, 10) * 200 - 100           # wanted 120 payers among 100 households
    shares, short = M.payer_shares(hh, [True, False] + [True] * 8, F(4, 10))
    assert shares[:2] == [0, F(4, 5)] and short == 0                         # 0.4 x 200 / 100 = 0.8
    assert M.payer_shares(hh, None, F(6, 10)) == ([F(6, 10)] * 10, 0)


def test_fee_today_payments_and_burden(inp):
    e0 = M.fee_today(inp, None)
    total = sum(M.households(inp))
    pi_tv, pi_r = inp.payers_tv / total, inp.payers_r / total
    assert e0["pay_hh"][0] == 1800 * pi_tv + 660 * pi_r == e0["pay_hh"][9]
    assert e0["burden"][0] == e0["pay_hh"][0] / (F(SY.NET_CU[0]) * F(SY.CU[0]))
    # every decile pays alike, so the ratio of burdens is the inverse ratio of incomes: 600 000 x 1.95 over 110 000 x 1.25
    assert e0["ratio"] == (F(600_000) * F(195, 100)) / (F(110_000) * F(125, 100))
    assert e0["household_revenue"] == 1800 * inp.payers_tv + 660 * inp.payers_r
    e1 = M.fee_today(inp, M.exempt_flags(inp.silc))
    assert e1["pay_hh"][0] == 0 and e1["ratio"] == 0 and e1["shortfall_tv"] == 0
    assert sum(h * s for h, s in zip(M.households(inp), e1["share_tv"], strict=True)) == inp.payers_tv   # payers preserved


def test_payer_share_one_is_the_upper_bound_check(inp):
    assert M.fee_today(inp, None, pi_one=True)["pay_hh"][3] == 2460


def test_interpolation_averages_each_pair_to_its_quintile():
    q = [F(10), F(20), F(30), F(40), F(50)]
    d = M.interpolate_pairs(q)
    assert [(d[2 * k] + d[2 * k + 1]) / 2 for k in range(5)] == q
    # raw: decile 1 flat = 10, decile 2 at position 2 = 10 x 3/4 + 20 x 1/4 = 12.5; rescale by 20 / 22.5 = 8/9
    assert d[0] == F(80, 9) and d[1] == F(100, 9)
    assert M.to_deciles(q, False) == [10, 10, 20, 20, 30, 30, 40, 40, 50, 50]


def test_vat_content_by_hand(inp):
    # rows at 21 %, 12 % and 0 %; 2 persons per household; per person 121, 112 and 500 CZK
    vat_map = [{"coicop": "A", "kind": "row", "vat_rate_pct": "21"}, {"coicop": "B", "kind": "row", "vat_rate_pct": "12"},
               {"coicop": "C", "kind": "row", "vat_rate_pct": "0"}]
    exc_map = [{"coicop": c, "kind": "row", "excised": e} for c, e in (("A", "1"), ("B", "0"), ("C", "0"))]
    hbs = P.Hbs([D(1)] * 5, [D(2)] * 5, {"A": [D(121)] * 5, "B": [D(112)] * 5, "C": [D(500)] * 5})
    sp = M.spending_parts(replace(inp, hbs=hbs, vat_map=vat_map, excise_map=exc_map))
    assert sp["vat"][0] == 2 * (21 + 12)               # 121 x 21/121 = 21 and 112 x 12/112 = 12 per person
    assert sp["excise"][0] == 2 * 121 and sp["total"][0] == 2 * (121 + 112 + 500)


def test_allocation_sums_to_the_bills_total_in_every_scenario_and_spec(inp):
    specs = [M.AfterSpec(), M.AfterSpec(pit_basis="work"), M.AfterSpec(pit_basis="net"), M.AfterSpec(vat_mode="uniform"),
             M.AfterSpec(other_like_vat=True), M.AfterSpec(include_social=True), M.AfterSpec(interpolate=True),
             M.AfterSpec(cit_household_share=F(1, 2))]
    for spec in specs:
        r = M.after(inp, spec)
        assert sum(r["decile_total"]) + r["firms"] == C.BILL_TOTAL == 7_807_592_000
        assert sum(r["parts"].values()) == C.BILL_TOTAL
    for sc in ("vat_only", "pit_only"):
        r = M.after(inp, scenario=sc)
        assert sum(r["decile_total"]) == C.BILL_TOTAL and r["firms"] == 0


def test_base_split_across_taxes_follows_the_state_lines(inp):
    r = M.after(inp)
    names = ("vat", "excise", "pit", "cit")
    assert r["parts"] == dict(zip(names, alloc.largest_remainder(C.BILL_TOTAL, [inp.pool[k] for k in names]), strict=True))
    pool = sum(inp.pool[k] for k in names)
    assert abs(F(r["parts"]["vat"], C.BILL_TOTAL) - inp.pool["vat"] / pool) < F(1, C.BILL_TOTAL)
    assert r["firms"] == r["parts"]["cit"]                                   # CIT goes to firms entire
    assert M.out_of_pool_share(inp.pool) == inp.pool["other"] / (pool + inp.pool["other"])


def test_cit_half_to_households_splits_the_cit_part_by_largest_remainder(inp):
    r = M.after(inp, M.AfterSpec(cit_household_share=F(1, 2)))
    cit = r["parts"]["cit"]
    assert r["firms"] in (cit // 2, cit - cit // 2) and abs(r["firms"] - sum(r["by_tax"]["cit"])) <= 1
    assert sum(r["by_tax"]["cit"]) + r["firms"] == cit


def test_vat_only_gives_the_two_deciles_of_a_quintile_the_same_spending_per_household(inp):
    r = M.after(inp, scenario="vat_only")
    assert abs(r["per_hh"][0] - r["per_hh"][1]) < F(2, 480_000)            # equal split within a quintile, up to a crown each
    assert M.after(inp, M.AfterSpec(interpolate=True), "vat_only")["per_hh"][0] != r["per_hh"][0]


def test_check_2_stops_the_run_on_a_rounding_or_coding_error(inp, monkeypatch):
    real = alloc.largest_remainder
    monkeypatch.setattr(alloc, "largest_remainder",
                        lambda total, w: [x - 1 if i == 0 else x for i, x in enumerate(real(total, w))])
    with pytest.raises(M.CheckFailure):
        M.after(inp)


def test_gross_lines_with_the_2026_2027_shares(inp):
    gross = {"vat": F(1000), "cit": F(2000), "pit_employment": F(3000), "pit_other": F(500),
             "excise_mineral_oils": F(400), "excise_other": F(100)}
    small = replace(inp, gross_lines=gross)
    lines = M.state_lines(small, M.AfterSpec(lines="gross_v17"))
    state = 1 - F(1023, 10000) - F(2593, 10000)
    assert state == F(6384, 10000)                                           # 63.84 %
    assert lines["vat"] == 1000 * state and lines["cit"] == 2000 * state
    assert lines["pit"] == 3000 * (state - F(15, 1000)) + 500 * state        # employment: 62.34 %
    assert lines["excise"] == 400 * F(909, 1000) + 100                 # 90.9 % of mineral oils, all other excise
    v15 = M.state_lines(small, M.AfterSpec(lines="gross_v15"))
    assert v15["vat"] == 1000 * F(6639, 10000) and v15["pit"] == 3000 * F(6489, 10000) + 500 * F(6639, 10000)
    assert M.after(small, M.AfterSpec(lines="gross_v17"))["total"] == C.BILL_TOTAL
    with pytest.raises(P.ParseError):
        M.state_lines(inp, M.AfterSpec(lines="gross_v17"))


@pytest.mark.parametrize("lo,hi,label", [
    (F(12, 10), F(3), "the poorest tenth carries a higher share of its income than the richest tenth"),
    (F(1, 2), F(8, 10), "the poorest tenth carries a lower share of its income than the richest tenth"),
    (F(9, 10), F(11, 10), "the poorest tenth carries a similar share of its income as the richest tenth"),
    (F(0), F(3), "depends on the assumption"), (F(8, 10), F(1), "depends on the assumption"),
    (F(111, 100), F(3), "the poorest tenth carries a higher share of its income than the richest tenth")])
def test_label_today(lo, hi, label):
    assert M.label_today(lo, hi) == label


def test_band_edges_are_inside_the_similar_band():
    assert M.label_after(F(9, 10)) == "similar" and M.label_after(F(11, 10)) == "similar"
    assert M.label_after(F(1101, 1000)) == "higher" and M.label_after(F(899, 1000)) == "lower"


def test_label_change_uses_both_bounds():
    assert M.label_change(F(2), F(1), F(1)) == "higher after"
    assert M.label_change(F(1, 2), F(1), F(1)) == "lower after"
    assert M.label_change(F(1), F(1), F(1)) == "about the same"
    assert M.label_change(F(2), F(1), F(4)) == "depends on the assumption"     # 2.0 against 1 and 0.5 against 4
    assert M.label_change(F(2), F(0), F(1)) == "higher after"                  # exempt first decile: Y = 0, read as above the band


def test_monotonicity_note():
    n = M.monotonicity([F(1), F(2), F(2), F(1), F(3), F(4), F(4), F(5), F(5), F(6)])
    assert n == {"steps_total": 9, "steps_where_burden_rises": 5, "into_deciles": [2, 5, 6, 8, 10]}


def test_firm_range_from_bands(loaded):
    inp = loaded.qb
    low, high = M.firm_range(inp.employer_counts, inp.band_labels)
    n = SY.BAND_COUNTS
    big = ("340", "410", "420", "430", "440", "450", "460", "470", "510")
    exp = (5 * n["230"] + 10 * n["240"] + 20 * n["310"] + 30 * n["320"] + 70 * n["330"]
           + 100 * sum(n[c] for c in big)) * 205 * 12
    assert low == high == exp                                                 # no band straddles: the range is one value


def test_firm_remainder_plausibility_and_the_response(inp):
    f = M.firms_today(inp)
    assert f["remainder"] == inp.fee_revenue_2026 - (1800 * inp.payers_tv + 660 * inp.payers_r)
    assert f["plausible"] is False and f["validated"] is False and "range only" in f["response"]
    low, _ = M.firm_range(inp.employer_counts, inp.band_labels)
    exact = replace(inp, fee_revenue_2026=1800 * inp.payers_tv + 660 * inp.payers_r + low)
    assert M.firms_today(exact)["plausible"] is True
    assert M.firms_today(replace(inp, fee_revenue_2026=F(1)))["plausible"] is False          # negative remainder
    r = M.firms_today(replace(inp, employer_counts=None))
    assert r["range"] is None and r["validated"] is False


def test_seniors_cut_is_descriptive(inp):
    e1 = M.fee_today(inp, M.exempt_flags(inp.silc))
    one = M.seniors_cut(inp, e1)[0]
    assert one["mean_size"] == 1 and one["net_income_hh"] == 190_000          # 190 000 per person x 1 person
    assert one["exempt_by_rule"] is False       # 15 833 a month against 2.15 x 4 860 = 10 449
    assert one["burden_e0"] == one["pay_hh_e0"] / 190_000
    assert M.seniors_cut(replace(inp, seniors=None), e1) is None


def test_full_run_structure_and_readings(loaded):
    res = A.run(loaded.qb, loaded.qa, loaded.gross_labels)
    assert set(res["checks_flag"]) == {"1_fee_revenue_today", "2_allocation_to_the_crown"}
    assert {"1_window_from_2026", "2_total_in_2026_prices", "3_vat_uniform_rate", "4_pit_basis", "5_payer_share_one",
            "6_mean_of_household_ratios", "7_sharing_2026_2027", "8_seniors", "9a_social_insurance_in_pool",
            "9b_cit_half_to_households", "9c_interpolated_consumption", "9d_no_exemption"} <= set(res["checks_reported"])
    assert res["checks_reported"]["7_sharing_2026_2027"]["computable"] is False
    assert res["qa"]["reading_a"].startswith("If the bill passes as introduced")
    assert "Funded from the state budget at the average tax structure" in res["qb"]["reading_b"]
    assert res["reading_c"]["text"].startswith("Today ČT and ČRo get")
    assert "not like for like" in res["firms"]["reading"]
    assert len(res["qa"]["members"]) == 12
    assert res["qb"]["y_order_ok"] and res["qb"]["exempt_deciles_e1"] == [1]
    assert res["checks_reported"]["9d_no_exemption"]["y"] == res["qb"]["y_hi"]


def test_gross_check_runs_when_lines_are_available(loaded):
    gross = {"vat": F(10) ** 12, "cit": F(10) ** 11, "pit_employment": F(10) ** 11, "pit_other": F(10) ** 10,
             "excise_mineral_oils": F(10) ** 10, "excise_other": F(10) ** 9}
    qb = replace(loaded.qb, gross_lines=gross)
    res = A.run(qb, loaded.qa, loaded.gross_labels)
    assert res["checks_reported"]["7_sharing_2026_2027"]["computable"] is True
