"""Pure logic of the meme event study (docs/research/memes-design.md §4): market model on pageview "attention
returns" (MacKinlay 1997, J. Economic Literature 35(1)), abnormal attention, CAR, half-life, the placebo test, the
falsification diagnostics, Holm adjustment and labels. No I/O: everything takes frames and returns numbers.

Positions are day offsets on a gap-free daily index, so a placebo refit is a few numpy operations. Omitted days are NaN.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

Window = tuple[int, int]
Interval = tuple[str, str]
MIN_EST_DAYS = 30
MAX_MISSING_SHARE = 0.05
ALPHA = 0.05
Z80 = 0.8416  # normal quantile for 80 % power
LABELS = ("positive", "no detectable jump", "inconclusive")


class EventDropped(ValueError):
    """The target of an event cannot be estimated (too many omitted days). Dropped, never replaced (design §3)."""


@dataclass(frozen=True)
class EventSpec:
    name: str
    target: str
    controls: tuple[str, ...]
    event_date: str | None
    source_note: str
    confirmatory: bool = False
    falsification: bool = False
    # the cast of the show, for the descriptive falsification (design §1); the baseline `controls` may differ
    cast: tuple[str, ...] = ()
    # actors outside both shows: the external index of the falsification and a pool whose members are dropped on any gap
    reference: tuple[str, ...] = ()
    # days dropped from the estimation window and kept out of the placebo pool (design §4, deviation C)
    blocked: tuple[Interval, ...] = ()
    # only for an event whose date was not found in a source (design §1)
    detect_window: Interval | None = None


@dataclass
class EventResult:
    name: str
    target: str
    event_date: str
    event_date_detected: bool
    beta: float
    resid_sd: float
    car: float
    car_pct_uplift: float
    peak_date: str
    peak_ar: float
    half_life_days: float | None
    placebo_p: float
    n_placebo: int
    source_note: str
    confirmatory: bool = False
    excess_views: float | None = None
    half_life_status: str | None = None
    half_life_raw_days: float | None = None
    peak_date_raw: str | None = None
    null_sd: float | None = None
    null_p95: float | None = None
    mdu_pct: float | None = None
    mdu80_pct: float | None = None
    falsification_car: float | None = None
    falsification_p: float | None = None
    loo_car: float | None = None
    loo_p: float | None = None
    space_time_p: float | None = None
    n_space_time: int | None = None
    dropped: list[str] = field(default_factory=list)
    holm_p: float | None = None
    label: str | None = None
    variant: str = "primary"


# ---------------------------------------------------------------- inputs

def control_index(panel: pd.DataFrame, controls: Sequence[str], how: Literal["median", "mean"] = "median") -> pd.Series:
    """Daily median (or mean, for a check) of log1p views of the control articles, over the articles that have a value
    that day; median because actors have news."""
    controls = list(controls)
    if not controls:
        raise ValueError("no control articles given")
    missing = [c for c in controls if c not in panel.columns]
    if missing:
        raise KeyError(f"controls missing in the panel: {missing}")
    if how not in ("median", "mean"):
        raise ValueError(f"how must be 'median' or 'mean', not {how!r}")
    views = panel[controls]
    if (views < 0).any().any():
        raise ValueError("negative pageview counts in the panel")
    logged = np.log1p(views)
    out = logged.median(axis=1) if how == "median" else logged.mean(axis=1)
    return out.rename("index")


def _daily_origin(idx: pd.DatetimeIndex) -> pd.Timestamp:
    if len(idx) < 2 or not (idx[1:] - idx[:-1] == pd.Timedelta(days=1)).all():
        raise ValueError("series must be a gap-free daily index; reindex the days the API omits first")
    return idx[0]


def _pair(target_log: pd.Series, index_log: pd.Series) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    if not target_log.index.equals(index_log.index):
        raise ValueError("target and control index must share the same dates")
    _daily_origin(index_log.index)
    return target_log.to_numpy(float), index_log.to_numpy(float), index_log.index


def _pos(idx: pd.DatetimeIndex, date: pd.Timestamp, offset: int = 0) -> int:
    return (pd.Timestamp(date) - idx[0]).days + offset


def _check_range(idx: pd.DatetimeIndex, lo: int, hi: int, what: str, event: pd.Timestamp) -> None:
    if lo < 0 or hi > len(idx) - 1:
        need = (idx[0] + pd.Timedelta(days=lo)).date(), (idx[0] + pd.Timedelta(days=hi)).date()
        raise ValueError(f"{what} for event {pd.Timestamp(event).date()} needs {need[0]}..{need[1]}, "
                         f"but the data cover {idx[0].date()}..{idx[-1].date()}")


# ---------------------------------------------------------------- the market model

def _design(x: np.ndarray, dow: np.ndarray, weekday: bool) -> np.ndarray:
    cols = [np.ones_like(x), x]
    if weekday:
        cols += [(dow == d).astype(float) for d in range(1, 7)]
    return np.column_stack(cols)


def _fit(y: np.ndarray, x: np.ndarray, dow: np.ndarray, weekday: bool) -> tuple[np.ndarray, float]:
    n = len(y)
    if n < MIN_EST_DAYS:
        raise ValueError(f"estimation window has {n} usable days, at least {MIN_EST_DAYS} are needed")
    if float(((x - x.mean()) ** 2).sum()) < 1e-12:
        raise ValueError("the control index is constant in the estimation window, the market model is not identified")
    X = _design(x, dow, weekday)
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ coef
    return coef, float(np.sqrt(resid @ resid / max(n - X.shape[1], 1)))


def fit_market_model(y: pd.Series, x: pd.Series, weekday: bool = False) -> tuple[float, float, float]:
    """OLS of y on x (plus weekday dummies if asked): (alpha, beta, residual sd)."""
    both = pd.concat([y, x], axis=1, join="inner").dropna()
    dow = both.index.dayofweek.to_numpy() if isinstance(both.index, pd.DatetimeIndex) else np.zeros(len(both), int)
    coef, sd = _fit(both.iloc[:, 0].to_numpy(float), both.iloc[:, 1].to_numpy(float), dow, weekday)
    return float(coef[0]), float(coef[1]), sd


def _check_windows(est_window: Window, event_window: Window) -> None:
    if est_window[0] > est_window[1] or event_window[0] > event_window[1]:
        raise ValueError("a window must run from its first to its last day offset")
    if est_window[1] >= event_window[0]:
        raise ValueError(f"the estimation window {est_window} must end before the event window {event_window} begins")


def _blocked_mask(idx: pd.DatetimeIndex, blocked: Sequence[Interval], lo: int, hi: int) -> np.ndarray:
    keep = np.ones(hi - lo + 1, dtype=bool)
    days = idx[lo:hi + 1]
    for start, end in blocked:
        keep &= ~((days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end)))
    return keep


def _real_fit(y, x, idx, ev, est_window, event_window, blocked, weekday):
    """Fit on the estimation window less blocked and omitted days; returns (AR values, coef, sd, usable days)."""
    e0, e1 = ev + est_window[0], ev + est_window[1]
    w0, w1 = ev + event_window[0], ev + event_window[1]
    dow = idx.dayofweek.to_numpy()
    rows = np.arange(e0, e1 + 1)[_blocked_mask(idx, blocked, e0, e1) & np.isfinite(y[e0:e1 + 1]) & np.isfinite(x[e0:e1 + 1])]
    coef, sd = _fit(y[rows], x[rows], dow[rows], weekday)
    w = np.arange(w0, w1 + 1)
    if not (np.isfinite(y[w]).all() and np.isfinite(x[w]).all()):
        raise EventDropped("an omitted day in the event window of the target or the baseline")
    ar = y[w] - _design(x[w], dow[w], weekday) @ coef
    return ar, coef, sd, len(rows)


def abnormal_attention(target_log: pd.Series, index_log: pd.Series, event: pd.Timestamp, est_window: Window,
                       event_window: Window, blocked: Sequence[Interval] = (), weekday: bool = True
                       ) -> tuple[pd.Series, float, float]:
    """AR_t = y_t - (a + b * index_t + weekday effect) over the event window, the model fitted on the estimation window
    less `blocked` and omitted days. Returns (AR by date, beta, residual sd)."""
    _check_windows(est_window, event_window)
    y, x, idx = _pair(target_log, index_log)
    ev = _pos(idx, event)
    _check_range(idx, ev + est_window[0], ev + event_window[1], "the windows", event)
    ar, coef, sd, _ = _real_fit(y, x, idx, ev, est_window, event_window, blocked, weekday)
    w0 = ev + event_window[0]
    return pd.Series(ar, index=idx[w0:w0 + len(ar)], name="ar"), float(coef[1]), sd


def excess_views(target_log: pd.Series, ar: pd.Series) -> float:
    """Views above the model's prediction summed over the event window (the model predicts log1p views, so the
    prediction is expm1 of the fitted value; a small retransformation bias is ignored)."""
    y = target_log.loc[ar.index].to_numpy(float)
    return float((np.expm1(y) - np.expm1(y - ar.to_numpy())).sum())


# ---------------------------------------------------------------- half-life

def half_life(ar: pd.Series) -> tuple[pd.Timestamp, float, float | None]:
    """The spec's definition on the raw series: (peak date, peak AR, days from the peak to the first day with AR below
    half the peak). None if the peak is not positive or AR never falls below half of it."""
    if ar.empty:
        raise ValueError("empty abnormal-attention series")
    peak_date, peak = ar.idxmax(), float(ar.max())
    if not peak > 0:
        return peak_date, peak, None
    after = ar.loc[peak_date:]
    below = after[after < peak / 2]
    if below.empty:
        return peak_date, peak, None
    return peak_date, peak, float((below.index[0] - peak_date).days)


def half_life_smoothed(ar: pd.Series, event: pd.Timestamp, window: int = 7, run: int = 3
                       ) -> tuple[pd.Timestamp, float, float | None, str]:
    """H2 (design §1): on the centred `window`-day mean of AR, defined from day 0 on where all `window` days exist,
    the peak and the days from it to the first day from which the smoothed AR stays below half the peak for `run` days.
    Status: observed, censored (it never does by the last smoothed day) or no positive peak (None for both)."""
    smooth = ar.rolling(window, center=True).mean().loc[pd.Timestamp(event):].dropna()
    if smooth.empty:
        raise ValueError(f"the event window is too short for a {window}-day smoothing from day 0")
    peak_date, peak = smooth.idxmax(), float(smooth.max())
    if not peak > 0:
        return peak_date, peak, None, "no positive peak"
    after = (smooth.loc[peak_date:] < peak / 2).to_numpy()
    for i in range(len(after) - run + 1):
        if after[i:i + run].all():
            return peak_date, peak, float((smooth.loc[peak_date:].index[i] - peak_date).days), "observed"
    return peak_date, peak, None, "censored"


def detect_event_date(target_log: pd.Series, index_log: pd.Series, search_start: str, search_end: str) -> pd.Timestamp:
    """Day of the largest one-day rise of target minus index inside the search range (exploratory, design §1)."""
    y, x, idx = _pair(target_log, index_log)
    jump = pd.Series(y - x, index=idx).diff().loc[search_start:search_end].dropna()
    if jump.empty:
        raise ValueError(f"search range {search_start}..{search_end} lies outside the data {idx[0].date()}..{idx[-1].date()}")
    return jump.idxmax()


# ---------------------------------------------------------------- placebo test

def placebo_candidates(idx: pd.DatetimeIndex, event: pd.Timestamp, est_window: Window, event_window: Window,
                       exclusion_days: int = 30, blocked: Sequence[Interval] = (), season_days: int | None = None,
                       pre_only: bool = False) -> np.ndarray:
    """Positions of admissible pseudo event dates. The span of a pseudo event (estimation plus event window) must lie
    fully in the data, stay at least `exclusion_days` days away from the real event window, and not touch a blocked
    interval (design §4, deviation C). `season_days` keeps dates within that many days of the event's calendar date,
    `pre_only` keeps dates before the real event."""
    _daily_origin(idx)
    n, ev = len(idx), _pos(idx, event)
    lo, hi = est_window[0], event_window[1]
    p = np.arange(-lo, n - hi)
    real_lo, real_hi = ev + event_window[0], ev + event_window[1]
    before = p + hi < real_lo - exclusion_days
    keep = before if pre_only else before | (p + lo > real_hi + exclusion_days)
    for start, end in blocked:
        b0, b1 = _pos(idx, pd.Timestamp(start)), _pos(idx, pd.Timestamp(end))
        keep &= (p + hi < b0) | (p + lo > b1)
    if season_days is not None:
        doy = idx[p].dayofyear.to_numpy() - pd.Timestamp(event).dayofyear
        keep &= np.minimum(np.abs(doy), 365 - np.abs(doy)) <= season_days
    return p[keep]


def _plan(y, x, idx, event, est_window, event_window, usable, exclusion_days, blocked, n_placebo, seed,
          min_candidates, season_days, pre_only):
    """The pseudo dates and, for each, the seeded draw that places its dropped block of estimation days (design §4.5)."""
    cand = placebo_candidates(idx, event, est_window, event_window, exclusion_days, blocked, season_days, pre_only)
    good = np.isfinite(y) & np.isfinite(x)
    cum = np.concatenate([[0], np.cumsum(good)])
    e0, e1 = cand + est_window[0], cand + est_window[1]
    w0, w1 = cand + event_window[0], cand + event_window[1]
    ok = (cum[e1 + 1] - cum[e0] >= usable) & (cum[w1 + 1] - cum[w0] == w1 - w0 + 1)
    cand = cand[ok]
    if len(cand) < min_candidates:
        raise ValueError(f"only {len(cand)} admissible placebo dates remain, at least {min_candidates} are needed: "
                         "use a longer data range (a one-year range gave about 30 % false positives in the prototype)")
    if n_placebo is not None and n_placebo < len(cand):
        cand = np.sort(np.random.default_rng(seed).choice(cand, size=n_placebo, replace=False))
    return cand, np.random.default_rng([seed, 1]).random(len(cand))


def _car_at(y, x, dow, p, u, est_window, event_window, usable, weekday) -> float:
    seg = np.arange(p + est_window[0], p + est_window[1] + 1)
    rows = seg[np.isfinite(y[seg]) & np.isfinite(x[seg])]
    k = len(rows) - usable
    if k > 0:  # the same number of estimation days as the real fit: a seeded contiguous block is left out
        start = int(u * (len(rows) - k + 1))
        rows = np.concatenate([rows[:start], rows[start + k:]])
    coef, _ = _fit(y[rows], x[rows], dow[rows], weekday)
    w = np.arange(p + event_window[0], p + event_window[1] + 1)
    if not (np.isfinite(y[w]).all() and np.isfinite(x[w]).all()):
        return float("nan")
    return float((y[w] - _design(x[w], dow[w], weekday) @ coef).sum())


def _cars(y, x, idx, plan, est_window, event_window, usable, weekday) -> np.ndarray:
    cand, u = plan
    dow = idx.dayofweek.to_numpy()
    return np.array([_car_at(y, x, dow, int(p), float(q), est_window, event_window, usable, weekday)
                     for p, q in zip(cand, u, strict=True)])


def _p(true_stat: float, cars: np.ndarray) -> tuple[float, int]:
    """One-sided p = (k + 1) / (n + 1): k placebo statistics at least as large as the true one, ties included."""
    cars = cars[np.isfinite(cars)]
    return (int((cars >= true_stat).sum()) + 1) / (len(cars) + 1), len(cars)


def null_summary(cars: np.ndarray, n_days: int) -> dict[str, float]:
    """Empirical placebo CAR sd and 95th percentile, and the mean uplifts they correspond to over `n_days` days: the
    critical uplift (CAR at the 95th percentile) and the uplift detected in 80 % of cases (design §5)."""
    cars = cars[np.isfinite(cars)]
    sd, p95 = float(cars.std(ddof=1)), float(np.percentile(cars, 95))
    return {"null_sd": sd, "null_p95": p95, "mdu_pct": float(np.expm1(p95 / n_days) * 100),
            "mdu80_pct": float(np.expm1((p95 + Z80 * sd) / n_days) * 100), "n": len(cars)}


def placebo_p_value(target_log: pd.Series, index_log: pd.Series, event: pd.Timestamp, true_car: float,
                    est_window: Window, event_window: Window, exclusion_days: int = 30, n_placebo: int | None = None,
                    seed: int = 42, min_candidates: int = 100, blocked: Sequence[Interval] = (),
                    season_days: int | None = None, pre_only: bool = False, weekday: bool = True
                    ) -> tuple[float, int]:
    """Placebo p of a CAR over all admissible pseudo dates (or `n_placebo` seeded draws)."""
    _check_windows(est_window, event_window)
    y, x, idx = _pair(target_log, index_log)
    usable = _usable(y, x, idx, event, est_window, blocked)
    plan = _plan(y, x, idx, event, est_window, event_window, usable, exclusion_days, blocked, n_placebo, seed,
                 min_candidates, season_days, pre_only)
    return _p(true_car, _cars(y, x, idx, plan, est_window, event_window, usable, weekday))


def _usable(y, x, idx, event, est_window, blocked) -> int:
    ev = _pos(idx, event)
    e0, e1 = ev + est_window[0], ev + est_window[1]
    _check_range(idx, e0, e1, "the estimation window", event)
    return int((_blocked_mask(idx, blocked, e0, e1) & np.isfinite(y[e0:e1 + 1]) & np.isfinite(x[e0:e1 + 1])).sum())


# ---------------------------------------------------------------- falsification diagnostics (design §1)

def external_falsification(panel: pd.DataFrame, cast: Sequence[str], reference: Sequence[str], event: pd.Timestamp,
                           est_window: Window, event_window: Window, blocked: Sequence[Interval] = (),
                           exclusion_days: int = 30, n_placebo: int | None = None, seed: int = 42,
                           min_candidates: int = 100, how: Literal["median", "mean"] = "median",
                           weekday: bool = True) -> tuple[float, float, int]:
    """CAR of the cast's daily median attention against an index of actors outside both shows, same model, windows
    and placebo as H1. A descriptive diagnostic. Returns (CAR, p, n placebo)."""
    cast_s, ref = control_index(panel, cast, how), control_index(panel, reference, how)
    ar, _, _ = abnormal_attention(cast_s, ref, event, est_window, event_window, blocked, weekday)
    car = float(ar.sum())
    p, n = placebo_p_value(cast_s, ref, event, car, est_window, event_window, exclusion_days, n_placebo, seed,
                           min_candidates, blocked, weekday=weekday)
    return car, p, n


def falsification_test(panel: pd.DataFrame, controls: Sequence[str], event: pd.Timestamp, est_window: Window,
                       event_window: Window, blocked: Sequence[Interval] = (), exclusion_days: int = 30,
                       n_placebo: int | None = None, seed: int = 42, min_candidates: int = 100,
                       how: Literal["median", "mean"] = "median", weekday: bool = True) -> tuple[float, float, int]:
    """Leave-one-out check: median over controls of the CAR of each against the median of the OTHER controls, p on
    the same pseudo-dates for all of them. Returns (median CAR, p, n placebo)."""
    controls = list(controls)
    if len(controls) < 2:
        raise ValueError("the leave-one-out check needs at least two controls")
    _check_windows(est_window, event_window)
    series = [_pair(np.log1p(panel[c]), control_index(panel, [o for o in controls if o != c], how)) for c in controls]
    idx = series[0][2]
    ev = _pos(idx, event)
    _check_range(idx, ev + est_window[0], ev + event_window[1], "the windows", event)
    usable = min(_usable(y, x, idx, event, est_window, blocked) for y, x, _ in series)
    cars = [_real_fit(y, x, idx, ev, est_window, event_window, blocked, weekday)[0].sum() for y, x, _ in series]
    true_stat = float(np.median(cars))
    y0, x0, _ = series[0]
    plan = _plan(y0, x0, idx, event, est_window, event_window, usable, exclusion_days, blocked, n_placebo, seed,
                 min_candidates, None, False)
    per = np.array([_cars(y, x, idx, plan, est_window, event_window, usable, weekday) for y, x, _ in series])
    p, n = _p(true_stat, np.median(per, axis=0))
    return true_stat, p, n


def space_time_p(panel: pd.DataFrame, pool: Sequence[str], target_car: float, event: pd.Timestamp, est_window: Window,
                 event_window: Window, blocked: Sequence[Interval] = (), how: Literal["median", "mean"] = "median",
                 weekday: bool = True) -> tuple[float, int]:
    """Space-time placebo (design §7): the rank of the target's CAR among the CARs of the pool actors at the real date,
    each against the median of the other pool actors. p = (k + 1) / (n + 1), k actors with a CAR at least as large."""
    pool = list(pool)
    if len(pool) < 3:
        raise ValueError("the space-time placebo needs at least three pool actors")
    cars = []
    for a in pool:
        ar, _, _ = abnormal_attention(np.log1p(panel[a]), control_index(panel, [o for o in pool if o != a], how),
                                      event, est_window, event_window, blocked, weekday)
        cars.append(float(ar.sum()))
    return _p(target_car, np.array(cars))


def monthly_gap(target_log: pd.Series, index_log: pd.Series, last_day: str, blocked: Sequence[Interval] = ()
                ) -> pd.Series:
    """Mean of target minus index by calendar month up to `last_day`, blocked days left out (design §3)."""
    gap = (target_log - index_log).loc[:last_day]
    for start, end in blocked:
        gap = gap.drop(gap.loc[start:end].index)
    return gap.groupby(gap.index.to_period("M")).mean().rename("gap")


# ---------------------------------------------------------------- the event

def _screen(panel: pd.DataFrame, spec: EventSpec, controls: Sequence[str], cast: Sequence[str],
            reference: Sequence[str], event: pd.Timestamp, est_window: Window, event_window: Window
            ) -> tuple[list[str], list[str], list[str], list[str]]:
    """Omitted days (NaN) per window (design §3): a target with more than 5 % of its estimation days omitted, or any
    omitted event-window day, is dropped (EventDropped). A cast or control article above 5 % is dropped. A member of
    the reference pool is dropped on any omitted day in either window. Never replaced."""
    idx = panel.index
    ev = _pos(idx, event)
    _check_range(idx, ev + est_window[0], ev + event_window[1], "the windows", event)
    e0, e1, w0, w1 = ev + est_window[0], ev + est_window[1], ev + event_window[0], ev + event_window[1]
    keep = _blocked_mask(idx, spec.blocked, e0, e1)
    est_days, dropped = int(keep.sum()), []
    pool = set(spec.reference)

    def missing(col: str) -> tuple[int, int]:
        v = panel[col].to_numpy(float)
        return int(np.isnan(v[e0:e1 + 1][keep]).sum()), int(np.isnan(v[w0:w1 + 1]).sum())

    t_est, t_ev = missing(spec.target)
    if t_ev or t_est > MAX_MISSING_SHARE * est_days:
        raise EventDropped(f"{spec.target}: {t_est} of {est_days} estimation days and {t_ev} event-window days omitted")

    def filt(names: Sequence[str]) -> list[str]:
        out = []
        for c in names:
            m_est, m_ev = missing(c)
            if c in pool and (m_est or m_ev):
                dropped.append(f"{c} (pool member, {m_est + m_ev} omitted days)")
            elif m_est > MAX_MISSING_SHARE * est_days:
                dropped.append(f"{c} ({m_est} of {est_days} estimation days omitted)")
            else:
                out.append(c)
        return out

    return filt(controls), filt(cast), filt(reference), dropped


def run_event(panel: pd.DataFrame, spec: EventSpec, *, est_window: Window = (-150, -31),
              event_window: Window = (-3, 30), n_placebo: int | None = None, seed: int = 42, min_candidates: int = 100,
              exclusion_days: int = 30, how: Literal["median", "mean"] = "median", drop: Sequence[str] = (),
              variant: str = "primary", controls: Sequence[str] | None = None, event_date: str | None = None,
              falsify: bool = True, season_days: int | None = None, pre_only: bool = False, weekday: bool = True,
              space_time: bool = False) -> tuple[EventResult, pd.Series]:
    """`controls` replaces the spec's baseline and `event_date` its day 0, `drop` removes articles everywhere, and
    `season_days`, `pre_only` and `exclusion_days` change the placebo rule, for the checks of design §7."""
    base = [c for c in (spec.controls if controls is None else controls) if c not in drop]
    cast = [c for c in (spec.cast or spec.controls) if c not in drop]
    ref = [c for c in spec.reference if c not in drop]
    needed = [spec.target, *base, *(cast + ref if falsify and spec.falsification else [])]
    missing = [c for c in needed if c not in panel.columns]
    if missing:
        raise KeyError(f"missing in the panel: {missing}")
    day0 = event_date or spec.event_date
    detected = day0 is None
    index_log = control_index(panel, base, how)
    target_log = np.log1p(panel[spec.target]).rename(spec.target)
    if detected:
        if spec.detect_window is None:
            raise ValueError(f"{spec.name}: no event date and no detection window")
        event = detect_event_date(target_log, index_log, *spec.detect_window)
        log.warning("%s: event date %s detected from the data (exploratory, kept out of H1 and Holm)",
                    spec.name, event.date())
    else:
        event = pd.Timestamp(day0)
    base, cast, ref, dropped = _screen(panel, spec, base, cast, ref, event, est_window, event_window)
    if not base:
        raise EventDropped(f"{spec.name}: no baseline article is left after the omitted-day rule: {dropped}")
    index_log = control_index(panel, base, how)
    _check_windows(est_window, event_window)
    y, x, idx = _pair(target_log, index_log)
    ev = _pos(idx, event)
    ar, coef, sd, usable = _real_fit(y, x, idx, ev, est_window, event_window, spec.blocked, weekday)
    ar_s = pd.Series(ar, index=idx[ev + event_window[0]:ev + event_window[1] + 1], name="ar")
    car = float(ar_s.sum())
    plan = _plan(y, x, idx, event, est_window, event_window, usable, exclusion_days, spec.blocked, n_placebo, seed,
                 min_candidates, season_days, pre_only)
    cars = _cars(y, x, idx, plan, est_window, event_window, usable, weekday)
    null = null_summary(cars, len(ar_s))
    p, n = _p(car, cars)
    peak_date, peak, hl, status = half_life_smoothed(ar_s, event)
    peak_raw, _, hl_raw = half_life(ar_s.loc[event:])
    f_car = f_p = l_car = l_p = st_p = st_n = None
    if falsify and spec.falsification:
        kw = {"exclusion_days": exclusion_days, "n_placebo": n_placebo, "seed": seed, "min_candidates": min_candidates,
              "how": how, "weekday": weekday}
        if ref and cast:
            f_car, f_p, _ = external_falsification(panel, cast, ref, event, est_window, event_window, spec.blocked, **kw)
        if len(cast) >= 2:
            l_car, l_p, _ = falsification_test(panel, cast, event, est_window, event_window, spec.blocked, **kw)
    if space_time and ref:
        st_p, st_n = space_time_p(panel, ref, car, event, est_window, event_window, spec.blocked, how, weekday)
    res = EventResult(
        name=spec.name, target=spec.target, event_date=str(event.date()), event_date_detected=detected,
        beta=float(coef[1]), resid_sd=sd, car=car, car_pct_uplift=float(np.expm1(ar_s.mean()) * 100),
        peak_date=str(peak_date.date()), peak_ar=peak, half_life_days=hl, placebo_p=p, n_placebo=n,
        source_note=spec.source_note, confirmatory=spec.confirmatory and not detected,
        excess_views=excess_views(target_log, ar_s), half_life_status=status, half_life_raw_days=hl_raw,
        peak_date_raw=str(peak_raw.date()), null_sd=null["null_sd"], null_p95=null["null_p95"],
        mdu_pct=null["mdu_pct"], mdu80_pct=null["mdu80_pct"], falsification_car=f_car, falsification_p=f_p,
        loo_car=l_car, loo_p=l_p, space_time_p=st_p, n_space_time=st_n, dropped=dropped, variant=variant)
    return res, ar_s


def null_distribution(panel: pd.DataFrame, spec: EventSpec, *, est_window: Window = (-150, -31),
                      event_window: Window = (-3, 30), n_placebo: int | None = None, seed: int = 42,
                      min_candidates: int = 100, exclusion_days: int = 30, how: Literal["median", "mean"] = "median",
                      weekday: bool = True) -> dict[str, float]:
    """The placebo CAR sd, its 95th percentile and the uplifts they imply, from non-event dates only. It never looks at
    the target's CAR at the event (design §5: computed and written before the estimates)."""
    base = list(spec.controls)
    event = pd.Timestamp(spec.event_date)
    base, _, _, _ = _screen(panel, spec, base, [], [], event, est_window, event_window)
    y, x, idx = _pair(np.log1p(panel[spec.target]), control_index(panel, base, how))
    usable = _usable(y, x, idx, event, est_window, spec.blocked)
    plan = _plan(y, x, idx, event, est_window, event_window, usable, exclusion_days, spec.blocked, n_placebo, seed,
                 min_candidates, None, False)
    return null_summary(_cars(y, x, idx, plan, est_window, event_window, usable, weekday),
                        event_window[1] - event_window[0] + 1)


# ---------------------------------------------------------------- family and labels

def holm_adjust(p: Mapping[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values."""
    order = sorted(p, key=lambda k: p[k])
    m, running, out = len(order), 0.0, {}
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * p[k]))
        out[k] = running
    return out


def confirmatory_family(results: Sequence[EventResult]) -> dict[str, float]:
    """The Holm family (design §1, deviation B): primary H1 runs whose date comes from a source, not from the data.
    Falsification and sensitivity runs never enter."""
    return {r.name: r.placebo_p for r in results if r.confirmatory and r.variant == "primary"}


def label_event(placebo_p: float, holm_p: float, car: float) -> str:
    """Labels rest on H1 alone (design §6)."""
    if holm_p < ALPHA and car > 0:
        return "positive"
    if placebo_p < ALPHA:
        return "inconclusive"
    return "no detectable jump"
