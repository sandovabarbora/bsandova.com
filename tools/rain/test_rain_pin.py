"""Golden-master pin: the published tram rain effect (docs/research/rain-delays-results.json), recomputed with the frozen
primary() from the screened units and the ČHMÚ precipitation. Point estimate only: the bootstrap switch is set so the
analytic interval is used. The inputs are local-only (tools/data/rain), so this skips where they are missing (as in CI).

    nice -n 20 uv run --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/rain/test_rain_pin.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # estimate.py imports power.py by name
spec = importlib.util.spec_from_file_location("rain_estimate_pin", HERE / "estimate.py")
re_ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(re_)

UNITS = re_.D / "units.parquet"
pytestmark = pytest.mark.skipif(not (UNITS.exists() and any(re_.CHMI.glob("1h-*.json"))),
                                reason="tools/data/rain units and ČHMÚ files are local-only")


def test_tram_rain_effect_matches_the_published_estimate(monkeypatch):
    monkeypatch.setattr(re_, "BOOT_BELOW", 0)  # point estimate only, no wild bootstrap
    units = pd.read_parquet(UNITS)
    wx = re_.weather(re_.precipitation())
    res = re_.primary(re_.frame(units, wx, "tram"), np.random.default_rng(0))
    assert res["delta_s"] == pytest.approx(9.70, abs=0.005)
