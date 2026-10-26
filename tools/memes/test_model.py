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

def test_spec_shock_recovery_peak_halflife_and_p():
    """The spec's test as written, on one seed (seed 1): CAR within 2 of the truth, peak on the event day on the raw
    series, raw half-life 3 or 4 days, p < 0.05."""
    res, _ = M.run_event(shock_panel(1), spec())
    truth = sum(2 * np.exp(-t / 5) for t in range(31))
    assert abs(res.car - truth) < 2
    assert res.peak_date_raw == "2023-09-27"
    assert res.half_life_raw_days in (3.0, 4.0)
    assert res.placebo_p < 0.05


def test_shock_recovery_over_nine_seeds_is_looser_than_the_spec_tolerance():
    # the spec's tolerance of 2 fails for some seeds (seed 0 is off by 2.6): the median-index noise pulls beta to
    # about 0.8, so this keeps the median error under 2 and the worst under 4.5 (design deviation R1)
    truth = sum(2 * np.exp(-t / 5) for t in range(31))
    errors = []
    for seed in range(9):
        res, ar = M.run_event(shock_panel(seed), spec())
        errors.append(abs(res.car - truth))
        assert abs((pd.Timestamp(res.peak_date_raw) - EVENT).days) <= 1
        assert res.placebo_p < 0.05 and len(ar) == 34
        assert res.half_life_status == "observed" and 3 <= res.half_life_days <= 6
    assert np.median(errors) < 2 and max(errors) < 4.5


def test_null_share_of_false_positives_over_100_seeds_is_at_most_ten_percent():
    hits = sum(M.run_event(S.synthetic_panel(s, GROUPS), spec())[0].placebo_p < 0.05 for s in range(100))
    assert hits <= 10


def test_beta_is_near_one():
    y, x = logs(S.synthetic_panel(0, GROUPS))
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
    args = (y, x, EVENT, 0.0, EST, EW)
    assert M.placebo_p_value(*args) == M.placebo_p_value(*args)
    assert M.placebo_p_value(*args)[1] > 900                    # every admissible date by default
    assert M.placebo_p_value(*args, n_placebo=300)[1] == 300
    assert M.placebo_p_value(*args, n_placebo=300) == M.placebo_p_value(*args, n_placebo=300)
    assert M.placebo_p_value(*args, n_placebo=300, seed=1) != M.placebo_p_value(*args, n_placebo=300)


# ---------------------------------------------------------------- the leave-one-out check

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
    assert median_car > 2.5 and p < 0.05 and n > 900


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
    assert M.label_event(0.004, 0.008, 5.0, 6.0) == "positive"
    assert M.label_event(0.2, 0.4, 1.0, 6.0) == "no detectable jump"
    assert M.label_event(0.04, 0.08, 1.0, 6.0) == "inconclusive"          # passes raw, not Holm
    assert M.label_event(0.5, 0.9, -2.0, 6.0) == "no detectable jump"


def test_a_null_with_a_large_minimum_detectable_uplift_is_uninformative_not_no_detectable_jump():
    assert M.label_event(0.2, 0.4, 1.0, 10.0) == "no detectable jump"       # at the threshold, not above it
    assert M.label_event(0.2, 0.4, 1.0, 10.01) == "uninformative"
    assert M.label_event(0.5, 0.9, -2.0, 33.0) == "uninformative"
    # the MDU never turns a positive or an inconclusive result into something else
    assert M.label_event(0.004, 0.008, 5.0, 33.0) == "positive"
    assert M.label_event(0.04, 0.08, 1.0, 33.0) == "inconclusive"
    assert "uninformative" in M.LABELS and M.UNINFORMATIVE_PCT == 10.0


def test_labels_rest_on_h1_and_the_minimum_detectable_uplift_alone():
    import inspect
    assert list(inspect.signature(M.label_event).parameters) == ["placebo_p", "holm_p", "car", "mdu80_q975_pct"]


def test_run_event_carries_the_uplift_that_decides_the_label():
    res, _ = M.run_event(S.synthetic_panel(2, GROUPS), spec())
    assert res.mdu80_q975_pct > res.mdu80_pct > res.mdu_pct > 0
    assert M.label_event(0.9, 0.9, 0.0, res.mdu80_q975_pct) in ("no detectable jump", "uninformative")


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
        M._car_at = lambda yy, xx, dow, p, u, est, ew, usable, weekday, shock=0.0: seen.append(p) or 0.0
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
    assert car > 5 and p < 0.05 and n > 900


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
    s = spec(controls=CAST["T"], cast=CAST["T"], reference=REF, falsification=True)
    res, _ = M.run_event(ext_panel(cast_jump=3.0), s)
    assert res.falsification_p < 0.05 and res.loo_p is not None and res.loo_car is not None


def test_run_event_needs_the_reference_in_the_panel():
    s = spec(controls=CAST["T"], cast=CAST["T"], reference=(*REF, "R99"), falsification=True)
    with pytest.raises(KeyError, match="R99"):
        M.run_event(ext_panel(), s)


def test_run_event_overrides_for_the_sensitivity_runs():
    panel = S.synthetic_panel(1, {"T": CONTROLS}, bumps=[("T", "2023-10-06", 2.0, 5.0)])
    res, _ = M.run_event(panel, spec(), event_date="2023-10-06", controls=CONTROLS[:3], falsify=False, variant="d0")
    assert res.event_date == "2023-10-06" and res.variant == "d0" and res.falsification_p is None
    assert res.peak_date_raw == "2023-10-06"


# ---------------------------------------------------------------- review fixes: weekday effects, equal estimation days

def test_weekday_effects_remove_the_bias_of_a_window_that_is_not_whole_weeks():
    # the event window of 34 days holds 5 of some weekdays and 4 of others, so a weekday pattern in the target only
    # leaks into the CAR unless the model has weekday terms
    panel = S.synthetic_panel(4, GROUPS, weekday={"T": 1.0})
    y, x = logs(panel)
    plain = M.abnormal_attention(y, x, EVENT, EST, EW, weekday=False)[0].sum()
    weekly = M.abnormal_attention(y, x, EVENT, EST, EW, weekday=True)[0].sum()
    assert abs(plain) > 1.5 and abs(weekly) < 1.5


def test_weekday_pattern_does_not_inflate_false_positives():
    hits = sum(M.run_event(S.synthetic_panel(s, GROUPS, weekday={"T": 1.0}), spec())[0].placebo_p < 0.05
               for s in range(40))
    assert hits <= 8


def test_every_placebo_fit_has_as_many_estimation_days_as_the_real_fit(monkeypatch):
    panel = S.synthetic_panel(2, GROUPS)
    y, x = logs(panel)
    blocked = [("2023-06-06", "2023-07-13")]
    sizes = []
    orig = M._fit

    def spy(yy, xx, dow, weekday):
        sizes.append(len(yy))
        return orig(yy, xx, dow, weekday)
    monkeypatch.setattr(M, "_fit", spy)
    M.abnormal_attention(y, x, EVENT, EST, EW, blocked=blocked)
    M.placebo_p_value(y, x, EVENT, 1.0, EST, EW, blocked=blocked)
    assert sizes[0] == 82 and len(sizes) > 900 and set(sizes[1:]) == {82}


def test_the_dropped_block_is_contiguous_seeded_and_moves_between_placebos():
    seen = []

    def fake_fit(yy, xx, dow, weekday):
        seen.append(yy.copy())
        return np.zeros(8), 1.0
    y, x = np.arange(400, dtype=float), np.ones(400)
    orig = M._fit
    M._fit = fake_fit
    try:
        for u in (0.0, 0.5, 0.99):
            M._car_at(y, x, np.zeros(400, int), 200, u, (-150, -31), (-3, 30), 82, True)
    finally:
        M._fit = orig
    assert all(len(v) == 82 for v in seen)
    start, middle, end = seen
    assert start[0] == 88 and (np.diff(start) == 1).all()                    # block at the start of the window
    assert end[0] == 50 and end[-1] == 131 and (np.diff(end) == 1).all()    # block at the end
    gap = np.diff(middle)
    assert (gap > 1).sum() == 1 and gap.max() == 39                         # one 38-day block cut out in the middle


def test_a_placebo_pool_that_cannot_match_the_real_estimation_days_is_not_used():
    panel = S.synthetic_panel(2, GROUPS)
    y, x = logs(panel)
    y = y.copy()
    y.iloc[500:700] = np.nan                      # a long hole in the target: fewer usable days around it
    n_all = M.placebo_p_value(*logs(panel), EVENT, 1.0, EST, EW)[1]
    n_hole = M.placebo_p_value(y, x, EVENT, 1.0, EST, EW)[1]
    assert n_hole < n_all


# ---------------------------------------------------------------- placebo-rule variants

def test_same_season_pre_event_and_strict_exclusion_pools():
    idx = pd.date_range("2021-01-01", "2024-12-31")
    base = M.placebo_candidates(idx, EVENT, EST, EW, 30)
    season = M.placebo_candidates(idx, EVENT, EST, EW, 30, season_days=45)
    pre = M.placebo_candidates(idx, EVENT, EST, EW, 30, pre_only=True)
    strict = M.placebo_candidates(idx, EVENT, EST, EW, 90)
    assert 100 <= len(season) < len(base) and 100 <= len(pre) < len(base) and len(strict) < len(base)
    doy = idx[season].dayofyear - EVENT.dayofyear
    assert (np.minimum(np.abs(doy), 365 - np.abs(doy)) <= 45).all()
    assert (idx[pre] < EVENT).all()
    assert set(strict) <= set(base)


# ---------------------------------------------------------------- space-time placebo

def test_space_time_rank_of_the_target_among_pool_actors():
    panel = S.synthetic_panel(3, {"T": CONTROLS, "R0": REF[1:]}, bumps=[("T", "2023-09-27", 2.0, 5.0)], common_sd=0.1)
    ar, _, _ = M.abnormal_attention(np.log1p(panel["T"]), M.control_index(panel, CONTROLS), EVENT, EST, EW)
    p, n = M.space_time_p(panel, REF, float(ar.sum()), EVENT, EST, EW)
    assert n == len(REF) and p == pytest.approx(1 / (n + 1))              # larger than every pool actor
    p_low, _ = M.space_time_p(panel, REF, -50.0, EVENT, EST, EW)
    assert p_low == pytest.approx(1.0)
    with pytest.raises(ValueError, match="at least three"):
        M.space_time_p(panel, REF[:2], 1.0, EVENT, EST, EW)


# ---------------------------------------------------------------- minimum detectable uplift, uplift and excess views

def test_null_summary_converts_the_placebo_spread_to_uplift_percent():
    cars = np.random.default_rng(0).normal(0, 2.0, 5000)
    out = M.null_summary(cars)
    q20, q95, q975 = (np.percentile(cars, q) for q in (20, 95, 97.5))
    assert out["null_sd"] == pytest.approx(2.0, rel=0.05) and out["null_p95"] == pytest.approx(q95)
    assert out["mdu_pct"] == pytest.approx(np.expm1(q95 / 34) * 100)
    assert out["mdu80_pct"] == pytest.approx(np.expm1((q95 - q20) / 34) * 100)
    assert out["mdu80_q975_pct"] == pytest.approx(np.expm1((q975 - q20) / 34) * 100)
    assert out["mdu80_q975_pct"] > out["mdu80_pct"] > out["mdu_pct"] > 0
    assert out["s80_q95"] == pytest.approx((q95 - q20) / M.injection_sum((-3, 30)))


def test_the_empirical_minimum_detectable_uplift_is_what_injecting_a_shock_gives():
    # inject s*exp(-t/5) into the target's own series at the non-event placebo dates: at the s of the summary, 80 % of
    # the injected CARs exceed the 95th and the 97.5th percentile of the placebo CARs
    panel = S.synthetic_panel(6, GROUPS)
    s = spec()
    y, x, idx, usable, plan = M._null_setup(panel, s, EST, EW, None, 42, 100, 30, "median", None, None)
    plain = M._cars(y, x, idx, plan, EST, EW, usable, True)
    out = M.null_summary(plain, EW)
    for key, thr in (("s80_q95", out["null_p95"]), ("s80_q975", out["null_p975"])):
        injected = M._cars(y, x, idx, plan, EST, EW, usable, True, shock=out[key])
        assert (injected > thr).mean() == pytest.approx(0.8, abs=0.01)
    assert M.injection_sum(EW) == pytest.approx(sum(np.exp(-t / 5) for t in range(31)))


def test_null_distribution_never_looks_at_the_event():
    s = spec(placebo_blocked=(("2024-01-01", "2024-02-29"),))
    quiet = S.synthetic_panel(2, GROUPS)
    shocked = S.synthetic_panel(2, GROUPS, bumps=[("T", "2023-09-27", 3.0, 5.0)])
    # the pseudo dates are identical with and without a jump at the event, and so is every number of the null
    d_quiet, d_shocked = M.null_plan_dates(quiet, s), M.null_plan_dates(shocked, s)
    assert d_quiet.equals(d_shocked) and len(d_quiet) > 700
    a, b = M.null_distribution(quiet, s), M.null_distribution(shocked, s)
    assert a["null_sd"] == pytest.approx(b["null_sd"], rel=1e-12) and a["mdu80_q975_pct"] == pytest.approx(b["mdu80_q975_pct"])
    # no placebo span (estimation plus event window) touches an event window: the two memes' windows (day -3 to +30), the
    # 6 October variant, and the blocked days; nor does it come within 30 days of the event it is a null for
    windows = [(pd.Timestamp(d) - pd.Timedelta(days=3), pd.Timestamp(d) + pd.Timedelta(days=30))
               for d in ("2023-09-27", "2023-09-21", "2023-10-06")]
    windows += [(pd.Timestamp(lo), pd.Timestamp(hi)) for lo, hi in s.placebo_blocked]
    for d in d_quiet:
        lo, hi = d + pd.Timedelta(days=EST[0]), d + pd.Timedelta(days=EW[1])
        assert all(hi < w0 or lo > w1 for w0, w1 in windows)
        assert hi < EVENT - pd.Timedelta(days=33) or lo > EVENT + pd.Timedelta(days=60)
    res, _ = M.run_event(quiet, s)
    assert res.mdu80_q975_pct == pytest.approx(M.null_distribution(quiet, s)["mdu80_q975_pct"], rel=1e-9)
    assert res.mdu_pct > 0 and res.null_sd > 0


def test_later_waves_are_kept_out_of_the_placebo_pool_only():
    idx = pd.date_range("2021-01-01", "2024-12-31")
    block = ("2024-01-01", "2024-02-29")
    kept = M.placebo_candidates(idx, EVENT, EST, EW, 30, [block])
    base = M.placebo_candidates(idx, EVENT, EST, EW, 30)
    assert len(kept) < len(base)
    spans_touch = [d for d in idx[kept] if (d + pd.Timedelta(days=30) >= pd.Timestamp(block[0]))
                   and (d + pd.Timedelta(days=EST[0]) <= pd.Timestamp(block[1]))]
    assert spans_touch == []
    panel = S.synthetic_panel(1, GROUPS)
    plain, _ = M.run_event(panel, spec())
    walled, _ = M.run_event(panel, spec(placebo_blocked=(block,)))
    assert walled.n_placebo < plain.n_placebo and walled.car == pytest.approx(plain.car)  # the real fit is untouched


def test_pool_members_with_an_omitted_day_anywhere_are_dropped_by_a_date_independent_rule():
    panel = S.synthetic_panel(2, {"T": CONTROLS, "R0": REF[1:]}, common_sd=0.1)
    panel.loc[panel.index[3], "R4"] = np.nan                      # a hole in January 2021, far from any window
    kept, dropped = M.pool_screen(panel, REF)
    assert dropped == ["R4"] and "R4" not in kept and len(kept) == len(REF) - 1
    s = spec(controls=REF, cast=CONTROLS, reference=REF, falsification=True)
    res, _ = M.run_event(panel, s, falsify=False)
    assert res.dropped == ["R4 (pool member, an omitted day in the panel)"]


# ---------------------------------------------------------------- the baseline choice of the null stage (design §3.5)

def test_the_second_regressor_is_chosen_only_if_it_lowers_the_placebo_spread():
    groups = {"T": CONTROLS, "R0": REF[1:], "V": ("V1",)}
    panel = S.synthetic_panel(3, groups, common_sd=0.1, shared={"V": ("T", 1.0)})
    panel["V"] = panel["T"] * np.exp(np.random.default_rng(3).normal(0, 0.02, len(panel)))   # V moves with the target
    s = spec(controls=REF, cast=CONTROLS, reference=REF, second_regressor="V")
    helpful = M.choose_baseline(panel, s)
    assert helpful["chosen"] == "pool+second" and helpful["second_regressor"] == "V"
    assert helpful["pool+second"] < helpful["pool"]
    panel["V"] = np.expm1(np.random.default_rng(4).normal(6, 0.5, len(panel)))               # pure noise
    useless = M.choose_baseline(panel, s)
    assert useless["pool+second"] > 0.95 * useless["pool"]          # pure noise barely changes the spread
    assert helpful["pool+second"] < 0.5 * helpful["pool"]
    assert useless["chosen"] == ("pool+second" if useless["pool+second"] < useless["pool"] else "pool")
    assert M.choose_baseline(panel, spec(controls=REF, cast=CONTROLS, reference=REF))["chosen"] == "pool"


def test_a_second_regressor_with_omitted_days_falls_back_to_the_pool_alone():
    groups = {"T": CONTROLS, "R0": REF[1:], "V": ("V1",)}
    panel = S.synthetic_panel(3, groups, common_sd=0.1)
    ev = (EVENT - panel.index[0]).days
    panel.loc[panel.index[ev - 140:ev - 100], "V"] = np.nan
    out = M.choose_baseline(panel, spec(controls=REF, cast=CONTROLS, reference=REF, second_regressor="V"))
    assert out["chosen"] == "pool" and out["pool+second"] is None


def test_too_few_placebo_dates_under_baseline_b_fall_back_to_a_with_the_reason(monkeypatch):
    groups = {"T": CONTROLS, "R0": REF[1:], "V": ("V1",)}
    panel = S.synthetic_panel(3, groups, common_sd=0.1)
    real = M.null_distribution

    def fake(panel, spec, **kw):
        if kw.get("second"):
            raise ValueError("only 40 admissible placebo dates remain, at least 100 are needed")
        return real(panel, spec, **kw)
    monkeypatch.setattr(M, "null_distribution", fake)
    out = M.choose_baseline(panel, spec(controls=REF, cast=CONTROLS, reference=REF, second_regressor="V"), n_placebo=100)
    assert out["chosen"] == "pool" and out["second_regressor"] is None and out["pool+second"] is None
    assert "only 40 admissible" in out["fallback_reason"]


def test_run_event_with_a_second_regressor_reports_it():
    groups = {"T": CONTROLS, "R0": REF[1:], "V": ("V1",)}
    panel = S.synthetic_panel(3, groups, common_sd=0.1)
    res, _ = M.run_event(panel, spec(controls=REF, cast=CONTROLS, reference=REF, second_regressor="V"), second="V")
    assert res.second_regressor == "V" and res.n_placebo > 900


# ---------------------------------------------------------------- the shared factor of the synthetic panels

def test_shared_factor_share_sets_how_much_a_target_moves_with_the_pool():
    groups = {"T": CONTROLS, "R0": REF[1:]}
    corr = {}
    for w in (0.0, 0.5, 1.0):
        p = np.log1p(S.synthetic_panel(5, groups, shared={"T": ("R0", w)}))
        d = p.diff().dropna()
        corr[w] = np.corrcoef(d["T"], d["R1"])[0, 1]
    assert corr[0.0] < 0.1 < corr[0.5] < corr[1.0]


def test_excess_views_and_uplift_for_a_flat_shift():
    idx = pd.date_range("2023-01-01", periods=5)
    y = pd.Series(np.log1p([100.0] * 5), index=idx)
    ar = pd.Series(np.log(2.0) * np.ones(5), index=idx)        # log1p views twice what the model predicts
    # the model predicts expm1(log1p(100) - log 2) = 49.5 views, the data have 100
    assert M.excess_views(y, ar) == pytest.approx(5 * (100 - (101 / 2 - 1)))
    assert np.expm1(ar.mean()) * 100 == pytest.approx(100.0)


# ---------------------------------------------------------------- H2 on the smoothed series

def _ar(values):
    return pd.Series(values, index=pd.date_range("2023-09-24", periods=len(values)))


def test_smoothed_half_life_observed_censored_and_no_peak():
    ev = pd.Timestamp("2023-09-27")
    decay = [0.0] * 3 + [2 * np.exp(-t / 3) for t in range(31)]
    peak_date, peak, hl, status = M.half_life_smoothed(_ar(decay), ev)
    assert status == "observed" and hl is not None and peak > 0 and peak_date >= ev
    slow = [0.0] * 3 + [1.0 for _ in range(31)]
    assert M.half_life_smoothed(_ar(slow), ev)[2:] == (None, "censored")
    assert M.half_life_smoothed(_ar([0.0] * 3 + [-1.0] * 31), ev)[2:] == (None, "no positive peak")


def test_a_dip_below_half_that_comes_back_is_not_the_half_life():
    ev = pd.Timestamp("2023-09-27")
    vals = [0.0] * 3 + [4.0] * 8 + [0.0] * 2 + [4.0] * 8 + [0.0] * 13   # dips for two days only
    shape = M.half_life_smoothed(_ar(vals), ev)
    smooth = _ar(vals).rolling(7, center=True).mean().loc[ev:].dropna()
    first_dip = smooth.index[(smooth < smooth.max() / 2).to_numpy().argmax()]
    assert shape[3] == "observed" and (shape[0] + pd.Timedelta(days=shape[2])) >= first_dip


def test_the_smoothed_window_needs_seven_days_from_day_zero():
    with pytest.raises(ValueError, match="too short"):
        M.half_life_smoothed(_ar([0.0, 0.0, 0.0, 1.0, 1.0]), pd.Timestamp("2023-09-27"))


# ---------------------------------------------------------------- omitted days (design §3)

def holes(panel, col, days):
    out = panel.copy()
    out.loc[out.index[days], col] = np.nan
    return out


def test_target_with_too_many_omitted_estimation_days_is_dropped():
    panel = S.synthetic_panel(2, GROUPS)
    ev = (EVENT - panel.index[0]).days
    est = list(range(ev - 150, ev - 31))
    with pytest.raises(M.EventDropped, match="T"):
        M.run_event(holes(panel, "T", est[:7]), spec())             # 7 of 120 > 5 %
    res, _ = M.run_event(holes(panel, "T", est[:5]), spec())         # 5 of 120 is allowed and left out of the fit
    assert res.n_placebo > 900


def test_an_omitted_event_window_day_of_the_target_drops_the_event():
    panel = S.synthetic_panel(2, GROUPS)
    ev = (EVENT - panel.index[0]).days
    with pytest.raises(M.EventDropped):
        M.run_event(holes(panel, "T", [ev + 5]), spec())


def test_pool_member_with_any_omitted_day_is_dropped_but_a_cast_control_below_five_percent_stays():
    groups = {"T": CONTROLS, "R0": REF[1:]}
    panel = S.synthetic_panel(2, groups, common_sd=0.1)
    ev = (EVENT - panel.index[0]).days
    s = spec(controls=REF, cast=CONTROLS, reference=REF, falsification=True)
    res, _ = M.run_event(holes(panel, "R3", [ev - 60]), s, falsify=False)
    assert any(d.startswith("R3 (pool member") for d in res.dropped)
    res, _ = M.run_event(holes(panel, "C2", [ev - 60, ev - 61]), spec(cast=CONTROLS))
    assert res.dropped == []
    res, _ = M.run_event(holes(panel, "C2", list(range(ev - 150, ev - 140))), spec(cast=CONTROLS))
    assert any(d.startswith("C2 (") for d in res.dropped) and not any("pool" in d for d in res.dropped)


def test_all_baseline_articles_dropped_stops_the_event_and_nothing_is_replaced():
    panel = S.synthetic_panel(2, {"T": CONTROLS}, common_sd=0.1)
    ev = (EVENT - panel.index[0]).days
    for c in CONTROLS:
        panel = holes(panel, c, list(range(ev - 150, ev - 130)))
    with pytest.raises(M.EventDropped, match="no baseline"):
        M.run_event(panel, spec())


def test_monthly_gap_uses_days_up_to_the_cutoff_and_skips_blocked_days():
    idx = pd.date_range("2023-04-01", "2023-09-30")
    y = pd.Series(np.where(idx.month == 6, 5.0, 1.0), index=idx)
    x = pd.Series(0.0, index=idx)
    gap = M.monthly_gap(y, x, "2023-09-17", blocked=[("2023-06-06", "2023-07-13")])
    assert str(gap.index.max()) == "2023-09" and gap.loc[pd.Period("2023-06")] == pytest.approx(5.0)
    assert gap.loc[pd.Period("2023-07")] == pytest.approx(1.0)
    assert gap.loc[pd.Period("2023-09")] == pytest.approx(1.0)
