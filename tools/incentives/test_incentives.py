"""Worked examples on made-up panels and project lists for the investment incentives study (design §2, §4, §6, §7).
No real MPSV or CzechInvest data is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import estimate as E
import projects as P
import screen as S

M = lambda y, m: y * 12 + m - 1


# ---------- made-up panels ----------

def clean_panel(n_events=24, n_comp=30, effect=-0.5, noise=0.05, seed=0, pre_trend=0.0):
    """Treated districts T00.. and comparison districts C00..; every event uses all comparisons, and a treated district
    is never a comparison, so the true Q1 is `effect` (years 1-3 minus years -2/-1)."""
    rng = np.random.default_rng(seed)
    months = np.arange(E.FIRST_MONTH, E.LAST_MONTH + 1)
    comps = [f"C{i:02d}" for i in range(n_comp)]
    treated = [f"T{i:02d}" for i in range(n_events)]
    cols = treated + comps
    level = rng.normal(6, 2, len(cols))
    nat = np.cumsum(rng.normal(0, 0.05, len(months)))
    y = level[None, :] + nat[:, None] + rng.normal(0, noise, (len(months), len(cols)))
    events = []
    for e, t in enumerate(treated):
        m0 = int(rng.integers(M(2006, 7), M(2021, 1) + 1))
        y[months >= m0, e] += effect
        y[:, e] += pre_trend * (months - m0) / 12 * (months < m0)
        events.append(E.Event(f"E{e:02d}", t, m0, tuple(comps), jobs=300.0 + 100 * e))
    return pd.DataFrame(y, index=months, columns=cols), events


def panels_of(wide, events, **kw):
    return [sp for ev in events if (sp := E.sub_panel(wide, ev, **kw))]


# ---------- estimator ----------

def test_recovers_known_effect():
    wide, events = clean_panel(effect=-0.5)
    r = E.estimate(panels_of(wide, events))
    assert r["q1"] == pytest.approx(-0.5, abs=0.02)
    assert r["pre_diff"] == pytest.approx(0.0, abs=0.02)
    for k in (0, 1, 2, 3):
        assert r[f"q2_y{k}"] == pytest.approx(-0.5, abs=0.03)


def test_null_case_interval_covers_zero_and_label_no_change():
    wide, events = clean_panel(effect=0.0, noise=0.05)
    res = E.run(panels_of(wide, events), draws=300, perms=300)
    assert abs(res["estimate"]) < 0.03
    assert res["ci95"][0] < 0 < res["ci95"][1]
    assert res["p_randomisation"] > 0.05
    assert res["label"] == "no change larger than 0.20 points"


def test_matches_statsmodels_with_full_dummies_and_weights():
    sm = pytest.importorskip("statsmodels.api")
    wide, events = clean_panel(n_events=3, n_comp=4, effect=-0.4, noise=0.3, seed=3)
    events[1] = E.Event("E01", "T01", events[1].month, ("C00", "C01"), 400.0)  # unequal n_e
    panels = panels_of(wide, events)
    ours = E.estimate(panels)["beta"]
    rows = []
    for sp in panels:
        n_e = len(sp.units) - 1
        for i, u in enumerate(sp.units):
            for j, k in enumerate(sp.years):
                rows.append({"y": sp.y[i, j], "unit": f"{sp.event.id}:{u}", "ey": f"{sp.event.id}:{k}",
                             "w": 1.0 if i == 0 else 1.0 / n_e, **{f"T{kk}": float(i == 0 and k == kk)
                                                                   for kk in E.YEARS if kk != -1}})
    d = pd.DataFrame(rows)
    ey = pd.get_dummies(d["ey"], dtype=float)
    X = pd.concat([d[[c for c in d if c.startswith("T")]], pd.get_dummies(d["unit"], dtype=float),
                   ey[[c for c in ey if not c.endswith(":-2")]]], axis=1)  # one event year per event left out
    fit = sm.WLS(d["y"], X, weights=d["w"]).fit()
    for k in E.YEARS:
        if k != -1:
            assert ours[k] == pytest.approx(fit.params[f"T{k}"], abs=1e-9)


def test_weights_give_each_event_equal_say():
    """Treated weight 1, comparisons 1/n_e: two events with 2 and 20 comparisons count equally."""
    wide, events = clean_panel(n_events=2, n_comp=20, effect=0.0, noise=0.0, seed=5)
    m_a, m_b = events[0].month, events[1].month
    wide.loc[wide.index >= m_a, "T00"] += -1.0
    wide.loc[wide.index >= m_b, "T01"] += -3.0
    ev = [E.Event("A", "T00", m_a, ("C00", "C01")), E.Event("B", "T01", m_b, tuple(f"C{i:02d}" for i in range(20)))]
    r = E.estimate(panels_of(wide, ev))
    assert r["q1"] == pytest.approx(-2.0, abs=1e-6)
    w = E.weights(np.array([True, False, False, False, False]))
    assert w.tolist() == [1.0, 0.25, 0.25, 0.25, 0.25]


def test_q1_formula_and_reference():
    beta = {-2: 0.2, -1: 0.0, 0: -0.1, 1: -0.3, 2: -0.3, 3: -0.6}
    assert E.q1(beta) == pytest.approx(-0.4 - 0.1)
    assert E.q1(beta, E.POST, (-1,)) == pytest.approx(-0.4)
    s = E.stats_of(beta, q3_den=0.5)
    assert s["pre_diff"] == pytest.approx(-0.2)
    assert s["q2_y0"] == pytest.approx(-0.2)
    assert s["q3"] == pytest.approx(-1.0)


def test_q3_denominator_event_weighted():
    wide, events = clean_panel(n_events=2, n_comp=3)
    pop = wide * 0 + 10_000.0
    pop["T01"] = 20_000.0
    ps = panels_of(wide, [E.Event("a", "T00", events[0].month, ("C00", "C01"), 300.0),
                          E.Event("b", "T01", events[1].month, ("C00", "C01"), 400.0)], pop=pop)
    assert E.q3_denominator(ps) == pytest.approx((3.0 + 2.0) / 2)


# ---------- missing months ----------

def test_missing_month_dropped_for_all_districts_of_the_event():
    wide, events = clean_panel(n_events=1, n_comp=3, noise=0.0, effect=0.0)
    ev = events[0]
    m = ev.month + 13  # year 1
    wide.loc[m, "C01"] = np.nan
    wide.loc[m, "T00"] += 100.0  # an outlier in the dropped month must not reach the means
    sp = E.sub_panel(wide, ev)
    full = wide.loc[[x for x in range(ev.month + 12, ev.month + 24) if x != m], ["T00", "C00", "C01", "C02"]].mean()
    assert sp.y[:, sp.years.index(1)] == pytest.approx(full.to_numpy())


def test_year_with_fewer_than_ten_months_drops_the_event():
    wide, events = clean_panel(n_events=1, n_comp=3)
    ev = events[0]
    wide.loc[ev.month - 24: ev.month - 22, "C02"] = np.nan  # 3 of 12 months of year -2 gone, 9 left
    assert E.sub_panel(wide, ev) is None
    wide2, _ = clean_panel(n_events=1, n_comp=3)
    wide2.loc[ev.month - 24: ev.month - 23, "C02"] = np.nan  # 10 left
    assert E.sub_panel(wide2, ev) is not None


def test_event_outside_data_is_dropped():
    wide, _ = clean_panel(n_events=1, n_comp=3)
    late = E.Event("late", "T00", M(2022, 6), ("C00", "C01", "C02"))
    assert E.sub_panel(wide, late) is None


# ---------- bootstrap with clones ----------

def test_clone_rows_and_n_e_on_copies():
    wide, events = clean_panel(n_events=1, n_comp=3)
    sp = E.sub_panel(wide, events[0])
    rows = E.clone_rows(sp, {"T00": 2, "C00": 3, "C02": 1})
    assert rows.tolist() == [0, 0, 1, 1, 1, 3]
    d = E.design_of(sp, rows, treated_row=0)
    assert d.treated.tolist() == [True, True, False, False, False, False]
    assert d.w.tolist() == [1.0, 1.0, 0.25, 0.25, 0.25, 0.25]
    assert E.design_of(sp, E.clone_rows(sp, {"C00": 2}), treated_row=0) is None  # no treated copy
    assert E.design_of(sp, E.clone_rows(sp, {"T00": 1}), treated_row=0) is None  # no comparison copy


def test_clones_get_their_own_fixed_effects():
    """Two copies of a comparison district equal one copy with double weight only through n_e; their own FE keep
    the estimate unchanged when the copies are identical."""
    wide, events = clean_panel(n_events=1, n_comp=3, noise=0.3, seed=9)
    sp = E.sub_panel(wide, events[0])
    once = E.fit([E.design_of(sp, np.array([0, 1, 2, 3]))])
    twice = E.fit([E.design_of(sp, np.array([0, 1, 1, 2, 2, 3, 3]))])
    assert once[3] == pytest.approx(twice[3], abs=1e-10)


def test_bootstrap_redraws_empty_draws_and_is_reproducible():
    wide, events = clean_panel(n_events=1, n_comp=1, noise=0.1)
    ps = panels_of(wide, events)
    a = E.bootstrap(ps, draws=50, seed=1)
    b = E.bootstrap(ps, draws=50, seed=1)
    assert len(a["draws"]) == 50
    assert a["redrawn"] > 0  # with two districts, half the draws miss one side
    assert a["redrawn"] == b["redrawn"] and a["draws"]["q1"].equals(b["draws"]["q1"])


def test_bootstrap_interval_and_label_for_known_effect():
    wide, events = clean_panel(effect=-0.5, noise=0.2, seed=11)
    res = E.run(panels_of(wide, events), draws=400, perms=200)
    assert res["ci95"][1] < 0 and res["ci95"][1] - res["ci95"][0] < 0.2
    assert res["p_randomisation"] <= 0.05
    assert res["label"] == "lower unemployment after the promise"


# ---------- randomisation inference ----------

def test_permutation_p_one_event_large_effect():
    """One event, pool of n_e + 1 districts: only drawing the true treated reaches the observed |Q1|."""
    wide, events = clean_panel(n_events=1, n_comp=9, effect=-5.0, noise=0.01, seed=2)
    ps = panels_of(wide, events)
    obs = E.estimate(ps)["q1"]
    r = E.permutation_p(ps, obs, perms=2000, seed=E.SEED_PERM)
    assert r["p"] == pytest.approx(0.1, abs=0.02)


def test_permutation_p_null_not_small():
    wide, events = clean_panel(effect=0.0, noise=0.2, seed=4)
    ps = panels_of(wide, events)
    r = E.permutation_p(ps, E.estimate(ps)["q1"], perms=300)
    assert r["p"] > 0.05


def test_permutation_pool_includes_true_treated():
    wide, events = clean_panel(n_events=1, n_comp=2, effect=-5.0, noise=0.01)
    ps = panels_of(wide, events)
    r = E.permutation_p(ps, E.estimate(ps)["q1"], perms=600)
    assert r["p"] == pytest.approx(1 / 3, abs=0.06)


# ---------- labels and minimum rule ----------

@pytest.mark.parametrize("est,ci90,ci95,p,expect", [
    (-0.10, [-0.15, -0.05], [-0.19, -0.0001], 0.05, "lower unemployment after the promise"),
    (-0.0999, [-0.15, -0.05], [-0.19, -0.0001], 0.05, "no change larger than 0.20 points"),
    (-0.30, [-0.4, -0.2], [-0.45, -0.1], 0.051, "inconclusive"),
    (-0.30, [-0.4, -0.2], [-0.45, 0.0], 0.01, "inconclusive"),
    (0.10, [0.05, 0.15], [0.0001, 0.2], 0.04, "higher unemployment after the promise"),
    (0.0, [-0.20, 0.20], [-0.25, 0.25], 0.5, "no change larger than 0.20 points"),
    (0.0, [-0.2001, 0.1999], [-0.25, 0.25], 0.5, "inconclusive"),
    (0.0, [-0.25, 0.15], [-0.3, 0.2], 0.5, "inconclusive"),
    (0.0, [-0.2001, 0.2001], [-0.3, 0.3], 0.5, "underpowered"),
    (0.0, [-0.30, 0.30], [-0.4, 0.4], 0.5, "underpowered"),
])
def test_label_boundaries(est, ci90, ci95, p, expect):
    assert E.label(est, ci90, ci95, p, [-0.1, 0.1]) == expect


def test_label_suffix_for_differing_pre_paths():
    lab = E.label(0.0, [-0.1, 0.1], [-0.15, 0.15], 0.5, [0.01, 0.2])
    assert lab == "no change larger than 0.20 points with differing paths in the two years before the promise"


def test_minimum_rule_removes_labels_1_to_3():
    assert E.label(-0.5, [-0.6, -0.4], [-0.7, -0.3], 0.0, [-0.1, 0.1], minimum_met=False) == "inconclusive"
    assert E.label(0.0, [-0.1, 0.1], [-0.2, 0.2], 0.5, [-0.1, 0.1], minimum_met=False) == "inconclusive"
    assert E.label(0.0, [-0.3, 0.3], [-0.4, 0.4], 0.5, [-0.1, 0.1], minimum_met=False) == "underpowered"
    assert E.label(-0.5, [-0.6, -0.4], [-0.7, -0.3], 0.0, [-0.1, 0.1], descriptive=True) is None


def test_minimum_counts_events_and_distinct_districts():
    wide, events = clean_panel(n_events=20, n_comp=5)
    ps = panels_of(wide, events)
    assert E.minimum_met(ps)
    assert not E.minimum_met(ps[:19])
    same = [E.SubPanel(E.Event(sp.event.id, f"T{i % 14:02d}", sp.event.month, ()), sp.units, sp.years, sp.y)
            for i, sp in enumerate(ps)]
    assert not E.minimum_met(same)  # 20 events in 14 districts


# ---------- checks ----------

def test_checks_run_on_made_up_panel():
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.1, seed=6)
    ps = panels_of(wide, events)
    regions = {u: ("R1" if int(u[1:]) % 2 else "R2") for u in wide.columns}
    out = E.checks(wide, events, ps, draws=30, perms=30, pop=None, boundary={"2007": ["C00"], "2016": []},
                   all_districts=list(wide.columns), regions=regions)
    assert out["1_jobs_1000"]["n_events"] == sum(ev.jobs >= 1000 for ev in events)
    assert out["1_without_largest"]["n_events"] == len(ps) - 1
    assert out["9_placebo_two_years_earlier"]["estimate"] == pytest.approx(0.0, abs=0.05)
    assert out["10_reference_year_minus1"]["estimate"] == pytest.approx(-0.5, abs=0.05)
    assert out["7_years_1_to_5"]["estimate"] == pytest.approx(-0.5, abs=0.05)
    assert out["11_control_change_minus3_to_minus2"]["n_events"] > 0
    assert "C00" not in E.restrict_pool(ps[0], set(ps[0].units) - {"C00"}).units


def test_covers_crisis_years():
    # years −2..3 run from 24 months before the decision month to 47 after it
    assert not E.covers(E.Event("x", "T", M(2012, 1), ()), *E.CRISIS)
    assert E.covers(E.Event("y", "T", M(2011, 12), ()), *E.CRISIS)
    assert E.covers(E.Event("v", "T", M(2005, 2), ()), *E.CRISIS)
    assert not E.covers(E.Event("u", "T", M(2005, 1), ()), *E.CRISIS)
    assert E.covers(E.Event("z", "T", M(2016, 2), ()), *E.COVID)
    assert not E.covers(E.Event("w", "T", M(2016, 1), ()), *E.COVID)


def test_refuses_without_unblind(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["estimate.py"])
    with pytest.raises(SystemExit, match="refused"):
        E.main()


# ---------- places, blockers, clean windows ----------

def fake_geo():
    """Region A: districts 3201 (Alfa, seat Alfa), 3202 (Beta); region B: 3301 (Gama); Prague 3100; plus filler
    districts F01..F12 in region C so pools can reach 10."""
    munis = {"1": ("Alfa", "3201"), "2": ("Beta", "3202"), "3": ("Gama", "3301"), "4": ("Ves", "3201"),
             "5": ("Ves", "3202"), "6": ("Praha", "3100"), "7": ("Delta", "3202")}
    dname = {"3201": "Alfa", "3202": "Beta", "3301": "Gama", "3100": "Hlavní město Praha"}
    dkraj = {"3201": "A kraj", "3202": "A kraj", "3301": "B kraj", "3100": "Hlavní město Praha"}
    for i in range(1, 13):
        code = f"39{i:02d}"
        dname[code], dkraj[code] = f"Filler{i}", "C kraj"
        munis[f"F{i}"] = (f"Filler{i}", code)
    g = P.Geo({k: v[1] for k, v in munis.items()}, {k: v[0] for k, v in munis.items()}, dname, dkraj)
    for code, (name, _) in munis.items():
        g.names.setdefault(P.norm(name), set()).add(code)
    g.parts = {P.norm("Horní Alfa"): {"1"}}
    g.plain_parts = {P.plain("Horní Alfa"): {"1"}}
    return g


def project_list(rows):
    d = pd.DataFrame(rows)
    for c in ("ipo_zruseni", "ipo_rezim"):
        d[c] = d.get(c, "")
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d["month"] = d["date"].map(P.ym)
    d["id_projekt"] = d["id_projekt"].astype(str)
    return d


def events_of(rows, geo=None, boundaries=None, **kw):
    geo = geo or fake_geo()
    d = project_list(rows)
    p = P.attach_places(d, P.places_table(d, geo))
    return P.build_events(p, geo, boundaries or {"2007": [], "2016": []}, **kw)


def row(i, place, date, jobs=300, kraj="A kraj", **kw):
    return {"id_projekt": i, "lokalita_mesto": place, "lokalita_kraj": kraj, "date": date, "jobs": jobs} | kw


def test_matching_rules():
    g = fake_geo()
    assert P.match("A kraj", "Alfa", g).status == "matched"
    m = P.match("A kraj", "Ves (okres Beta)", g)
    assert m.status == "matched" and m.districts == {"3202"}
    assert P.match("A kraj", "Alfa, Gama", g).status == "multi"
    assert P.match("A kraj", "Alfa atd.", g).status == "multi"
    assert P.match("A kraj", "Horní Alfa", g).districts == {"3201"}
    assert P.match("A kraj", "Alfa - Horní Alfa", g).districts == {"3201"}
    assert P.match("A kraj", "Nowhere", g).status == "unmatched"
    assert P.match("A kraj", "Nowhere", g).blocking(g) == {"3201", "3202"}
    assert P.match("A kraj", "Alfa - Beta", g).status == "multi"  # two municipalities joined by a hyphen
    assert P.match("B kraj", "Gamma", g).districts == {"3301"}  # one letter away from one name in the region
    assert P.match("A kraj", "Gama", g).districts == {"3301"}  # a municipality outside the row's region
    assert P.match("A kraj", "Delta", g).districts == {"3202"}


def test_shared_name_is_ambiguous_and_blocks_both():
    g = fake_geo()
    m = P.match("A kraj", "Ves", g)
    assert m.status == "ambiguous" and m.blocking(g) == {"3201", "3202"}


def test_clean_window_edges():
    # blocker 48 months before the event month: inside; 49 months before: outside
    kept, dropped = events_of([row(1, "Alfa", "2012-06-15"), row(2, "Alfa", "2008-06-01", jobs=200)])
    assert [d["reason"] for d in dropped if d["id_projekt"] == "1"] == ["clean window"]
    kept, dropped = events_of([row(1, "Alfa", "2012-06-15"), row(2, "Alfa", "2008-05-31", jobs=200)])
    assert [e["id_projekt"] for e in kept] == ["1"]
    # 47 months after: inside; 48 after: outside, but then the later one is blocked by the earlier (−48)
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2013-12-10", jobs=199)])
    assert [e["id_projekt"] for e in kept] == ["1"]  # 199 jobs does not block
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2013-12-10", jobs=200)])
    assert kept == []
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2014-01-10", jobs=300)])
    assert [e["id_projekt"] for e in kept] == ["1"]
    assert {d["id_projekt"]: d["reason"] for d in dropped} == {"2": "clean window"}


def test_events_that_block_each_other_both_drop():
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2011-01-10")])
    assert kept == [] and {d["reason"] for d in dropped} == {"clean window"}


def test_multi_place_project_blocks_each_matched_district_and_is_not_an_event():
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Gama", "2010-01-10", kraj="B kraj"),
                               row(3, "Beta, Gama", "2011-01-10", jobs=250)])
    assert [e["id_projekt"] for e in kept] == ["1"]
    assert {d["id_projekt"]: d["reason"] for d in dropped}["2"] == "clean window"
    kept, dropped = events_of([row(3, "Beta, Gama", "2011-01-10", jobs=900)])
    assert dropped[0]["reason"] == "matching: several places"


def test_comparison_pool_excludes_blocked_and_prague_and_needs_ten():
    kept, _ = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Filler1", "2012-01-10", jobs=200, kraj="C kraj"),
                         row(3, "Praha", "2001-01-01", jobs=50, kraj="Hlavní město Praha")])
    comps = kept[0]["comparisons"]
    assert "3901" not in comps and "3100" not in comps and "3201" not in comps
    assert len(comps) == 13  # 3202, 3301 and eleven fillers
    rows = [row(1, "Alfa", "2010-01-10")] + [row(10 + i, f"Filler{i}", "2010-02-01", jobs=200, kraj="C kraj")
                                            for i in range(1, 6)]  # 14 others, 5 blocked: 9 left
    kept, dropped = events_of(rows)
    assert kept == [] and dropped[0]["reason"] == "fewer than 10 comparison districts"


def test_prague_window_and_boundary_rules():
    _, dropped = events_of([row(1, "Praha", "2010-01-10", kraj="Hlavní město Praha")])
    assert dropped[0]["reason"] == "Prague"
    _, dropped = events_of([row(1, "Alfa", "2006-06-30"), row(2, "Beta", "2021-02-01")])
    assert {d["reason"] for d in dropped} == {"window"}
    kept, _ = events_of([row(1, "Alfa", "2006-07-01"), row(2, "Beta", "2021-01-31")])
    assert len(kept) == 2
    # years −2..3 of an event in month m0 run from m0 − 24 to m0 + 47
    b = {"2007": ["3201"], "2016": ["3301"]}
    _, dropped = events_of([row(1, "Alfa", "2009-01-15")], boundaries=b)  # from January 2007
    assert dropped[0]["reason"] == "boundaries"
    kept, _ = events_of([row(1, "Alfa", "2009-02-15")], boundaries=b)  # from February 2007, to January 2013
    assert kept and "3301" in kept[0]["comparisons"]
    kept, _ = events_of([row(1, "Alfa", "2012-02-15")], boundaries=b)  # to January 2016
    assert kept and "3301" not in kept[0]["comparisons"]


def test_screen_outcome_rule_from_presence():
    def month(js, pop, uoz, n=77):
        return {"file": True, "districts": n, "same_district_set": True,
                "present": {S.JOBSEEKERS: js, S.POPULATION: pop, S.FALLBACK: uoz}}
    pre, post = "2010-01", "2015-01"
    assert S.outcome_rule({pre: month(77, 77, 77), post: month(77, 77, 77)})["rule"] == "primary"
    assert S.outcome_rule({pre: month(0, 77, 77), post: month(77, 77, 77)})["rule"].startswith("fallback")
    assert S.outcome_rule({pre: month(0, 0, 77), post: month(77, 77, 77)})["rule"].startswith("descriptive")
    assert S.outcome_rule({pre: month(77, 0, 77), post: month(77, 77, 77)})["rule"].startswith("descriptive")
    assert S.outcome_rule({pre: month(77, 0, 77), post: month(77, 0, 77)})["rule"].startswith("none")
    r = S.outcome_rule({pre: month(77, 77, 77), "2011-03": month(76, 77, 77), post: month(77, 77, 77)})
    assert r["rule"] == "primary" and r["months_dropped"] == ["2011-03"]
