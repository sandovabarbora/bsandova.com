"""Worked examples on made-up votes for the UN votes study (design §2, §4, §6)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("un_votes", HERE / "votes.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
spec_e = importlib.util.spec_from_file_location("un_estimate", HERE / "estimate.py")
e = importlib.util.module_from_spec(spec_e)
spec_e.loader.exec_module(e)

Y, N, A, X = 0, 1, 2, -1


def matrix(rows: list[dict], fill: int = Y) -> pd.DataFrame:
    """Votes × members, every EU-27 member voting `fill` unless a row says otherwise."""
    cols = list(v.EU27) + ["USA"]
    return pd.DataFrame([{c: r.get(c, fill) for c in cols} for r in rows], index=range(len(rows)))


def test_score_partial_credit():
    a, b = np.array([Y, Y, Y, X]), np.array([Y, A, N, Y])
    assert np.allclose(v.score(a, b)[:3], [1, 0.5, 0]) and np.isnan(v.score(a, b)[3])
    assert np.allclose(v.score(a, b, partial=False)[:3], [1, 0, 0])


def test_leave_out_majority_and_ties():
    # vote 0: all yes but Czechia abstains; vote 1: 13 yes, 13 no among the others, a tie for Czechia
    others = [c for c in v.EU27 if c != "CZE"]
    tie = {c: (Y if i < 13 else N) for i, c in enumerate(others)} | {"CZE": Y}
    m = matrix([{"CZE": A}, tie])
    a = v.agreement_eu(m, "CZE")
    assert a[0] == 0.5 and np.isnan(a[1])
    # a comparison member's majority leaves out the focal member too
    m2 = matrix([{"CZE": N, "AUT": N}])
    assert v.agreement_eu(m2, "AUT", exclude=("CZE",))[0] == 0.0


def test_beta_equals_hand_computation():
    # four votes before, four after; Czechia leaves the EU on one vote after, the others never do
    rows = [{} for _ in range(4)] + [{"CZE": N}, {}, {}, {}]
    m = matrix(rows)
    a_f, a_c = v.agreements(m, "CZE", None)
    before = pd.Series([True] * 4 + [False] * 4)
    after = ~before
    cluster = pd.Series([f"item {i % 4}" for i in range(8)])
    b = v.beta(a_f, a_c, before, after, cluster, draws=200)
    assert b["est"] == pytest.approx(-0.25) and b["n_before"] == 4 and b["n_after"] == 4
    assert b["comparison"] == 26


def test_partner_is_neither_focal_nor_comparison():
    m = matrix([{"HUN": N}, {}])
    a_f, a_c = v.agreements(m, "CZE", "HUN")
    assert "HUN" not in a_c.columns and list(a_f) == [0.0, 1.0]


def test_labels_in_order():
    def b(est, ci95, ci90):
        return {"est": est, "ci95": ci95, "ci90": ci90}
    assert v.label(b(-0.04, [-0.07, -0.01], [-0.06, -0.02]), 0.05) == "lower agreement after the change"
    # significant but within ordinary movement in rank: not a shift
    assert v.label(b(-0.04, [-0.07, -0.01], [-0.06, -0.02]), 0.30) == "inconclusive"
    # too small to be a shift even with a narrow interval
    assert v.label(b(-0.015, [-0.025, -0.005], [-0.02, -0.01]), 0.04) == "no change larger than 3 points"
    assert v.label(b(0.0, [-0.08, 0.08], [-0.07, 0.07]), 0.5) == "underpowered"


def test_rank_counts_czechia_and_ties():
    p, n = v.rank_p(2.0, [1.0, -2.0, 0.5])
    assert n == 4 and p == pytest.approx(0.5)


def test_windows_and_buffer():
    assert v.after_cabinet("2017-12-13") == "2018-01-12"
    assert v.after_cabinet("2021-12-17") == "2022-01-16"
    d = pd.Series(pd.to_datetime(["2017-12-12", "2017-12-20", "2018-01-12"]))
    b, a = v.windows(d, ("2014-01-29", "2017-12-12"), ("2018-01-12", "2021-12-16"))
    assert list(b) == [True, False, False] and list(a) == [False, False, True]


def test_split_mask_ignores_focal():
    m = matrix([{"CZE": N}, {"AUT": N}])
    assert list(e.split_mask(m, "CZE")) == [False, True]


def test_changes_match_design():
    assert e.CHANGES["q2a"]["after"] == ("2018-01-12", "2021-12-16")
    assert e.CHANGES["q2b"]["after"] == ("2022-01-16", "2025-12-14")
    assert e.CHANGES["q1"]["before"] == ("2022-01-16", "2025-12-14")
    assert e.CHANGES["q1"]["after"] == ("2026-10-16", "2026-12-31")
