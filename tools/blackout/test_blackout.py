"""Worked examples for the blackout estimate, on made-up data only (no transit record is read).

    uv run --no-project --with numpy --with pandas --with pyarrow --with pytest pytest -q tools/blackout/test_blackout.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location("blackout_estimate", Path(__file__).resolve().parent / "estimate.py")
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)

EVENT, BASE = "2025-07-04", ["2025-07-11", "2025-07-18", "2025-07-25"]
NOON = 12 * 60


def passes(day: str, mode: str = "tramvaj", segs: int = 20, every: float = 2.0, stop=None, back=None,
           extra_delay=0.0, route: str = "22", rng=None) -> pd.DataFrame:
    """Passes every `every` minutes on each segment from 10:00 to 22:00; none in [stop, back) on the event."""
    rng = rng or np.random.default_rng(1)
    rows = []
    for s in range(segs):
        for t in np.arange(10 * 60 + s * 0.1, 22 * 60, every):
            if stop is not None and stop <= t < back:
                continue
            late = extra_delay if back is not None and back <= t < back + 120 else 0.0
            rows.append((mode, route, f"S{s}", f"S{s + 1}", day, t, t - 0.5, 30 + late + rng.normal(0, 5)))
    return pd.DataFrame(rows, columns=["mode", "route", "seg_from", "seg_to", "date", "t", "t_dep", "delay"])


def network(stop=NOON, back=NOON + 60, extra_delay=300.0) -> pd.DataFrame:
    parts = [passes(d) for d in BASE] + [passes(EVENT, stop=stop, back=back, extra_delay=extra_delay)]
    return pd.concat(parts, ignore_index=True)


def test_outage_restart_and_delay_recovery():
    p = network()
    b = be.binned(p)
    t = be.times(b, EVENT, BASE, "tramvaj")
    assert t["T50"] == "13:00" and t["T90"] == "13:00"
    # delays stay high for two hours after the restart, then come back into the band
    assert t["TD"] == "15:00"


def test_placebo_is_noon_on_an_ordinary_day():
    p = network()
    b = be.binned(p)
    out = be.with_placebo(lambda d, r: be.times(b, d, r, "tramvaj"), EVENT, BASE)
    assert all(v == {"T50": "12:00", "T90": "12:00", "TD": "12:00"} for v in out["placebo"].values())


def test_one_noisy_bin_does_not_move_t90():
    p = network(stop=None, back=None)
    # drop half the passes of one bin on the event day
    p = p[~((p.date == EVENT) & (p.t >= NOON + 20) & (p.t < NOON + 30) & (p.seg_from.str[1:].astype(int) % 2 == 0))]
    t = be.times(be.binned(p), EVENT, BASE, "tramvaj")
    assert t["T90"] == "12:00"


def test_stopped_share_and_order():
    p = network()
    q1 = be.stopped_share(p, EVENT, BASE)
    assert q1["share"] == 1.0 and q1["segments_stopped"] == 20
    order = be.restart_order(p, EVENT, BASE)
    assert len(order) == 20 and all(r["mapped"] for r in order)
    # restart at 13:00 + segment offset; lag = 13:00 − 12:10 − half a 2-minute headway ≈ 49 min
    assert abs(order[0]["lag_min"] - 49.0) < 0.5
    assert abs(order[0]["after_13_01_min"] - (-1.0)) < 0.5


def test_low_frequency_segments_are_excluded_from_the_share():
    p = pd.concat([network(), *[passes(d, segs=1, every=15.0).assign(seg_from="R", seg_to="Q") for d in [*BASE, EVENT]]])
    q1 = be.stopped_share(p, EVENT, BASE)
    assert q1["low_frequency_excluded"] == 1 and q1["segments"] == 20


def test_metro_control():
    parts = []
    for line, back in (("991", NOON + 15), ("992", NOON + 35)):
        parts.append(passes(EVENT, mode="metro", segs=5, stop=NOON, back=back, route=line))
    m = be.metro_control(pd.concat(parts), EVENT)
    assert 0 <= m["991"]["miss_min"] < 2 and 0 <= m["992"]["miss_min"] < 2
    assert m["993"]["estimated"] is None


def test_first_run_skips_missing_bins():
    ok = pd.Series([1.0] * 12 + [np.nan] + [1.0] * 59)
    assert be.first_run(ok, 10) == 12 * 60 + 10
