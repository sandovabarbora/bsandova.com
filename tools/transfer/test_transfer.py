"""Worked examples for the transfers screen and estimate, on made-up data only (no stop pass is read).

    uv run --with numpy --with pandas --with pyarrow --with duckdb --with pytest pytest -q tools/transfer/test_transfer.py
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sc, es = load("screen"), load("estimate")


def test_labels_follow_the_rule_in_its_literal_order():
    assert es.label((0.012, 0.03), (0.013, 0.028)) == "supported"
    assert es.label((-0.008, 0.009), (-0.006, 0.007)) == "not supported"
    assert es.label((-0.009, -0.002), (-0.008, -0.003)) == "not supported"  # below 0 but within ±1 point
    assert es.label((-0.03, -0.012), (-0.028, -0.014)) == "inconclusive"  # below 0 and past −1 point
    assert es.label((0.002, 0.02), (0.004, 0.018)) == "inconclusive"


def passes(rows: list[dict]) -> pd.DataFrame:
    base = {"sdate": pd.Timestamp("2025-05-06"), "first_row": False, "terminal_arrival": False, "od": np.nan,
            "prev_sa": np.nan, "prev_oa": np.nan, "oa": np.nan, "sd": np.nan}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_dep_hat_planned_b_and_exclusions():
    t0 = 1_746_500_000.0
    plat = pd.DataFrame({"stop_name": ["H", "H"], "stop_lat": [50.0, 50.0], "stop_lon": [14.0, 14.0009]},
                        index=["PA", "PB"])  # about 64 m apart: m = 60 + 64/1.2 ≈ 114 s
    p = passes([
        # A arrives at PA, scheduled t0, observed 30 s late; it came from X and goes on to Y
        dict(trip="a1", route="1", terminal="T1", stop_id="PA", stop_name="H", prev_name="X", next_stop_name="Y",
             sa=t0, oa=t0 + 30, sd=t0 + 20),
        # B trips at PB towards Z: one too early to plan (sd < sa + m), the planned one arrives early and waits,
        # the next arrives late
        dict(trip="b0", route="2", terminal="T2", stop_id="PB", stop_name="H", prev_name="W", next_stop_name="Z",
             sa=t0 + 60, oa=t0 + 60, sd=t0 + 90),
        dict(trip="b1", route="2", terminal="T2", stop_id="PB", stop_name="H", prev_name="W", next_stop_name="Z",
             sa=t0 + 150, oa=t0 + 100, sd=t0 + 180, od=t0 + 170),
        dict(trip="b2", route="2", terminal="T2", stop_id="PB", stop_name="H", prev_name="W", next_stop_name="Z",
             sa=t0 + 750, oa=t0 + 800, sd=t0 + 780),
        # line 3 goes back to X from the same platform: a return, kept but flagged as excluded
        dict(trip="c1", route="3", terminal="T3", stop_id="PA", stop_name="H", prev_name="Q", next_stop_name="X",
             sa=t0 + 200, oa=t0 + 200, sd=t0 + 240),
        # line 4 starts at the hub with no observed departure: dep_hat is its scheduled departure
        dict(trip="d1", route="4", terminal="T4", stop_id="PB", stop_name="H", prev_name=None, next_stop_name="V",
             sa=t0 + 300, sd=t0 + 300, first_row=True),
    ])
    conns, bt, info = sc.build_connections(p, {"H": ["1", "2", "3", "4"]}, plat)
    a_to_b = conns[(conns["aroute"] == "1") & (conns["broute"] == "2")].iloc[0]
    assert a_to_b["b_sd"] == t0 + 180 and a_to_b["slack"] == 180
    assert a_to_b["b_dep_hat"] == t0 + 180  # early arrival waits for its scheduled departure
    assert a_to_b["m"] == pytest.approx(60 + 64.0 / 1.2, abs=2)
    late = bt[(bt["bkey"].str.startswith("2|")) & (bt["sd"] == t0 + 780)].iloc[0]
    assert late["dep_hat"] == t0 + 800  # a late arrival leaves when it arrives
    assert bool(conns[(conns["aroute"] == "1") & (conns["broute"] == "3")]["excluded"].iloc[0])
    starts = bt[bt["bkey"].str.startswith("4|")].iloc[0]
    assert starts["dep_hat"] == t0 + 300 and bool(starts["starts_here"])
    assert info["counts"]["excluded_return_or_trunk"] >= 1


def synthetic(shared_trip: float, shared_day: float, days: int = 70, seed: int = 4) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One hub, one line pair, B every 10 min, A arriving 3 min before each B, so slack is 3 min and m = 60 s."""
    rng = np.random.default_rng(seed)
    rows_b, rows_c = [], []
    for i in range(days):
        d = date(2025, 4, 7) + timedelta(days=i)
        mid = pd.Timestamp(d).timestamp()
        day = rng.normal(0, shared_day)
        n = 84
        sd = mid + 6 * 3600 + 600 * np.arange(n)
        e = rng.normal(0, shared_trip, n)  # shared by A arrival k and its planned B trip k only
        delta = np.maximum(0, day + e + rng.normal(30, 40, n))
        d_a = day + e + rng.normal(0, 40, n)
        rows_b.append(pd.DataFrame({"date": d, "hub": "H", "bkey": "2|T2|PB", "sd": sd, "dep_hat": sd + delta,
                                    "od": np.nan, "starts_here": False}))
        sa = sd - 180
        rows_c.append(pd.DataFrame({
            "date": d, "hub": "H", "akey": "1|T1|PA", "bkey": "2|T2|PB", "aroute": "1", "broute": "2", "dist_m": 0.0,
            "m": 60.0, "a_sa": sa, "a_oa": sa + d_a, "a_prev_sa": np.nan, "a_prev_oa": np.nan,
            "a_terminal_arrival": False, "b_idx": np.arange(n), "b_sd": sd, "b_dep_hat": sd + delta, "b_oa": sd + delta,
            "b_od": np.nan, "b_starts_here": False, "slack": 180.0, "excluded": False}))
    return pd.concat(rows_c, ignore_index=True), pd.concat(rows_b, ignore_index=True)


def run_q1(c: pd.DataFrame, b: pd.DataFrame) -> tuple[dict, dict]:
    b = es.b_table(b)
    c = es.prepare(c, set())
    weeks = np.array(sorted(c["week"].unique()))
    q = es.q1_frame(c, b)
    q["sig"] = es.signature(q, b)
    S, N = es.day_donors(q, weeks)
    W = es.draws(len(weeks), 99, np.random.default_rng(0))
    return es.interval(es.within_stat(q, W, weeks)), es.interval(es.day_stat(q, S, N, W, weeks))


def test_independent_trips_give_no_within_day_effect_but_a_shared_day_moves_q1b():
    within, day = run_q1(*synthetic(shared_trip=0.0, shared_day=120.0))
    assert abs(within["est"]) < 0.01
    assert within["label"] == "not supported"
    assert day["est"] > 0.03  # the day's shock is shared by A and B, and other days do not share it


def test_a_planted_trip_level_shock_is_found_within_the_day():
    within, _ = run_q1(*synthetic(shared_trip=150.0, shared_day=0.0))
    assert within["est"] > 0.05
    assert within["label"] == "supported"


def test_within_donors_are_exact_and_skip_the_planned_trip_and_its_neighbours():
    c, b = synthetic(shared_trip=0.0, shared_day=0.0, days=1)
    b = es.b_table(b)
    c = es.prepare(c, set())
    made, n = es.within_donors(c, b)
    # ±60 min at 10-min headways holds 13 trips; the planned one and its two neighbours are excluded
    assert n[40] == 10
    k = 40
    sd, dl = b["sd"].to_numpy(), b["delta_b"].to_numpy()
    ok = (np.abs(sd - sd[k]) <= 3600) & (np.abs(np.arange(len(sd)) - k) > 1)
    assert made[k] == np.sum(dl[ok] >= c["req"].to_numpy()[k])


def test_extra_wait_counts_from_the_planned_schedule_and_is_censored():
    c, b = synthetic(shared_trip=0.0, shared_day=0.0, days=1)
    b = es.b_table(b)
    c = es.prepare(c, set())
    w = es.extra_wait(c, b)
    assert np.all(w <= es.CENSOR_S)
    caught = c["made"].to_numpy() == 1
    assert np.all(w[caught] == (c["b_dep_hat"] - c["b_sd"]).to_numpy()[caught])  # caught: wait = B's lateness
    assert np.all(w[~caught] >= 600 - 1)  # missed: at least one headway later, at 10-min headways


def test_checks_and_bounds_run_end_to_end():
    c, b = synthetic(shared_trip=150.0, shared_day=0.0, days=28)
    c.loc[c.index[::50], "b_dep_hat"] = np.nan  # a few unobserved planned B
    b = es.b_table(b)
    c = es.prepare(c, set())
    c["delta_od_c"] = (c["b_od"] - c["b_sd"]).where(~c["b_starts_here"])
    c["w"] = es.extra_wait(c, b)
    es.CHECK_REPS = 19
    weeks = np.array(sorted(c["week"].unique()))
    W = es.draws(len(weeks), 19, np.random.default_rng(1))
    missing = pd.DataFrame({"stop_name": ["H"], "route": ["2"], "sdate": [pd.Timestamp("2025-04-08")],
                            "hour": [9], "missing": [1]})
    bd = es.bounds(c, b, missing, W, weeks)
    assert bd["all_made"]["est"] >= bd["all_missed"]["est"]
    out = es.checks(c, b, weeks, np.random.default_rng(2))
    for k in ("timing_a_plus_30s", "margin_m_plus_30s", "margin_m_fixed_2min", "without_exclusions", "peaks_only"):
        assert "est" in out[k]
    assert out["margin_m_minus_30s"]["est"] > 0.03  # the planted link survives a different margin
    cost = es.cost(c)
    assert set(cost) == {"3"} and 0 < cost["3"]["made"] < 1
