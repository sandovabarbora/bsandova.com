"""Golden-master pins: the published S and ρ (docs/research/delay-origins-results.json), recomputed from the screened
segments with the frozen functions. Point estimates only, no bootstrap. The segments are local-only (tools/data/late),
so these skip where the file is missing (as in CI).

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with scipy --with pytest pytest -q tools/late/test_late_pin.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("late_estimate_pin", Path(__file__).resolve().parent / "estimate.py")
le = importlib.util.module_from_spec(spec)
spec.loader.exec_module(le)

SEGMENTS = le.DATA / "segments.parquet"
pytestmark = pytest.mark.skipif(not SEGMENTS.exists(), reason="tools/data/late/segments.parquet is local-only")


@pytest.fixture(scope="module")
def seg() -> pd.DataFrame:
    return pd.read_parquet(SEGMENTS)


@pytest.mark.parametrize("mode, s_pub, rho_pub", [("tram", 0.5059, 0.9994), ("bus", 0.5119, 0.9984)])
def test_concentration_and_stability_match_the_published_estimates(seg, mode, s_pub, rho_pub):
    _, dates, G, N = le.matrix(seg[seg["mode"] == mode])  # as in primary(), without the bootstrap
    odd = np.array([pd.Timestamp(d).isocalendar().week for d in dates]) % 2 == 1
    assert le.concentration(G.sum(1)) == pytest.approx(s_pub, abs=5e-5)
    assert le.stability(G, N, odd) == pytest.approx(rho_pub, abs=5e-5)
