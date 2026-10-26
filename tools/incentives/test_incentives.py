"""Worked examples on made-up panels and project lists for the investment incentives study (design §2, §4, §6, §7).
No real MPSV or CzechInvest data is read."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import estimate as E
import population as POP
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


def test_label_not_computable_when_an_input_is_missing():
    nan = float("nan")
    assert E.label(-0.5, [nan, nan], [nan, nan], nan, [-0.1, 0.1]) == "not computable"
    assert E.label(-0.5, [-0.6, -0.4], [-0.7, -0.3], nan, [-0.1, 0.1]) == "not computable"


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
    ps = [E.SubPanel(replace(sp.event, moved=("C00", "T03") if sp.event.treated in ("T03", "T04") else ("C00",)),
                     sp.units, sp.years, sp.y) for sp in ps]
    out = E.checks(wide, [sp.event for sp in ps], ps, draws=30, perms=30, all_districts=list(wide.columns),
                   regions=regions)
    assert out["6_without_boundary_districts"]["n_events"] == len(ps) - 1  # T03 moved as treated; T04 does not
    assert out["6_without_boundary_districts"]["bootstrap_failed"] == 0
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


def reasons(dropped):
    return {d["id_projekt"]: d["reason"] for d in dropped}


def kept_ids(kept):
    return [e["id_projekt"] for e in kept]


def test_clean_window_edges():
    # window: 24 months before the event month to 47 after (amended 26 October 2026)
    kept, dropped = events_of([row(1, "Alfa", "2012-06-15"), row(2, "Alfa", "2010-06-01")])
    assert reasons(dropped)["1"] == "clean window"  # blocker 24 months before: inside
    kept, dropped = events_of([row(1, "Alfa", "2012-06-15"), row(2, "Alfa", "2010-05-31")])
    assert "1" in kept_ids(kept)  # 25 before: outside
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2013-12-10")])
    assert "1" not in kept_ids(kept)  # 47 after: inside
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2014-01-10")])
    assert kept_ids(kept) == ["1", "2"]  # 48 after: outside, and the earlier one is 48 before the later: outside
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2012-01-10", jobs=299)])
    assert kept_ids(kept) == ["1"]  # a blocker needs 300 jobs, not 299
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10", jobs=500), row(2, "Alfa", "2011-12-10", jobs=250)])
    assert kept_ids(kept) == ["1"]  # 250 jobs: neither an event nor a blocker
    assert dropped == []


def test_window_is_asymmetric_the_earlier_of_two_distant_events_drops():
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2012-07-10")])  # 30 months apart
    assert kept_ids(kept) == ["2"] and reasons(dropped) == {"1": "clean window"}


def test_events_that_block_each_other_both_drop():
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Alfa", "2011-01-10")])
    assert kept == [] and {d["reason"] for d in dropped} == {"clean window"}


def test_multi_place_project_blocks_each_matched_district_and_is_not_an_event():
    kept, dropped = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Gama", "2010-01-10", kraj="B kraj"),
                               row(3, "Beta, Gama", "2011-01-10", jobs=300)])
    assert kept_ids(kept) == ["1"]
    assert reasons(dropped)["2"] == "clean window"
    kept, dropped = events_of([row(3, "Beta, Gama", "2011-01-10", jobs=900)])
    assert dropped[0]["reason"] == "matching: several places"


def test_comparison_pool_excludes_blocked_and_prague_and_needs_ten():
    kept, _ = events_of([row(1, "Alfa", "2010-01-10"), row(2, "Filler1", "2012-01-10", jobs=300, kraj="C kraj"),
                         row(3, "Praha", "2001-01-01", jobs=50, kraj="Hlavní město Praha")])
    comps = next(e for e in kept if e["id_projekt"] == "1")["comparisons"]
    assert "3901" not in comps and "3100" not in comps and "3201" not in comps
    assert len(comps) == 13  # 3202, 3301 and eleven fillers
    rows = [row(1, "Alfa", "2010-01-10")] + [row(10 + i, f"Filler{i}", "2010-02-01", jobs=300, kraj="C kraj")
                                            for i in range(1, 6)]  # 14 others, 5 blocked: 9 left
    kept, dropped = events_of(rows)
    assert "1" not in kept_ids(kept) and reasons(dropped)["1"] == "fewer than 10 comparison districts"
    rows[1:] = [r | {"jobs": 299} for r in rows[1:]]  # below 300 they block nothing
    kept, _ = events_of(rows)
    assert kept_ids(kept) == ["1"]


def test_prague_window_and_boundary_rules():
    _, dropped = events_of([row(1, "Praha", "2010-01-10", kraj="Hlavní město Praha")])
    assert dropped[0]["reason"] == "Prague"
    _, dropped = events_of([row(1, "Alfa", "2006-06-30"), row(2, "Beta", "2021-02-01")])
    assert {d["reason"] for d in dropped} == {"window"}
    kept, _ = events_of([row(1, "Alfa", "2006-07-01"), row(2, "Beta", "2021-01-31")])
    assert len(kept) == 2
    # districts with a boundary change stay in the headline, as treated and as comparison; the event lists the ones
    # inside its years −2..3, which run from m0 − 24 to m0 + 47
    b = {"2007": ["3201"], "2016": ["3301"]}
    kept, dropped = events_of([row(1, "Alfa", "2009-01-15")], boundaries=b)  # from January 2007
    assert dropped == [] and kept[0]["moved"] == ["3201"] and "3301" in kept[0]["comparisons"]
    kept, _ = events_of([row(1, "Alfa", "2009-02-15")], boundaries=b)  # from February 2007, to January 2013
    assert kept[0]["moved"] == [] and "3301" in kept[0]["comparisons"]
    kept, _ = events_of([row(1, "Alfa", "2012-02-15")], boundaries=b)  # to January 2016
    assert kept[0]["moved"] == ["3301"] and "3301" in kept[0]["comparisons"]


def test_screen_outcome_rule_from_presence():
    def month(js, pop, uoz, rate=77, n=77):
        return {"file": True, "districts": n, "same_district_set": True,
                "present": {S.JOBSEEKERS: js, S.POPULATION: pop, S.FALLBACK: uoz, S.RATE: rate}}
    pre, post = "2010-01", "2015-01"
    reg = lambda r: S.outcome_rule(r)["registered_rule"]
    assert reg({pre: month(77, 77, 77), post: month(77, 77, 77)}) == "primary"
    assert reg({pre: month(0, 77, 77), post: month(77, 77, 77)}).startswith("fallback")
    assert reg({pre: month(0, 0, 77), post: month(77, 77, 77)}).startswith("descriptive")
    assert reg({pre: month(77, 0, 77), post: month(77, 77, 77)}).startswith("descriptive")
    assert reg({pre: month(77, 0, 77), post: month(77, 0, 77)}).startswith("none")
    # the amended rule needs MPSV's rate in the pre-2013 and the later months, not a population field
    r = S.outcome_rule({pre: month(77, 0, 77), post: month(77, 0, 77)})
    assert r["rule"].startswith("amended") and r["months_dropped"] == []
    r = S.outcome_rule({pre: month(77, 0, 77, rate=76), "2011-03": month(77, 0, 77), post: month(77, 0, 77)})
    assert r["rule"].startswith("amended") and r["months_dropped"] == [pre]
    assert S.outcome_rule({pre: month(77, 0, 77, rate=0), post: month(77, 0, 77, rate=0)})["rule"].startswith("none")
    assert S.outcome_rule({pre: month(77, 0, 77, rate=0), post: month(77, 0, 77)})["rule"].startswith("none")


# ---------- known effects of either sign ----------

def test_wrong_sign_effect_is_estimated_with_its_sign_and_labelled_higher():
    """The design expects a fall; a rise of the same size must come out as a rise, never as a fall."""
    wide, events = clean_panel(effect=+0.5, noise=0.2, seed=11)
    ps = panels_of(wide, events)
    res = E.run(ps, draws=400, perms=200)
    assert res["estimate"] == pytest.approx(0.5, abs=0.05)
    assert res["ci95"][0] > 0 and res["p_randomisation"] <= 0.05
    assert res["label"] == "higher unemployment after the promise"
    assert all(res["q2"][str(k)]["est"] > 0 for k in (0, 1, 2, 3))


def test_wrong_sign_is_the_mirror_of_the_expected_sign():
    down, ev = clean_panel(effect=-0.4, noise=0.0, seed=8)
    up, _ = clean_panel(effect=+0.4, noise=0.0, seed=8)
    a, b = E.estimate(panels_of(down, ev))["q1"], E.estimate(panels_of(up, ev))["q1"]
    assert a == pytest.approx(-0.4, abs=1e-9) and b == pytest.approx(0.4, abs=1e-9)


def test_small_true_effect_below_the_label_threshold_is_not_labelled_lower():
    wide, events = clean_panel(effect=-0.05, noise=0.05, seed=12)
    res = E.run(panels_of(wide, events), draws=300, perms=200)
    assert res["label"] == "no change larger than 0.20 points"


def test_pre_trend_shows_in_pre_diff_and_suffix():
    wide, events = clean_panel(effect=0.0, noise=0.02, seed=13, pre_trend=0.6)
    res = E.run(panels_of(wide, events), draws=300, perms=100)
    assert res["pre_diff_ci95"][0] > 0 or res["pre_diff_ci95"][1] < 0
    assert res["label"].endswith("with differing paths in the two years before the promise")


# ---------- a failing draw is a missing draw, never a crash ----------

def small_panels():
    wide, events = clean_panel(n_events=4, n_comp=6, effect=-0.3, noise=0.2, seed=21)
    return panels_of(wide, events)


def flaky_fit(monkeypatch, every, error):
    real = E.fit
    calls = {"n": 0}

    def fit(*a, **k):
        calls["n"] += 1
        if calls["n"] % every == 0:
            raise error
        return real(*a, **k)
    monkeypatch.setattr(E, "fit", fit)
    return calls


@pytest.mark.parametrize("error", [np.linalg.LinAlgError("Singular matrix"), KeyError(3), IndexError("x"),
                                   ZeroDivisionError("x"), ValueError("x"), FloatingPointError("x")])
def test_bootstrap_draw_failure_of_any_kind_is_left_missing(monkeypatch, error):
    ps = small_panels()
    flaky_fit(monkeypatch, 4, error)
    b = E.bootstrap(ps, draws=40, seed=3)
    assert len(b["draws"]) == 40 and b["failed"] == 10
    assert b["draws"]["q1"].isna().sum() == 10
    lo, hi = E.interval(b["draws"]["q1"], 0.95)
    assert np.isfinite(lo) and np.isfinite(hi)


def test_bootstrap_statistic_failure_is_left_missing_too():
    ps = small_panels()
    seen = {"n": 0}

    def stat(beta, den):
        seen["n"] += 1
        if seen["n"] % 5 == 0:
            raise KeyError("beta_9")
        return {"q": E.q1(beta)}
    b = E.bootstrap(ps, draws=20, seed=3, stat=stat)
    assert len(b["draws"]) == 20 and b["failed"] == 4


def test_bootstrap_with_every_draw_failing_still_returns(monkeypatch):
    ps = small_panels()
    flaky_fit(monkeypatch, 1, np.linalg.LinAlgError("Singular matrix"))
    b = E.bootstrap(ps, draws=10, seed=3)
    assert b["failed"] == 10 and len(b["draws"]) == 10
    assert E.interval(E.column(b["draws"], "q1"), 0.95)[0] != E.interval(E.column(b["draws"], "q1"), 0.95)[0]  # NaN


def test_run_survives_failing_draws_and_reports_them(monkeypatch):
    ps = small_panels()
    real = E.fit
    state = {"primary_done": False, "n": 0}

    def fit(*a, **k):
        if not state["primary_done"]:  # the first call is the point estimate
            state["primary_done"] = True
            return real(*a, **k)
        state["n"] += 1
        if state["n"] % 3 == 0:
            raise np.linalg.LinAlgError("Singular matrix")
        return real(*a, **k)
    monkeypatch.setattr(E, "fit", fit)
    res = E.run(ps, draws=30, perms=30)
    assert res["bootstrap_failed"] > 0 and res["bootstrap_missing_q"] >= res["bootstrap_failed"]
    assert res["permutations_missing"] > 0
    assert np.isfinite(res["ci95"][0]) and 0 <= res["p_randomisation"] <= 1


def test_permutations_that_fail_are_not_counted_as_smaller_than_observed(monkeypatch):
    ps = small_panels()
    obs = E.estimate(ps)["q1"]
    flaky_fit(monkeypatch, 1, np.linalg.LinAlgError("Singular matrix"))
    r = E.permutation_p(ps, obs, perms=20)
    assert r["failed"] == 20 and np.isnan(r["p"])  # not p = 0


def test_unidentified_coefficient_gives_missing_not_a_crash():
    """Events whose years 4 and 5 are missing leave those coefficients unidentified (NaN)."""
    wide, events = clean_panel(n_events=3, n_comp=4, seed=5)
    ps = panels_of(wide, events)
    beta = E.fit([E.design_of(sp) for sp in ps], years=(-2, -1, 0, 1, 2, 3, 4, 5))
    assert np.isnan(beta[4]) and np.isnan(beta[5]) and np.isfinite(beta[3])


def test_check_that_cannot_be_estimated_is_reported_and_the_others_still_run(monkeypatch):
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.1, seed=6)
    ps = panels_of(wide, events)
    real_run = E.run

    def run(sel, *a, name="", **k):
        if name == "3":
            raise np.linalg.LinAlgError("Singular matrix")
        return real_run(sel, *a, name=name, **k)
    monkeypatch.setattr(E, "run", run)
    regions = {u: ("R1" if int(u[1:]) % 2 else "R2") for u in wide.columns}
    out = E.checks(wide, events, ps, draws=10, perms=10, all_districts=list(wide.columns), regions=regions)
    assert "LinAlgError" in out["3_same_region"]["error"]
    assert "error" not in out["4_same_tercile"] and "error" not in out["10_reference_year_minus1"]


# ---------- the draw log ----------

def test_draws_are_appended_as_they_are_made(monkeypatch, tmp_path):
    ps = small_panels()
    path = tmp_path / "draws.jsonl"
    log = E.DrawLog(path)
    real = E.fit
    lines_seen = []

    def fit(*a, **k):
        lines_seen.append(len(path.read_text().splitlines()))  # lines on disk when the next draw starts
        return real(*a, **k)
    monkeypatch.setattr(E, "fit", fit)
    log.run = "t"
    E.bootstrap(ps, draws=5, seed=1, log=log)
    assert lines_seen == [0, 1, 2, 3, 4]
    E.permutation_p(ps, 0.0, perms=3, log=log)
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["boot"] * 5 + ["perm"] * 3
    assert all(r["run"] == "t" and r["error"] is None for r in rows)


def test_failed_draw_is_logged_with_its_error(monkeypatch, tmp_path):
    ps = small_panels()
    log = E.DrawLog(tmp_path / "d.jsonl")
    flaky_fit(monkeypatch, 2, np.linalg.LinAlgError("Singular matrix"))
    E.bootstrap(ps, draws=4, seed=1, log=log)
    rows = [json.loads(x) for x in (tmp_path / "d.jsonl").read_text().splitlines()]
    assert [r["error"] is not None for r in rows] == [False, True, False, True]
    assert "LinAlgError" in rows[1]["error"]


def test_run_and_checks_name_their_draws_in_the_log(tmp_path):
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.1, seed=6)
    ps = panels_of(wide, events)
    log = E.DrawLog(tmp_path / "d.jsonl")
    E.run(ps, draws=3, perms=2, log=log, name="primary")
    regions = {u: "R" for u in wide.columns}
    E.checks(wide, events, ps, draws=3, perms=2, all_districts=list(wide.columns), regions=regions, log=log)
    names = {json.loads(x)["run"] for x in (tmp_path / "d.jsonl").read_text().splitlines()}
    assert {"primary", "1_jobs_1000", "6", "9", "11"} <= names


# ---------- Q3 without population, real-data plumbing ----------

def test_q3_is_not_computable_without_population_and_computable_with_it():
    wide, events = clean_panel(n_events=3, n_comp=4, effect=-0.5, noise=0.05, seed=2)
    res = E.run(panels_of(wide, events), draws=20, perms=10)
    assert res["q3"]["est"] is None and "not computable" in res["q3"]["reason"]
    pop = wide * 0 + 50_000.0
    res = E.run(panels_of(wide, events, pop=pop), draws=20, perms=10)
    assert res["q3"]["est"] == pytest.approx(res["estimate"] / (100 * np.mean([e.jobs for e in events]) / 50_000), rel=1e-6)


def test_results_serialise_missing_numbers_as_null():
    out = E.jsonable({"a": float("nan"), "b": [np.float64("inf"), 1.5], "c": np.int64(3)})
    assert json.dumps(out, allow_nan=False) == '{"a": null, "b": [null, 1.5], "c": 3}'


def test_load_panel_reads_the_rate_and_nothing_else(tmp_path):
    from fetch import months, mpsv_name
    for y, m in months((2004, 7), (2004, 9)):
        items = [{"okres": f"x/{code}", "podilNezamestnanychOsobPNO": v, "dosazitelniUchazeci15_64": 999}
                 for code, v in (("3201", 1.0 * m), ("3202", None))]
        (tmp_path / mpsv_name(y, m)).write_text(json.dumps({"polozky": items}))
    wide = E.load_panel(tmp_path)
    assert wide.columns.tolist() == ["3201", "3202"] and wide["3201"].tolist() == [7.0, 8.0, 9.0]
    assert wide["3202"].isna().all()


def test_events_from_the_project_step_load_into_the_estimator():
    kept, _ = events_of([row(1, "Alfa", "2009-01-15", jobs=450, ipo_zruseni="ANO", ipo_rezim="Zákonná pobídka")],
                        boundaries={"2007": ["3201"], "2016": []})
    (ev,) = E.to_events(kept)
    assert (ev.id, ev.treated, ev.jobs, ev.cancelled, ev.regime, ev.moved) == ("1", "3201", 450.0, "ANO",
                                                                             "Zákonná pobídka", ("3201",))
    assert ev.month == M(2009, 1) and len(ev.comparisons) == kept[0]["n_comparisons"]


def test_permutation_p_is_missing_when_the_observed_value_is_missing():
    ps = small_panels()
    assert np.isnan(E.permutation_p(ps, float("nan"), perms=5)["p"])  # not 0


def test_label_not_computable_when_the_pre_interval_is_missing():
    nan = float("nan")
    assert E.label(0.0, [-0.1, 0.1], [-0.15, 0.15], 0.5, [nan, nan]) == "not computable"


def test_run_label_not_computable_when_too_many_draws_are_missing(monkeypatch):
    ps = small_panels()
    real = E.fit
    state = {"n": 0}

    def fit(*a, **k):
        state["n"] += 1
        if state["n"] > 1 and state["n"] % 2 == 0:
            raise np.linalg.LinAlgError("Singular matrix")
        return real(*a, **k)
    monkeypatch.setattr(E, "fit", fit)
    assert E.run(ps, draws=20, perms=20)["label"] == "not computable"


def test_bootstrap_that_never_holds_an_event_stops_and_is_logged(monkeypatch, tmp_path):
    ps = small_panels()
    monkeypatch.setattr(E, "MAX_REDRAWS", 5)
    monkeypatch.setattr(E, "design_of", lambda *a, **k: None)
    log = E.DrawLog(tmp_path / "d.jsonl")
    with pytest.raises(RuntimeError, match="no draw holds an event"):
        E.bootstrap(ps, draws=3, seed=1, log=log)
    assert [json.loads(x)["kind"] for x in (tmp_path / "d.jsonl").read_text().splitlines()] == ["boot_redraw"] * 6


def test_log_rows_carry_a_run_stamp(tmp_path):
    log = E.DrawLog(tmp_path / "d.jsonl")
    E.permutation_p(small_panels(), 0.0, perms=2, log=log)
    rows = [json.loads(x) for x in (tmp_path / "d.jsonl").read_text().splitlines()]
    assert len({r["stamp"] for r in rows}) == 1 and rows[0]["stamp"]


def test_unblind_refuses_other_draw_counts_and_unavailable_rules(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["estimate.py", "--unblind", "--draws", "10"])
    with pytest.raises(SystemExit, match="registered run uses"):
        E.main()
    f = tmp_path / "screening.json"
    f.write_text(json.dumps({"mpsv": {"outcome_rule": {"rule": "none: x", "months_dropped": "n/a"}}}))
    monkeypatch.setattr(E, "SCREENING", f)
    with pytest.raises(SystemExit, match="refused"):
        E.real(1, 1)


def test_main_prints_only_the_path(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["estimate.py", "--unblind"])
    monkeypatch.setattr(E, "real", lambda *a, **k: {"primary": {"estimate": -0.123456}})
    monkeypatch.setattr(E, "OUT", tmp_path / "r.json")
    monkeypatch.setattr(E, "DRAW_LOG", tmp_path / "d.jsonl")
    E.main()
    assert capsys.readouterr().out == f"written {tmp_path / 'r.json'}\n"


def test_checks_2_5_8_select_the_right_events():
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.1, seed=6)
    events = [replace(ev, cancelled=("ANO" if i % 4 == 0 else "ověřit" if i == 1 else ""),
                      regime="Zákonná pobídka" if i % 2 else "Program PM") for i, ev in enumerate(events)]
    ps = panels_of(wide, events)
    regions = {u: "R" for u in wide.columns}
    out = E.checks(wide, events, ps, draws=5, perms=5, all_districts=list(wide.columns), regions=regions)
    assert out["2_without_cancelled_or_unverified"]["n_events"] == sum(i % 4 != 0 and i != 1 for i in range(22))
    assert out["8_statutory_regime_only"]["n_events"] == 11
    n5 = sum(not E.covers(ev, *E.CRISIS) and not E.covers(ev, *E.COVID) for ev in events)
    assert out["5_without_2009_2020_21"].get("n_events", 0) == n5


def test_check_11_recovers_effect_when_a_rise_precedes_the_promise():
    """Districts with a recent rise (year -3 to -2) get a later effect only through the control interaction."""
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.05, seed=7)
    regions = {u: "R" for u in wide.columns}
    out = E.checks(wide, events, panels_of(wide, events), draws=5, perms=5, all_districts=list(wide.columns),
                   regions=regions)
    assert out["11_control_change_minus3_to_minus2"]["estimate"] == pytest.approx(-0.5, abs=0.1)


def test_tercile_pool_keeps_comparisons_in_the_treated_tercile():
    wide, events = clean_panel(n_events=1, n_comp=6, noise=0.0, effect=0.0, seed=3)
    sp = E.sub_panel(wide, events[0])
    base = pd.Series({u: float(i) for i, u in enumerate(sp.units)})  # 0..6, terciles by rank
    assert E.tercile_pool(sp, base) == {sp.units[1]}  # cut-offs 2 and 4: values 0 and 1 share a tercile


# ---------- ČSÚ population for Q3 (made-up files) ----------


MPSV_OKRESY = {"polozky": [
    {"kod": "9999", "kodLau": "CZ0100", "nazev": {"cs": "území Hlavního města Prahy"}},
    {"kod": "3100", "kodLau": "CZ0100", "nazev": {"cs": "Hlavní město Praha"}},
    {"kod": "3201", "kodLau": "CZ0201", "nazev": {"cs": "Benešov"}},
    {"kod": "3702", "kodLau": "CZ0642", "nazev": {"cs": "Brno-město"}},
    {"kod": "3703", "kodLau": "CZ0643", "nazev": {"cs": "Brno-venkov"}},
]}


def csu_row(chodnota, text, lau, ruian):
    return {"chodnota": chodnota, "text": text, "okres_lau": lau, "kod_ruian": ruian}


CSU_101 = [csu_row("40002", "Extra-Regio", "CZZZZZ", ""), csu_row("40169", "Benešov", "CZ0201", "3201"),
           csu_row("40711", "Brno-město", "CZ0642", "3702"), csu_row("40720", "Brno-venkov", "CZ0643", "3703"),
           csu_row("40924", "Praha", "CZ0100", "")]


def mpsv_codes(tmp_path):
    (tmp_path / "mpsv_okresy.json").write_text(json.dumps(MPSV_OKRESY), encoding="utf-8")
    return POP.mpsv_districts(tmp_path)


def pop_row(kod, year, value, cis="101", vek=POP.AGE_15_64, sex=""):
    return {"uzemi_cis": cis, "stapro_kod": POP.STAPRO, "vek_kod": vek, "pohlavi_kod": sex, "uzemi_kod": kod,
            "uzemi_txt": "x", "obdobi": f"{year}-12-31", "hodnota": str(value)}


def test_district_map_uses_lau_and_keeps_brno_and_prague_apart(tmp_path):
    cmap = POP.district_map(CSU_101, mpsv_codes(tmp_path))
    assert cmap == {"40169": "3201", "40711": "3702", "40720": "3703", "40924": "3100"}


@pytest.mark.parametrize("bad", [
    csu_row("40999", "Nowhere", "CZ0999", "3999"),  # LAU with no MPSV district
    csu_row("40711", "Brno-město", "CZ0642", "3703"),  # kod_ruian of Brno-venkov on Brno-město
    csu_row("40711", "Brno-venkov", "CZ0642", "3702"),  # name of the other Brno district
    csu_row("40169", "Benešov", "CZ0201", ""),  # no kod_ruian outside Prague
])
def test_district_map_fails_loudly_on_a_district_that_does_not_map(tmp_path, bad):
    with pytest.raises(POP.DistrictMismatch):
        POP.district_map([*CSU_101, bad], mpsv_codes(tmp_path))


def test_year_end_keeps_both_sexes_15_64_of_districts_only_and_fails_on_an_unmapped_district():
    cmap = {"40169": "3201", "40711": "3702"}
    rows = [pop_row("40169", 2010, 100), pop_row("40711", 2010, 300),
            pop_row("40169", 2010, 7, sex="1"), pop_row("40169", 2010, 8, vek="400000610015000"),
            pop_row("3018", 2010, 9, cis="100")]
    ye = POP.year_end_15_64(rows, cmap)
    assert ye.loc[2010].to_dict() == {"3201": 100.0, "3702": 300.0}
    with pytest.raises(POP.DistrictMismatch, match="40720"):
        POP.year_end_15_64([*rows, pop_row("40720", 2010, 5)], cmap)
    with pytest.raises(ValueError, match="two values"):
        POP.year_end_15_64([*rows, pop_row("40169", 2010, 101)], cmap)


def test_monthly_population_is_linear_between_year_ends():
    ye = pd.DataFrame({"3201": [1200.0, 2400.0]}, index=[2010, 2011])
    m = POP.monthly(ye, ["3201"], M(2011, 1), M(2012, 1))
    assert m.loc[M(2011, 1), "3201"] == pytest.approx(1300.0)  # end of January 2011
    assert m.loc[M(2011, 12), "3201"] == pytest.approx(2400.0)  # 31 December 2011
    assert np.isnan(m.loc[M(2012, 1), "3201"])  # no 2012 stock


def test_monthly_population_refuses_prague_and_a_district_without_population():
    ye = pd.DataFrame({"3201": [1.0, 2.0]}, index=[2010, 2011])
    with pytest.raises(POP.DistrictMismatch, match="Prague"):
        POP.monthly(ye, ["3201", "3100"], M(2011, 1), M(2011, 12))
    with pytest.raises(POP.DistrictMismatch, match="3702"):
        POP.monthly(ye, ["3201", "3702"], M(2011, 1), M(2011, 12))


def test_q3_denominator_uses_the_mean_population_over_year_minus_1():
    """Treated 3201 grows from 12 000 to 24 000 over 2011; decided in January 2012, year -1 is 2011, whose monthly
    mean is 12 000 + 6.5/12 × 12 000 = 18 500. 370 promised jobs give 100 × 370 / 18 500 = 2 points."""
    months = np.arange(M(2009, 1), M(2016, 12) + 1)
    wide = pd.DataFrame(1.0, index=months, columns=["3201", "3702", "3703"])
    ye = pd.DataFrame({"3201": [12_000.0] * 2 + [24_000.0] * 6, "3702": 5e4, "3703": 5e4}, index=range(2009, 2017))
    ye.loc[2009:2010, "3201"] = 12_000.0
    pop = POP.monthly(ye, ["3201", "3702", "3703"], months[0], months[-1])
    ev = E.Event("a", "3201", M(2012, 1), ("3702", "3703"), jobs=370.0)
    sp = E.sub_panel(wide, ev, pop=pop)
    assert sp.pop_pre == pytest.approx(18_500.0)
    assert E.q3_denominator([sp]) == pytest.approx(2.0)


def test_population_loads_end_to_end_from_a_made_up_zip(tmp_path):
    import zipfile
    mpsv_codes(tmp_path)
    cols = ["idhod", "hodnota", "stapro_kod", "pohlavi_cis", "pohlavi_kod", "vek_cis", "vek_kod", "uzemi_cis",
            "uzemi_kod", "obdobi", "pohlavi_txt", "vek_txt", "uzemi_txt", "uzemi_typ"]
    lines = [",".join(f'"{c}"' for c in cols)]
    for i, (kod, y, v) in enumerate([("40169", 2010, 1200), ("40169", 2011, 2400), ("40711", 2010, 10),
                                     ("40711", 2011, 10), ("40720", 2010, 5), ("40720", 2011, 5)]):
        lines.append(f'"{i}","{v}","2406",,,"7700","{POP.AGE_15_64}","101","{kod}","{y}-12-31",,"15 až 64","x","okres"')
    with zipfile.ZipFile(tmp_path / "p.zip", "w") as z:
        z.writestr("OD_DEM05.CSV", "﻿" + "\n".join(lines) + "\n")
    with open(tmp_path / "101.csv", "w", encoding="utf-8", newline="") as f:
        f.write('"chodnota","text","okres_lau","kod_ruian"\n')
        f.writelines(f'"{r["chodnota"]}","{r["text"]}","{r["okres_lau"]}","{r["kod_ruian"]}"\n' for r in CSU_101)
    m = POP.load(["3201", "3702", "3703"], M(2011, 1), M(2011, 12), tmp_path / "p.zip", tmp_path / "101.csv", tmp_path)
    assert m.loc[M(2011, 1), "3201"] == pytest.approx(1300.0) and m["3702"].eq(10.0).all()


# ---------- check 12: windows spanning January 2013 ----------

@pytest.mark.parametrize("decided, spans", [
    (M(2009, 1), False),  # months -24..+47 end December 2012
    (M(2009, 2), True),  # end January 2013
    (M(2015, 1), True),  # start January 2013
    (M(2015, 2), False),  # start February 2013
])
def test_check_12_boundary_months(decided, spans):
    assert E.spans_pno_change(E.Event("a", "T", decided, ())) is spans


def test_check_12_drops_exactly_the_events_spanning_january_2013():
    wide, events = clean_panel(n_events=22, n_comp=12, effect=-0.5, noise=0.1, seed=6)
    ps = panels_of(wide, events)
    regions = {u: "R" for u in wide.columns}
    out = E.checks(wide, events, ps, draws=5, perms=5, all_districts=list(wide.columns), regions=regions)
    kept = [sp for sp in ps if not (M(2009, 2) <= sp.event.month <= M(2015, 1))]
    assert 0 < len(kept) < len(ps)
    assert out["12_without_window_spanning_2013_01"]["n_events"] == len(kept)
    assert out["12_without_window_spanning_2013_01"]["label"] is None  # a check never relabels the primary
