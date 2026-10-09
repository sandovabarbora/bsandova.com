"""Golden-master pins: the event-month-0 effects (docs/research/eras-inflation-results.json, att0_direct; shown to two
decimals on the Taylor Swift page), recomputed with the frozen panel() and att0() from the committed HICP extract
(docs/research/eras-inflation-hicp.csv). Point estimates only, no multiplier bootstrap or permutations. Runs in CI.

    uv run --with csdid==0.4.2 --with numpy --with pandas --with pytest pytest -q tools/eras/test_eras_pin.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("csdid")  # estimate.py imports it at the top; att0() itself does not use it
spec = importlib.util.spec_from_file_location("eras_estimate_pin", Path(__file__).resolve().parent / "estimate.py")
ea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ea)


@pytest.mark.parametrize("outcome, published", [("accommodation", 0.79), ("restaurants", -0.12), ("all_items", 0.23)])
def test_month0_effect_matches_the_published_estimate(outcome, published):
    assert ea.att0(ea.panel(ea.Q[outcome])) == pytest.approx(published, abs=0.005)
