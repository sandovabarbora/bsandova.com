"""Golden-master pin: the published H3 effect (docs/research/eurovision-results.json), recomputed by the frozen main()
with its data folder pointed at a scratch copy, so tools/data/eurovision/results.json is not rewritten. Point estimates
only (the design has no bootstrap). The inputs are local-only (tools/data/eurovision), so this skips where they are
missing (as in CI).

    nice -n 20 uv run --with numpy --with pandas --with pyarrow --with pyfixest --with pytest pytest -q tools/eurovision/test_eurovision_pin.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("eurovision_estimate_pin", Path(__file__).resolve().parent / "estimate.py")
ee = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ee)

INPUTS = ["h1.parquet", "h1_absent_zero.parquet", "h2.parquet", "h3.parquet", "raw/mirovision_jurors.csv"]
pytestmark = pytest.mark.skipif(not all((ee.D / f).exists() for f in INPUTS),
                                reason="tools/data/eurovision inputs are local-only")


def test_h3_effect_matches_the_published_estimate(tmp_path, monkeypatch):
    for f in INPUTS:
        (tmp_path / f).parent.mkdir(exist_ok=True)
        (tmp_path / f).symlink_to(ee.D / f)
    monkeypatch.setattr(ee, "D", tmp_path)
    ee.main()
    res = json.loads((tmp_path / "results.json").read_text())
    assert res["H3"]["b"] == pytest.approx(-0.00907, abs=5e-6)
