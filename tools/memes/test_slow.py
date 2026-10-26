"""The slow simulations of design §5 on made-up panels: false-positive rate over 300 seeds and power for shocks of
0.3, 0.5 and 1.0. Run with -m slow."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import simulate as SIM

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("spec", C.EVENTS, ids=lambda s: s.name)
def test_false_positive_rate_over_300_seeds_stays_near_five_percent(spec):
    r = SIM.false_positive_rate(spec)
    assert r["n_seeds"] == 300
    assert r["h1_p_below_0.05"] <= 0.10
    assert r["external_falsification_p_below_0.05"] <= 0.10
    assert r["leave_one_out_p_below_0.05"] <= 0.10


@pytest.mark.parametrize("spec", C.EVENTS, ids=lambda s: s.name)
def test_power_rises_with_the_shock(spec):
    pw = [SIM.power(spec, s)["p_below_0.05"] for s in SIM.SHOCKS]
    assert pw == sorted(pw)
    assert pw[0] > 0.4 and pw[-1] > 0.95


def test_external_falsification_sees_a_cast_wide_jump_that_leave_one_out_cannot():
    n = len(C.STONESTREET.controls)
    unanimous = SIM.cast_jump_detection(C.STONESTREET, n, 1.0, n_seeds=100)
    assert unanimous["external_falsification_p_below_0.05"] > 0.3
    assert unanimous["leave_one_out_p_below_0.05"] < unanimous["external_falsification_p_below_0.05"]
