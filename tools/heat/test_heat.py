"""Worked examples for the heat estimate, on made-up data only (no delay or temperature record is read).

    uv run --with numpy --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/heat/test_heat.py
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("heat_estimate", Path(__file__).resolve().parent / "estimate.py")
he = importlib.util.module_from_spec(spec)
spec.loader.exec_module(he)


def test_lead_two_days_points_at_the_same_hour_two_days_later():
    c = pd.DataFrame({"date": [date(2025, 7, 1), date(2025, 7, 1), date(2025, 7, 3), date(2025, 7, 3)],
                      "hour": [14, 15, 14, 15], "hot": [False, False, True, False]})
    assert list(he.lead_two_days(c)) == [True, False, False, False]


def synthetic(delta: float, noise: float, seed: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    days = [date(2025, 6, 2) + timedelta(days=i) for i in range(70)]  # ten weeks
    wx = pd.DataFrame([(d, h) for d in days for h in range(5, 24)], columns=["date", "hour"])
    hot_day = {d: rng.random() < 0.3 for d in days}
    wx["t"] = [32.0 if hot_day[d] and 12 <= h <= 18 else 20.0 for d, h in zip(wx["date"], wx["hour"])]
    wx["dry"], wx["rain_any"] = True, False
    wx["hot"], wx["mild"] = wx["t"] >= 30, wx["t"].between(15, 25)
    wx["hot_lead2"] = False
    week_fx = {d: rng.normal(0, 10) for d in days}
    rows = []
    for r in range(6):
        for direction in ("a", "b"):
            fx = rng.normal(0, 20)
            for d, h, hot in zip(wx["date"], wx["hour"], wx["hot"]):
                y = fx + week_fx[d - timedelta(days=d.weekday())] + 2 * (h % 5) + delta * hot + rng.normal(0, noise)
                rows.append(("tram", str(r + 1), direction, d.isoformat(), h, 4, y, y + 50, False, False, False))
    u = pd.DataFrame(rows, columns=["mode", "route", "direction", "date", "hour", "trips", "y", "level",
                                    "rule1", "rule1_literal", "rule2"])
    return u, wx


def test_recovers_a_known_heat_effect_with_week_effects():
    u, wx = synthetic(delta=15.0, noise=8.0)
    he.BOOT_REPS = 49
    r = he.primary(he.frame(u, wx, "tram"), np.random.default_rng(0))
    assert r["delta_s"] == pytest.approx(15.0, abs=3 * r["se_s"])
    assert r["label"] == "supported"
    assert r["inference"] == "wild cluster bootstrap by date"  # fewer than 30 hot dates


def test_a_null_effect_is_not_supported():
    u, wx = synthetic(delta=0.0, noise=4.0)
    he.BOOT_REPS = 49
    assert he.primary(he.frame(u, wx, "tram"), np.random.default_rng(0))["label"] == "not supported"


def test_every_check_runs():
    u, wx = synthetic(delta=15.0, noise=8.0)
    m = u.assign(mode="metro", route="991")
    c = he.checks(pd.concat([u, m], ignore_index=True), wx)
    assert set(c) == {"date_effects", "dose", "metro", "threshold_28", "threshold_32", "wet_hours_kept",
                      "level_instead_of_gain", "placebo_two_days_later"}
    assert c["dose"]["t32_up"]["est_s"] == pytest.approx(15.0, abs=4)
    # no rain and no later heat in the made-up data: listed as not estimable, the run goes on
    assert c["placebo_two_days_later"]["hot_lead2"]["est_s"] is None
