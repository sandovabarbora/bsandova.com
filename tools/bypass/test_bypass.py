"""Worked examples on made-up towns and accidents for the bypass accidents study (design §2, §4, §6). No real accident
record is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


import estimate as E  # noqa: E402
import towns as T  # noqa: E402

YEARS = range(2016, 2026)


def made_up(n_treated=40, n_comp=40, effect=1.0, outside=1.0, seed=1, base=(8, 25)):
    """Towns with works starting 2018–2021 and opening two years later, comparison towns never treated in the data;
    accidents Poisson with town and year effects and a multiplicative effect in post years."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_treated):
        start = 2018 + i % 4
        rows.append({"town": f"T{i}", "role": "treated", "cluster": f"B{i // 2}", "start_year": start,
                     "open_year": start + 2, "open_month": 6, "last_year": None, "road_class": "I" if i % 2 else "II"})
    for j in range(n_comp):
        rows.append({"town": f"C{j}", "role": "comparison", "cluster": f"K{j}", "start_year": None, "open_year": None,
                     "open_month": None, "last_year": 2025 if j % 3 else 2022, "road_class": "I"})
    towns = pd.DataFrame(rows)
    towns["cohort"] = [T.cohort(y) if r == "treated" else None for y, r in zip(towns["open_year"], towns["role"])]
    year_fx = {y: 1 + 0.03 * (y - 2016) for y in YEARS}
    c = []
    for t in towns.itertuples():
        level = rng.uniform(*base)
        for y in YEARS:
            post = t.role == "treated" and y > t.open_year
            mu = level * year_fx[y] * (effect if post else 1.0)
            mo = level * year_fx[y] * (outside if post else 1.0)
            q1, out = rng.poisson(mu), rng.poisson(mo)
            c.append({"town": t.town, "year": y, "q1": q1, "outside": out, "q2": q1 + out})
    return towns, pd.DataFrame(c)


def test_known_effect_recovered():
    towns, counts = made_up(effect=0.7, seed=2)
    f = E.fit(towns, counts, YEARS, E.Spec("q1"))
    assert f.converged and f.ok
    assert f.est == pytest.approx(-0.30, abs=0.05)
    assert f.delta < 0
    b = E.bootstrap(towns, counts, YEARS, {"q1": E.Spec("q1")}, draws=40, gate=("q1",))
    lo, hi = E.interval(b["draws"]["q1"]["est"], 0.95)
    assert hi < 0 and lo < f.est < hi


def test_null_case():
    towns, counts = made_up(effect=1.0, seed=3)
    f = E.fit(towns, counts, YEARS, E.Spec("q1"))
    assert abs(f.est) < 0.06
    b = E.bootstrap(towns, counts, YEARS, {"q1": E.Spec("q1")}, draws=40, gate=("q1",))
    lo, hi = E.interval(b["draws"]["q1"]["est"], 0.95)
    assert lo < 0 < hi


def test_q2_offset_in_counts():
    # inside falls by 30 %, outside rises by the same number of accidents: Q2 change near zero, offset near 1
    towns, counts = made_up(effect=0.7, outside=1.3, seed=4)
    f1 = E.fit(towns, counts, YEARS, E.Spec("q1"))
    f2 = E.fit(towns, counts, YEARS, E.Spec("q2"))
    assert abs(f2.est) < 0.06
    assert 1 - f2.delta / f1.delta == pytest.approx(1.0, abs=0.25)


def test_event_time_and_censoring():
    towns = pd.DataFrame([
        {"town": "T", "role": "treated", "cluster": "a", "cohort": "2020-2022", "start_year": 2018, "open_year": 2021,
         "open_month": 3, "last_year": None},
        {"town": "C", "role": "comparison", "cluster": "b", "cohort": None, "start_year": None, "open_year": None,
         "open_month": None, "last_year": 2019}])
    p = E.event_rows(towns, YEARS, E.Spec())
    t = p[p["town"] == "T"].set_index("year")
    assert 2021 not in t.index  # opening year dropped
    assert list(t.loc[[2016, 2017], "phase"]) == ["pre", "pre"]
    assert t.loc[2018, "phase"] == "construction" and t.loc[2018, "k"] == 3 and t.loc[2020, "k"] == 1
    assert t.loc[2022, "phase"] == "post" and t.loc[2022, "k"] == 1
    assert sorted(p[p["town"] == "C"]["year"]) == [2016, 2017, 2018, 2019]  # censored after its last year
    assert E.comparisons_by_year(p) == {2016: 2, 2017: 2, 2018: 1, 2019: 1}
    d = E.event_rows(towns, YEARS, E.Spec(opening_dose=True))
    assert d.loc[(d["town"] == "T") & (d["year"] == 2021), "dose"].item() == pytest.approx(10 / 12)


def test_thin_years_kept_out_of_q1():
    towns, counts = made_up(n_treated=20, n_comp=4, seed=5)
    f = E.fit(towns, counts, YEARS, E.Spec("q1"))
    # four comparison towns and treated towns before their works: late years fall below 15
    assert f.thin_cells and all(n < 15 for n in f.thin_cells.values())
    assert all(not c.startswith("x|") for c in f.weights)


def test_zero_towns_dropped_and_listed_on_q2_for_every_outcome():
    towns, counts = made_up(seed=6)
    counts.loc[counts["town"] == "C5", ["q1", "outside", "q2"]] = 0
    counts.loc[counts["town"] == "C6", "q1"] = 0  # accidents only outside the built-up area: kept
    counts.loc[counts["town"] == "C6", "q2"] = counts.loc[counts["town"] == "C6", "outside"]
    f1 = E.fit(towns, counts, YEARS, E.Spec("q1"))
    f2 = E.fit(towns, counts, YEARS, E.Spec("q2"))
    assert f1.dropped_zero == f2.dropped_zero == ["C5"]
    assert f1.weights == f2.weights


def test_inside_and_outside_add_up_to_q2():
    towns, counts = made_up(effect=0.7, outside=1.2, seed=14)
    late = towns.loc[towns["role"] == "treated", "town"].iloc[:3]
    counts.loc[counts["town"].isin(late), "q1"] = 0  # treated towns with no accident inside the built-up area
    counts["q2"] = counts["q1"] + counts["outside"]
    f1, f2, fo = (E.fit(towns, counts, YEARS, E.Spec(o)) for o in ("q1", "q2", "outside"))
    assert f1.dropped_zero == f2.dropped_zero == fo.dropped_zero
    # the reported outside change is Q2 − Q1 by construction; the separate outside fit lands near it
    assert f2.delta - f1.delta == pytest.approx(fo.delta, abs=0.15 * abs(fo.delta) + 0.05)


def test_missing_town_years_are_an_error():
    towns, counts = made_up(seed=15)
    with pytest.raises(AssertionError, match="missing"):
        E.fit(towns, counts[~((counts["town"] == "T0") & (counts["year"] == 2016))], YEARS, E.Spec("q1"))


def test_plain_event_study_reference_is_year_before_opening():
    towns, counts = made_up(effect=0.7, seed=16)
    p = E.event_rows(towns, YEARS, E.Spec(event_study=True))
    X, _ = E.indicators(p, E.Spec(event_study=True))
    assert not any(c.endswith("|-1") for c in X.columns if c.startswith("e|"))
    assert any(c.startswith("e|") and c.endswith("|-2") for c in X.columns)
    assert not any(c.startswith("c|") for c in X.columns)
    f = E.fit(towns, counts, YEARS, E.Spec("q1", event_study=True))
    assert f.est == pytest.approx(-0.30, abs=0.06)


def test_separation_ignores_unreported_cells():
    towns, counts = made_up(n_treated=8, n_comp=30, seed=17)
    # post year 4 and later of one cohort all zero: not a reported cell, so not a separation
    late = towns.loc[(towns["role"] == "treated") & (towns["open_year"] == 2020), "town"]
    counts.loc[counts["town"].isin(late) & (counts["year"] >= 2024), "q1"] = 0
    f = E.fit(towns, counts, YEARS, E.Spec("q1"))
    assert not f.separated and f.ok and np.isfinite(f.est)


def test_bootstrap_writes_draws_as_it_goes(tmp_path):
    towns, counts = made_up(n_treated=12, n_comp=20, seed=18)
    log = tmp_path / "draws.jsonl"
    E.bootstrap(towns, counts, YEARS, {"q1": E.Spec("q1")}, draws=3, gate=("q1",), log=log, name="t")
    lines = log.read_text().splitlines()
    assert len(lines) == 3 and '"set": "t"' in lines[0]


def test_label_not_estimated_without_finite_numbers():
    kw = {"differing_trends": False, "minimum_met": True, "stage": "test"}
    assert E.label(np.nan, [-0.1, 0.1], [-0.1, 0.1], **kw) == "not estimated"
    assert E.label(0.0, None, [-0.1, 0.1], **kw) == "not estimated"


def test_separated_cell_flagged_and_redrawn():
    towns, counts = made_up(n_treated=8, n_comp=30, seed=7)
    # the 2023–24 cohort (works from 2021) has no accident in its post years: a separated cell
    late = towns.loc[(towns["role"] == "treated") & (towns["open_year"] >= 2023), "town"]
    counts.loc[counts["town"].isin(late) & (counts["year"] >= 2024), "q1"] = 0
    f = E.fit(towns, counts, YEARS, E.Spec("q1"))
    assert any(c.startswith("p|2023-2024") for c in f.separated) and not f.ok
    b = E.bootstrap(towns, counts, YEARS, {"q1": E.Spec("q1")}, draws=5, gate=("q1",))
    assert sum(b["redrawn"].values()) > 0
    assert len(b["draws"]["q1"]["est"]) == 5


def test_redraw_when_post_year_has_no_treated_town():
    towns, counts = made_up(n_treated=2, n_comp=20, seed=8)
    # one bypass of two towns opening in 2020 is the only source of post years; dropping it must be redrawn
    towns.loc[towns["role"] == "treated", "cluster"] = ["X", "Y"]
    towns.loc[towns["town"] == "T1", ["start_year", "open_year"]] = [2021, 2024]
    b = E.bootstrap(towns, counts, YEARS, {"q1": E.Spec("q1")}, draws=10, seed=1, gate=("q1",))
    assert b["redrawn"]["no_treated_post_year"] > 0


def test_resample_keeps_bypasses_whole_and_groups_apart():
    towns, counts = made_up(n_treated=6, n_comp=5, seed=9)
    tw, ct = E.resample(towns, counts, np.random.default_rng(0))
    assert (tw["role"] == "treated").sum() == 6 and (tw["role"] == "comparison").sum() == 5
    assert tw.groupby("cluster")["role"].nunique().max() == 1
    assert tw.groupby("cluster").size().max() == 2 or tw[tw["role"] == "treated"].groupby("cluster").size().eq(2).all()
    assert set(ct["town"]) == set(tw["town"])


def test_labels_in_order_and_at_boundaries():
    lab = lambda e, c95, c90, **k: E.label(e, c95, c90, **{"differing_trends": False, "minimum_met": True,  # noqa: E731
                                                           "stage": "test", **k})
    assert lab(-0.10, [-0.2, -0.01], [-0.18, -0.03]) == "fewer accidents after opening"
    assert lab(-0.12, [-0.2, -0.01], [-0.14, -0.10]) == "fewer accidents after opening"  # 1 before 3
    assert lab(-0.09, [-0.15, -0.01], [-0.14, -0.03]) == "no change larger than 15 %"
    assert lab(0.10, [0.01, 0.2], [0.02, 0.18]) == "more accidents after opening"
    assert lab(0.0, [-0.2, 0.2], [-0.15, 0.15]) == "no change larger than 15 %"
    assert lab(0.0, [-0.2, 0.2], [-0.14, 0.1501]) == "inconclusive"
    assert lab(0.0, [-0.3, 0.3], [-0.16, 0.14]) == "inconclusive"  # width exactly 0.30 is not wider than 30 points
    assert lab(0.0, [-0.4, 0.4], [-0.2, 0.2]) == "underpowered"
    assert lab(-0.2, [-0.3, -0.1], [-0.28, -0.12], differing_trends=True) == \
        "fewer accidents after opening with differing trends before construction"
    assert lab(0.0, [-0.1, 0.1], [-0.08, 0.08], differing_trends=True) == "inconclusive"


def test_stage_a_bans_label_3_and_carries_caveat():
    assert E.label(0.0, [-0.1, 0.1], [-0.08, 0.08], differing_trends=False, minimum_met=True, stage="A") == "inconclusive"
    assert E.label(-0.3, [-0.4, -0.2], [-0.38, -0.22], differing_trends=False, minimum_met=True, stage="A").endswith(
        "with differing trends before construction")


def test_minimum_rule_withholds_labels_1_to_3():
    assert E.label(-0.3, [-0.4, -0.2], [-0.38, -0.22], differing_trends=False, minimum_met=False,
                   stage="test") == "inconclusive"
    assert E.label(-0.3, [-0.6, -0.1], [-0.55, -0.12], differing_trends=False, minimum_met=False,
                   stage="test") == "underpowered"
    assert E.label(0.0, [-0.1, 0.1], [-0.08, 0.08], differing_trends=False, minimum_met=False,
                   stage="test") == "inconclusive"


def test_offset_share_rules():
    q1 = {"ci95": [-0.3, 0.05], "delta_per_town_year": -1.0}
    assert E.offset_share(q1, {"delta_per_town_year": 0.0}, [-1.0] * 100, [0.0] * 100)["reported"] is False
    q1 = {"ci95": [-0.3, -0.05], "delta_per_town_year": -1.0}
    d1 = [-1.0] * 94 + [0.05] * 6
    r = E.offset_share(q1, {"delta_per_town_year": -0.5}, d1, [-0.5] * 100)
    assert r["value"] == "not defined"
    d1 = [-1.0] * 96 + [0.05] * 4
    r = E.offset_share(q1, {"delta_per_town_year": -0.5}, d1, [-0.5] * 100)
    assert r["value"] == pytest.approx(0.5)


def test_sign_sentence():
    assert E.sign_sentence(-0.2, {"I": -0.1, "II": -0.3}) is None
    assert "class II" in E.sign_sentence(-0.2, {"I": -0.1, "II": 0.05})


def test_pre_trend_leads_and_uninformative_rule():
    towns, counts = made_up(n_treated=12, seed=10)
    f = E.fit(towns, counts, YEARS, E.Spec("q1", leads=True), clustered=True)
    # works from 2018–2021: lead −2 always exists, lead −3 only from 2019
    assert f.leads["towns_per_lead"]["lead|-2"] == 12 and f.leads["towns_per_lead"]["lead|-3"] == 9
    assert f.leads["uninformative"] and f.leads["df"] == 2 and 0 <= f.leads["p"] <= 1


def test_placebo_finds_nothing_on_null_data():
    towns, counts = made_up(seed=11)
    r = E.placebo(towns, counts, YEARS)
    assert r["run"] and r["ci95"][0] < 0 < r["ci95"][1]


def test_callaway_santanna_sign():
    towns, counts = made_up(effect=0.6, seed=12)
    assert E.callaway_santanna(towns, counts, YEARS) == pytest.approx(-0.4, abs=0.1)


def test_analyse_end_to_end_small():
    towns, counts = made_up(n_treated=32, n_comp=30, effect=0.7, seed=13)
    for k in ("q1_all", "q2_all", "q1_ksi", "q2_ksi", "q1_oldroad"):
        counts[k] = counts["q1"] if k.startswith("q1") else counts["q2"]
    r = E.analyse(towns, counts, YEARS, stage="A", draws=8)
    q1 = r["questions"]["q1"]
    assert q1["est"] < 0 and r["minimum_met"] and q1["label"] != "no change larger than 15 %"
    assert r["checks"]["14_by_opening_period"]["run"] is False
    assert "9_town_trends_q1" in r["checks"] and "13_class_I" in r["checks"]


def test_main_refuses_without_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["estimate.py", "--stage", "A"])
    with pytest.raises(SystemExit) as e:
        E.main()
    assert "refusing" in str(e.value)
    monkeypatch.setattr(sys, "argv", ["estimate.py", "--stage", "B", "--headline-fixed"])
    with pytest.raises(SystemExit):
        E.main()


def made_up_list(tmp_path):
    """A list of bypasses with the frozen columns, construction facts only."""
    cols = pd.read_csv(T.LIST, nrows=0).columns
    rows = [
        # treated, works 2019, opened 2021
        dict(id="BYP-1", town="A", municipality_code="100001", road="I/1", road_class="I", status="opened",
             opened_date="2021-05-01", construction_start="2019-03", kind="full", carries_through_traffic="yes"),
        # treated but works from 2017: too few pre-construction years in stage A
        dict(id="BYP-2", town="B", municipality_code="100002", road="I/2", road_class="I", status="opened",
             opened_date="2020-05-01", construction_start="2017", kind="full", carries_through_traffic="yes"),
        # treated with another row in the town opened 2018: other works
        dict(id="BYP-3", town="C", municipality_code="100003", road="II/3", road_class="II", status="opened",
             opened_date="2022-05-01", construction_start="2020", kind="full", carries_through_traffic="yes"),
        dict(id="BYP-4", town="C", municipality_code="100003", road="II/30", road_class="II", status="opened",
             opened_date="2018-05-01", construction_start="2017", kind="relocation", carries_through_traffic="yes"),
        # staged: a partial first stage carrying the through traffic gives the opening
        dict(id="BYP-5", town="D", municipality_code="100004", road="I/5", road_class="I", status="opened",
             opened_date="2024-05-01", construction_start="2022", kind="full", carries_through_traffic="yes"),
        dict(id="BYP-6", town="D", municipality_code="100004", road="I/5", road_class="I", status="opened",
             opened_date="2021-05-01", construction_start="2019", kind="partial", carries_through_traffic="yes"),
        # comparison: in construction since 2023, serves to 2022; two towns, one bypass
        dict(id="BYP-7", town="E; F", municipality_code="100005; 100006", road="II/7", road_class="II",
             status="planned", stage="in construction", construction_start="2023-04", kind="full"),
        # comparison at an undated stage: left out
        dict(id="BYP-8", town="G", municipality_code="100007", road="I/8", road_class="I", status="planned",
             stage="pre-ÚR (EIA/záměr)", kind="full"),
        # comparison in construction without a date: excluded and listed
        dict(id="BYP-9", town="H", municipality_code="100008", road="I/9", road_class="I", status="planned",
             stage="in construction", kind="full"),
        # comparison opened 2026 without a start: serves to 2025
        dict(id="BYP-10", town="I", municipality_code="100009", road="II/10", road_class="II", status="opened",
             opened_date="2026-03-01", kind="full", carries_through_traffic="yes"),
    ]
    path = tmp_path / "list.csv"
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)
    return T.load_list(path)


def test_selection_rules_on_made_up_list(tmp_path):
    b = made_up_list(tmp_path)
    sel = T.select(b, area_change={100009: 0.03})
    t = sel.towns.set_index("code")
    assert set(t.index) == {100001, 100004, 100005, 100006}
    assert t.loc[100004, "open_year"] == 2021 and t.loc[100004, "start_year"] == 2019 and t.loc[100004, "staged"]
    assert t.loc[100005, "last_year"] == 2022 and t.loc[100005, "cluster"] == t.loc[100006, "cluster"]
    reasons = {r["id"]: r["reason"] for r in sel.rows_excluded}
    assert "before 2018" in reasons["BYP-2"] and reasons["BYP-9"] == "in construction without a start date"
    assert "BYP-8" not in reasons
    towns_out = {r["code"]: r["excluded"] for r in sel.excluded}
    assert "other works" in towns_out[100003] and "RÚIAN" in towns_out[100009]
    serving = T.comparisons_per_year(sel.towns)
    assert serving[2018] == 4 and serving[2023] == 0  # A and D before their works, E and F until 2022


def test_real_counts_on_made_up_records(tmp_path, monkeypatch):
    rec = pd.DataFrame({
        "year": [2018, 2018, 2018, 2019, 2019, 2019],
        "injury": [True, True, False, True, True, True],
        "ksi": [True, False, False, False, False, False],
        "built_up": [True, False, True, True, True, pd.NA],
        "road": ["I/1", "I/1", None, "II/9", "I/1", None],
        "muni_polygon": [1, 1, 1, 1, 2, pd.NA],
        "muni": [1, 1, 1, 1, 2, 1]}).astype({"built_up": "boolean", "muni_polygon": "Int64"})
    path = tmp_path / "acc.parquet"
    rec.to_parquet(path)
    monkeypatch.setattr(E, "ACCIDENTS", path)
    towns = pd.DataFrame({"town": [1], "road": ["I/1, I/16"]})
    c = E.real_counts(towns, None).set_index(["town", "year"])
    assert c.loc[(1, 2018), ["q1", "q1_all", "q1_ksi", "q1_oldroad", "q2", "q2_all", "outside"]].tolist() == \
        [1, 2, 1, 1, 2, 3, 1]
    # the record without coordinates counts in Q2 only; the record in municipality 2 is not a town of the table
    assert c.loc[(1, 2019), ["q1", "q2", "q1_oldroad"]].tolist() == [1, 2, 0]
    assert c.loc[(1, 2016), "q2"] == 0
