"""Worked examples for the gehl-trams estimate, on made-up data only (no dwell or weather record is read).

    uv run --with numpy --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/gehl/test_gehl.py
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("gehl_estimate", Path(__file__).resolve().parent / "estimate.py")
ge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ge)


def test_lead_two_days_points_at_the_same_hour_two_days_later():
    c = pd.DataFrame({"date": [date(2025, 7, 1), date(2025, 7, 1), date(2025, 7, 3), date(2025, 7, 3)],
                      "hour": [14, 15, 14, 15], "rain": [False, False, True, False]})
    assert list(ge.lead_two_days(c)) == [True, False, False, False]


def test_label_rules():
    assert ge.label((-3, -1), (-2.8, -1.2), 2.0) == "supported"
    assert ge.label((-1.5, 1.5), (-1.2, 1.2), 2.0) == "not supported"
    assert ge.label((1, 3), (1.2, 2.8), 2.0) == "inconclusive"  # the opposite of the prediction
    assert ge.label((-4, 1), (-3.5, 0.5), 2.0) == "inconclusive"


def synthetic(theta: float, noise: float, seed: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    days = [date(2025, 5, 5) + timedelta(days=i) for i in range(84)]  # twelve weeks
    wx = pd.DataFrame([(d, h) for d in days for h in range(5, 24)], columns=["date", "hour"])
    wet_day = {d: rng.random() < 0.25 for d in days}
    wx["rain"] = [wet_day[d] and rng.random() < 0.4 for d in wx["date"]]
    wx["mean"] = np.where(wx["rain"], 1.5, 0.0)
    wx["dry"] = ~wx["rain"]
    hot_day = {d: rng.random() < 0.15 for d in days}
    wx["t"] = [31.0 if hot_day[d] and 12 <= h <= 18 else 20.0 for d, h in zip(wx["date"], wx["hour"])]
    wx["hot"], wx["mild"] = wx["dry"] & (wx["t"] >= 30), wx["dry"] & wx["t"].between(15, 25)
    wx["rain_lead2"] = ge.lead_two_days(wx)
    week_fx = {d: rng.normal(0, 1) for d in days}
    rows = []
    for r in range(8):
        for direction in ("a", "b"):
            fx = rng.normal(40, 4)
            for d, h, rain in zip(wx["date"], wx["hour"], wx["rain"]):
                off = d.weekday() >= 5
                y = (fx + week_fx[d - timedelta(days=d.weekday())] + 0.3 * (h % 4) + 1.0 * rain
                     + theta * rain * off + rng.normal(0, noise))
                rows.append((str(r + 1), direction, d, h, 30, y, d.weekday(), False, 10, y + 2, y - 1))
    u = pd.DataFrame(rows, columns=["route", "direction", "date", "hour", "passes", "y", "weekday", "holiday",
                                    "passes_centre", "y_centre", "y_outer"])
    return u, wx


def test_recovers_a_known_interaction_with_week_effects():
    u, wx = synthetic(theta=-3.0, noise=1.5)
    ge.BOOT_REPS = 49
    r = ge.estimate(ge.frame(u, wx), ge.PRIMARY, "rain_opt", "rain_opt", 2.0, np.random.default_rng(0))
    assert r["est_s"] == pytest.approx(-3.0, abs=3 * r["se_s"])
    assert r["label"] == "supported"
    assert r["inference"] == "wild cluster bootstrap by date"


def test_a_null_interaction_is_not_supported():
    u, wx = synthetic(theta=0.0, noise=0.5)
    ge.BOOT_REPS = 49
    r = ge.estimate(ge.frame(u, wx), ge.PRIMARY, "rain_opt", "rain_opt", 2.0, np.random.default_rng(0))
    assert r["label"] == "not supported"


def test_rain_common_to_both_windows_cancels_in_theta():
    u, wx = synthetic(theta=0.0, noise=0.5)
    m = ge.fit(ge.frame(u, wx), ge.PRIMARY)
    assert float(m.coef()["rain"]) == pytest.approx(1.0, abs=0.3)
    assert abs(float(m.coef()["rain_opt"])) < 0.5


def test_every_check_runs_and_is_reported():
    u, wx = synthetic(theta=-3.0, noise=1.5)
    out = ge.checks(u, wx, 2.0, np.random.default_rng(0))
    assert set(out) == {"date_effects", "by_window", "dose", "evening", "school_holidays_out", "weekday_midday",
                        "centre", "outer", "placebo_rain_two_days_later", "heat_gehl_contrast"}
    assert out["centre"]["rain_opt"]["est_s"] == pytest.approx(-3.0, abs=1.5)
    assert set(out["dose"]) == {"r0_2", "r2_5", "r5_up", "r0_2_opt", "r2_5_opt", "r5_up_opt"}
    assert out["dose"]["r5_up"]["est_s"] is None  # no hour reaches 5 mm in the made-up weather
