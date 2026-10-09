"""Golden-master pin: the published H1 evening ratio (docs/research/dst-darkness-results.csv), recomputed with the frozen
frame() and poisson() from the region × date × hour cells. The cells are local-only (tools/data/dst), so this skips
where the file is missing (as in CI).

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/dst/test_dst_pin.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("dst_estimate_pin", Path(__file__).resolve().parent / "estimate.py")
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)

CELLS = de.D / "cells.parquet"
pytestmark = pytest.mark.skipif(not CELLS.exists(), reason="tools/data/dst/cells.parquet is local-only")


def test_h1_evening_ratio_matches_the_published_estimate():
    fit = de.poisson(de.frame(pd.read_parquet(CELLS), -14, 14))
    assert de.ratio(fit, "pe")["ratio"] == pytest.approx(1.7513, abs=5e-5)
