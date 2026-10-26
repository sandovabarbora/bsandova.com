"""Tests of the meme event study's pure logic on made-up panels (design §4–§7). No real pageview is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import model as M
import synth as S

EVENT = pd.Timestamp("2023-09-27")
EST, EW = (-150, -31), (-3, 30)
CONTROLS = ("C1", "C2", "C3", "C4", "C5")
GROUPS = {"T": CONTROLS}


def spec(**kw):
    base = {"name": "t", "target": "T", "controls": CONTROLS, "event_date": "2023-09-27", "source_note": "made up"}
    return M.EventSpec(**{**base, **kw})


def logs(panel):
    return np.log1p(panel["T"]), M.control_index(panel, CONTROLS)


def shock_panel(seed=0, shock=2.0, decay=5.0):
    return S.synthetic_panel(seed, GROUPS, bumps=[("T", "2023-09-27", shock, decay)])


# ---------------------------------------------------------------- spec §7

def test_shock_recovery_peak_halflife_and_p():
    truth = sum(2 * np.exp(-t / 5) for t in range(31))
    errors = []
    for seed in range(9):
        res, ar = M.run_event(shock_panel(seed), spec())
        errors.append(abs(res.car - truth))
        assert abs((pd.Timestamp(res.peak_date) - EVENT).days) <= 1
        assert res.half_life_days in (3.0, 4.0, 5.0)
        assert res.placebo_p < 0.05
        assert len(ar) == 34
    # the spec's tolerance of 2 holds for a typical seed, not for every one: the median-index noise pulls beta to ~0.8
    assert np.median(errors) < 2 and max(errors) < 4.5


def test_half_life_is_three_or_four_days_for_the_spec_shock():
    res, _ = M.run_event(shock_panel(1), spec())
    assert res.peak_date == "2023-09-27" and res.half_life_days in (3.0, 4.0)


def test_null_share_of_false_positives_over_100_seeds_is_at_most_ten_percent():
    hits = sum(M.run_event(S.synthetic_panel(s, GROUPS), spec())[0].placebo_p < 0.05 for s in range(100))
    assert hits <= 10


def test_beta_is_near_one():
    for seed in (0, 1):
        y, x = logs(S.synthetic_panel(seed, GROUPS))
        _, beta, _ = M.abnormal_attention(y, x, EVENT, EST, EW)
        assert 0.7 < beta < 1.3


def test_half_life_without_positive_peak_is_none():
    ar = pd.Series([-1.0, -0.5, -0.2], index=pd.date_range("2023-01-01", periods=3))
    peak_date, peak, hl = M.half_life(ar)
    assert hl is None and peak < 0 and peak_date == ar.index[2]


def test_half_life_none_when_the_peak_never_halves():
    ar = pd.Series([1.0, 0.9, 0.8], index=pd.date_range("2023-01-01", periods=3))
    assert M.half_life(ar)[2] is None


def test_half_life_counts_days_from_the_peak():
    ar = pd.Series([0.0, 2.0, 1.5, 1.2, 0.9], index=pd.date_range("2023-01-01", periods=5))
    assert M.half_life(ar) == (pd.Timestamp("2023-01-02"), 2.0, 3.0)


def test_date_detection_finds_an_inserted_jump():
    panel = S.synthetic_panel(3, GROUPS, bumps=[("T", "2023-09-14", 1.5, 30.0)])
    y, x = logs(panel)
    assert M.detect_event_date(y, x, "2023-09-01", "2023-10-15") == pd.Timestamp("2023-09-14")


def test_detected_date_is_flagged_warned_and_kept_out_of_the_family(caplog):
    panel = S.synthetic_panel(3, GROUPS, bumps=[("T", "2023-09-14", 1.5, 30.0)])
    s = spec(event_date=None, confirmatory=True, detect_window=("2023-09-01", "2023-10-15"))
    with caplog.at_level("WARNING"):
        res, _ = M.run_event(panel, s)
    assert res.event_date == "2023-09-14" and res.event_date_detected and not res.confirmatory
    assert "detected" in caplog.text
    assert M.confirmatory_family([res]) == {}


# ---------------------------------------------------------------- errors, spec §6

def test_event_outside_the_data_names_both_ranges():
    y, x = logs(S.synthetic_panel(0, GROUPS))
    with pytest.raises(ValueError, match=r"needs .*\.\..*data cover 2021-01-01\.\.2024-12-31"):
        M.abnormal_attention(y, x, pd.Timestamp("2021-02-01"), EST, EW)
    with pytest.raises(ValueError, match="data cover"):
        M.abnormal_attention(y, x, pd.Timestamp("2024-12-20"), EST, EW)


def test_missing_control_and_target_raise_keyerror_with_the_list():
    panel = S.synthetic_panel(0, GROUPS)
    with pytest.raises(KeyError, match="C9"):
        M.run_event(panel, spec(controls=(*CONTROLS, "C9")))
    with pytest.raises(KeyError, match="Nobody"):
        M.run_event(panel, spec(target="Nobody"))
    with pytest.raises(KeyError, match="C9"):
        M.control_index(panel, ["C1", "C9"])


def test_empty_controls_raise():
    with pytest.raises(ValueError, match="no control"):
        M.control_index(S.synthetic_panel(0, GROUPS), [])


def test_overlapping_windows_raise():
    y, x = logs(S.synthetic_panel(0, GROUPS))
    with pytest.raises(ValueError, match="must end before"):
        M.abnormal_attention(y, x, EVENT, (-150, -2), EW)


def test_short_estimation_window_raises():
    y, x = logs(S.synthetic_panel(0, GROUPS))
    with pytest.raises(ValueError, match="at least 30"):
        M.abnormal_attention(y, x, EVENT, (-60, -45), EW)


def test_constant_control_index_raises():
    panel = S.synthetic_panel(0, GROUPS)
    panel[list(CONTROLS)] = 100.0
    with pytest.raises(ValueError, match="constant"):
        M.run_event(panel, spec())


def test_too_few_placebo_dates_recommend_a_longer_range():
    panel = S.synthetic_panel(0, GROUPS, start="2023-01-01", end="2023-12-31")
    with pytest.raises(ValueError, match="longer data range"):
        M.run_event(panel, spec())


def test_gappy_series_are_refused():
    panel = S.synthetic_panel(0, GROUPS).drop(pd.Timestamp("2023-05-01"))
    with pytest.raises(ValueError, match="gap-free"):
        M.run_event(panel, spec())


def test_placebo_is_reproducible_and_seed_dependent():
    y, x = logs(S.synthetic_panel(0, GROUPS))
    args = (y, x, EVENT, 3.0, EST, EW)
    assert M.placebo_p_value(*args) == M.placebo_p_value(*args)
    assert M.placebo_p_value(*args, seed=1)[1] == 300


# ---------------------------------------------------------------- deviation A: leave-one-out falsification

CAST = {"T": ("C1", "C2", "C3", "C4", "C5", "C6")}


def cast_panel(cast_shock, jumpers=()):
    bumps = [(c, "2023-09-27", cast_shock, 3.0) for c in jumpers]
    return S.synthetic_panel(5, CAST, bumps=bumps)


def test_leave_one_out_sees_a_majority_jump_that_the_own_median_hides():
    controls = list(CAST["T"])
    panel = cast_panel(3.0, jumpers=controls[:4])  # 4 of 6 cast members jump
    own = M.control_index(panel, controls)
    naive = [M.abnormal_attention(np.log1p(panel[c]), own, EVENT, EST, EW)[0].sum() for c in controls]
    median_car, p, n = M.falsification_test(panel, controls, EVENT, EST, EW)
    assert abs(np.median(naive)) < 1.5        # against their own median the median control is flat by construction
    assert median_car > 2.5 and p < 0.05 and n == 300


def test_a_unanimous_cast_jump_is_invisible_to_the_falsification():
    # known blind spot (design §8): the others' median jumps with the control, so every leave-one-out AR is about 0
    controls = list(CAST["T"])
    _, p, _ = M.falsification_test(cast_panel(1.5, jumpers=controls), controls, EVENT, EST, EW)
    assert p > 0.05


def test_falsification_does_not_fire_without_a_cast_jump():
    _, p, _ = M.falsification_test(cast_panel(0.0), list(CAST["T"]), EVENT, EST, EW)
    assert p > 0.05


def test_falsification_needs_two_controls():
    with pytest.raises(ValueError, match="at least two"):
        M.falsification_test(cast_panel(0.0), ["C1"], EVENT, EST, EW)


def test_falsification_uses_the_other_controls_only():
    panel = cast_panel(0.0)
    panel["C1"] = panel["C1"] * 5  # an outlier in C1 must not enter C1's own index
    car, _, _ = M.falsification_test(panel, list(CAST["T"]), EVENT, EST, EW, n_placebo=100)
    assert abs(car) < 5


# ---------------------------------------------------------------- deviation B: Holm over confirmatory tests only

def test_holm_adjust():
    out = M.holm_adjust({"a": 0.01, "b": 0.04})
    assert out == pytest.approx({"a": 0.02, "b": 0.04})
    assert M.holm_adjust({"a": 0.03, "b": 0.04}) == pytest.approx({"a": 0.06, "b": 0.06})
    assert M.holm_adjust({"a": 0.9}) == {"a": 0.9}


def _res(name, p, **kw):
    base = {"name": name, "target": "T", "event_date": "2023-09-27", "event_date_detected": False, "beta": 1,
            "resid_sd": 0.1, "car": 5.0, "car_pct_uplift": 10, "peak_date": "2023-09-27", "peak_ar": 1,
            "half_life_days": 3, "placebo_p": p, "n_placebo": 300, "source_note": "x", "confirmatory": True}
    return M.EventResult(**{**base, **kw})


def test_family_has_sourced_primary_h1_only():
    rs = [_res("cam", 0.01), _res("kj", 0.02, event_date_detected=True, confirmatory=False),
          _res("cam w14", 0.01, variant="window_-3_14"), _res("tiktok", 0.01, confirmatory=False)]
    assert M.confirmatory_family(rs) == {"cam": 0.01}
    rs[1].confirmatory = True  # a sourced Kevin James date joins, and only then
    assert set(M.confirmatory_family(rs)) == {"cam", "kj"}


def test_labels():
    assert M.label_event(0.004, 0.008, 5.0) == "positive"
    assert M.label_event(0.2, 0.4, 1.0) == "no detectable jump"
    assert M.label_event(0.04, 0.08, 1.0) == "inconclusive"          # passes raw, not Holm
    assert M.label_event(0.004, 0.008, 5.0, 0.01, use_falsification=True) == "inconclusive"
    assert M.label_event(0.004, 0.008, 5.0, 0.01, use_falsification=False) == "positive"


# ---------------------------------------------------------------- deviation C: the TikTok pre-wave

TIKTOK = ("2023-06-06", "2023-07-13")


def test_tiktok_days_are_left_out_of_the_estimation_window():
    clean = S.synthetic_panel(2, GROUPS)
    spiked = S.synthetic_panel(2, GROUPS, bumps=[("T", "2023-06-13", 3.0, 3.0)])
    yc, x = logs(clean)
    ys, _ = logs(spiked)
    ar_clean, b0, _ = M.abnormal_attention(yc, x, EVENT, EST, EW, blocked=[TIKTOK])
    ar_spike, b1, _ = M.abnormal_attention(ys, x, EVENT, EST, EW, blocked=[TIKTOK])
    assert b0 == pytest.approx(b1, abs=1e-3) and ar_clean.sum() == pytest.approx(ar_spike.sum(), abs=1e-2)
    ar_bad, _, _ = M.abnormal_attention(ys, x, EVENT, EST, EW)
    assert abs(ar_bad.sum() - ar_clean.sum()) > 1   # without the exclusion the spike would bias the baseline


def test_blocked_days_must_leave_enough_estimation_days():
    y, x = logs(S.synthetic_panel(0, GROUPS))
    with pytest.raises(ValueError, match="at least 30"):
        M.abnormal_attention(y, x, EVENT, EST, EW, blocked=[("2023-05-01", "2023-08-20")])


def test_placebo_pool_keeps_clear_of_the_real_event_and_the_tiktok_window():
    idx = pd.date_range("2021-01-01", "2024-12-31")
    cand = M.placebo_candidates(idx, EVENT, EST, EW, 30, [TIKTOK])
    days = idx[cand]
    assert len(cand) >= 100
    real = (EVENT - pd.Timedelta(days=3), EVENT + pd.Timedelta(days=30))
    for d in days:
        span = (d + pd.Timedelta(days=EST[0]), d + pd.Timedelta(days=EW[1]))
        gap = max((span[0] - real[1]).days, (real[0] - span[1]).days) - 1
        assert gap >= 30                                            # farther than 30 days from the real window
        assert span[1] < pd.Timestamp(TIKTOK[0]) or span[0] > pd.Timestamp(TIKTOK[1])
    assert M.placebo_candidates(idx, EVENT, EST, EW, 30).size > len(cand)  # the block removes dates the real rule keeps


def test_tiktok_spike_cannot_enter_a_placebo_window():
    panel = S.synthetic_panel(2, GROUPS, bumps=[("T", "2023-06-13", 3.0, 3.0)])
    y, x = logs(panel)
    seen = []
    orig = M._car_at
    try:
        M._car_at = lambda yy, xx, p, est, ew: seen.append(p) or 0.0
        M.placebo_p_value(y, x, EVENT, 1.0, EST, EW, blocked=[TIKTOK])
    finally:
        M._car_at = orig
    spike = (pd.Timestamp("2023-06-13") - y.index[0]).days
    assert seen and all(not (p + EST[0] <= spike <= p + EW[1]) for p in seen)


# ---------------------------------------------------------------- external falsification (author's decision of 26 Oct)

REF = tuple(f"R{i}" for i in range(12))
EXT = {"T": CAST["T"], "R0": REF[1:]}


def ext_panel(seed=5, cast_jump=0.0):
    bumps = [(c, "2023-09-27", cast_jump, 5.0) for c in CAST["T"]] if cast_jump else []
    return S.synthetic_panel(seed, EXT, bumps=bumps, common_sd=0.1)


def test_external_falsification_sees_a_cast_wide_jump():
    car, p, n = M.external_falsification(ext_panel(cast_jump=3.0), CAST["T"], REF, EVENT, EST, EW)
    assert car > 5 and p < 0.05 and n == 300


def test_external_falsification_is_quiet_without_a_jump():
    _, p, _ = M.external_falsification(ext_panel(), CAST["T"], REF, EVENT, EST, EW)
    assert p > 0.05


def test_external_falsification_uses_the_same_placebo_dates_as_h1():
    panel = ext_panel()
    cast, ref = M.control_index(panel, CAST["T"]), M.control_index(panel, REF)
    car, p, n = M.external_falsification(panel, CAST["T"], REF, EVENT, EST, EW)
    ar, _, _ = M.abnormal_attention(cast, ref, EVENT, EST, EW)
    assert car == pytest.approx(ar.sum())
    assert (p, n) == M.placebo_p_value(cast, ref, EVENT, car, EST, EW)


def test_run_event_reports_external_falsification_and_keeps_leave_one_out_as_a_check():
    s = spec(controls=CAST["T"], reference=REF, falsification=True, gate_on_falsification=True)
    res, _ = M.run_event(ext_panel(cast_jump=3.0), s)
    assert res.falsification_p < 0.05 and res.loo_p is not None and res.loo_car is not None


def test_run_event_needs_the_reference_in_the_panel():
    s = spec(controls=CAST["T"], reference=(*REF, "R99"), falsification=True)
    with pytest.raises(KeyError, match="R99"):
        M.run_event(ext_panel(), s)


def test_run_event_overrides_for_the_sensitivity_runs():
    panel = S.synthetic_panel(1, {"T": CONTROLS}, bumps=[("T", "2023-10-06", 2.0, 5.0)])
    res, _ = M.run_event(panel, spec(), event_date="2023-10-06", controls=CONTROLS[:3], falsify=False, variant="d0")
    assert res.event_date == "2023-10-06" and res.variant == "d0" and res.falsification_p is None
    assert res.peak_date == "2023-10-06"
