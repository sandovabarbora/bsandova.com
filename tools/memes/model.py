"""Pure logic of the meme event study (docs/research/memes-design.md §4): market model on pageview "attention
returns" (MacKinlay 1997, J. Economic Literature 35(1)), abnormal attention, CAR, half-life, the placebo test, the
leave-one-out falsification, Holm adjustment and labels. No I/O: everything takes frames and returns numbers.

Positions are day offsets on a gap-free daily index, so a placebo refit is a few numpy operations.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

Window = tuple[int, int]
Interval = tuple[str, str]
MIN_EST_DAYS = 30
ALPHA = 0.05
LABELS = ("positive", "no detectable jump", "inconclusive")


@dataclass(frozen=True)
class EventSpec:
    name: str
    target: str
    controls: tuple[str, ...]
    event_date: str | None
    source_note: str
    confirmatory: bool = False
    falsification: bool = False
    # whether a significant falsification test turns a positive H1 into inconclusive (design §6)
    gate_on_falsification: bool = False
    # actors outside both shows, for the external falsification (design §1)
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
    falsification_car: float | None = None
    falsification_p: float | None = None
    loo_car: float | None = None
    loo_p: float | None = None
    holm_p: float | None = None
    label: str | None = None
    variant: str = "primary"


# ---------------------------------------------------------------- inputs

def control_index(panel: pd.DataFrame, controls: Sequence[str], how: Literal["median", "mean"] = "median") -> pd.Series:
    """Daily median (or mean, for a check) of log1p views of the control articles; median because actors have news."""
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
        raise ValueError("series must be a gap-free daily index; reindex and fill the days the API omits first")
    return idx[0]


def _pair(target_log: pd.Series, index_log: pd.Series) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    if not target_log.index.equals(index_log.index):
        raise ValueError("target and control index must share the same dates")
    _daily_origin(index_log.index)
    y, x = target_log.to_numpy(float), index_log.to_numpy(float)
    if np.isnan(y).any() or np.isnan(x).any():
        raise ValueError("missing values in the target or the control index")
    return y, x, index_log.index


def _pos(idx: pd.DatetimeIndex, date: pd.Timestamp, offset: int = 0) -> int:
    return (pd.Timestamp(date) - idx[0]).days + offset


def _check_range(idx: pd.DatetimeIndex, lo: int, hi: int, what: str, event: pd.Timestamp) -> None:
    if lo < 0 or hi > len(idx) - 1:
        need = (idx[0] + pd.Timedelta(days=lo)).date(), (idx[0] + pd.Timedelta(days=hi)).date()
        raise ValueError(f"{what} for event {pd.Timestamp(event).date()} needs {need[0]}..{need[1]}, "
                         f"but the data cover {idx[0].date()}..{idx[-1].date()}")


def _fit(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float]:
    n = len(y)
    if n < MIN_EST_DAYS:
        raise ValueError(f"estimation window has {n} usable days, at least {MIN_EST_DAYS} are needed")
    xm = x.mean()
    sxx = float(((x - xm) ** 2).sum())
    if sxx < 1e-12:
        raise ValueError("the control index is constant in the estimation window, the market model is not identified")
    b = float(((x - xm) * (y - y.mean())).sum() / sxx)
    a = float(y.mean() - b * xm)
    resid = y - (a + b * x)
    return a, b, float(np.sqrt((resid ** 2).sum() / (n - 2)))


def fit_market_model(y: pd.Series, x: pd.Series) -> tuple[float, float, float]:
    """OLS of y on x: (alpha, beta, residual sd)."""
    both = pd.concat([y, x], axis=1, join="inner").dropna()
    return _fit(both.iloc[:, 0].to_numpy(float), both.iloc[:, 1].to_numpy(float))


# ---------------------------------------------------------------- abnormal attention

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


def abnormal_attention(target_log: pd.Series, index_log: pd.Series, event: pd.Timestamp, est_window: Window,
                       event_window: Window, blocked: Sequence[Interval] = ()
                       ) -> tuple[pd.Series, float, float]:
    """AR_t = y_t - (a + b * index_t) over the event window, with the market model fitted on the estimation window
    minus `blocked` days. Returns (AR by date, beta, residual sd)."""
    _check_windows(est_window, event_window)
    y, x, idx = _pair(target_log, index_log)
    ev = _pos(idx, event)
    _check_range(idx, ev + est_window[0], ev + event_window[1], "the windows", event)
    e0, e1 = ev + est_window[0], ev + est_window[1]
    keep = _blocked_mask(idx, blocked, e0, e1)
    a, b, sd = _fit(y[e0:e1 + 1][keep], x[e0:e1 + 1][keep])
    w0, w1 = ev + event_window[0], ev + event_window[1]
    ar = pd.Series(y[w0:w1 + 1] - (a + b * x[w0:w1 + 1]), index=idx[w0:w1 + 1], name="ar")
    return ar, b, sd


def half_life(ar: pd.Series) -> tuple[pd.Timestamp, float, float | None]:
    """(peak date, peak AR, days from the peak to the first day with AR below half the peak). None if the peak is not
    positive or AR never falls below half of it within the series."""
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


def detect_event_date(target_log: pd.Series, index_log: pd.Series, search_start: str, search_end: str) -> pd.Timestamp:
    """Day of the largest one-day rise of target minus index inside the search range (exploratory, design §1)."""
    y, x, idx = _pair(target_log, index_log)
    jump = pd.Series(y - x, index=idx).diff().loc[search_start:search_end].dropna()
    if jump.empty:
        raise ValueError(f"search range {search_start}..{search_end} lies outside the data {idx[0].date()}..{idx[-1].date()}")
    return jump.idxmax()


# ---------------------------------------------------------------- placebo test

def _car_at(y: np.ndarray, x: np.ndarray, p: int, est_window: Window, event_window: Window) -> float:
    e0, e1 = p + est_window[0], p + est_window[1]
    a, b, _ = _fit(y[e0:e1 + 1], x[e0:e1 + 1])
    w0, w1 = p + event_window[0], p + event_window[1]
    return float((y[w0:w1 + 1] - (a + b * x[w0:w1 + 1])).sum())


def placebo_candidates(idx: pd.DatetimeIndex, event: pd.Timestamp, est_window: Window, event_window: Window,
                       exclusion_days: int = 30, blocked: Sequence[Interval] = ()) -> np.ndarray:
    """Positions of admissible pseudo event dates. The span of a pseudo event (its estimation plus event window) must
    lie fully in the data, stay at least `exclusion_days` days away from the real event window, and not touch a
    blocked interval at all (design §4, deviation C)."""
    _daily_origin(idx)
    n, ev = len(idx), _pos(idx, event)
    lo, hi = est_window[0], event_window[1]
    p = np.arange(-lo, n - hi)
    real_lo, real_hi = ev + event_window[0], ev + event_window[1]
    keep = (p + hi < real_lo - exclusion_days) | (p + lo > real_hi + exclusion_days)
    for start, end in blocked:
        b0, b1 = _pos(idx, pd.Timestamp(start)), _pos(idx, pd.Timestamp(end))
        keep &= (p + hi < b0) | (p + lo > b1)
    return p[keep]


def placebo_p_from_stat(stat: Callable[[int], float], true_stat: float, candidates: np.ndarray,
                        n_placebo: int = 300, seed: int = 42, min_candidates: int = 100) -> tuple[float, int]:
    """One-sided p = (k + 1) / (n + 1), k = placebo statistics at least as large as the true one."""
    if len(candidates) < min_candidates:
        raise ValueError(f"only {len(candidates)} admissible placebo dates remain, at least {min_candidates} are needed: "
                         "use a longer data range (a one-year range gave about 30 % false positives in the prototype)")
    n = min(n_placebo, len(candidates))
    chosen = np.random.default_rng(seed).choice(candidates, size=n, replace=False)
    k = sum(stat(int(p)) >= true_stat for p in chosen)
    return (k + 1) / (n + 1), n


def placebo_p_value(target_log: pd.Series, index_log: pd.Series, event: pd.Timestamp, true_car: float,
                    est_window: Window, event_window: Window, exclusion_days: int = 30, n_placebo: int = 300,
                    seed: int = 42, min_candidates: int = 100, blocked: Sequence[Interval] = ()
                    ) -> tuple[float, int]:
    _check_windows(est_window, event_window)
    y, x, idx = _pair(target_log, index_log)
    cand = placebo_candidates(idx, event, est_window, event_window, exclusion_days, blocked)
    return placebo_p_from_stat(lambda p: _car_at(y, x, p, est_window, event_window), true_car, cand,
                               n_placebo, seed, min_candidates)


# ---------------------------------------------------------------- falsification (deviation A)

def falsification_test(panel: pd.DataFrame, controls: Sequence[str], event: pd.Timestamp, est_window: Window,
                       event_window: Window, blocked: Sequence[Interval] = (), exclusion_days: int = 30,
                       n_placebo: int = 300, seed: int = 42, min_candidates: int = 100,
                       how: Literal["median", "mean"] = "median") -> tuple[float, float, int]:
    """Median over controls of the CAR of each control against the index of the OTHER controls (leave-one-out: against
    their own index the median control AR is about zero by construction). Placebo p on the same dates as the target's.
    Returns (median CAR, p, n placebo)."""
    controls = list(controls)
    if len(controls) < 2:
        raise ValueError("the leave-one-out falsification needs at least two controls")
    _check_windows(est_window, event_window)
    series = []
    for c in controls:
        others = [o for o in controls if o != c]
        series.append(_pair(np.log1p(panel[c]), control_index(panel, others, how)))
    idx = series[0][2]
    ev = _pos(idx, event)
    _check_range(idx, ev + est_window[0], ev + event_window[1], "the windows", event)
    cars = []
    for y, x, _ in series:
        e0, e1 = ev + est_window[0], ev + est_window[1]
        keep = _blocked_mask(idx, blocked, e0, e1)
        a, b, _sd = _fit(y[e0:e1 + 1][keep], x[e0:e1 + 1][keep])
        w0, w1 = ev + event_window[0], ev + event_window[1]
        cars.append(float((y[w0:w1 + 1] - (a + b * x[w0:w1 + 1])).sum()))
    true_stat = float(np.median(cars))
    cand = placebo_candidates(idx, event, est_window, event_window, exclusion_days, blocked)
    p, n = placebo_p_from_stat(
        lambda q: float(np.median([_car_at(y, x, q, est_window, event_window) for y, x, _ in series])),
        true_stat, cand, n_placebo, seed, min_candidates)
    return true_stat, p, n


def external_falsification(panel: pd.DataFrame, controls: Sequence[str], reference: Sequence[str], event: pd.Timestamp,
                           est_window: Window, event_window: Window, blocked: Sequence[Interval] = (),
                           exclusion_days: int = 30, n_placebo: int = 300, seed: int = 42, min_candidates: int = 100,
                           how: Literal["median", "mean"] = "median") -> tuple[float, float, int]:
    """CAR of the cast's daily median attention against an index of actors outside both shows, same model, windows
    and placebo as H1 (design §1). Returns (CAR, p, n placebo)."""
    cast = control_index(panel, controls, how)
    ref = control_index(panel, reference, how)
    ar, _, _ = abnormal_attention(cast, ref, event, est_window, event_window, blocked)
    car = float(ar.sum())
    p, n = placebo_p_value(cast, ref, event, car, est_window, event_window, exclusion_days, n_placebo, seed,
                           min_candidates, blocked)
    return car, p, n


# ---------------------------------------------------------------- the event

def run_event(panel: pd.DataFrame, spec: EventSpec, *, est_window: Window = (-150, -31),
              event_window: Window = (-3, 30), n_placebo: int = 300, seed: int = 42, min_candidates: int = 100,
              exclusion_days: int = 30, how: Literal["median", "mean"] = "median", drop: Sequence[str] = (),
              variant: str = "primary", controls: Sequence[str] | None = None, event_date: str | None = None,
              falsify: bool = True) -> tuple[EventResult, pd.Series]:
    """`controls` replaces the spec's controls and `event_date` its day 0, for the sensitivity runs (design §7)."""
    controls = [c for c in (spec.controls if controls is None else controls) if c not in drop]
    needed = [spec.target, *controls, *(spec.reference if falsify and spec.falsification else ())]
    missing = [c for c in needed if c not in panel.columns]
    if missing:
        raise KeyError(f"missing in the panel: {missing}")
    index_log = control_index(panel, controls, how)
    target_log = np.log1p(panel[spec.target]).rename(spec.target)
    day0 = event_date or spec.event_date
    detected = day0 is None
    if detected:
        if spec.detect_window is None:
            raise ValueError(f"{spec.name}: no event date and no detection window")
        event = detect_event_date(target_log, index_log, *spec.detect_window)
        log.warning("%s: event date %s detected from the data (exploratory, kept out of H1 and Holm)",
                    spec.name, event.date())
    else:
        event = pd.Timestamp(day0)
    ar, beta, sd = abnormal_attention(target_log, index_log, event, est_window, event_window, spec.blocked)
    car = float(ar.sum())
    peak_date, peak, hl = half_life(ar.loc[event:])
    p, n = placebo_p_value(target_log, index_log, event, car, est_window, event_window, exclusion_days, n_placebo,
                           seed, min_candidates, spec.blocked)
    f_car = f_p = l_car = l_p = None
    if falsify and spec.falsification:
        if spec.reference:
            f_car, f_p, _ = external_falsification(panel, controls, spec.reference, event, est_window, event_window,
                                                   spec.blocked, exclusion_days, n_placebo, seed, min_candidates, how)
        if len(controls) >= 2:
            l_car, l_p, _ = falsification_test(panel, controls, event, est_window, event_window, spec.blocked,
                                               exclusion_days, n_placebo, seed, min_candidates, how)
    res = EventResult(
        name=spec.name, target=spec.target, event_date=str(event.date()), event_date_detected=detected, beta=beta,
        resid_sd=sd, car=car, car_pct_uplift=float(np.expm1(ar.mean()) * 100), peak_date=str(peak_date.date()),
        peak_ar=peak, half_life_days=hl, placebo_p=p, n_placebo=n, source_note=spec.source_note,
        confirmatory=spec.confirmatory and not detected, falsification_car=f_car, falsification_p=f_p, loo_car=l_car, loo_p=l_p, variant=variant)
    return res, ar


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


def label_event(placebo_p: float, holm_p: float, car: float, falsification_p: float | None = None,
                use_falsification: bool = False) -> str:
    if holm_p < ALPHA and car > 0:
        if use_falsification and falsification_p is not None and falsification_p < ALPHA:
            return "inconclusive"
        return "positive"
    if placebo_p < ALPHA:
        return "inconclusive"
    return "no detectable jump"
