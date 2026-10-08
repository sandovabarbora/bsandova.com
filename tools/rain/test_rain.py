"""Worked examples for units.py and estimate.py, on made-up data only (no thesis record is read).

    uv run --with duckdb --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/rain/test_rain.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate  # noqa: E402
import units  # noqa: E402

DAY = date(2025, 5, 6)  # Prague is UTC+2 in May


def utc(h: int, m: int) -> datetime:
    return datetime(2025, 5, 6, h - 2, m, tzinfo=timezone.utc)


@pytest.fixture()
def db(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "t.duckdb"
    con = duckdb.connect(str(path))
    con.execute("""CREATE TABLE stop_times_history_modeling (rt_trip_id VARCHAR, route_type VARCHAR,
        gtfs_stop_sequence BIGINT, next_stop_name VARCHAR, real_current_stop_arrival TIMESTAMPTZ,
        real_current_stop_departure TIMESTAMPTZ, current_stop_arr_delay BIGINT, current_stop_dep_delay BIGINT,
        year BIGINT, month BIGINT)""")
    rows = [
        # trip A, line 22 towards Bílá Hora: 08:10 +30 s, 08:20 +50 s, 08:40 +90 s -> gain 60; 09:05 is alone in its hour
        ("t_22_1_250501_1", "tramvaj", 1, "B", utc(8, 10), utc(8, 11), 30, 35),
        ("t_22_1_250501_1", "tramvaj", 2, "C", utc(8, 20), utc(8, 21), 50, 55),
        ("t_22_1_250501_1", "tramvaj", 3, "D", utc(8, 40), utc(8, 41), 90, 95),
        ("t_22_1_250501_1", "tramvaj", 4, "Bílá Hora", utc(9, 5), utc(9, 6), 100, 100),
        # trip B, same line and terminal: 08:15 −20 s, then arrival missing so departure 08:50 with its own delay +10 s
        ("t_22_2_250501_1", "tramvaj", 1, "C", utc(8, 15), utc(8, 16), -20, -15),
        ("t_22_2_250501_1", "tramvaj", 2, "Bílá Hora", None, utc(8, 50), 999, 10),
        # trip C, the other direction: a single trip in the hour, a thin unit
        ("t_22_3_250501_1", "tramvaj", 1, "Y", utc(8, 5), utc(8, 6), 0, 0),
        ("t_22_3_250501_1", "tramvaj", 2, "Nádraží Hostivař", utc(8, 30), utc(8, 31), 40, 40),
        # regional bus 400 is not a city bus and is left out
        ("t_400_1_250501_1", "autobus", 1, "X", utc(8, 0), utc(8, 1), 0, 0),
        ("t_400_1_250501_1", "autobus", 2, "Z", utc(8, 30), utc(8, 31), 60, 60),
    ]
    con.executemany("INSERT INTO stop_times_history_modeling VALUES (?, ?, ?, ?, ?, ?, ?, ?, 2025, 5)", rows)
    con.execute("""CREATE TABLE stop_times_history_intermediate_stops (gtfs_route_short_name VARCHAR,
        ze_zastavky VARCHAR, ze_zastavky_lat DOUBLE, ze_zastavky_lon DOUBLE)""")
    con.execute("INSERT INTO stop_times_history_intermediate_stops VALUES ('22', 'A', 50.0, 14.4), ('22', 'B', 50.2, 14.6)")
    con.close()
    screen, feed = tmp_path / "screen.json", tmp_path / "feed.json"
    screen.write_text(json.dumps({"exclusions": {"tram": {"22": [DAY.isoformat()]}, "bus": {}},
                                  "exclusions_literal": {"tram": {"22": [DAY.isoformat()]}, "bus": {}}}))
    feed.write_text(json.dumps({"rule2_dates_excluded": []}))
    monkeypatch.setattr(units, "SCREEN", screen)
    monkeypatch.setattr(units, "FEED", feed)
    return path


def test_units_worked_example(db):
    u, centroids = units.build(db, months=[5])
    u = u.set_index(["route", "direction", "hour"])
    a = u.loc[("22", "Bílá Hora", 8)]
    assert a["trips"] == 2
    assert a["y"] == pytest.approx((60 + 30) / 2)  # A gains 90 − 30, B gains 10 − (−20)
    assert a["level"] == pytest.approx((30 + 50 + 90 - 20 + 10) / 5)
    assert bool(a["rule1"]) and not bool(a["rule2"])
    assert u.loc[("22", "Nádraží Hostivař", 8), "trips"] == 1  # thin, dropped later by trips >= 2
    assert u.loc[("22", "Bílá Hora", 9), "trips"] == 0  # one pass only: no gain for that hour
    assert set(u["mode"]) == {"tram"}  # route 400 is regional
    assert centroids.set_index("route").loc["22", "lat"] == pytest.approx(50.1)


def test_weather_classes():
    idx = pd.date_range("2025-05-06 00:00", periods=8, freq="h", tz="Europe/Prague")
    w = pd.DataFrame({st: [0, 0, 0, 0, 1.0, 0, 0, 0] for st in estimate.STATIONS}, index=idx)
    wx = estimate.weather(w)
    assert list(wx["rain"]) == [False, False, False, False, True, False, False, False]
    # dry needs zero in the hour and the two before: hours 5 and 6 follow rain, hour 7 is dry again
    assert list(wx["dry"]) == [False, False, True, True, False, False, False, True]
    assert bool(wx.loc[3, "rain_next"]) and bool(wx.loc[5, "rain_l1"]) and bool(wx.loc[6, "rain_l2"])


def synthetic(delta: float, noise: float, seed: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    days = [date(2025, 5, 1) + timedelta(days=i) for i in range(60)]
    wx = pd.DataFrame([(d, h) for d in days for h in range(5, 24)], columns=["date", "hour"])
    wx["rain"] = rng.random(len(wx)) < 0.12
    wx["dry"] = ~wx["rain"]
    for c in ("rain_next", "dry_next", "rain_l1", "rain_l2"):
        wx[c] = False
    wx["p"] = np.where(wx["rain"], 1.0, 0.0)
    rows = []
    day_fx = {d: rng.normal(0, 15) for d in days}
    for r in range(8):
        for direction in ("north", "south"):
            route_fx = rng.normal(0, 20)
            for d, h, rain in zip(wx["date"], wx["hour"], wx["rain"]):
                y = route_fx + day_fx[d] + 3 * (h % 4) + delta * rain + rng.normal(0, noise)
                rows.append(("tram", str(r + 1), direction, d.isoformat(), h, 5, y, y + 60, False, False, False))
    u = pd.DataFrame(rows, columns=["mode", "route", "direction", "date", "hour", "trips", "y", "level",
                                    "rule1", "rule1_literal", "rule2"])
    return u, wx


def test_estimate_recovers_a_known_effect():
    u, wx = synthetic(delta=20.0, noise=10.0)
    r = estimate.primary(estimate.frame(u, wx, "tram"), np.random.default_rng(0))
    assert r["delta_s"] == pytest.approx(20.0, abs=3 * r["se_s"])
    assert r["label"] == "supported"
    assert r["inference"] == "clustered by date"  # well over 30 rain dates


def test_estimate_labels_a_null_effect_not_supported():
    u, wx = synthetic(delta=0.0, noise=5.0)
    r = estimate.primary(estimate.frame(u, wx, "tram"), np.random.default_rng(0))
    assert r["label"] == "not supported"


def test_screened_units_are_left_out():
    u, wx = synthetic(delta=0.0, noise=5.0)
    u.loc[u["route"] == "1", "rule1"] = True
    u.loc[u["date"] == "2025-05-02", "rule2"] = True
    u.loc[u["route"] == "2", "trips"] = 1
    f = estimate.frame(u, wx, "tram")
    assert not set(f["route"]) & {"1", "2"}
    assert date(2025, 5, 2) not in set(f["date"])


def test_label_rules():
    assert estimate.label((0.5, 9.0), (1.0, 8.0)) == "supported"
    assert estimate.label((-12.0, 11.0), (-9.0, 9.5)) == "not supported"
    assert estimate.label((-1.0, 25.0), (0.5, 20.0)) == "inconclusive"  # 90 % above 0 is not enough


def test_wild_bootstrap_interval_covers_the_estimate():
    u, wx = synthetic(delta=20.0, noise=10.0)
    lone = u.iloc[[0]].assign(direction="lone")  # a singleton cell, as the real data have; must not break the fit
    u = pd.concat([u, lone], ignore_index=True)
    s = estimate.frame(u, wx, "tram")
    s = s[s["rain"] | s["dry"]].assign(rain=lambda x: x["rain"].astype(int))
    estimate.BOOT_REPS = 49
    lo, hi = estimate.wild_interval(s, "rain", 0.95, np.random.default_rng(0))
    assert lo < 20.0 < hi


def test_every_check_runs_and_the_metro_control_finds_nothing():
    u, wx = synthetic(delta=20.0, noise=10.0)
    for st in estimate.STATIONS:
        wx[f"rain_{st}"], wx[f"dry_{st}"] = wx["rain"], wx["dry"]
    wx["rain_next"], wx["dry_next"] = wx["rain"].shift(-1, fill_value=False), wx["dry"].shift(-1, fill_value=False)
    wx["rain_l1"], wx["rain_l2"] = wx["rain"].shift(1, fill_value=False), wx["rain"].shift(2, fill_value=False)
    m_rows = u.copy()
    m_rows["mode"], m_rows["route"] = "metro", "991"
    wx_by = wx.assign(date=wx["date"].astype(str)).set_index(["date", "hour"])["rain"]
    m_rows["y"] = m_rows["y"] - 20.0 * wx_by.loc[list(zip(m_rows["date"], m_rows["hour"]))].to_numpy()
    allu = pd.concat([u, m_rows], ignore_index=True)
    near = estimate.nearest_station(pd.DataFrame({"route": [str(r) for r in range(1, 9)], "lat": 50.08, "lon": 14.42}))
    assert set(near.values()) == {"0-203-0-11514"}  # Klementinum is closest to the centre
    c = estimate.checks(allu, wx, near)
    assert set(c) == {"placebo_lead", "lags", "dose", "nearest_station", "metro", "level_instead_of_gain",
                      "disruption_days_kept", "rule1_literal"}
    assert c["nearest_station"]["rain_st"]["est_s"] == pytest.approx(20.0, abs=4)
    assert abs(c["metro"]["rain"]["est_s"]) < 4
