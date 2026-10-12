"""The bunching estimator on made-up contracts with known rounding and known bunching (no register record is read).

    uv run --with numpy --with scipy --with pytest pytest -q tools/procurement/test_procurement.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bunching as bu  # noqa: E402
from synth_contracts import World, draw  # noqa: E402


def point(world: World, seed: int = 1, spec: bu.Spec | None = None) -> dict:
    est, _ = bu.estimate(*draw(world, seed), spec=spec, draws=0)
    return est


def test_a_contract_at_the_limit_is_below_it():
    j = bu.bin_index(np.array([2_000_000, 2_000_000.01, 1_990_000.01]))
    assert j[0] + 1 == j[1] and j[2] == j[0]
    assert bu.edges()[j[0] + 1] == 2_000_000
    assert set(bu.below(3_000_000)) == set(range(bu.bin_index(np.array([2_850_000.01]))[0],
                                                 bu.bin_index(np.array([3_000_000]))[0] + 1))


def test_every_round_million_is_in_an_excluded_window():
    ex = bu.Spec().excluded()
    for m in range(1, 14):
        assert ex[bu.bin_index(np.array([m * 1_000_000]))[0]], m


def test_rounding_alone_gives_no_move():
    est = point(World(n_pre=300_000, n_post=300_000))
    assert est["controls_pooled_pre"] > 0.05  # round millions do bunch
    assert abs(est["D_new"]) < 0.08 and abs(est["D_old"]) < 0.08
    # A round million bunches more, relative to its window, the lower it lies: a threshold cannot be judged
    # against the control locations in one period (design §6.1), only against itself before and after.
    assert est["old_supplies_services_pre"] > est["controls_pooled_pre"] + 0.1


def test_a_moved_threshold_is_found_at_both_ends():
    est = point(World(n_pre=300_000, n_post=300_000, move={"pre": 0.3, "post": 0.3}))
    assert est["D_new"] > 0.1 and est["D_old"] > 0.1
    assert est["above_new_supplies_services_post"] < -0.1  # missing mass just above the new limit


def test_more_rounding_after_the_change_is_differenced_out():
    w = World(n_pre=300_000, n_post=300_000, round_1m={"pre": 0.02, "post": 0.06})
    est = point(w)
    raw = est["new_supplies_services_post"] - est["new_supplies_services_pre"]
    # rounding triples: the ratio adjustment leaves a residual of about a tenth, the additive one far more
    assert raw > 0.2 and abs(est["D_new_supplies_services"]) < 0.15 and abs(est["D_old"]) < 0.15
    diff = bu.estimate(*draw(w, 1), draws=0, adjust="difference")[0]
    assert abs(diff["D_old_supplies_services"]) > 0.2  # the additive adjustment fails when rounding scales


def test_the_planted_excess_is_recovered():
    moved = World(n_pre=300_000, n_post=300_000, move={"pre": 0.0, "post": 0.3})
    flat = World(n_pre=300_000, n_post=300_000)
    v1, a1, p1 = draw(moved, 3)
    v0, _, p0 = draw(flat, 3)  # same seed, same draws up to the move
    w = bu.below(3_000_000)
    j1, j0 = bu.bin_index(v1[p1 == "post"]), bu.bin_index(v0[p0 == "post"])
    truth = (np.isin(j1, w).sum() - np.isin(j0, w).sum()) / np.isin(j0, w).sum()
    est, _ = bu.estimate(v1, a1, p1, draws=0)
    assert abs((est["new_supplies_services_post"] - est["new_supplies_services_pre"]) - truth) < 0.15


def test_bootstrap_and_label_on_a_clear_move():
    est, ci = bu.estimate(*draw(World(move={"pre": 0.3, "post": 0.3}), 5), draws=49)
    assert ci["D_new"]["ci95"][0] < est["D_new"] < ci["D_new"]["ci95"][1]
    assert bu.label(ci["D_new"]["ci95"], ci["D_new"]["ci90"]) == "supported"


def test_labels_follow_the_rule_in_its_literal_order():
    assert bu.label((0.01, 0.4), (0.03, 0.35)) == "supported"
    assert bu.label((-0.12, 0.13), (-0.1, 0.1)) == "not supported"
    assert bu.label((-0.3, 0.2), (-0.25, 0.15)) == "inconclusive"
    assert bu.label((0.2, 0.9), (0.25, 0.8), underpowered=True) == "underpowered"


def test_the_control_placebo_is_null_without_a_threshold_effect():
    est = point(World(n_pre=300_000, n_post=300_000, move={"pre": 0.3, "post": 0.3},
                      round_1m={"pre": 0.02, "post": 0.03}))
    assert abs(est["placebo_controls"]) < 0.08 and est["D_new"] > 0.1


def test_dropping_exact_millions_removes_pure_rounding_but_not_the_move():
    w = World(n_pre=300_000, n_post=300_000, move={"pre": 0.3, "post": 0.3}, round_1m={"pre": 0.05, "post": 0.05})
    est = bu.estimate(*draw(w, 2), draws=0, drop_exact_millions=True, adjust="difference")[0]
    assert abs(est["controls_pooled_pre"]) < 0.05  # synthetic rounding goes to the exact million only
    assert est["D_new"] > 0.1
