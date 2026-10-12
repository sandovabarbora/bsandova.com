"""The bunching estimator on made-up contracts with known rounding and known bunching (no register record is read).

    uv run --with numpy==2.5.3 --with scipy==1.18.1 --with pytest==9.1.1 pytest -q tools/procurement
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bunching as bu  # noqa: E402
from synth_contracts import World, draw  # noqa: E402

BIG = {"n_pre": 300_000, "n_post": 300_000}


def point(world: World, seed: int = 1, **kw) -> dict:
    return bu.estimate(*draw(world, seed), draws=0, **kw)[0]


def test_a_contract_at_the_limit_is_below_it():
    j = bu.bin_index(np.array([2_000_000, 2_000_000.01, 1_990_000.01]))
    assert j[0] + 1 == j[1] and j[2] == j[0]
    assert bu.edges()[j[0] + 1] == 2_000_000
    assert bu.exact_million(np.array([3_000_000.0, 3_000_000.4, 2_999_999.0])).tolist() == [True, True, False]


def test_every_round_million_is_in_an_excluded_window():
    ex = bu.Spec().excluded()
    for m in range(1, 14):
        assert ex[bu.bin_index(np.array([m * 1_000_000]))[0]], m


def test_rounding_alone_gives_no_move_on_either_estimand():
    est = point(World(**BIG, tilt_sd=0.3, habit_shape=0.5))
    assert est["controls_a_pre"] > 0.05
    for k in ("D_new_a", "D_old_a", "D_new_b", "D_old_b"):
        assert abs(est[k]) < 0.08, k


def test_placement_at_the_limit_lands_in_a_and_spread_below_lands_in_b():
    at = point(World(**BIG, move={"pre": 0.3, "post": 0.3}, move_exact=1.0))
    assert at["D_new_a"] > 0.1 and at["D_old_a"] > 0.1 and abs(at["D_new_b"]) < 0.08
    spread = point(World(**BIG, move={"pre": 0.3, "post": 0.3}, move_exact=0.0))
    assert spread["D_new_b"] > 0.1 and spread["D_old_b"] > 0.1 and abs(spread["D_new_a"]) < 0.08
    assert spread["m_above_new_supplies_services_post"] < -0.1


def test_more_rounding_after_the_change_is_scaled_out_of_a():
    w = World(**BIG, round_1m={"pre": 0.02, "post": 0.06})
    ratio = point(w, adjust="ratio")
    assert ratio["a_new_supplies_services_post"] - ratio["a_new_supplies_services_pre"] > 0.2
    assert abs(ratio["D_new_a"]) < 0.15 and abs(ratio["D_old_a"]) < 0.15
    assert abs(point(w, adjust="difference")["D_old_a_supplies_services"]) > 0.2


@pytest.mark.parametrize("exact", [1.0, 0.0])
def test_the_planted_excess_is_recovered_within_15_percent(exact):
    what = "a" if exact else "b"
    errs = []
    for seed in range(5):
        v1, a1, p1 = draw(World(**BIG, move={"pre": 0.0, "post": 0.4}, move_exact=exact), seed)
        v0, _, p0 = draw(World(**BIG), seed)  # same seed: identical draws up to the move
        w = bu.below(3_000_000)
        def band(v, p, w=w):
            post = v[p == "post"]
            return np.isin(bu.bin_index(post[~bu.exact_million(post)]), w).sum(), (post == 3_000_000).sum()
        (o1, e1), (o0, e0) = band(v1, p1), band(v0, p0)
        truth = ((e1 - e0) if exact else (o1 - o0)) / o0
        est = bu.estimate(v1, a1, p1, draws=0, adjust="ratio")[0][f"D_new_{what}_supplies_services"]
        errs.append((est - truth) / truth)
    assert abs(np.mean(errs)) < 0.15 and max(abs(e) for e in errs) < 0.25, errs


def test_dilution_by_the_other_type_scales_the_pooled_estimate():
    full = point(World(**BIG, move={"pre": 0.3, "post": 0.3}, move_exact=1.0), 4)["D_new_a"]
    half = point(World(**BIG, move={"pre": 0.3, "post": 0.3}, move_exact=1.0, relevant_share=0.5), 4)["D_new_a"]
    assert 0.35 < half / full < 0.65


def test_undefined_ratio_draws_stop_the_run_and_the_full_sample_rule_avoids_them():
    data = draw(World(n_pre=20_000, n_post=5_000, round_100k=0.0, round_1m={"pre": 0.0, "post": 0.001}), 6)
    with pytest.raises(RuntimeError):
        bu.estimate(*data, draws=19, adjust="ratio")
    est, ci = bu.estimate(*data, draws=19)
    assert est["adjust"] == "difference" and ci["D_new_a"]["failed_draws"] == 0


def test_bootstrap_label_and_gate_on_a_clear_move():
    est, ci = bu.estimate(*draw(World(move={"pre": 0.3, "post": 0.3}, move_exact=1.0), 5), draws=49)
    assert ci["D_new_a"]["ci95"][0] < est["D_new_a"] < ci["D_new_a"]["ci95"][1]
    assert bu.label(ci["D_new_a"]["ci95"], ci["D_new_a"]["ci90"])[0] == "supported"


def _gate_inputs(bias_ci=(-0.05, 0.05), k_ci=(-0.1, 0.1), adjust="ratio"):
    point = {"adjust": adjust}
    ci = {"placebo_a_mean": {"ci90": bias_ci}, "k_low_minus_high": {"ci90": k_ci}}
    return point, ci


def test_gate_fails_only_on_a_bias_or_a_k_drift_wholly_outside_their_bounds():
    assert bu.gate_failed(*_gate_inputs()) == (False, [])
    assert bu.gate_failed(*_gate_inputs(bias_ci=(-0.3, 0.1)))[0] is False  # wide, not wholly outside
    assert bu.gate_failed(*_gate_inputs(bias_ci=(0.16, 0.4))) == (True, ["placebo bias"])
    assert bu.gate_failed(*_gate_inputs(k_ci=(0.55, 0.9))) == (True, ["k unstable by magnitude"])
    assert bu.gate_failed(*_gate_inputs(k_ci=(0.55, 0.9), adjust="difference"))[0] is False


def test_calibration_subtracts_the_placebo_bias_and_inflates_the_se():
    point = {"D_new_a": 0.30, "D_old_a": 0.20, "placebo_a_mean": 0.05, "placebo_a_sd": 0.10}
    ci = {"D_new_a": {"se": 0.04}, "D_old_a": {"se": 0.04}} | {k: {"se": 0.06} for k in bu.PLACEBO_KEYS}
    new, old = bu.calibrate(point, ci, "D_new_a"), bu.calibrate(point, ci, "D_old_a")
    assert new["estimate"] == pytest.approx(0.25) and old["estimate"] == pytest.approx(0.25)
    assert new["se"] == pytest.approx((0.04 ** 2 + 0.10 ** 2 - 0.06 ** 2) ** 0.5)
    quiet = ci | {k: {"se": 0.2} for k in bu.PLACEBO_KEYS}  # placebo spread within its own noise: no inflation
    assert bu.calibrate(point, quiet, "D_new_a")["se"] == pytest.approx(0.04)


def test_the_failure_cap_covers_every_label_key_at_one_percent():
    point = {k: 0.0 for k in bu.label_keys("ratio")} | {"adjust": "ratio"}
    reps = [dict(point) for _ in range(100)]
    for k in bu.label_keys("ratio"):
        trial = [dict(r) for r in reps]
        trial[0][k] = float("nan")  # 1 of 100: at the cap, allowed
        assert bu.summarise_draws(point, trial, bu.label_keys("ratio"))[k]["failed_draws"] == 1
        trial[1][k] = float("nan")  # 2 of 100: over the cap
        with pytest.raises(RuntimeError):
            bu.summarise_draws(point, trial, bu.label_keys("ratio"))


def test_non_convergence_and_a_missing_authority_fail_loudly():
    X = bu.design_matrix(7)
    with pytest.raises(RuntimeError):
        bu.poisson_fit(np.arange(bu.N_BINS, dtype=float), X, iters=1)
    v, a, p = draw(World(n_pre=20_000, n_post=5_000), 3)
    a = a.astype(object)
    a[0] = None
    with pytest.raises(ValueError):
        bu.estimate(v, a, p, draws=0)


def test_rounding_that_drifts_by_magnitude_moves_k_low_minus_high():
    flat = point(World(**BIG))["k_low_minus_high"]
    drift = point(World(**BIG, round_1m={"pre": 0.1, "post": 0.1}, round_1m_drift={"pre": 0.0, "post": 1.0}))
    assert abs(flat) < 0.2 and drift["k_low_minus_high"] < -0.5


def test_labels_follow_the_rule_in_its_literal_order():
    assert bu.label((0.01, 0.4), (0.03, 0.35)) == ("supported", "")
    assert bu.label((0.02, 0.05), (0.025, 0.045)) == ("not supported", "detected, below the margin")
    assert bu.label((-0.12, 0.13), (-0.1, 0.1)) == ("not supported", "")
    assert bu.label((-0.3, 0.2), (-0.25, 0.15)) == ("inconclusive", "")
    assert bu.label((-0.6, -0.2), (-0.55, -0.25)) == ("inconclusive", "interval wholly below 0")
    assert bu.label((0.2, 0.9), (0.25, 0.8), gate=True) == ("inconclusive", "validity gate failed")
    assert bu.label((0.2, 0.9), (0.25, 0.8), underpowered=True, gate=True) == ("underpowered", "")
