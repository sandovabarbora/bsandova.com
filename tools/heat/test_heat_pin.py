"""Golden-master pins: the published heat effects (docs/research/heat-delays-results.json), recomputed with the frozen
primary() from the rain study's units and the ČHMÚ temperature. Point estimates only: the bootstrap switch is set so the
analytic interval is used. The inputs are local-only (tools/data/rain, tools/data/heat), so these skip where they are
missing (as in CI).

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/heat/test_heat_pin.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("heat_estimate_pin", Path(__file__).resolve().parent / "estimate.py")
he = importlib.util.module_from_spec(spec)
spec.loader.exec_module(he)

UNITS = he.rx.D / "units.parquet"
pytestmark = pytest.mark.skipif(not (UNITS.exists() and any(he.hp.T10.glob("10m-*.json"))),
                                reason="tools/data/rain units and tools/data/heat ČHMÚ files are local-only")


@pytest.fixture(scope="module")
def inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_parquet(UNITS), he.weather()


@pytest.mark.parametrize("mode, published", [("tram", -14.86), ("bus", -15.90)])
def test_heat_effect_matches_the_published_estimate(inputs, monkeypatch, mode, published):
    monkeypatch.setattr(he, "BOOT_BELOW", 0)  # point estimate only, no wild bootstrap
    units, wx = inputs
    res = he.primary(he.frame(units, wx, mode), np.random.default_rng(0))
    assert res["delta_s"] == pytest.approx(published, abs=0.005)
