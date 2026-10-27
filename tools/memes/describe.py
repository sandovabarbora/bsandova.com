"""After the results, not registered: the numbers behind the article's figures, from the panel of stage 1 and the frozen
model (imported, nothing in it changed). Writes docs/research/memes-describe.json:

  - per primary event, day by day over (-3, +30): views, the model's expected views, AR, and the 5th and 95th
    percentiles of the placebo AR and of the placebo cumulative AR at the same day offset, over the registered pseudo
    dates (the same plan, seed and equal estimation days as the test);
  - the fitted coefficients of each primary model;
  - the pre-event series of the screening figure (target and baseline, to day -4 of Kevin James) and the spikes of the
    README's confounder list, by a fixed rule.

It refuses to write unless the panel hash, each primary CAR, n and the placebo percentiles reproduce
docs/research/memes-results.json.

    uv run --no-project --with pandas==3.0.6 --with numpy==2.5.3 python -I tools/memes/describe.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cli
import config as C
import model as M

OUT = C.ROOT / "docs/research/memes-describe.json"
BAND = (5, 95)
SPIKE_RATIO = 3.0     # a day at least three times the centred 61-day median of its own article
SPIKE_GAP_DAYS = 14   # spike days closer than this belong to one episode, which keeps its largest day


def _setup(panel: pd.DataFrame, spec: M.EventSpec, second: str | None):
    """The primary run's inputs exactly as run_event builds them."""
    event = pd.Timestamp(spec.event_date)
    base, _, _, _ = M._screen(panel, spec, list(spec.controls), [], [], event, C.EST_WINDOW, C.EVENT_WINDOW)
    y, x, idx = M._pair(np.log1p(panel[spec.target]), M._baseline(panel, base, "median", second))
    ev = M._pos(idx, event)
    ar, coef, _, usable = M._real_fit(y, x, idx, ev, C.EST_WINDOW, C.EVENT_WINDOW, spec.blocked, True)
    plan = M._plan(y, x, idx, event, C.EST_WINDOW, C.EVENT_WINDOW, usable, C.EXCLUSION_DAYS,
                   tuple(spec.blocked) + tuple(spec.placebo_blocked), C.N_PLACEBO, C.SEED, C.MIN_CANDIDATES, None, False)
    return y, x, idx, ev, ar, coef, usable, plan


def _ar_at(y, x, dow, p, u, usable) -> np.ndarray:
    """M._car_at, returning the daily AR instead of its sum."""
    seg = np.arange(p + C.EST_WINDOW[0], p + C.EST_WINDOW[1] + 1)
    rows = seg[M._fin(y[seg], x[seg])]
    k = len(rows) - usable
    if k > 0:
        start = int(u * (len(rows) - k + 1))
        rows = np.concatenate([rows[:start], rows[start + k:]])
    coef, _ = M._fit(y[rows], x[rows], dow[rows], True)
    w = np.arange(p + C.EVENT_WINDOW[0], p + C.EVENT_WINDOW[1] + 1)
    if not M._fin(y[w], x[w]).all():
        return np.full(len(w), np.nan)
    return y[w] - M._design(x[w], dow[w], True) @ coef


def event_block(panel: pd.DataFrame, spec: M.EventSpec, second: str | None, result: dict) -> dict:
    y, x, idx, ev, ar, coef, usable, plan = _setup(panel, spec, second)
    dow = idx.day_of_week.to_numpy()
    placebo = np.array([_ar_at(y, x, dow, int(p), float(u), usable) for p, u in zip(*plan, strict=True)])
    placebo = placebo[np.isfinite(placebo).all(axis=1)]
    cars = M._cars(y, x, idx, plan, C.EST_WINDOW, C.EVENT_WINDOW, usable, True)
    assert np.allclose(np.sort(placebo.sum(axis=1)), np.sort(cars[np.isfinite(cars)]), atol=1e-9)
    assert abs(float(ar.sum()) - result["car"]) < 1e-9 and len(placebo) == result["n_placebo"]
    null = M.null_summary(cars, C.EVENT_WINDOW)
    assert abs(null["null_p95"] - result["null_p95"]) < 1e-9 and abs(null["null_p975"] - result["null_p975"]) < 1e-9
    cum = np.cumsum(placebo, axis=1)
    lo, hi = np.percentile(placebo, BAND, axis=0)
    clo, chi = np.percentile(cum, BAND, axis=0)
    w = np.arange(ev + C.EVENT_WINDOW[0], ev + C.EVENT_WINDOW[1] + 1)
    views = panel[spec.target].to_numpy(float)[w]
    expected = np.expm1(y[w] - ar)
    days = [{"day": int(t), "date": str(idx[i].date()), "views": int(v), "expected": round(float(e), 1),
             "ar": float(a), "band": [float(b0), float(b1)], "car": float(c), "car_band": [float(c0), float(c1)]}
            for t, i, v, e, a, b0, b1, c, c0, c1 in zip(range(C.EVENT_WINDOW[0], C.EVENT_WINDOW[1] + 1), w, views,
                                                         expected, ar, lo, hi, np.cumsum(ar), clo, chi, strict=True)]
    names = ["alpha", "beta_baseline"] + ([f"beta_{second}"] if second else [])
    return {"target": spec.target, "event_date": spec.event_date, "second_regressor": second,
            "coef": dict(zip(names, map(float, coef[:len(names)]), strict=True)), "estimation_days": usable,
            "n_placebo": len(placebo), "band_percentiles": list(BAND), "days": days}


def screening_block(panel: pd.DataFrame) -> dict:
    """The pre-event series to day -4 of Kevin James (the cutoff of the registered screening figure), TikTok block
    blank, and the spike episodes of every article of that figure."""
    cutoff = cli.pre_event_cutoff()
    kept, _ = M.pool_screen(panel, C.REFERENCE_POOL)
    series = {
        "Eric_Stonestreet": np.log1p(panel["Eric_Stonestreet"]),
        "median of the Modern Family cast": M.control_index(panel, C.MF_CAST),
        "Kevin_James": np.log1p(panel["Kevin_James"]),
        "median of the reference pool": M.control_index(panel, kept),
        "Victor_Williams": np.log1p(panel["Victor_Williams"]),
    }
    out = {}
    for name, s in series.items():
        s = s.loc[C.START:cutoff].copy()
        s.loc[C.TIKTOK_BLOCK[0]:C.TIKTOK_BLOCK[1]] = np.nan
        out[name] = [[str(d.date()), None if np.isnan(v) else round(float(v), 4)] for d, v in s.items()]
    spikes = {}
    for a in [C.STONESTREET.target, *C.MF_CAST, C.KEVIN_JAMES.target, *C.KOQ_CAST]:
        s = np.log1p(panel[a]).loc[C.START:cutoff].copy()
        s.loc[C.TIKTOK_BLOCK[0]:C.TIKTOK_BLOCK[1]] = np.nan
        base = s.rolling(61, center=True, min_periods=20).median()
        over = (s - base)[(s - base) > np.log(SPIKE_RATIO)].sort_values(ascending=False)
        eps: list[pd.Timestamp] = []
        for d in over.index:
            if all(abs((d - e).days) >= SPIKE_GAP_DAYS for e in eps):
                eps.append(d)
        spikes[a] = [{"date": str(d.date()), "views": int(panel[a][d]), "median_61d": round(float(np.expm1(base[d]))),
                      "ratio": round(float(np.exp(over[d])), 1)} for d in sorted(eps)]
    windows = {}
    for spec in C.EVENTS:
        e = pd.Timestamp(spec.event_date)
        windows[spec.name] = [str((e + pd.Timedelta(days=C.EST_WINDOW[0])).date()),
                              str((e + pd.Timedelta(days=C.EST_WINDOW[1])).date())]
    return {"cutoff": cutoff, "blank": list(C.TIKTOK_BLOCK), "estimation_windows": windows, "series": out,
            "spike_rule": f"a day at least {SPIKE_RATIO:g} times the centred 61-day median of its article; days under "
                          f"{SPIKE_GAP_DAYS} apart are one episode, dated by its largest day",
            "spikes": spikes}


def main() -> None:
    res = json.loads(C.RESULTS.read_text(encoding="utf-8"))
    digest = hashlib.sha256(C.RAW.read_bytes()).hexdigest()
    if digest != res["meta"]["null"]["panel_sha256"]:
        sys.exit("refusing: the panel is not the one of stage 1")
    panel = pd.read_csv(C.RAW, index_col=0, parse_dates=True)
    events = {}
    for spec in C.EVENTS:
        result = next(e for e in res["events"] if e["name"] == spec.name)
        events[spec.name] = event_block(panel, spec, result["second_regressor"], result)
    payload = {"note": "after the results, not registered: descriptive numbers for the article's figures",
               "panel_sha256": digest, "events": events, "screening": screening_block(panel)}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({k: {"coef": v["coef"], "n": v["n_placebo"]} for k, v in events.items()}, indent=1))


if __name__ == "__main__":
    main()
