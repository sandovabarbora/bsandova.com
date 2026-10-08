"""Worked examples for the delay-origins estimate, on made-up data only (no segment record is read).

    uv run --with numpy --with pandas --with pyarrow --with scipy --with pytest pytest -q tools/late/test_late.py
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("late_estimate", Path(__file__).resolve().parent / "estimate.py")
le = importlib.util.module_from_spec(spec)
spec.loader.exec_module(le)


def test_concentration_counts_only_producers_in_the_denominator():
    total = np.array([50.0, 10, 10, 10, 10, 5, 5, 0, -20, -30])  # top 10 % = 1 segment of 10
    assert le.concentration(total) == pytest.approx(50 / 100)
    assert le.concentration(total, 0.20) == pytest.approx(60 / 100)


def test_labels():
    assert le.label([0.55, 0.70], 0.50) == "supported"
    assert le.label([0.30, 0.45], 0.50) == "not supported"
    assert le.label([0.45, 0.60], 0.50) == "inconclusive"
    assert le.label([0.70, 0.80], 0.70, at_or_above=True) == "supported"


def synthetic(hot: float, noise: float, seed: int = 1, segments: int = 60, days: int = 84) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = rng.normal(2, 3, segments)
    base[:6] += hot  # a tenth of the segments are hotspots
    rows = []
    for s in range(segments):
        for i in range(days):
            d = date(2025, 4, 7) + timedelta(days=i)
            for h in (8, 12, 16):
                n = 20
                g = n * (base[s] + rng.normal(0, noise))
                rows.append(("tram", f"S{s}", f"S{s + 1}", d, h, s == 0, n, g, n, g, n, 0.8 * g))
    return pd.DataFrame(rows, columns=["mode", "seg_from", "seg_to", "date", "hour", "terminal", "n", "gsum",
                                       "n300", "gsum300", "n_run", "gsum_run"])


def test_strong_hotspots_are_concentrated_and_stable():
    le.REPS = 49
    r = le.primary(synthetic(hot=40, noise=2), np.random.default_rng(0))
    assert r["S"]["label"] == "supported"
    assert r["rho"]["label"] == "supported"
    assert r["segments"] == 60


def test_no_hotspots_and_pure_noise_is_neither_concentrated_nor_stable():
    le.REPS = 49
    r = le.primary(synthetic(hot=0, noise=40, segments=200), np.random.default_rng(0))
    assert r["S"]["label"] == "not supported"
    assert r["rho"]["label"] == "not supported"


def test_checks_and_map_rows():
    seg = synthetic(hot=40, noise=2)
    c = le.checks(seg)
    assert set(c) == {"per_pass", "top_5", "top_20", "without_terminal_segments", "gain_within_300s", "running_time_only",
                      "by_month", "peak_midday_jaccard"}
    assert c["top_5"] < c["top_20"]
    assert c["peak_midday_jaccard"] == pytest.approx(1.0)  # the same hotspots at every hour
    stops = pd.DataFrame({"name": [f"S{i}" for i in range(61)], "lat": 50.0, "lon": np.linspace(14.3, 14.6, 61)})
    rows = le.segments_for_map(seg, stops)
    assert len(rows) == 60 and rows[0]["line"][0] == (14.3, 50.0)
