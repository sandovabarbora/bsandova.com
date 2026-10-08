"""Worked examples for the bunching estimate, on made-up data only (no headway is read).

    uv run --with numpy --with pandas --with pyarrow --with scipy --with pytest pytest -q tools/bunch/test_bunch.py
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("bunch_estimate", Path(__file__).resolve().parent / "estimate.py")
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)


def synthetic(gamma: float, noise: float, hot: dict | None = None, days: int = 56, pairs: int = 60, K: int = 18,
              seed: int = 3) -> pd.DataFrame:
    """Pairs on two patterns; r follows r_k = r_{k−1} + γ(r_{k−1} − 1) + shock (+ a push at hotspot stops), observed
    with noise. Returns the pair-stop table in the screening's layout."""
    rng = np.random.default_rng(seed)
    hot = hot or {}
    rows = []
    for di in range(days):
        d = date(2025, 4, 7) + timedelta(days=di)
        for p in range(pairs):
            pat = "A" if p % 2 else "B"
            r = 1.0 + rng.normal(0, 0.05)
            for k in range(K):
                if k:
                    r = r + gamma * (r - 1) + rng.normal(0, 0.04) - hot.get((pat, k), 0) * (rng.random() < 0.3)
                H = 480.0
                ro = r + rng.normal(0, noise)
                rows.append((pat, d, f"L{p}", f"F{p}", k, f"{pat}{k}", f"{pat}{k - 1}" if k else None, H, H, ro * H,
                             np.nan, 1, 7 + p % 12, K + 2, f"{pat}{k}", f"{pat}{k - 1}" if k else None))
    return be.prepare(pd.DataFrame(rows, columns=["pattern", "sdate", "lead", "follow", "k", "stop_id",
                                                  "prev_stop_id", "H0", "H", "h", "h_dep", "status", "hour", "L",
                                                  "stop_name", "prev_name"]))


def test_iv_is_near_zero_under_pure_diffusion_with_noise_and_the_registered_shuffle_is_not():
    be.REPS = 49
    r = be.q1(synthetic(gamma=0.0, noise=0.05), np.random.default_rng(0))
    assert abs(r["gamma_iv"]) < 0.01
    assert r["gamma_ols"] < -0.1  # noise alone pulls the plain estimate down
    assert r["gamma_minus_gamma0_registered"] < -0.1  # and the shuffle does not remove it: why the design changed


def test_iv_recovers_a_known_amplification_through_noise():
    be.REPS = 49
    r = be.q1(synthetic(gamma=0.04, noise=0.05), np.random.default_rng(0))
    assert r["gamma_iv"] == pytest.approx(0.04, abs=0.015)
    assert r["label"] == "supported"


def test_gamma_labels():
    assert be.label_gamma([0.01, 0.03], [0.012, 0.028]) == "supported"
    assert be.label_gamma([-0.009, 0.008], [-0.008, 0.007]) == "not supported"
    assert be.label_gamma([-0.05, -0.02], [-0.045, -0.025]) == "inconclusive"  # correction, reported as such


def odd_mask(ps: pd.DataFrame) -> tuple[int, np.ndarray]:
    dates = ps.drop_duplicates("date_id").sort_values("date_id")
    n = int(ps["date_id"].max() + 1)
    odd = np.zeros(n, bool)
    odd[dates["date_id"].to_numpy()] = (dates["week"] % 2 == 1).to_numpy()
    return n, odd


def test_birth_concentration_is_near_one_without_hotspots_and_above_with_them():
    be.REPS, be.NULL_POINT, be.NULL_DRAW = 19, 49, 9
    be.FLOOR, be.FLOOR_LOW, be.MIN_PLATFORMS = 100, 50, 5
    uniform = {(p, k): 0.85 for p in "AB" for k in range(1, 18)}
    planted = {("A", 5): 0.85, ("B", 11): 0.85, ("A", 13): 0.85}
    # γ = −1: every stop starts again from r ≈ 1, so a birth's chance is the same everywhere unless planted
    for hot, check in ((uniform, lambda x: 0.8 < x < 1.2), (planted, lambda x: x > 1.25)):
        ps = synthetic(gamma=-1.0, noise=0.02, hot=hot, pairs=40, days=42)
        n, odd = odd_mask(ps)
        res = be.q2(be.events(ps), n, odd, np.random.default_rng(1), reps=19)
        assert check(res["ratio"]), (hot, res["ratio"])


def test_parity_follows_the_iso_week():
    ps = synthetic(gamma=0.0, noise=0.0, days=14, pairs=2)
    n, odd = odd_mask(ps)
    weeks = ps.drop_duplicates("date_id").set_index("date_id")["week"]
    assert all(odd[i] == (weeks[i] % 2 == 1) for i in weeks.index)


def test_events_definitions():
    ps = synthetic(gamma=0.0, noise=0.0, days=1, pairs=2, K=4)
    ps.loc[:, "r"] = [1.0, 0.6, 0.1, 0.7, 1.0, 0.6, -0.2, 0.9]  # pattern B pair then A pair (sorted by pair, k)
    ev = be.events(ps)
    assert ev["birth"].sum() == 1 and ev["death"].sum() == 1 and ev["swap_tr"].sum() == 1
