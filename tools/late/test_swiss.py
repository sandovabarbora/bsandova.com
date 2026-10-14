"""Worked examples for the swiss-trams estimate, on made-up data only (no Swiss record is read).

    uv run --no-project --with numpy --with pandas --with pyarrow --with scipy --with pytest pytest -q tools/late/test_swiss.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("swiss_estimate", HERE / "swiss_estimate.py")
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)


def test_q3_labels():
    rng = np.random.default_rng(1)
    assert se.q3_label(rng.normal(0.00, 0.01, 999)) == "like Prague"
    assert se.q3_label(rng.normal(0.15, 0.02, 999)) == "unlike Prague, more concentrated"
    assert se.q3_label(rng.normal(-0.15, 0.02, 999)) == "unlike Prague, less concentrated"
    assert se.q3_label(rng.normal(0.00, 0.05, 999)) == "underpowered for equivalence"
    assert se.q3_label(rng.normal(0.045, 0.01, 999)) == "inconclusive"


def passes(place_effect: float, segs: int = 100, per: int = 400, seed: int = 2):
    rng = np.random.default_rng(seed)
    mu = place_effect * rng.exponential(1.0, segs)
    seg = np.repeat(np.arange(segs), per)
    g = rng.normal(mu[seg], 30.0)
    group = rng.integers(0, 50, len(seg))
    return seg, group, g


def test_chance_level_is_low_without_a_place_effect_and_below_s_with_one():
    seg, group, g = passes(place_effect=40.0)
    s = se.concentration(np.bincount(seg, weights=g))
    s0 = se.chance(seg, group, g, seg.max() + 1, np.random.default_rng(3))
    assert s0["median"] < s - 0.2
    seg, group, g = passes(place_effect=0.0)
    s0 = se.chance(seg, group, g, seg.max() + 1, np.random.default_rng(3))
    assert s0["range95"][0] <= se.concentration(np.bincount(seg, weights=g)) <= s0["range95"][1] + 0.05


def test_gini():
    assert se.gini(np.array([1.0, 1.0, 1.0, -5.0])) == 0.0
    assert abs(se.gini(np.array([0.0, 0.0, 0.0, 10.0])) - 0.0) < 1e-12  # one producer only
    assert se.gini(np.array([1.0, 9.0])) > 0.3


def test_length_share_counts_each_pair_once_and_needs_placed_passes():
    seg = pd.DataFrame({"seg_from": ["A", "B", "B", "C"], "seg_to": ["B", "A", "C", "B"],
                        "gsum": [100.0, 10.0, 5.0, -20.0], "n": [10, 10, 10, 10]})
    xy = {"A": (8.0, 47.0), "B": (8.01, 47.0), "C": (8.02, 47.0)}
    out = se.length_share(seg, xy, top=0.5)
    assert out["reported"] and out["segments_taken"] == 1 and abs(out["S_length"] - 100 / 115) < 1e-4
    assert not se.length_share(seg, {"A": (8.0, 47.0)})["reported"]
