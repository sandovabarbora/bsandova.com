"""The estimation on invented projects, checked against hand calculations: the label bands at their edges, D_eff,
the 180-day boundaries, the bounds and the decomposition, the Aalen–Johansen curve, Q3, the median split and Q5."""
from __future__ import annotations

import datetime as dt
import json
from fractions import Fraction as F

import analysis as A
import config as C
import parse as P
import pytest
import synth as SY

LD = dt.date(2026, 1, 30)                                   # list A's date
DAY = dt.timedelta(days=1)


def project(ev="1P/2016", list_name="A", list_date=LD, **kw) -> A.Project:
    kw.setdefault("title", "Invented")
    kw.setdefault("request_date", dt.date(2016, 1, 1))
    listed = frozenset(kw.pop("listed", ()))
    return A.Project(P.Row(list_name, 1, ev, listed=listed, **kw), list_date)


def mature(**kw) -> A.Project:
    # a deadline long before the list date
    kw.setdefault("deadline", dt.date(2020, 1, 1))
    kw.setdefault("evidence_date", (dt.date(2016, 6, 1),))
    return project(**kw)


# ---------------------------------------------------------------- §5 labels

@pytest.mark.parametrize("lo, hi, want", [
    (F(95, 100), F(95, 100), A.NEARLY_ALL_PAID),
    (F(95, 100), F(1), A.NEARLY_ALL_PAID),
    (F(80, 100), F(9499, 10000), A.MOST_PAID),
    (F(80, 100), F(80, 100), A.MOST_PAID),
    (F(7999, 10000), F(7999, 10000), A.SUBSTANTIALLY_LESS),
    (F(0), F(1, 2), A.SUBSTANTIALLY_LESS),
    (F(7999, 10000), F(80, 100), A.DEPENDS),
    (F(9499, 10000), F(95, 100), A.DEPENDS),
    (F(1, 2), F(99, 100), A.DEPENDS),
])
def test_label_bands_at_their_edges(lo, hi, want):
    assert A.label(lo, hi) == want


def test_no_label_without_a_denominator():
    assert A.label(None, None) is None


# ---------------------------------------------------------------- §2.4 and §2.5

def test_d_eff_adds_365_days_only_with_a_1st_decision():
    assert project(deadline=dt.date(2020, 1, 1)).d_eff == dt.date(2020, 1, 1)
    assert project(deadline=dt.date(2020, 1, 1), decision_1_date=dt.date(2019, 5, 1)).d_eff == dt.date(2020, 12, 31)


def test_deadline_falls_back_to_the_registration_certificate_plus_4_years_and_else_is_none():
    assert project(registration_date=dt.date(2016, 2, 29)).deadline == dt.date(2020, 2, 29)
    assert project(registration_date=dt.date(2017, 3, 1)).deadline == dt.date(2021, 3, 1)
    p = project(allocation=100)
    assert p.deadline is None and p.d_eff is None and not p.mature(180)


def test_mature_exactly_at_d_eff_plus_180_days():
    d = LD - 180 * DAY
    assert project(deadline=d).mature(180)
    assert not project(deadline=d + DAY).mature(180)
    assert not project(deadline=d, decision_1_date=dt.date(2020, 1, 1)).mature(180)   # D_eff is a year later


def test_payout_pending_for_a_decision_less_than_180_days_old():
    assert project(decision_2_date=LD - 180 * DAY).status(180) == A.DECIDED
    assert project(decision_2_date=LD - 179 * DAY).status(180) == A.PENDING
    assert project(decision_2_date=LD - 179 * DAY).status(90) == A.DECIDED


def test_status_order_a_decision_beats_a_cancellation():
    assert project(cancellation_date=dt.date(2018, 1, 1)).status(180) == A.CANCELLED
    assert project(cancellation_date=dt.date(2018, 1, 1), decision_2_date=dt.date(2019, 1, 1)).status(180) == A.DECIDED
    assert project().status(180) == A.LAPSED


def test_p1_is_the_new_allocation_where_one_is_printed():
    assert project(allocation=100).p1 == 100
    assert project(allocation=100, new_allocation=80, listed={"new_allocation"}).p1 == 80
    assert project(allocation=100, new_allocation=0, listed={"new_allocation"}).p1 == 0


def test_q2_starts_at_the_earlier_of_two_evidence_dates():
    assert project(evidence_date=(dt.date(2018, 5, 1), dt.date(2017, 9, 1))).start == dt.date(2017, 9, 1)


# ---------------------------------------------------------------- Q1

def four_statuses():
    return [mature(ev="1P/2016", allocation=100, paid=90, decision_2_date=dt.date(2021, 1, 1)),   # decided
            mature(ev="2P/2016", allocation=100, decision_2_date=LD - 10 * DAY),                     # pending
            mature(ev="3P/2016", allocation=100, paid=20, decision_1_date=dt.date(2019, 1, 1)),      # lapsed
            mature(ev="4P/2016", allocation=100, cancellation_date=dt.date(2018, 1, 1)),             # cancelled
            mature(ev="5P/2016", allocation=50, paid=60, decision_2_date=dt.date(2021, 1, 1)),       # decided, V > P0
            project(ev="6P/2016", allocation=100, deadline=LD),                                      # not mature
            mature(ev="7P/2016")]                                                                    # no allocation


def test_q1_bounds_by_hand():
    q = A.q1(four_statuses())
    assert q["projects"] == 5 and q["promised"] == 450 and q["paid"] == 170
    assert q["r_low"] == F(170, 450)
    assert q["r_high"] == F(90 + 100 + 100 + 0 + 60, 450)      # pending and lapsed at max(V, P0)
    assert q["status_counts"] == {A.DECIDED: 2, A.PENDING: 1, A.CANCELLED: 1, A.LAPSED: 1}
    assert q["median_paid_over_p0"] == F(1, 5)                  # 0, 0, 1/5, 9/10, 6/5
    assert q["label"] == A.SUBSTANTIALLY_LESS                 # 170/450 and 350/450, both below 0.80


def test_decomposition_adds_up_to_the_shortfall_with_v_above_p0_negative():
    d = A.q1(four_statuses())["decomposition"]
    assert d["shortfall"] == 450 - 170
    assert d["parts"]["c_decided_paid_below_p0"] == 10
    assert d["parts"]["e_decided_payout_pending"] == 100
    assert d["parts"]["d_lapsed_paid_above_0_with_1st_decision"] == 80
    assert d["parts"]["a_cancelled_paid_0"] == 100
    assert d["parts"]["f_decided_paid_above_p0"] == -10
    assert sum(d["parts"].values()) == d["shortfall"] and sum(d["shares"].values()) == 1


# ---------------------------------------------------------------- Q2

def test_aalen_johansen_by_hand():
    obs = [(1, A.DECISION), (2, A.CANCELLATION), (2, None), (3, A.DECISION), (4, None)]
    steps = A.aalen_johansen(obs)
    # t=1: 5 at risk, 1/5 decided, S = 4/5; t=2: 4 at risk (the censoring of day 2 included), 4/5 * 1/4 cancelled,
    # S = 3/5; t=3: 2 at risk, decided + 3/5 * 1/2 = 1/2
    assert [(t, n) for t, n, _ in steps] == [(1, 5), (2, 4), (3, 2)]
    assert steps[-1][2] == {A.DECISION: F(1, 2), A.CANCELLATION: F(1, 5), A.LAPSE: F(0)}


def test_aalen_johansen_without_competing_events_is_one_minus_kaplan_meier():
    obs = [(1, A.DECISION), (2, None), (3, A.DECISION), (3, A.DECISION), (5, None)]
    # KM: (1 - 1/5) * (1 - 2/3) = 4/15; CIF = 11/15
    assert A.aalen_johansen(obs)[-1][2][A.DECISION] == F(11, 15)


def test_q2_observation_kinds_and_the_lapse_time():
    start = dt.date(2017, 1, 1)
    lapsed = mature(allocation=100, deadline=dt.date(2020, 1, 1))
    assert A.observation(lapsed, start, 180) == ((dt.date(2020, 1, 1) + 180 * DAY - start).days, A.LAPSE)
    late = mature(allocation=100, decision_2_date=dt.date(2021, 1, 1))     # after the lapse point: still a decision
    assert A.observation(late, start, 180) == ((dt.date(2021, 1, 1) - start).days, A.DECISION)
    both = mature(allocation=100, cancellation_date=dt.date(2018, 1, 1), decision_2_date=dt.date(2019, 1, 1))
    assert A.observation(both, start, 180)[1] == A.DECISION
    open_ = project(allocation=100, deadline=LD)
    assert A.observation(open_, start, 180) == ((LD - start).days, None)


def test_q2_horizons_need_30_at_risk_and_the_50_percent_time():
    start = dt.date(2017, 1, 1)
    ps = [mature(ev=f"{i}P/2017", allocation=100, evidence_date=(start,), decision_2_date=start + (100 + i) * DAY)
          for i in range(40)]
    ps += [project(ev=f"{i}P/2018", allocation=100, evidence_date=(start,), deadline=LD) for i in range(40, 70)]
    q = A.q2(ps)
    assert q["projects"] == 70 and q["events"][A.DECISION] == 40 and q["censored"] == 30
    one = q["horizons_years"][1]
    assert one["at_risk"] == 30 and one["estimable"] and one["cumulative_incidence"][A.DECISION] == F(40, 70)
    # the 35th decision, on day 134, brings the curve to 1/2; 36 were still at risk then
    assert q["years_to_50_percent_decided"] == F(134) / F(36525, 100)
    ten = A.q2(ps[:40] + ps[40:69])["horizons_years"][1]
    assert ten["at_risk"] == 29 and ten["cumulative_incidence"] == "not estimable"


def test_q2_not_reached_and_breaches_left_out():
    start = dt.date(2017, 1, 1)
    ps = [project(ev=f"{i}P/2018", allocation=100, evidence_date=(start,), deadline=LD) for i in range(40)]
    ps.append(mature(ev="1P/2019", allocation=100, evidence_date=(start,), decision_2_date=start - DAY))
    ps.append(mature(ev="2P/2019", allocation=100, evidence_date=()))
    q = A.q2(ps)
    assert q["years_to_50_percent_decided"] == "not reached"
    assert q["event_before_start"] == ["1P/2019"] and q["without_start_date"] == ["2P/2019"]


# ---------------------------------------------------------------- Q3

def test_q3_open_remainder_and_its_r1_version():
    ps = [project(ev="1P/2024", list_name="B", allocation=100, paid=30, deadline=LD),
          project(ev="2P/2024", list_name="B", allocation=100, paid=150, deadline=LD),            # V > P1: 0
          project(ev="3P/2024", list_name="B", allocation=100, new_allocation=200, listed={"new_allocation"},
                  deadline=LD),                                                                     # on P1
          project(ev="4P/2024", list_name="B", allocation=100, deadline=LD, decision_2_date=LD - 10 * DAY),  # pending
          project(ev="5P/2024", list_name="B", allocation=100, deadline=LD, decision_2_date=LD - 200 * DAY),  # decided
          project(ev="6P/2024", list_name="B", allocation=100, deadline=LD, cancellation_date=LD - DAY),      # cancelled
          mature(ev="7P/2016", list_name="B", allocation=100, paid=40)]                            # mature, lapsed
    q = A.q3(ps, {"r_low": F(1, 2), "r_high": F(1)})
    b = q["lists"]["B"]
    assert b["open_projects"] == 4
    assert b["o"] == 70 + 0 + 200 + 100
    assert b["o_r_low"] == 20 + 0 + 100 + 50 and b["o_r_high"] == b["o"]
    assert b["o_ratio_to_s2026"] == F(370, C.S2026)
    assert b["mature_lapsed_projects"] == 1 and b["mature_lapsed_remainder"] == 60


# ---------------------------------------------------------------- Q4

def test_q4_median_tie_goes_low_and_the_largest_is_left_out():
    ps = [mature(ev=f"{i}P/2016", allocation=a, paid=a, decision_2_date=dt.date(2021, 1, 1))
          for i, a in enumerate((100, 200, 200, 300))]
    q = A.q4(ps)
    assert q["median_p0"] == 200
    assert q["above_median"]["projects"] == 1 and q["at_or_below_median"]["projects"] == 3
    assert q["top_share"]["share_of_p0"] == 1                                   # four projects, top five
    assert q["without_largest"]["left_out"] == "3P/2016" and q["without_largest"]["promised"] == 500
    odd = A.q4(ps[:3])
    assert odd["median_p0"] == 200 and odd["above_median"]["projects"] == 0


def test_the_median_is_exact():
    assert A.median([1, 2]) == F(3, 2) and A.median([]) is None


# ---------------------------------------------------------------- Q5

def test_q5_base_at_the_rate_of_the_request_date():
    ps = [mature(ev="1P/2024", allocation=20, request_date=dt.date(2024, 12, 31)),
          mature(ev="2P/2025", allocation=25, request_date=dt.date(2025, 1, 1)),
          mature(ev="3P/2025", allocation=35, request_date=dt.date(2025, 2, 1), cancellation_date=dt.date(2025, 6, 1))]
    q = A.q5(ps)["by_registration_year"]
    assert q["main"][2024] == {"projects": 1, "p0": 20, "base": 100, "base_low": 100}
    assert q["main"][2025] == {"projects": 1, "p0": 25, "base": 100, "base_low": F(25) / F(35, 100)}
    assert q["cancelled"][2025]["base"] == 140
    assert A.q5(ps)["by_evidence_year"]["main"] == {2016: {"projects": 2, "p0": 45, "base": 200,
                                                           "base_low": 100 + F(25) / F(35, 100)}}


# ---------------------------------------------------------------- §3 checks 4 and 5

def test_check_4_counts_order_breaches_and_flags_above_2_percent():
    ok = [mature(ev=f"{i}P/2016", registration_date=dt.date(2016, 2, 1)) for i in range(98)]
    bad = mature(ev="99P/2016", registration_date=dt.date(2016, 2, 1), decision_1_date=dt.date(2016, 3, 1))  # before OOE
    c = A.check_4([*ok, bad, mature(ev="100P/2016", deadline=None)])
    assert c["breaches"] == 1 and c["breach_numbers"] == ["99P/2016"] and c["without_deadline"] == ["100P/2016"]
    assert not c["flag"]
    assert A.check_4([*ok[:40], bad])["flag"]


def test_check_5_paid_above_p1_on_decided_projects():
    dec = {"decision_2_date": dt.date(2021, 1, 1)}
    ps = [mature(ev=f"{i}P/2016", allocation=100, paid=100, **dec) for i in range(49)]
    ps.append(mature(ev="50P/2016", allocation=100, paid=101, **dec))
    assert A.check_5(ps)["paid_above_p1"] == ["50P/2016"] and not A.check_5(ps)["flag"]
    assert A.check_5(ps[25:])["flag"]


# ---------------------------------------------------------------- the run

def test_run_on_invented_lists_is_json_and_carries_the_registered_parts(tmp_path):
    specs = SY.make_lists(tmp_path)
    lists = {s.name: P.parse_list(s.path, s.name) for s in specs}
    res = A.run(lists, specs)
    json.dumps(res)
    assert set(res) >= {"label", "q1", "q2", "q2_from_request", "q3", "q4", "q5", "counts", "checks_3", "checks_6",
                        "flags"}
    assert res["label"] == res["q1"]["label"]
    assert set(res["checks_6"]) == {"1_on_p1", "2_without_cancelled", "3_by_list", "4_by_registration_year",
                                    "5_all_decided", "6_r_floor", "7_q2_list_a", "8_margin"}
    assert set(res["checks_6"]["8_margin"]) == {"90", "365"}
    assert set(res["q3"]["lists"]) == {"A", "B"}


def test_run_refuses_on_a_data_step_stop(tmp_path):
    rows = SY.list_rows((2016, 2021))
    rows[1]["evidence"] = rows[0]["evidence"]
    specs = SY.make_lists(tmp_path, a=rows)
    lists = {s.name: P.parse_list(s.path, s.name) for s in specs}
    with pytest.raises(SystemExit, match="check_2"):
        A.run(lists, specs)
